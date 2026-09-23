# Vitis HLS 2024.2 smoke test

状态：`PASS`（2026-09-23，真实运行）。

测试将 64 元素 `float` 向量加法 kernel 设为顶层，目标器件为
`xck26-sfvc784-2LV-c`，依次执行 C simulation、C synthesis 和 Vivado IP
export。测试只在主机上生成工程与 IP，不会连接或编程 KV260。

## 验收结果

- C simulation：`vector_add C simulation: PASS`
- C synthesis：完成；目标周期 5.00 ns，估算周期 3.650 ns，估算 Fmax
  273.97 MHz
- 综合延迟：81 cycles；流水线 II=1
- 资源估算：6 BRAM_18K、0 DSP、2,775 FF、2,601 LUT、0 URAM
- IP export：`export.zip` 生成成功

持久化证据位于 `evidence/`：

- `vector_add_csim.log`
- `vector_add_csynth.rpt`
- `solution1.log`
- `export.zip`

`build/` 是可再生中间目录，已从 Git 排除；验收和 reviewer 复核后已
删除，上述证据已保留。

## 复现

```bash
cd /home/zhiro/research/kv260-vlm
source env/setup_fpga.sh
vitis_hls -f env/hls_smoke_test/run_hls.tcl
```
