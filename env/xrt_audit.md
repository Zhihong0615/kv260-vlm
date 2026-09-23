# XRT / Vitis acceleration audit

审计时间：2026-09-22 至 2026-09-23。

## Host

- `vitis`: 2024.2（project-local）
- `vivado`: 2024.2（project-local）
- `vitis_hls`: 2024.2（project-local）
- K26 device / KV260 board database：`PASS`

## KV260

板端 `xbutil examine` 真实结果：

```text
Release              : 5.15.0-1027-xilinx-zynqmp
Machine              : aarch64
Model                : ZynqMP KV260 revB
XRT Version          : 2.13.0
Devices present      : KV260
Device Ready         : Yes
```

包管理器显示：`xrt 2.13.479-0ubuntu2`（arm64）。

## 结论

板端 XRT/runtime 与 KV260 device 可见性：`PASS`。

本轮只验收主机 Vivado/Vitis/HLS 工具与板端已有 XRT device readiness；没有
构建或加载 `.xo/.xclbin`，因此不对完整 application acceleration runtime
兼容性作额外声明。没有自动升级板端 XRT、没有更换 platform，也没有加载
应用或 bitstream。
