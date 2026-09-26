#include "arg.h"
#include "debug.h"
#include "log.h"
#include "common.h"
#include "sampling.h"
#include "llama.h"
#include "ggml.h"
#include "console.h"
#include "chat.h"
#include "mtmd.h"
#include "mtmd-helper.h"

#include <vector>
#include <limits.h>
#include <cinttypes>
#include <clocale>

#include <chrono>
#include <unordered_map>
#include <unordered_set>
#include <cstdlib>
#include <fstream>
#include <sstream>
#include <vector>
#include <cstdio>
struct PMTrace { std::string phase; uint64_t group = 0; std::unordered_map<const ggml_tensor *, std::chrono::steady_clock::time_point> starts; std::vector<std::string> rows; };
static PMTrace pm_text{"text_prefill", 0, {}, {}}, pm_vision{"vision_encoder", 0, {}, {}};
static std::unordered_map<const ggml_backend_buffer *, uint64_t> pm_buffer_ids;
static uint64_t pm_next_buffer_id = 0;
static std::unordered_set<std::string> pm_capture_seen;
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
    std::fprintf(stderr, "RM11_TENSOR_CAPTURE path=%s bytes=%zu dtype=%s name=%s\n",
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
    const char * capture_dir_env = std::getenv("RM11_CAPTURE_DIR");
    const char * capture_names_env = std::getenv("RM11_CAPTURE_NAMES");
    if (tr->phase == "vision_encoder" && capture_dir_env && *capture_dir_env &&
        capture_names_env && *capture_names_env && ask && t->op == GGML_OP_MUL_MAT) {
        const std::string name(t->name);
        const std::string targets = std::string(",") + capture_names_env + ",";
        if (targets.find(std::string(",") + name + ",") != std::string::npos &&
            pm_capture_seen.find(name) == pm_capture_seen.end() && !pm_capture_tensor) {
            const bool known_target = name == "ffn_up-0" || name == "ffn_up-13" || name == "ffn_up-26";
            const int expected_n = name == "ffn_up-0" ? 1120 : 280;
            const std::string expected_x = "ffn_inp_normed-" + name.substr(std::string("ffn_up-").size());
            const ggml_tensor * w = t->src[0];
            const ggml_tensor * x = t->src[1];
            const bool signature_ok = known_target && w && x &&
                w->type == GGML_TYPE_F16 && x->type == GGML_TYPE_F32 && t->type == GGML_TYPE_F32 &&
                w->ne[0] == 1152 && w->ne[1] == 4304 && w->ne[2] == 1 && w->ne[3] == 1 &&
                x->ne[0] == 1152 && x->ne[1] == expected_n && x->ne[2] == 1 && x->ne[3] == 1 &&
                t->ne[0] == 4304 && t->ne[1] == expected_n && t->ne[2] == 1 && t->ne[3] == 1 &&
                w->nb[0] == 2 && w->nb[1] == 2304 &&
                x->nb[0] == 4 && x->nb[1] == 4608 &&
                t->nb[0] == 4 && t->nb[1] == 17216 &&
                ggml_is_contiguous(w) && ggml_is_contiguous(x) && ggml_is_contiguous(t) &&
                x->name == expected_x && w->buffer && x->buffer && t->buffer;
            if (!signature_ok) {
                std::fprintf(stderr,
                    "RM11_TENSOR_CAPTURE_SKIP name=%s expected_N=%d w=%p x=%p input_name=%s\n",
                    name.c_str(), expected_n, static_cast<const void *>(w),
                    static_cast<const void *>(x), x ? x->name : "<null>");
            } else {
                pm_capture_tensor = t;
                std::fprintf(stderr,
                    "RM11_TENSOR_CAPTURE_PENDING name=%s group=%llu W=[%lld,%lld,%lld,%lld] F16 nb=[%zu,%zu,%zu,%zu] X=[%lld,%lld,%lld,%lld] F32 nb=[%zu,%zu,%zu,%zu] Y=[%lld,%lld,%lld,%lld] F32 nb=[%zu,%zu,%zu,%zu]\n",
                    name.c_str(), static_cast<unsigned long long>(tr->group),
                    static_cast<long long>(w->ne[0]), static_cast<long long>(w->ne[1]),
                    static_cast<long long>(w->ne[2]), static_cast<long long>(w->ne[3]),
                    w->nb[0], w->nb[1], w->nb[2], w->nb[3],
                    static_cast<long long>(x->ne[0]), static_cast<long long>(x->ne[1]),
                    static_cast<long long>(x->ne[2]), static_cast<long long>(x->ne[3]),
                    x->nb[0], x->nb[1], x->nb[2], x->nb[3],
                    static_cast<long long>(t->ne[0]), static_cast<long long>(t->ne[1]),
                    static_cast<long long>(t->ne[2]), static_cast<long long>(t->ne[3]),
                    t->nb[0], t->nb[1], t->nb[2], t->nb[3]);
                return true;
            }
        }
    }
    if (!ask) {
        if (t == pm_capture_tensor) {
            const char * capture_dir_env = std::getenv("RM11_CAPTURE_DIR");
            const std::string name(t->name);
            const char * slash = capture_dir_env[std::strlen(capture_dir_env) - 1] == '/' ? "" : "/";
            pm_capture_base = std::string(capture_dir_env) + slash + name;
            const ggml_tensor * w = t->src[0];
            const ggml_tensor * x = t->src[1];
            const bool saved = w && x && pm_save_tensor(w, ".weight.f16") &&
                               pm_save_tensor(x, ".activation.f32") &&
                               pm_save_tensor(t, ".output.f32");
            if (!saved) std::fprintf(stderr, "RM11_TENSOR_CAPTURE_ABORT tensor-write-failed name=%s\n", name.c_str());
            else {
                pm_capture_seen.insert(name);
                std::fprintf(stderr, "RM11_TENSOR_CAPTURE_DONE name=%s\n", name.c_str());
            }
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


#if defined (__unix__) || (defined (__APPLE__) && defined (__MACH__))
#include <signal.h>
#include <unistd.h>
#elif defined (_WIN32)
#define WIN32_LEAN_AND_MEAN
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <signal.h>
#endif

// volatile, because of signal being an interrupt
static volatile bool g_is_generating = false;
static volatile bool g_is_interrupted = false;

/**
 * Please note that this is NOT a production-ready binary.
 * It is a playground for trying multimodal support in llama.cpp.
 * For contributors: please keep this code simple and easy to understand. Do not add unnecessary complexity. The goal is to have a simple CLI for testing multimodal support.
 */

static void show_additional_info(int /*argc*/, char ** argv) {
    LOG(
        "Experimental CLI for multimodal\n\n"
        "Usage: %s [options] -m <model> --mmproj <mmproj> --image <image> --audio <audio> -p <prompt>\n\n"
        "  -m and --mmproj are required\n"
        "  -hf user/repo can replace both -m and --mmproj in most cases\n"
        "  --image, --audio and -p are optional, if NOT provided, the CLI will run in chat mode\n"
        "  to disable using GPU for mmproj model, add --no-mmproj-offload\n",
        argv[0]
    );
}

#if defined (__unix__) || (defined (__APPLE__) && defined (__MACH__)) || defined (_WIN32)
static void sigint_handler(int signo) {
    if (signo == SIGINT) {
        if (g_is_generating) {
            g_is_generating = false;
        } else {
            console::cleanup();
            if (g_is_interrupted) {
                _exit(1);
            }
            g_is_interrupted = true;
        }
    }
}
#endif

// this is only used by tests.sh to capture the response ; it's not meant to be used in production
static void inject_test_response_marker() {
    const char * env = std::getenv("MTMD_TEST_RESPONSE_MARKER");
    if (env) {
        LOG("%s\n", env);
    }
}

struct mtmd_cli_context {
    mtmd::context_ptr ctx_vision;
    common_init_result_ptr llama_init;

    llama_model       * model;
    llama_context     * lctx;
    const llama_vocab * vocab;
    common_sampler    * smpl;
    llama_batch         batch;
    int                 n_batch;

    mtmd::bitmaps bitmaps;
    std::vector<mtmd_helper::video_ptr> videos;

    mtmd_helper_init_opt init_opt = mtmd_helper_init_opt_default();
    std::string video_ffmpeg_bin_dir;

    mtmd::batch_ptr mbatch;

    // chat template
    common_chat_templates_ptr tmpls;
    std::vector<common_chat_msg> chat_history;
    bool use_jinja = false;
    // TODO: support for --system-prompt with /clear command

    // support for legacy templates (models not having EOT token)
    llama_tokens antiprompt_tokens;

    int n_threads    = 1;
    llama_pos n_past = 0;

    common_debug_cb_user_data cb_data;

    mtmd_cli_context(common_params & params) : llama_init(common_init_from_params(params)) {
        model = llama_init->model();
        lctx = llama_init->context();
        if (!model || !lctx) {
            exit(1);
        }
        vocab = llama_model_get_vocab(model);
        smpl = common_sampler_init(model, params.sampling);
        n_threads = params.cpuparams.n_threads;
        batch = llama_batch_init(1, 0, 1); // batch for next token generation
        n_batch = params.n_batch;

        init_vision_context(params);

        if (!mtmd_helper_model_can_chat(lctx, ctx_vision.get())) {
            LOG_ERR("Model does not support chat mode\n");
            LOG_ERR("Hint: for TTS models, please use llama-tts\n");
            exit(1);
        }

        if (!llama_model_chat_template(model, nullptr) && params.chat_template.empty()) {
            LOG_ERR("Model does not have chat template.\n");
            LOG_ERR("  For old llava models, you may need to use '--chat-template vicuna'\n");
            LOG_ERR("  For MobileVLM models, use '--chat-template deepseek'\n");
            LOG_ERR("  For Mistral Small 3.1, use '--chat-template mistral-v7'\n");
            exit(1);
        }

        tmpls = common_chat_templates_init(model, params.chat_template);
        use_jinja = params.use_jinja;
        chat_history.clear();
        LOG_INF("%s: chat template example:\n%s\n", __func__, common_chat_format_example(tmpls.get(), params.use_jinja, params.default_template_kwargs).c_str());

        // load antiprompt tokens for legacy templates
        if (params.chat_template == "vicuna") {
            antiprompt_tokens = common_tokenize(lctx, "ASSISTANT:", false, true);
        } else if (params.chat_template == "deepseek") {
            antiprompt_tokens = common_tokenize(lctx, "###", false, true);
        }
    }

    ~mtmd_cli_context() {
        llama_batch_free(batch);
        common_sampler_free(smpl);
    }

    void init_vision_context(common_params & params) {
        const char * clip_path = params.mmproj.path.c_str();
        mtmd_context_params mparams = mtmd_context_params_default();
        mparams.use_gpu          = params.mmproj_use_gpu;
        mparams.device           = params.mmproj_device;
        mparams.print_timings    = true;
        mparams.n_threads        = params.cpuparams.n_threads;
        mparams.flash_attn_type  = params.flash_attn_type;
        mparams.warmup           = params.warmup;
        mparams.image_min_tokens = params.image_min_tokens;
        mparams.image_max_tokens = params.image_max_tokens;
        if (pm_enabled()) {
            mparams.cb_eval_user_data = &pm_vision;
            mparams.cb_eval = pm_eval;
        } else if (std::getenv("MTMD_DEBUG_GRAPH") != nullptr) {
            mparams.cb_eval_user_data = &cb_data;
            mparams.cb_eval = common_debug_cb_eval;
        }
        ctx_vision.reset(mtmd_init_from_file(clip_path, model, mparams));
        if (!ctx_vision.get()) {
            LOG_ERR("Failed to load vision model from %s\n", clip_path);
            exit(1);
        }

        video_ffmpeg_bin_dir = params.video_ffmpeg_bin_dir;
        init_opt.video_params.fps_target = params.video_fps;
        init_opt.video_params.timestamp_interval_ms = params.video_timestamp_interval_ms;
        init_opt.video_params.ffmpeg_bin_dir = video_ffmpeg_bin_dir.empty()
                            ? nullptr : video_ffmpeg_bin_dir.c_str();
    }

    bool check_antiprompt(const llama_tokens & generated_tokens) {
        if (antiprompt_tokens.empty() || generated_tokens.size() < antiprompt_tokens.size()) {
            return false;
        }
        return std::equal(
            generated_tokens.end() - antiprompt_tokens.size(),
            generated_tokens.end(),
            antiprompt_tokens.begin()
        );
    }

    bool load_media(const std::string & fname) {
        auto res = mtmd_helper_bitmap_init_from_file(ctx_vision.get(), fname.c_str(), false, init_opt);
        if (!res.bitmap) {
            return false;
        }
        bitmaps.entries.emplace_back(res.bitmap);
        if (res.video_ctx) {
            videos.emplace_back(res.video_ctx);
        }
        return true;
    }
};

static int generate_response(mtmd_cli_context & ctx, int n_predict) {
    llama_tokens generated_tokens;
    for (int i = 0; i < n_predict; i++) {
        if (i > n_predict || !g_is_generating || g_is_interrupted) {
            LOG("\n");
            break;
        }

        llama_token token_id = common_sampler_sample(ctx.smpl, ctx.lctx, -1);
        generated_tokens.push_back(token_id);
        common_sampler_accept(ctx.smpl, token_id, true);

        if (llama_vocab_is_eog(ctx.vocab, token_id) || ctx.check_antiprompt(generated_tokens)) {
            LOG("\n");
            break; // end of generation
        }

        LOG("%s", common_token_to_piece(ctx.lctx, token_id).c_str());
        fflush(stdout);

        if (g_is_interrupted) {
            LOG("\n");
            break;
        }

        // eval the token
        common_batch_clear(ctx.batch);
        common_batch_add(ctx.batch, token_id, ctx.n_past++, {0}, true);
        pm_text.phase = "token_decode";
        ++pm_text.group;
        if (llama_decode(ctx.lctx, ctx.batch)) {
            LOG_ERR("failed to decode token\n");
            return 1;
        }
    }

    std::string generated_text = common_detokenize(ctx.lctx, generated_tokens);
    common_chat_msg msg;
    msg.role    = "assistant";
    msg.content = generated_text;
    ctx.chat_history.push_back(std::move(msg));

    return 0;
}

static std::string chat_add_and_format(mtmd_cli_context & ctx, common_chat_msg & new_msg) {
    LOG_DBG("chat_add_and_format: new_msg.role='%s', new_msg.content='%s'\n",
        new_msg.role.c_str(), new_msg.content.c_str());
    auto formatted = common_chat_format_single(ctx.tmpls.get(), ctx.chat_history,
        new_msg, new_msg.role == "user",
        ctx.use_jinja);
    ctx.chat_history.push_back(new_msg);
    return formatted;
}

static int eval_message(mtmd_cli_context & ctx, common_chat_msg & msg) {
    inject_test_response_marker();

    bool add_bos = ctx.chat_history.empty();
    auto formatted_chat = chat_add_and_format(ctx, msg);
    LOG_DBG("formatted_chat.prompt: %s\n", formatted_chat.c_str());

    if (g_is_interrupted) return 0;

    // note: we replace the marker here instead of letting mtmd_tokenize() to do that
    //       because we want to demonstrate how to use mtmd_tokenize_from_parts()

    // split the formatted chat on the media marker to get text segments
    const std::string marker = mtmd_default_marker();
    std::vector<std::string> segments;
    size_t start = 0;
    size_t pos;
    while ((pos = formatted_chat.find(marker, start)) != std::string::npos) {
        segments.push_back(formatted_chat.substr(start, pos - start));
        start = pos + marker.size();
    }
    segments.push_back(formatted_chat.substr(start));

    auto bitmaps_c_ptr = ctx.bitmaps.c_ptr();
    if (segments.size() - 1 != bitmaps_c_ptr.size()) {
        LOG_ERR("Number of media markers (%zu) does not match number of loaded media (%zu)\n",
                segments.size() - 1, bitmaps_c_ptr.size());
        return 1;
    }

    // interleave text and media parts
    std::vector<mtmd_input_text> texts(segments.size());
    std::vector<mtmd_input_part> parts;
    for (size_t i = 0; i < segments.size(); i++) {
        texts[i] = {segments[i].data(), segments[i].size(), /* add_special */ false, /* parse_special */ true};
        parts.push_back({&texts[i], nullptr});
        if (i < bitmaps_c_ptr.size()) {
            parts.push_back({nullptr, bitmaps_c_ptr[i]});
        }
    }
    std::vector<const mtmd_input_part *> parts_ptr;
    for (const auto & p : parts) {
        parts_ptr.push_back(&p);
    }

    mtmd::input_chunks chunks(mtmd_input_chunks_init());
    int32_t res = mtmd_tokenize_from_parts(ctx.ctx_vision.get(),
                        chunks.ptr.get(), // output
                        parts_ptr.data(),
                        parts_ptr.size(),
                        add_bos);
    if (res != 0) {
        LOG_ERR("Unable to tokenize prompt, res = %d\n", res);
        return 1;
    }

    ctx.bitmaps.entries.clear();
    ctx.videos.clear();

    // batch encode all media chunks, then decode each
    size_t n_chunks = mtmd_input_chunks_size(chunks.ptr.get());
    for (size_t i = 0; i < n_chunks; i++) {
        auto chunk = mtmd_input_chunks_get(chunks.ptr.get(), i);
        auto chunk_type = mtmd_input_chunk_get_type(chunk);

        if (chunk_type == MTMD_INPUT_CHUNK_TYPE_TEXT) {
            pm_text.phase = "text_prefill";
            // decode text chunk
            llama_pos new_n_past = ctx.n_past;
            res = mtmd_helper_eval_chunk_single(ctx.ctx_vision.get(),
                        ctx.lctx,
                        chunk,
                        ctx.n_past,
                        0, // seq_id
                        ctx.n_batch,
                        i == n_chunks - 1, // logits_last
                        &new_n_past);
            if (res != 0) {
                LOG_ERR("Unable to eval text chunk %zu\n", i);
                return 1;
            }
            ctx.n_past = new_n_past;
        } else {
            pm_text.phase = "image_embedding_prefill";
            // media chunk: try to get embd from existing batch, or create a new batch
            float * embd = nullptr;
            if (ctx.mbatch) {
                embd = mtmd_batch_get_output_embd(ctx.mbatch.get(), chunk);

                if (embd) {
                    LOG_DBG("found embd for media chunk %zu in existing batch\n", i);
                } else {
                    LOG_DBG("media chunk %zu not found in existing batch, creating new batch\n", i);
                }
            }

            if (!embd) {
                // create and encode a new batch with as many media chunks as possible
                ctx.mbatch.reset(mtmd_batch_init(ctx.ctx_vision.get()));
                res = mtmd_batch_add_chunk(ctx.mbatch.get(), chunk);
                GGML_ASSERT(res == 0); // first chunk must always succeed

                int n_added = 1;
                // add as many subsequent media chunks as possible
                for (size_t j = i + 1; j < n_chunks; j++) {
                    auto next_chunk = mtmd_input_chunks_get(chunks.ptr.get(), j);
                    auto next_type = mtmd_input_chunk_get_type(next_chunk);
                    if (next_type == MTMD_INPUT_CHUNK_TYPE_TEXT) {
                        break; // text chunk splits the batch
                    }
                    res = mtmd_batch_add_chunk(ctx.mbatch.get(), next_chunk);
                    if (res != 0) {
                        break; // batch full or incompatible
                    }
                    n_added++;
                }

                int64_t time_start = ggml_time_ms();
                LOG_INF("encoding mtmd batch, n_chunks = %d (done = %zu, total = %zu)\n", n_added, i, n_chunks);
                res = mtmd_batch_encode(ctx.mbatch.get());
                if (res != 0) {
                    LOG_ERR("Failed to encode mtmd batch, res = %d\n", res);
                    return 1;
                }
                LOG_INF("mtmd batch encoding done in %d ms\n", (int)(ggml_time_ms() - time_start));

                embd = mtmd_batch_get_output_embd(ctx.mbatch.get(), chunk);
            }

            GGML_ASSERT(embd != nullptr);

            llama_pos new_n_past = ctx.n_past;
            res = mtmd_helper_decode_image_chunk(ctx.ctx_vision.get(),
                        ctx.lctx,
                        chunk,
                        embd,
                        ctx.n_past,
                        0, // seq_id
                        ctx.n_batch,
                        &new_n_past,
                        nullptr, // callback
                        nullptr  // user_data
                    );
            if (res != 0) {
                LOG_ERR("Unable to decode media chunk %zu\n", i);
                return 1;
            }
            ctx.n_past = new_n_past;
        }
    }

    LOG("\n");

    return 0;
}

int main(int argc, char ** argv) {
    std::setlocale(LC_NUMERIC, "C");

    ggml_time_init();

    common_params params;

    common_init();

    if (!common_params_parse(argc, argv, params, LLAMA_EXAMPLE_MTMD, show_additional_info)) {
        return 1;
    }

    mtmd_helper_log_set(common_log_default_callback, nullptr);
    if (pm_enabled()) { params.cb_eval = pm_eval; params.cb_eval_user_data = &pm_text; std::atexit(pm_flush); }

    if (params.mmproj.path.empty()) {
        show_additional_info(argc, argv);
        LOG_ERR("ERR: Missing --mmproj argument\n");
        return 1;
    }

    ggml_backend_load_all();

    mtmd_cli_context ctx(params);
    LOG_INF("%s: loading model: %s\n", __func__, params.model.path.c_str());

    bool is_single_turn = !params.prompt.empty() && !params.image.empty();

    int n_predict = params.n_predict < 0 ? INT_MAX : params.n_predict;

    console::init(params.simple_io, params.use_color);
    atexit([]() { console::cleanup(); });

    // Ctrl+C handling
    {
#if defined (__unix__) || (defined (__APPLE__) && defined (__MACH__))
        struct sigaction sigint_action;
        sigint_action.sa_handler = sigint_handler;
        sigemptyset (&sigint_action.sa_mask);
        sigint_action.sa_flags = 0;
        sigaction(SIGINT, &sigint_action, NULL);
#elif defined (_WIN32)
        auto console_ctrl_handler = +[](DWORD ctrl_type) -> BOOL {
            return (ctrl_type == CTRL_C_EVENT) ? (sigint_handler(SIGINT), true) : false;
        };
        SetConsoleCtrlHandler(reinterpret_cast<PHANDLER_ROUTINE>(console_ctrl_handler), true);
#endif
    }

    if (g_is_interrupted) return 130;

    auto eval_system_prompt_if_present = [&] {
        if (params.system_prompt.empty()) {
            return 0;
        }

        common_chat_msg msg;
        msg.role = "system";
        msg.content = params.system_prompt;
        return eval_message(ctx, msg);
    };

    LOG_WRN("WARN: This is an experimental CLI for testing multimodal capability.\n");
    LOG_WRN("      For normal use cases, please use the standard llama-cli\n");

    if (eval_system_prompt_if_present()) {
        return 1;
    }

    if (is_single_turn) {
        g_is_generating = true;
        if (params.prompt.find(mtmd_default_marker()) == std::string::npos) {
            for (size_t i = 0; i < params.image.size(); i++) {
                // most models require the marker before each image
                // ref: https://github.com/ggml-org/llama.cpp/pull/17616
                params.prompt = mtmd_default_marker() + params.prompt;
            }
        }

        common_chat_msg msg;
        msg.role = "user";
        msg.content = params.prompt;
        for (const auto & image : params.image) {
            if (!ctx.load_media(image)) {
                return 1; // error is already printed by libmtmd
            }
        }
        if (eval_message(ctx, msg)) {
            return 1;
        }
        if (!g_is_interrupted && generate_response(ctx, n_predict)) {
            return 1;
        }

    } else {
        LOG("\n Running in chat mode, available commands:");
        if (mtmd_support_vision(ctx.ctx_vision.get())) {
            LOG("\n   /image <path>    load an image");
        }
        if (mtmd_support_audio(ctx.ctx_vision.get())) {
            LOG("\n   /audio <path>    load an audio");
        }
        if (mtmd_helper_support_video(ctx.ctx_vision.get())) {
            LOG("\n   /video <path>    load a video");
        }
        LOG("\n   /clear           clear the chat history");
        LOG("\n   /quit or /exit   exit the program");
        LOG("\n");

        std::string content;

        while (!g_is_interrupted) {
            g_is_generating = false;
            LOG("\n> ");
            console::set_display(DISPLAY_TYPE_USER_INPUT);
            std::string line;
            console::readline(line, false);
            if (g_is_interrupted) break;
            console::set_display(DISPLAY_TYPE_RESET);
            line = string_strip(line);
            if (line.empty()) {
                continue;
            }
            if (line == "/quit" || line == "/exit") {
                break;
            }
            if (line == "/clear") {
                ctx.n_past = 0;
                ctx.chat_history.clear();
                llama_memory_clear(llama_get_memory(ctx.lctx), true);
                if (eval_system_prompt_if_present()) {
                    return 1;
                }
                LOG("Chat history cleared\n\n");
                continue;
            }
            g_is_generating = true;
            bool is_image = line == "/image" || line.find("/image ") == 0;
            bool is_audio = line == "/audio" || line.find("/audio ") == 0;
            bool is_video = line == "/video" || line.find("/video ") == 0;
            if (is_image || is_audio || is_video) {
                if (line.size() < 8) {
                    LOG_ERR("ERR: Missing media filename\n");
                    continue;
                }
                std::string media_path = line.substr(7);
                if (ctx.load_media(media_path)) {
                    LOG("%s %s loaded\n", media_path.c_str(), is_image ? "image" : is_audio ? "audio" : "video");
                    content += mtmd_default_marker();
                }
                // else, error is already printed by libmtmd
                continue;
            } else {
                content += line;
            }
            common_chat_msg msg;
            msg.role = "user";
            msg.content = content;
            int ret = eval_message(ctx, msg);
            if (ret) {
                return 1;
            }
            if (g_is_interrupted) break;
            if (generate_response(ctx, n_predict)) {
                return 1;
            }
            content.clear();
        }
    }
    if (g_is_interrupted) LOG("\nInterrupted by user\n");
    LOG("\n\n");
    llama_perf_context_print(ctx.lctx);
    return g_is_interrupted ? 130 : 0;
}
