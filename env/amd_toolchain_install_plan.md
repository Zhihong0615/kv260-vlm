# AMD/Xilinx 2024.2 installation and acceptance record

状态：`INSTALLED — 主机端工具链与 smoke test 已通过；板端只读权限验收已通过`。

## 安装结果

以下工具已统一安装到项目本地目录
`/home/zhiro/research/kv260-vlm/tools/Xilinx/`：

- Vivado 2024.2（Build 5239630）
- Vitis 2024.2（Build 5238363）
- Vitis HLS 2024.2（Build 5238294）

器件支持包含：

- Zynq UltraScale+ MPSoC
- Kria K26 / KV260 对应器件

未主动选择 Versal AI Engine、Alveo 全系列、MATLAB Model Composer、
System Generator 等无关组件。

## 安装记录

| 项目 | 最终值 | 状态 |
|---|---|---|
| 官方 installer 文件 | `FPGAs_AdaptiveSoCs_Unified_2024.2_1113_2356_Lin64.bin` | AMD 官方 Web Installer；Makeself 自检 PASS |
| installer SHA256 | `accbea8a0f4096d5242aaef2ad22d3b349a791163a366add48628ab96960a395` | 已记录 |
| 安装根目录 | `/home/zhiro/research/kv260-vlm/tools/Xilinx/` | project-local；约 136 GB |
| settings64.sh | `tools/Xilinx/Vitis/2024.2/settings64.sh` | 已加载并验证 |
| 下载选择 | Vitis Unified、Kria SOM/Starter Kit、Zynq UltraScale+ MPSoC、Edge acceleration devices | 约 93.74 GB |
| 安装耗时 | 文件安装阶段 3 小时 45 分钟 | 正常完成 |
| 下载缓存 | `tools/Xilinx/Downloads/` | 安装器成功收尾时自动清空 |
| 根分区余量 | 验收时约 241 GB；中间文件清理后约 246 GB | 安全 |

安装过程中因根分区安全余量不足主动暂停解包；在清理用户明确授权的旧
安装包后，使用磁盘空间 guard 保护下恢复。未删除未完成下载缓存。
完整验收及独立复核后，删除了已不再使用的模型下载分片、Web Installer
原始副本与解包目录、HLS/Vivado `build/` 目录，约回收 5 GB。模型、
`tools/Xilinx/` 已安装内容和 `evidence/` 下的报告与 bitstream 均保留。

## 验收结果

```bash
source env/setup_fpga.sh
vivado -version
vitis -v
vitis_hls -version
```

实际结果：

- 三个工具均真实报告 2024.2
- Vivado 数据库包含 2 个 `xck26` part 和 3 个 KV260 board part
- Vitis HLS C simulation、C synthesis、IP export 均通过并保留真实报告
- Vivado implementation、routing、DRC、timing 和 bitstream 生成均通过
- 模型环境检查及 `models/SHA256SUMS` 的 4 个文件全部通过
- KV260 SSH、FPGA Manager、CMA、XRT Device Ready 和 `xmutil listapps` 通过

Vitis 2024.2 使用 `vitis -v` 查询版本；`vitis -version` 不是该版本 CLI 的
有效版本参数。

## 未执行的高风险动作

没有更换软件源，没有覆盖其他版本工具链，没有执行系统升级，也没有向
KV260 编程或加载新 bitstream；板卡镜像、QSPI、boot firmware、DTBO 和启动
分区均未改动。安装器提示的系统级可选库与 cable driver 安装未使用 host
sudo；本任务要求的真实主机 smoke tests 已在当前环境通过。
