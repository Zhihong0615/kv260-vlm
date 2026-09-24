#!/usr/bin/env python3
"""Build a pinned MTMD CLI that captures real FFN-down W/X/Y for 3 layers."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "scripts/rm04/build_tensor_capture_cli.py"
spec = importlib.util.spec_from_file_location("rm04_capture_builder", BASE)
if spec is None or spec.loader is None:
    raise SystemExit("cannot import pinned RM04 capture builder")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)

builder.OUT = Path("/tmp/rm06-multilayer-tensor-capture-build")
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
replacement = r'''    const char * capture_dir_env = std::getenv("RM06_CAPTURE_DIR");
    const char * capture_names_env = std::getenv("RM06_CAPTURE_NAMES");
    if (tr->phase == "vision_encoder" && capture_dir_env && *capture_dir_env &&
        capture_names_env && *capture_names_env && ask && t->op == GGML_OP_MUL_MAT) {
        const std::string name(t->name);
        const std::string targets = std::string(",") + capture_names_env + ",";
        if (targets.find(std::string(",") + name + ",") != std::string::npos &&
            pm_capture_seen.find(name) == pm_capture_seen.end() && !pm_capture_tensor) {
            const int tokens = name == "ffn_down-0" ? 1120 : 280;
            const ggml_tensor * w = t->src[0];
            const ggml_tensor * x = t->src[1];
            if ((name != "ffn_down-0" && name != "ffn_down-13" && name != "ffn_down-26") ||
                !w || !x || w->type != GGML_TYPE_F16 || x->type != GGML_TYPE_F32 ||
                t->type != GGML_TYPE_F32 || w->ne[0] != 4304 || w->ne[1] != 1152 ||
                x->ne[0] != 4304 || x->ne[1] != tokens || t->ne[0] != 1152 ||
                t->ne[1] != tokens || w->nb[0] != 2 || w->nb[1] != 8608 ||
                x->nb[0] != 4 || x->nb[1] != 17216 || t->nb[0] != 4 ||
                t->nb[1] != 4608 || !w->buffer || !x->buffer || !t->buffer) {
                std::fprintf(stderr, "RM06_TENSOR_CAPTURE_SKIP signature-mismatch name=%s\n", name.c_str());
            } else {
                pm_capture_tensor = t;
                std::fprintf(stderr, "RM06_TENSOR_CAPTURE_PENDING_SYNC name=%s group=%llu\n",
                             name.c_str(), static_cast<unsigned long long>(tr->group));
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
            const char * capture_dir_env = std::getenv("RM06_CAPTURE_DIR");
            const std::string name(t->name);
            const char * slash = capture_dir_env[std::strlen(capture_dir_env) - 1] == '/' ? "" : "/";
            pm_capture_base = std::string(capture_dir_env) + slash + name;
            const ggml_tensor * w = t->src[0];
            const ggml_tensor * x = t->src[1];
            const bool saved = w && x && pm_save_tensor(w, ".weight.f16") &&
                               pm_save_tensor(x, ".activation.f32") &&
                               pm_save_tensor(t, ".output.f32");
            if (!saved) std::fprintf(stderr, "RM06_TENSOR_CAPTURE_ABORT tensor-write-failed name=%s\n", name.c_str());
            else {
                pm_capture_seen.insert(name);
                std::fprintf(stderr, "RM06_TENSOR_CAPTURE_DONE name=%s\n", name.c_str());
            }
            pm_capture_tensor = nullptr;
        }
''' + trace[pending_end:]
trace = trace.replace(
    'std::fprintf(stderr, "RM04_TENSOR_CAPTURE path=%s bytes=%zu dtype=%s name=%s\\n",',
    'std::fprintf(stderr, "RM06_TENSOR_CAPTURE path=%s bytes=%zu dtype=%s name=%s\\n",',
    1,
)
builder.TRACE = trace

if __name__ == "__main__":
    original_main = builder.main

    def rm06_main() -> int:
        result = original_main()
        import json

        report_path = builder.OUT / "build.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        report["capture_contract"] = (
            "synchronize at each selected FFN-down MUL_MAT; then save real W/X/Y "
            "for ffn_down-0, ffn_down-13, and ffn_down-26 after node completion"
        )
        report["capture_names"] = ["ffn_down-0", "ffn_down-13", "ffn_down-26"]
        report["source"] = "scripts/rm06/build_multilayer_tensor_capture_cli.py"
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
        return result

    builder.main = rm06_main
    raise SystemExit(builder.main())
