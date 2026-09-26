# KV260 VLM

MiniCPM-V 4.6 在 AMD Kria KV260 上的 CPU 与 FPGA/PL 异构推理研究。仓库包含冻结输入、构建与运行参数、HLS/板端集成代码、原始实验记录及分阶段结论。当前 [`codex/rm13-integration`](https://github.com/Zhihong0615/kv260-vlm/tree/codex/rm13-integration) 收录 RM08–RM13 的集成证据；**最佳已测完整请求来自 RM10 FFN-down 引擎**，RM13 本身是质量评测与量化协议的准备阶段。

> GitHub 默认分支 [`codex/rm02-a-cpu-baseline`](https://github.com/Zhihong0615/kv260-vlm/tree/codex/rm02-a-cpu-baseline) 是早期 CPU 基线快照。这里的跨阶段报告链接固定在 RM13 集成提交 `5674df3`，便于核对，不依赖默认分支的相对路径。

## 已测板端系统结果

KV260 上完成了真实 MiniCPM-V 多模态请求，视觉 Transformer 的编号 FFN-down 调用由 PL 执行，超出硬件支持范围的 merger 调用回退到 PS/A53。下表为冻结开发请求的完整进程墙钟时间，单位秒：

| TextVQA QID / 媒体组 | CPU-only | RM09 静态 PS+PL | RM10 FFN-down PS+PL | 结果范围 |
| --- | ---: | ---: | ---: | --- |
| 38299 / 3 | 368.51 | 299.14 | **285.53** | RM09/10 与 CPU 使用同一运行时；81 次编号 PL 调用，答案 `3`。 |
| 37804 / 5 | 668.35* | 519.39 | **504.24** | 135 次编号 PL 调用，答案 `G`；RM10 比同运行时 RM09 静态实现快 2.92%。 |
| 35419 / 7 | 822.35 | 652.32 | **619.70** | RM09/10 与 CPU 使用同一运行时；189 次编号 PL 调用，答案 `SHERIFF'S`。 |

\* QID 37804 的 CPU-only 数值是 RM08 的历史冻结基线，运行时/构建与后续 RM09/10 对照并不完全相同；**RM10 的 504.24 秒不应直接用它计算受控请求加速比**。RM10 与 RM09 的 QID 37804 比较使用相同运行时，但单次运行顺序和缓存状态仍未完全平衡。全部请求的 PL 时钟约 100 MHz；这些开发请求不能代表总体吞吐或稳定延迟。详见 [RM09 里程碑](https://github.com/Zhihong0615/kv260-vlm/blob/5674df3b86adc954b1c503795b8ac5ed6788c0f2/experiments/rm09/RM09_MILESTONE_RESULTS.md)、[RM10 最佳请求原始报告](https://github.com/Zhihong0615/kv260-vlm/blob/5674df3b86adc954b1c503795b8ac5ed6788c0f2/experiments/rm10_boardprep/evidence/rm10-a-ra-q37804-20260926T084944Z/RESULTS.md)和[额外请求汇总](https://github.com/Zhihong0615/kv260-vlm/blob/5674df3b86adc954b1c503795b8ac5ed6788c0f2/experiments/rm11_post_rm10_profile/RM11_POST_RM10_PROFILE.md)。

## 研究阶段

| 阶段 | 核心结论 | 证据 |
| --- | --- | --- |
| RM02 | 在 KV260 A53 上建立 CPU-only 请求基线；属于早期快照。 | [CPU 板端报告](https://github.com/Zhihong0615/kv260-vlm/blob/432519e15dd78982d3d9bcc15c0b0b6b62d62a1c/experiments/RM02_A_CPU_BOARD_BASELINE.md) |
| RM08 | QID 37804 首次完成真实 PS+PL 全请求：522.34 秒，135 次 FFN-down PL 调用，对历史四线程 CPU-only 668.35 秒；板端恢复通过。 | [RM08 结果](https://github.com/Zhihong0615/kv260-vlm/blob/5674df3b86adc954b1c503795b8ac5ed6788c0f2/experiments/rm08/RM08_RESULTS.md) |
| RM09 | 扩展静态引擎的实际 token extent 覆盖，并用相同运行时的 CPU/PL 配对完成 QID 38299、35419。 | [RM09 结果](https://github.com/Zhihong0615/kv260-vlm/blob/5674df3b86adc954b1c503795b8ac5ed6788c0f2/experiments/rm09/RM09_MILESTONE_RESULTS.md) |
| RM10 | 十 bank 递归解耦将 FFN-down K 循环从 II=5 降至 II=1；通过数值、全系统布线和板端完整请求。保留为当前最强已测实现。 | [RM10 最佳请求](https://github.com/Zhihong0615/kv260-vlm/blob/5674df3b86adc954b1c503795b8ac5ed6788c0f2/experiments/rm10_boardprep/evidence/rm10-a-ra-q37804-20260926T084944Z/RESULTS.md) |
| RM11 | 共享 FFN-up/down 引擎通过真实张量独立板端数值检查，但 FFN-up 完整调用慢于先前 A53 参考，未运行 FFN-up 完整 VLM 请求。 | [RM11 里程碑](https://github.com/Zhihong0615/kv260-vlm/blob/5674df3b86adc954b1c503795b8ac5ed6788c0f2/experiments/rm11/RM11_MILESTONE_RESULTS.md) |
| RM12 | F16×F32 专用乘法的标量实验未通过 LUT/吞吐可行性门控；没有新全阵列布线或板端请求。 | [RM12 结果](https://github.com/Zhihong0615/kv260-vlm/blob/5674df3b86adc954b1c503795b8ac5ed6788c0f2/experiments/rm12/RM12_RESULTS.md) |
| RM13 | 预注册 W8A8/W4A8 视觉 FFN 量化契约和 TextVQA 验证划分、评分、通过阈值；尚无最终质量结论或量化板端加速结果。 | [量化契约](https://github.com/Zhihong0615/kv260-vlm/blob/5674df3b86adc954b1c503795b8ac5ed6788c0f2/experiments/rm13/quantization_contract.json) · [质量门控](https://github.com/Zhihong0615/kv260-vlm/blob/5674df3b86adc954b1c503795b8ac5ed6788c0f2/experiments/rm13/quality_gate.json) |

## 范围与使用

从上表的报告阅读输入哈希、板卡配置、资源检查、原始日志和失败记录；模型权重、完整数据及 KV260 环境需另行准备。没有公开推理 API、持续运行服务、正式 TextVQA 测试集质量或可推广的论文新颖性结论。RM11–RM13 是对新方向的门控与预注册，不代表在 RM10 之后获得了更快的完整请求。
