# Vivado 2024.2 KV260 smoke test

状态：`PASS`（2026-09-23，真实综合、实现与 bitstream 生成）。

测试从 Vivado device database 选择
`xilinx.com:kv260_som:part0:1.4`，目标器件为
`xck26-sfvc784-2LV-c`，建立 Zynq UltraScale+ MPSoC + AXI GPIO
Block Design，并执行 validate、synthesis、implementation、routing、DRC 和
`write_bitstream`。

## 验收结果

- implementation 状态：`write_bitstream Complete!`
- bitstream：7,797,818 bytes，非空
- bitstream 前置 DRC：0 errors、0 critical warnings
- routed timing：setup WNS 5.884 ns、hold WHS 0.002 ns，均为 0 个失败端点
- routed utilization：1,152 LUT、1,434 registers、0 BRAM、0 DSP

持久化证据位于 `evidence/`：

- `run_status.txt`
- `kv260_smoke_bd_wrapper.bit`
- `drc.rpt`
- `utilization.rpt`
- `timing_summary.rpt`

`build/` 是可再生中间目录，已从 Git 排除；验收和 reviewer 复核后已
删除，上述证据已保留。

## 复现与安全边界

```bash
cd /home/zhiro/research/kv260-vlm
source env/setup_fpga.sh
vivado -mode batch -source env/vivado_smoke_test/run_vivado.tcl
```

该脚本只生成主机端工程和 bitstream，未调用硬件管理器、`xmutil loadapp`
或任何下载命令；不会向 KV260 加载 bitstream，也不会修改镜像、boot、
QSPI、DTBO 或启动分区。
