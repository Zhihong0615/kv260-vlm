# OS compatibility

审计时间：2026-09-22 至 2026-09-23。

## 当前系统

- Host OS：Ubuntu 24.04.5 LTS (`noble`)，x86-64。
- Kernel：`7.0.0-31-generic`。
- RAM：31 GiB。
- 可用磁盘：安装前约 390 GiB；2024.2 安装及验收后约 241 GiB。

## AMD 2024.2 文档核对

- Vivado 2024.2 的 UG973 支持 Ubuntu 24.04 LTS（64-bit, English）。
- Vitis 2024.2 的 UG1742 将 Ubuntu 24.04 LTS 列为开发主机支持系统；嵌入式/HLS 流程最低内存为 32 GB，完整 Vitis 安装空间为 200 GB。
- 当前 24.04.5 属于 Ubuntu 24.04 LTS 系列；AMD 文档以 LTS/基线版本表达，未单独列出 `.5`。2024.2 installer 和真实 smoke tests 已完成实测。

官方依据：

- [AMD UG973 2024.2 — Supported Operating Systems](https://docs.amd.com/r/2024.2-English/ug973-vivado-release-notes-install-license/Supported-Operating-Systems)
- [AMD UG1742 2024.2 — Installation Requirements](https://docs.amd.com/r/2024.2-English/ug1742-vitis-release-notes/Installation-Requirements)

## 判断

`PASS（文档层面）`：没有理由为了 2024.2 更换 Ubuntu 大版本，当前系统保留。

`PASS（实测）`：Vivado、Vitis、Vitis HLS 2024.2 已安装并运行；K26/KV260
device database、HLS C simulation/synthesis/IP export、Vivado
implementation/bitstream/DRC/timing 均通过。

`RESIDUAL RISK`：主机使用 7.0 内核，而 AMD 2024.2 文档按发行版支持而非
这个具体内核点版本给出保证。该风险已由本任务范围内的真实工具运行覆盖，
但不能外推为所有 cable driver 或未来第三方插件都兼容。

## 推荐处理方案

保持 Ubuntu 24.04.5 不变；继续通过 `env/setup_fpga.sh` 加载项目本地 2024.2
工具链。不要为了规避已被 smoke test 覆盖的风险而升级或降级系统。
