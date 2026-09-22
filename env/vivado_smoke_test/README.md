# Vivado smoke test

状态：`BLOCKED — Vivado 2024.2 未安装`。

测试内容：从 Vivado device database 选择 `*kv260*` board part，建立 Zynq UltraScale+ MPSoC + AXI GPIO（AXI-Lite 寄存器）Block Design，执行 validate、synthesis/implementation、bitstream 生成和 utilization/timing report。

运行方式（安装并加载工具链后）：

```bash
cd ~/research/kv260-vlm
source env/setup_fpga.sh
vivado -mode batch -source env/vivado_smoke_test/run_vivado.tcl
```

脚本只生成本地 disposable project，不会向 KV260 下载或加载 bitstream；真实板端加载需要另行取得用户授权。
