#!/usr/bin/env python3
"""Build a pinned CPU-only MTMD CLI that captures three real vision FFN-up ops."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "scripts/rm04/build_tensor_capture_cli.py"
spec = importlib.util.spec_from_file_location("rm04_capture_builder", BASE)
if spec is None or spec.loader is None:
    raise SystemExit("cannot import pinned RM04 capture builder")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)

builder.OUT = Path("/tmp/rm11-ffn-up-capture-build")
trace = builder.TRACE
trace = trace.replace(
    "#include <unordered_map>", "#include <unordered_map>\n#include <unordered_set>", 1
)
trace = trace.replace(
    "static uint64_t pm_capture_ordinal_seen = 0;\n"
    "static bool pm_predecessor_completed = false;\n"
    "static ggml_tensor * pm_capture_tensor = nullptr;\n"
    "static std::string pm_capture_base;",
    "static std::unordered_set<std::string> pm_capture_seen;\n"
    "static ggml_tensor * pm_capture_tensor = nullptr;\n"
    "static std::string pm_capture_base;",
    1,
)

start = trace.index(
    '    const char * capture_env = std::getenv("RM04_CAPTURE_BASE");',
    trace.index("static bool pm_eval"),
)
end = trace.index("    if (!ask) {", start)
replacement = r'''    const char * capture_dir_env = std::getenv("RM11_CAPTURE_DIR");
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
'''
trace = trace[:start] + replacement + trace[end:]

callback_start = trace.index("static bool pm_eval")
not_ask = trace.index("    if (!ask) {", callback_start)
pending_start = trace.index("        if (t == pm_capture_tensor) {", not_ask)
pending_end = trace.index("        auto it = tr->starts.find(t);", pending_start)
trace = trace[:pending_start] + r'''        if (t == pm_capture_tensor) {
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
''' + trace[pending_end:]
trace = trace.replace(
    'std::fprintf(stderr, "RM04_TENSOR_CAPTURE path=%s bytes=%zu dtype=%s name=%s\\n",',
    'std::fprintf(stderr, "RM11_TENSOR_CAPTURE path=%s bytes=%zu dtype=%s name=%s\\n",',
    1,
)
builder.TRACE = trace

if __name__ == "__main__":
    original_main = builder.main

    def rm11_main() -> int:
        result = original_main()
        report_path = builder.OUT / "build.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        report["capture_contract"] = (
            "capture first occurrence of ffn_up-0/-13/-26 from the real QID37804 "
            "CPU vision graph; require F16 W [1152,4304], F32 X [1152,N], "
            "F32 Y [4304,N], rank-2 contiguous layouts, exact strides and matching "
            "ffn_inp_normed-N input; expected N=1120 for layer 0 and N=280 for layers 13/26"
        )
        report["capture_names"] = ["ffn_up-0", "ffn_up-13", "ffn_up-26"]
        report["source"] = "scripts/rm11/build_ffn_up_capture_cli.py"
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
        return result

    builder.main = rm11_main
    raise SystemExit(builder.main())
