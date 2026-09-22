# XRT / Vitis acceleration audit

审计时间：2026-09-22。

## Host

- `vitis`: not found
- `vivado`: not found
- Host XRT/platform packages: `UNKNOWN`（主机工具链尚未安装）
- Host available platforms: `UNKNOWN`

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

Vitis application acceleration build flow：`BLOCKED`，因为主机 2024.2 工具链尚未安装；本阶段没有自动升级板端 XRT、没有更换 platform、没有启用 `.xo/.xclbin` flow。
