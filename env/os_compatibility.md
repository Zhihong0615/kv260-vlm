# OS compatibility

审计时间：2026-09-22。

## 当前系统

- Host OS：Ubuntu 24.04.5 LTS (`noble`)，x86-64。
- Kernel：`7.0.0-31-generic`。
- RAM：31 GiB。
- 可用磁盘：根分区约 390 GiB。

## AMD 2024.2 文档核对

- Vivado 2024.2 的 UG973 支持 Ubuntu 24.04 LTS（64-bit, English）。
- Vitis 2024.2 的 UG1742 将 Ubuntu 24.04 LTS 列为开发主机支持系统；嵌入式/HLS 流程最低内存为 32 GB，完整 Vitis 安装空间为 200 GB。
- 当前 24.04.5 属于 Ubuntu 24.04 LTS 系列；AMD 文档以 LTS/基线版本表达，未单独列出 `.5`。具体 2024.2 installer 运行仍需实测。

官方依据：

- [AMD UG973 2024.2 — Supported Operating Systems](https://docs.amd.com/r/2024.2-English/ug973-vivado-release-notes-install-license/Supported-Operating-Systems)
- [AMD UG1742 2024.2 — Installation Requirements](https://docs.amd.com/r/2024.2-English/ug1742-vitis-release-notes/Installation-Requirements)

## 判断

`PASS（文档层面）`：没有理由为了 2024.2 更换 Ubuntu 大版本，当前系统保留。

`RISK`：主机使用 7.0 内核，而 AMD 2024.2 文档按发行版支持而非本机这个内核点版本给出保证；Vivado/Vitis 安装及 smoke test 仍需在安装器可用后实测。

`BLOCKED`：Vivado/Vitis/Vitis HLS 尚未安装，无法完成工具链兼容性和器件数据库实测。

## 推荐处理方案

保持 Ubuntu 24.04.5 不变；安装 AMD/Xilinx 2024.2 Unified Installer 到统一路径，并在安装后用 `settings64.sh`、版本命令、K26 device check、HLS smoke test 和 Vivado smoke test 逐项确认。不要为了规避未知风险而升级/降级系统。
