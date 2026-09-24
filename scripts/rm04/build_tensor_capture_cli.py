#!/usr/bin/env python3
"""Build a project-local metadata-only MTMD op tracer; never edits llama.cpp."""
from __future__ import annotations
import hashlib, json, shlex, subprocess, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = Path("/home/zhiro/research/kv260-vlm/runtime/llama.cpp")
COMMIT = "7ab4ee7baad2d920464cbacfad4f4b07cf111fd2"
SRC = RUNTIME / "tools/mtmd/mtmd-cli.cpp"
SRC_SHA = "92694f41553d76165428deddc11e5100da9bce79f66fd4918b4972bb9e6959bb"
OUT = Path(tempfile.gettempdir()) / "rm04-vlm-tensor-capture-build"

TRACE = r'''
#include <chrono>
#include <unordered_map>
#include <cstdlib>
#include <fstream>
#include <sstream>
#include <vector>
#include <cstdio>
struct PMTrace { std::string phase; uint64_t group = 0; std::unordered_map<const ggml_tensor *, std::chrono::steady_clock::time_point> starts; std::vector<std::string> rows; };
static PMTrace pm_text{"text_prefill", 0, {}, {}}, pm_vision{"vision_encoder", 0, {}, {}};
static std::unordered_map<const ggml_backend_buffer *, uint64_t> pm_buffer_ids;
static uint64_t pm_next_buffer_id = 0;
static uint64_t pm_capture_ordinal_seen = 0;
static bool pm_predecessor_completed = false;
static ggml_tensor * pm_capture_tensor = nullptr;
static std::string pm_capture_base;
static bool pm_enabled() { const char * p = std::getenv("PHASEMAP_OPTRACE_PATH"); return p && *p; }
static bool pm_save_tensor(const ggml_tensor * t, const char * suffix) {
    if (!t || !t->buffer || !t->data) return false;
    const size_t n = ggml_nbytes(t);
    std::vector<unsigned char> bytes(n);
    ggml_backend_tensor_get(t, bytes.data(), 0, n);
    const std::string path = pm_capture_base + suffix;
    std::ofstream f(path, std::ios::binary | std::ios::trunc);
    f.write(reinterpret_cast<const char *>(bytes.data()), static_cast<std::streamsize>(n));
    f.close();
    if (!f) return false;
    std::fprintf(stderr, "RM04_TENSOR_CAPTURE path=%s bytes=%zu dtype=%s name=%s\n",
                 path.c_str(), n, ggml_type_name(t->type), t->name);
    return true;
}
static void pm_quote(std::ostream & o, const std::string & s) { o << '"'; for (unsigned char c : s) { if (c == '"' || c == '\\') o << '\\' << c; else if (c == '\n') o << "\\n"; else if (c == '\r') o << "\\r"; else if (c == '\t') o << "\\t"; else if (c >= 0x20) o << (char)c; } o << '"'; }
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
    const char * prefixes_env = std::getenv("PHASEMAP_TARGET_OP_PREFIXES");
    if (prefixes_env && *prefixes_env) {
        if (t->op != GGML_OP_MUL_MAT) return false;
        const std::string prefixes(prefixes_env);
        for (int src = 0; src < GGML_MAX_SRC; ++src) {
            if (!t->src[src]) continue;
            const std::string src_name = t->src[src]->name;
            std::size_t begin = 0;
            while (begin <= prefixes.size()) {
                const std::size_t end = prefixes.find(',', begin);
                const std::string prefix = prefixes.substr(begin, end == std::string::npos ? end : end - begin);
                if (!prefix.empty() && (src_name.rfind(prefix, 0) == 0 ||
                                        src_name.find(prefix) != std::string::npos)) return true;
                if (end == std::string::npos) break;
                begin = end + 1;
            }
        }
        return false;
    }
    const char * target_env = std::getenv("PHASEMAP_TARGET_OP_NAME");
    const char * predecessor_env = std::getenv("PHASEMAP_TARGET_PREDECESSOR_NAME");
    const std::string target = target_env && *target_env ? target_env : "ffn_up-0";
    const std::string predecessor = predecessor_env && *predecessor_env ? predecessor_env : "ffn_inp_normed-0";
    const std::string name = t->name;
    return name == predecessor || (name == target && t->op == GGML_OP_MUL_MAT);
}
static bool pm_eval(ggml_tensor * t, bool ask, void * p) {
    auto * tr = static_cast<PMTrace *>(p);
    const char * capture_env = std::getenv("RM04_CAPTURE_BASE");
    const char * ordinal_env = std::getenv("RM04_CAPTURE_ORDINAL");
    const uint64_t capture_ordinal = ordinal_env ? std::strtoull(ordinal_env, nullptr, 10) : 0;
    if (tr->phase == "vision_encoder" && std::string(t->name) == "ffn_inp_normed-0") {
        if (!ask) pm_predecessor_completed = true;
    }
    if (tr->phase == "vision_encoder" && capture_env && *capture_env && ask &&
        std::string(t->name) == "ffn_up-0" && t->op == GGML_OP_MUL_MAT) {
        const uint64_t ordinal = pm_capture_ordinal_seen++;
        if (ordinal == capture_ordinal) {
            const ggml_tensor * w = t->src[0];
            const ggml_tensor * x = t->src[1];
            if (!pm_predecessor_completed || !w || !x ||
                w->type != GGML_TYPE_F16 || x->type != GGML_TYPE_F32 || t->type != GGML_TYPE_F32 ||
                w->ne[0] != 1152 || w->ne[1] != 4304 || x->ne[0] != 1152 || x->ne[1] != 1120 ||
                t->ne[0] != 4304 || t->ne[1] != 1120 ||
                w->nb[0] != 2 || w->nb[1] != 2304 || x->nb[0] != 4 || x->nb[1] != 4608 ||
                t->nb[0] != 4 || t->nb[1] != 17216 || !w->buffer || !x->buffer || !t->buffer) {
                std::fprintf(stderr, "RM04_TENSOR_CAPTURE_ABORT exact-signature-or-adjacency-check-failed predecessor=%d ordinal=%llu\n",
                             pm_predecessor_completed ? 1 : 0, static_cast<unsigned long long>(ordinal));
                return true;
            }
            pm_capture_base = capture_env;
            if (!pm_save_tensor(w, ".weight.f16") || !pm_save_tensor(x, ".activation.f32")) {
                std::fprintf(stderr, "RM04_TENSOR_CAPTURE_ABORT input-write-failed\n");
                return true;
            }
            pm_capture_tensor = t;
            std::fprintf(stderr, "RM04_TENSOR_CAPTURE_BEGIN ordinal=%llu group=%llu\n",
                         static_cast<unsigned long long>(ordinal), static_cast<unsigned long long>(tr->group));
        }
    }
    if (!ask) {
        if (t == pm_capture_tensor) {
            if (!pm_save_tensor(t, ".output.f32")) std::fprintf(stderr, "RM04_TENSOR_CAPTURE_ABORT output-write-failed\n");
            else std::fprintf(stderr, "RM04_TENSOR_CAPTURE_DONE\n");
            pm_capture_tensor = nullptr;
        }
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
        const char * prefixes_env = std::getenv("PHASEMAP_TARGET_OP_PREFIXES");
        if (tr->phase == target_phase && prefixes_env && *prefixes_env && pm_target_boundary(tr, t)) timed << ",\"kind\":\"isolated_family_node\"";
        else if (tr->phase == target_phase && std::string(t->name) == target) timed << ",\"kind\":\"isolated_target_node\"";
        else if (tr->phase == target_phase && std::string(t->name) == predecessor) timed << ",\"kind\":\"target_prelude_boundary\"";
        else timed << ",\"kind\":\"layer_boundary\"";
        timed << ",\"elapsed_ns\":" << ns << ",\"output_name\":"; pm_quote(timed, t->name);
        timed << ",\"op\":"; pm_quote(timed, ggml_op_name(t->op));
        if (t->op == GGML_OP_MUL_MAT && t->src[0] && t->src[1]) {
            timed << ",\"src0_name\":"; pm_quote(timed, t->src[0]->name);
            timed << ",\"src1_name\":"; pm_quote(timed, t->src[1]->name);
            timed << ",\"src0_dtype\":"; pm_quote(timed, ggml_type_name(t->src[0]->type));
            timed << ",\"src1_dtype\":"; pm_quote(timed, ggml_type_name(t->src[1]->type));
            timed << ",\"output_dtype\":"; pm_quote(timed, ggml_type_name(t->type));
            timed << ",\"src0_ne\":[" << t->src[0]->ne[0] << ',' << t->src[0]->ne[1]
                  << ',' << t->src[0]->ne[2] << ',' << t->src[0]->ne[3] << ']'
                  << ",\"src1_ne\":[" << t->src[1]->ne[0] << ',' << t->src[1]->ne[1]
                  << ',' << t->src[1]->ne[2] << ',' << t->src[1]->ne[3] << ']'
                  << ",\"output_ne\":[" << t->ne[0] << ',' << t->ne[1]
                  << ',' << t->ne[2] << ',' << t->ne[3] << ']';
        }
        timed << '}';
        tr->rows.push_back(timed.str()); tr->starts.erase(it); return true;
    }
    std::ostringstream o; o << "{\"record\":\"node\",\"phase\":"; pm_quote(o, tr->phase);
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
    report={'binary':str(binary),'binary_sha256':sha(binary),'generated_source_sha256':sha(generated),'upstream_source':str(SRC.relative_to(RUNTIME)),'upstream_source_sha256':SRC_SHA,'runtime_commit':commit,'linked_libraries':[{'name':p.name,'sha256':sha(p)} for p in libs],'build_method':'project-local source copy with exact-signature tensor capture; upstream files unchanged; compile flags from pinned compile_commands.json; existing pinned runtime libraries','capture_contract':'first target ffn_up-0 occurrence by default; require preceding ffn_inp_normed-0 synchronized callback; validate exact F16/F32/F32 GGML shape and strides; use ggml_backend_tensor_get for weight, activation, and output payloads'}
    (OUT/'build.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2)); return 0

if __name__=='__main__': raise SystemExit(main())
