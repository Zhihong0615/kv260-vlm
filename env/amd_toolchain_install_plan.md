# AMD/Xilinx 2024.2 install plan

状态：`BLOCKED — installer 未提供且当前 sudo 不可用`。

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
| 官方 installer 文件 | AMD/Xilinx Unified Installer 2024.2 | `UNKNOWN`（本机未发现） |
| installer SHA256 | UNKNOWN | 待下载后记录 |
| 安装根目录 | `/tools/Xilinx/2024.2/` | 待 root 权限和 installer |
| settings64.sh | `/tools/Xilinx/Vivado/2024.2/settings64.sh` 或安装器实际路径 | 待安装后确认 |
| 预计空间 | 完整 Vitis 约 200 GB；器件/组件选择会影响实际值 | 可用空间约 390 GB，空间层面满足 |
| 预计时间 | UNKNOWN；取决于网络、磁盘和组件选择 | 待实测 |

## 安装前必须完成

1. 用户在有交互式 sudo 的终端执行 `sudo apt update`。
2. 安装基础包：`cmake ninja-build ccache python3-pip python3-venv libcurl4-openssl-dev tmux screen htop` 及任务说明中的其余包。
3. 从 AMD 官方账户获取 2024.2 Unified Installer，并记录文件名、SHA256、下载时间和来源页面。
4. 安装器中选择 Vivado、Vitis、Vitis HLS 及 K26 所需 device support。

## 安装后验收

```bash
source /tools/Xilinx/Vivado/2024.2/settings64.sh
vivado -version
vitis -version
vitis_hls -version
```

然后执行 `scripts/check_host_env.sh`、K26 device check、HLS smoke test 和 Vivado smoke test，并把真实版本/日志写入 `env/`。

## 未执行的高风险动作

没有自动下载未知来源的 installer，没有更换软件源，没有覆盖已有工具链（当前未发现已有工具链），没有执行系统升级，也没有触碰 KV260 镜像、QSPI、boot firmware 或启动分区。
