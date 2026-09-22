# HLS smoke test

状态：`BLOCKED — Vitis HLS 2024.2 未安装`。

运行方式（安装并加载工具链后）：

```bash
cd ~/research/kv260-vlm
source env/setup_fpga.sh
vitis_hls -f env/hls_smoke_test/run_hls.tcl
```

验收证据应包括 C simulation 成功、C synthesis 成功和生成的 synthesis report。`build/` 已被 `.gitignore` 排除；本阶段未伪造报告，也未将该 kernel 当作正式项目算子。
