# AMD/Xilinx 2024.2 install plan

状态：`IN PROGRESS — 2024.2 Web Installer 已认证，后台下载/安装中`。

## 目标

统一安装以下同一套 2024.2 工具链：

- Vivado 2024.2
- Vitis 2024.2
- Vitis HLS 2024.2

器件支持至少包含：

- Zynq UltraScale+ MPSoC
- Kria K26 / KV260 对应器件

不主动选择 Versal AI Engine、Alveo 全系列、MATLAB Model Composer、System Generator 等无关组件，除非 Unified Installer 自动声明依赖。

## 安装输入与路径

| 项目 | 计划值 | 状态 |
|---|---|---|
| 官方 installer 文件 | `FPGAs_AdaptiveSoCs_Unified_2024.2_1113_2356_Lin64.bin` | AMD 官方 Web Installer；Makeself 自检 PASS |
| installer SHA256 | `accbea8a0f4096d5242aaef2ad22d3b349a791163a366add48628ab96960a395` | 已记录 |
| 安装根目录 | `/home/zhiro/research/kv260-vlm/tools/Xilinx/` | project-local、无需 root |
| settings64.sh | `tools/Xilinx/Vitis/2024.2/settings64.sh` 或 Vivado 对应路径 | 安装结束后确认 |
| 下载选择 | Vitis Unified、Kria SOM/Starter Kit、Zynq UltraScale+ MPSoC、Edge acceleration devices | 93.74 GB |
| 后台服务 | `kv260-amd-install-2024-2.service` | user systemd service，运行中 |
| 可用空间 | 约 372 GB（安装启动时） | 满足 |

## 安装前必须完成

1. AMD 账户认证已完成；令牌文件权限为 owner-read-only。
2. 安装器和内部 archive 完整性检查已通过。
3. 安装配置保存在 `env/amd-vitis-2024.2-install_config.txt`。
4. 安装采用 user-local 目录，不依赖 host sudo；系统级可选库和 cable drivers 仍需另行验证。

## 安装后验收

```bash
source env/setup_fpga.sh
vivado -version
vitis -version
vitis_hls -version
```

然后执行 `scripts/check_host_env.sh`、K26 device check、HLS smoke test 和 Vivado smoke test，并把真实版本/日志写入 `env/`。

## 未执行的高风险动作

没有更换软件源，没有覆盖已有工具链（启动前未发现已有工具链），没有执行系统升级，也没有触碰 KV260 镜像、QSPI、boot firmware 或启动分区。
