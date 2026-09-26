# KV260 VLM

本项目研究 MiniCPM-V 4.6 在 AMD Kria KV260 上的推理路径：从 CPU 基线、视觉 FFN-down 的 FPGA 实现，到真实 PS+PL 多模态请求的板端验证。报告保留原始运行记录、输入与构建哈希、对照条件及失败边界；这是一项研究工程，不是已上线的推理服务。

> **分支导航：**当前 GitHub 默认分支 [`codex/rm02-a-cpu-baseline`](https://github.com/Zhihong0615/kv260-vlm/tree/codex/rm02-a-cpu-baseline) 是 **RM02 CPU 基线快照**，不是项目最新进展。后续板端 PS+PL 集成与研究记录请从 [`codex/rm13-integration`](https://github.com/Zhihong0615/kv260-vlm/tree/codex/rm13-integration) 阅读。下列报告链接固定到该集成分支当前提交 `5674df3`，避免默认分支上的相对路径指向旧文件。

## 板端结果与后续阶段

| 阶段 | 已核验的进展 | 报告 |
| --- | --- | --- |
| RM02 · CPU 基线 | 三个冻结 TextVQA 请求在 KV260 四核 Cortex-A53 上完成 CPU-only 推理；作为早期板端对照，不代表后续 PL 结果。 | [RM02 CPU 板端基线](https://github.com/Zhihong0615/kv260-vlm/blob/432519e15dd78982d3d9bcc15c0b0b6b62d62a1c/experiments/RM02_A_CPU_BOARD_BASELINE.md) |
| RM08 · 首次 PS+PL 集成 | QID 37804 完成真实 MiniCPM-V 请求，135 次视觉 Transformer FFN-down 调用在 PL 执行、10 次超出范围的 merger 调用回退 CPU；**522.34 秒**，冻结四线程 CPU-only 对照 **668.35 秒**，请求级 **1.280×**。 | [RM08 板端结果](https://github.com/Zhihong0615/kv260-vlm/blob/5674df3b86adc954b1c503795b8ac5ed6788c0f2/experiments/rm08/RM08_RESULTS.md) |
| RM09 · 扩展形状覆盖 | 同一运行时的 QID 38299 / 35419 CPU-only 与 PS+PL 配对请求分别为 **368.51→299.14 秒**、**822.35→652.32 秒**；编号 FFN-down 调用在 PL 执行，答案匹配。每个请求只测一次。 | [RM09 里程碑](https://github.com/Zhihong0615/kv260-vlm/blob/5674df3b86adc954b1c503795b8ac5ed6788c0f2/experiments/rm09/RM09_MILESTONE_RESULTS.md) |
| RM10 · 最佳已测完整请求 | 十 bank 递归解耦 FFN-down 引擎在 QID 37804 完整请求达到 **504.24 秒**，对照 RM09 静态实现 **519.39 秒**（快 **2.92%**）；135 次编号 FFN-down 调用在 PL 执行，答案 `G`。这是已测最佳完整请求，但运行顺序和缓存状态仍影响单次墙钟对照。另两个请求的 RM10 结果为 285.53 / 619.70 秒。 | [RM10 完整请求原始结果](https://github.com/Zhihong0615/kv260-vlm/blob/5674df3b86adc954b1c503795b8ac5ed6788c0f2/experiments/rm10_boardprep/evidence/rm10-a-ra-q37804-20260926T084944Z/RESULTS.md) · [跨请求汇总](https://github.com/Zhihong0615/kv260-vlm/blob/5674df3b86adc954b1c503795b8ac5ed6788c0f2/experiments/rm11_post_rm10_profile/RM11_POST_RM10_PROFILE.md) |
| RM11 · 共享 FFN 探索 | 共享 FFN-up/down 位流完成路由，并在真实张量的三次独立板端 FFN-up 调用中通过数值检查；完整调用时间慢于先前 A53 CPU 参考，因此**未做 FFN-up 完整 VLM 请求**，保留 RM10 FFN-down 路线。 | [RM11 里程碑](https://github.com/Zhihong0615/kv260-vlm/blob/5674df3b86adc954b1c503795b8ac5ed6788c0f2/experiments/rm11/RM11_MILESTONE_RESULTS.md) |
| RM12 · 算术密度门控 | F16×F32 专用乘法的独立算术实验通过所列数值比较，但 LUT 代价不满足扩阵门控；**没有**完整阵列布线、新板卡镜像或新 VLM 请求，结论是继续采用 RM10。 | [RM12 结果](https://github.com/Zhihong0615/kv260-vlm/blob/5674df3b86adc954b1c503795b8ac5ed6788c0f2/experiments/rm12/RM12_RESULTS.md) |
| RM13 · 质量评测准备 | 固定了 W8A8/W4A8 视觉 FFN 量化契约与 TextVQA 验证划分、评分及通过阈值；当前记录是**预注册协议**，没有可据此宣称的量化后质量或板端性能提升。 | [量化契约](https://github.com/Zhihong0615/kv260-vlm/blob/5674df3b86adc954b1c503795b8ac5ed6788c0f2/experiments/rm13/quantization_contract.json) · [质量门控](https://github.com/Zhihong0615/kv260-vlm/blob/5674df3b86adc954b1c503795b8ac5ed6788c0f2/experiments/rm13/quality_gate.json) |

## 如何阅读结果

优先阅读[最新集成分支](https://github.com/Zhihong0615/kv260-vlm/tree/codex/rm13-integration)及上表的阶段报告。RM08/09/10 是 KV260 上真实完成的 PS+PL 请求；RM11/12/13 是后续不同门控阶段，不能视作连续提升的完整请求版本。板端运行使用冻结输入、模型及运行环境；这些小样本和单次观测不能推出通用吞吐、稳定延迟、正式 TextVQA 测试集精度或论文方法新颖性。仓库没有公开推理 API 或持续运行的产品服务。
