#!/usr/bin/env python3
"""Build a project-local metadata-only MTMD op tracer; never edits llama.cpp."""
from __future__ import annotations
import hashlib, json, os, shlex, subprocess, tempfile
from pathlib import Path

ROOT = Path(os.environ.get("PHASEMAP_OPTRACE_SOURCE_ROOT", Path(__file__).resolve().parents[1]))
RUNTIME = ROOT / "runtime/llama.cpp"
COMMIT = "7ab4ee7baad2d920464cbacfad4f4b07cf111fd2"
SRC = RUNTIME / "tools/mtmd/mtmd-cli.cpp"
SRC_SHA = "92694f41553d76165428deddc11e5100da9bce79f66fd4918b4972bb9e6959bb"
OUT = Path(os.environ.get("PHASEMAP_OPTRACE_BUILD_DIR", Path(tempfile.gettempdir()) / "phasemap-vlm-optrace-build"))

TRACE = r'''
#include <chrono>
#include <unordered_map>
#include <cstdlib>
#include <fstream>
#include <sstream>
struct PMTrace { std::string phase; uint64_t group = 0; std::unordered_map<const ggml_tensor *, std::chrono::steady_clock::time_point> starts; std::vector<std::string> rows; };
static PMTrace pm_text{"text_prefill", 0, {}, {}}, pm_vision{"vision_encoder", 0, {}, {}};
static std::unordered_map<const ggml_backend_buffer *, uint64_t> pm_buffer_ids;
static uint64_t pm_next_buffer_id = 0;
static uint64_t pm_next_vision_group = 0;
static bool pm_enabled() { const char * p = std::getenv("PHASEMAP_OPTRACE_PATH"); return p && *p; }
static void pm_quote(std::ostream & o, const std::string & s) { o << '"'; for (unsigned char c : s) { if (c == '"' || c == '\\') o << '\\' << c; else if (c == '\n') o << "\\n"; else if (c == '\r') o << "\\r"; else if (c == '\t') o << "\\t"; else if (c >= 0x20) o << (char)c; } o << '"'; }
static void pm_request_fields(std::ostream & o) {
    const char * request_id = std::getenv("PHASEMAP_REQUEST_ID");
    const char * image_sha = std::getenv("PHASEMAP_IMAGE_SHA256");
    if (request_id && *request_id) { o << ",\"request_id\":"; pm_quote(o, request_id); }
    if (image_sha && *image_sha) { o << ",\"image_sha256\":"; pm_quote(o, image_sha); }
}
static void pm_storage(std::ostream & o, const ggml_tensor * t) {
    const char * enabled = std::getenv("PHASEMAP_ALLOCATOR_METADATA");
    if (!enabled || !*enabled || !t->buffer || !t->data) { o << ",\"storage\":{\"available\":false}"; return; }
    ggml_backend_buffer_t buffer = t->buffer;
    auto result = pm_buffer_ids.emplace(buffer, pm_next_buffer_id);
    if (result.second) ++pm_next_buffer_id;
    void * base = ggml_backend_buffer_get_base(buffer);
    const size_t buffer_size = ggml_backend_buffer_get_size(buffer);
    const uintptr_t data_addr = (uintptr_t)t->data;
    const uintptr_t base_addr = (uintptr_t)base;
    const bool offset_valid = base && data_addr >= base_addr && data_addr - base_addr <= buffer_size;
    o << ",\"storage\":{\"available\":true,\"buffer_id\":" << result.first->second << ",\"buffer_name\":";
    pm_quote(o, ggml_backend_buffer_name(buffer));
    o << ",\"usage\":" << (int)ggml_backend_buffer_get_usage(buffer)
      << ",\"is_host\":" << (ggml_backend_buffer_is_host(buffer) ? "true" : "false")
      << ",\"buffer_size_bytes\":" << buffer_size
      << ",\"alignment_bytes\":" << ggml_backend_buffer_get_alignment(buffer)
      << ",\"alloc_size_bytes\":" << ggml_backend_buffer_get_alloc_size(buffer, t)
      << ",\"base_available\":" << (base ? "true" : "false")
      << ",\"offset_valid\":" << (offset_valid ? "true" : "false")
      << ",\"offset_bytes\":";
    if (offset_valid) o << (data_addr - base_addr); else o << "null";
    o << '}';
}
static void pm_tensor(std::ostream & o, const ggml_tensor * t) {
    o << "{\"id\":" << (uintptr_t)t << ",\"name\":"; pm_quote(o, t->name);
    o << ",\"dtype\":"; pm_quote(o, ggml_type_name(t->type));
    o << ",\"ne\":[" << t->ne[0] << ',' << t->ne[1] << ',' << t->ne[2] << ',' << t->ne[3]
      << "],\"nb\":[" << t->nb[0] << ',' << t->nb[1] << ',' << t->nb[2] << ',' << t->nb[3]
      << "],\"bytes\":" << ggml_nbytes(t) << ",\"view_src_id\":";
    if (t->view_src) o << (uintptr_t)t->view_src; else o << "null";
    o << ",\"view_offs_bytes\":" << t->view_offs << ",\"flags\":" << t->flags;
    pm_storage(o, t);
    o << '}';
}
static bool pm_layer_boundary(const PMTrace * tr, const ggml_tensor * t) {
    const std::string name = t->name;
    if (tr->phase == "vision_encoder") return name.rfind("layer_out-", 0) == 0;
    return name.rfind("ffn_out-", 0) == 0;
}
static bool pm_target_boundary(const PMTrace * tr, const ggml_tensor * t) {
    const char * phase_env = std::getenv("PHASEMAP_TARGET_PHASE");
    const std::string target_phase = phase_env && *phase_env ? phase_env : "vision_encoder";
    if (tr->phase != target_phase) return false;
    const char * target_env = std::getenv("PHASEMAP_TARGET_OP_NAME");
    const char * predecessor_env = std::getenv("PHASEMAP_TARGET_PREDECESSOR_NAME");
    const std::string target = target_env && *target_env ? target_env : "ffn_up-0";
    const std::string predecessor = predecessor_env && *predecessor_env ? predecessor_env : "ffn_inp_normed-0";
    const std::string name = t->name;
    return name == predecessor || (name == target && t->op == GGML_OP_MUL_MAT);
}
static bool pm_eval(ggml_tensor * t, bool ask, void * p) {
    auto * tr = static_cast<PMTrace *>(p);
    if (!ask) {
        auto it = tr->starts.find(t);
        if (it == tr->starts.end()) return true;
        auto ns = std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now() - it->second).count();
        std::ostringstream timed; timed << "{\"record\":\"layer_segment\",\"phase\":"; pm_quote(timed, tr->phase);
        const char * target_env = std::getenv("PHASEMAP_TARGET_OP_NAME");
        const char * predecessor_env = std::getenv("PHASEMAP_TARGET_PREDECESSOR_NAME");
        const std::string target = target_env && *target_env ? target_env : "ffn_up-0";
        const std::string predecessor = predecessor_env && *predecessor_env ? predecessor_env : "ffn_inp_normed-0";
        const char * phase_env = std::getenv("PHASEMAP_TARGET_PHASE");
        const std::string target_phase = phase_env && *phase_env ? phase_env : "vision_encoder";
        if (tr->phase == target_phase && std::string(t->name) == target) timed << ",\"kind\":\"isolated_target_node\"";
        else if (tr->phase == target_phase && std::string(t->name) == predecessor) timed << ",\"kind\":\"target_prelude_boundary\"";
        else timed << ",\"kind\":\"layer_boundary\"";
        timed << ",\"elapsed_ns\":" << ns << ",\"output_name\":"; pm_quote(timed, t->name);
        timed << ",\"op\":"; pm_quote(timed, ggml_op_name(t->op)); timed << '}';
        tr->rows.push_back(timed.str()); tr->starts.erase(it); return true;
    }
    std::ostringstream o; o << "{\"record\":\"node\""; pm_request_fields(o); o << ",\"phase\":"; pm_quote(o, tr->phase);
    o << ",\"group\":" << tr->group << ",\"op\":"; pm_quote(o, ggml_op_name(t->op)); o << ",\"output\":"; pm_tensor(o, t);
    o << ",\"inputs\":["; bool comma = false; for (int i = 0; i < GGML_MAX_SRC; ++i) if (t->src[i]) { if (comma) o << ','; pm_tensor(o, t->src[i]); comma = true; }
    o << "]}"; tr->rows.push_back(o.str());
    if (std::getenv("PHASEMAP_LAYER_TIMING") && pm_layer_boundary(tr, t)) {
        tr->starts[t] = std::chrono::steady_clock::now();
        return true;
    }
    if (std::getenv("PHASEMAP_TARGET_OP_TIMING") && pm_target_boundary(tr, t)) {
        tr->starts[t] = std::chrono::steady_clock::now();
        return true;
    }
    return false; // Metadata-only mode preserves graph batching; layer mode synchronizes only at explicit layer outputs.
}
static void pm_flush() {
    const char * path = std::getenv("PHASEMAP_OPTRACE_PATH"); if (!path || !*path) return;
    std::ofstream o(path, std::ios::trunc); if (!o) return;
    for (const auto * tr : {&pm_vision, &pm_text}) for (const auto & row : tr->rows) o << row << '\n';
}
'''

def sha(p: Path) -> str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20), b''): h.update(b)
    return h.hexdigest()

def replace(source: str, old: str, new: str, label: str) -> str:
    n=source.count(old)
    if n != 1: raise RuntimeError(f"{label}: expected one anchor, found {n}")
    return source.replace(old,new,1)

def main() -> int:
    commit=subprocess.check_output(['git','-C',str(RUNTIME),'rev-parse','HEAD'],text=True).strip()
    if commit != COMMIT: raise SystemExit(f"pinned runtime commit mismatch: {commit}")
    if sha(SRC) != SRC_SHA: raise SystemExit("upstream MTMD CLI source hash changed; refusing to patch")
    text=SRC.read_text(encoding='utf-8')
    text=replace(text,'#include <clocale>\n','#include <clocale>\n'+TRACE+'\n','trace support')
    text=replace(text,
        '        if (std::getenv("MTMD_DEBUG_GRAPH") != nullptr) {\n            mparams.cb_eval_user_data = &cb_data;\n            mparams.cb_eval = common_debug_cb_eval;\n        }\n',
        '        if (pm_enabled()) {\n            mparams.cb_eval_user_data = &pm_vision;\n            mparams.cb_eval = pm_eval;\n        } else if (std::getenv("MTMD_DEBUG_GRAPH") != nullptr) {\n            mparams.cb_eval_user_data = &cb_data;\n            mparams.cb_eval = common_debug_cb_eval;\n        }\n','vision callback')
    text=replace(text,
        '        if (chunk_type == MTMD_INPUT_CHUNK_TYPE_TEXT) {\n            // decode text chunk\n',
        '        if (chunk_type == MTMD_INPUT_CHUNK_TYPE_TEXT) {\n            pm_text.phase = "text_prefill";\n            // decode text chunk\n','text prefill label')
    text=replace(text,
        '        } else {\n            // media chunk: try to get embd from existing batch, or create a new batch\n',
        '        } else {\n            pm_text.phase = "image_embedding_prefill";\n            // media chunk: try to get embd from existing batch, or create a new batch\n','image embedding label')
    text=replace(text,
        '                res = mtmd_batch_encode(ctx.mbatch.get());\n',
        '                pm_vision.group = pm_next_vision_group++;\n'
        '                std::ostringstream media_row; media_row << "{\\\"record\\\":\\\"media_batch\\\""; pm_request_fields(media_row);\n'
        '                media_row << ",\\\"group\\\":" << pm_vision.group << ",\\\"chunk_index\\\":" << i << ",\\\"chunks_added\\\":" << n_added << ",\\\"chunks_total\\\":" << n_chunks << "}";\n'
        '                pm_vision.rows.push_back(media_row.str());\n'
        '                res = mtmd_batch_encode(ctx.mbatch.get());\n','media batch identity')
    text=replace(text,
        '        llama_token token_id = common_sampler_sample(ctx.smpl, ctx.lctx, -1);\n',
        '        llama_token token_id = common_sampler_sample(ctx.smpl, ctx.lctx, -1);\n','sampling anchor')
    text=replace(text,
        '        if (llama_decode(ctx.lctx, ctx.batch)) {\n',
        '        pm_text.phase = "token_decode";\n        ++pm_text.group;\n        if (llama_decode(ctx.lctx, ctx.batch)) {\n','decode label')
    text=replace(text,
        '    mtmd_helper_log_set(common_log_default_callback, nullptr);\n',
        '    mtmd_helper_log_set(common_log_default_callback, nullptr);\n    if (pm_enabled()) { params.cb_eval = pm_eval; params.cb_eval_user_data = &pm_text; std::atexit(pm_flush); }\n','language callback')
    OUT.mkdir(parents=True,exist_ok=True)
    generated=OUT/'mtmd-cli-optrace.cpp'; generated.write_text(text,encoding='utf-8')
    db=json.loads((RUNTIME/'build/compile_commands.json').read_text(encoding='utf-8'))
    entry=next(x for x in db if x['file'].endswith('/tools/mtmd/mtmd-cli.cpp'))
    cmd=shlex.split(entry['command']); obj=OUT/'mtmd-cli-optrace.o'
    for i,a in enumerate(cmd):
        if a==entry['file']: cmd[i]=str(generated)
        if a=='-o': cmd[i+1]=str(obj)
    subprocess.run(cmd,cwd=entry['directory'],check=True)
    build=RUNTIME/'build'; binary=OUT/'llama-mtmd-optrace'
    libs=[build/'bin/libllama-common.so.0.4.1',build/'bin/libmtmd.so.0.4.1',build/'common/libllama-common-base.a',build/'bin/libllama.so.0.4.1',build/'bin/libggml.so.0.24.0',build/'bin/libggml-cpu.so.0.24.0',build/'bin/libggml-base.so.0.24.0']
    missing=[str(p) for p in libs if not p.is_file()]
    if missing: raise SystemExit('missing pinned runtime libraries: '+', '.join(missing))
    subprocess.run(['/usr/bin/c++','-O3','-DNDEBUG','-o',str(binary),str(obj),f"-Wl,-rpath,{build/'bin'}",*map(str,libs)],cwd=build,check=True)
    report={'binary':str(binary),'binary_sha256':sha(binary),'generated_source_sha256':sha(generated),'upstream_source':str(SRC.relative_to(ROOT)),'upstream_source_sha256':SRC_SHA,'runtime_commit':commit,'linked_libraries':[{'name':p.name,'sha256':sha(p)} for p in libs],'build_method':'B03 isolated source copy and metadata callback; primary/upstream files unchanged; compile flags from pinned compile_commands.json; existing pinned CPU libraries; output directed to task-specific temporary directory','media_group_semantics':'media_batch ordinal advances once per mtmd_batch_encode call; it identifies the encoded media batch/chunk group, not an individual internal image crop or patch','callback_semantics':'ggml eval callback records logical graph-node/tensor metadata during scheduled graph compute after backend splitting; it does not record supports_op eligibility or final backend placement','layer_timing_mode':'optional PHASEMAP_LAYER_TIMING env var measures graph segments ending at layer_out-N or ffn_out-N; introduces one scheduler sync per reported layer and is not per-op timing','target_op_timing_mode':'optional PHASEMAP_TARGET_OP_TIMING env var; phase configurable with PHASEMAP_TARGET_PHASE, target and immediately preceding sentinel names configurable with PHASEMAP_TARGET_OP_NAME and PHASEMAP_TARGET_PREDECESSOR_NAME; bracketed target MUL_MAT scheduler graph view includes dispatch/synchronization overhead','allocator_metadata_mode':'optional PHASEMAP_ALLOCATOR_METADATA env var records opaque buffer ordinal, backend buffer name/usage/capacity, alignment, per-tensor allocator allocation size, data offset relative to buffer base when available, and view source/offset/flags; reads metadata only, never tensor payload; offset is null for buffers without a usable base'}
    (OUT/'build.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2)); return 0

if __name__=='__main__': raise SystemExit(main())
