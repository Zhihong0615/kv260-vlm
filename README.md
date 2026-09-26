# KV260 VLM

在 AMD Kria KV260 上建立可复现的多模态问答推理与性能评测基线。项目使用 MiniCPM-V 4.6、固定版本的 `llama.cpp` 和 TextVQA 开发样本，覆盖模型产物校验、主机 CPU 评测、板端运行前检、结果回传及性能分析。当前默认分支保留 RM02 CPU 基线；后续分支已完成实验性 PS+PL 端到端推理。最新研究进展见 [RM13 集成分支](https://github.com/Zhihong0615/kv260-vlm/tree/codex/rm13-integration)，完整请求结果见 [RM11 里程碑汇总](https://github.com/Zhihong0615/kv260-vlm/blob/codex/rm13-integration/experiments/rm11/RM11_MILESTONE_RESULTS.md)。

## 系统组成

| 模块 | 内容 |
| --- | --- |
| 模型与环境 | [`scripts/build_model_artifacts.sh`](scripts/build_model_artifacts.sh)、[`models/manifests/`](models/manifests/) 和 [`env/`](env/) 固定模型、量化产物、运行时版本及校验信息。 |
| 推理与评测 | [`scripts/run_board_cpu_p2_textvqa.py`](scripts/run_board_cpu_p2_textvqa.py)、[`scripts/board_cpu_preflight_remote.py`](scripts/board_cpu_preflight_remote.py)、[`scripts/parse_board_textvqa_pilot.py`](scripts/parse_board_textvqa_pilot.py) 负责有界板端请求、资源检查和结果解析。 |
| 证据与回归 | [`experiments/`](experiments/) 保存实验报告与可追溯记录；[`tests/`](tests/) 包含解析、资源门控和运行编排的契约测试。 |

## 已验证结果

- **主机 CPU 基线：**TextVQA 50 个开发样本均产生可解析输出；MMF soft accuracy 为 **0.644**，单样本新进程总耗时中位数 **8.558 秒**、P95 **12.548 秒**。配置为 x86 主机、8 线程、Q4_K_M 语言模型和 F16 视觉投影。这是小规模开发集结果，不能作为 KV260 性能或泛化精度。详见[主机工作负载报告](experiments/derived/minicpmv_hardware_relevant_workload_profile_b01.md)。
- **KV260 CPU 推理：**3 个不同的冻结 TextVQA 请求在四核 Cortex-A53 板卡上端到端完成，使用 2 线程、`--device none -ngl 0`。三个请求的板端总耗时分别约为 **670、1233、1486 秒**；其中两条与主机输出完全一致，一条输出不同。结果、失败尝试及边界见[板端 CPU 基线报告](experiments/RM02_A_CPU_BOARD_BASELINE.md)。
- **线程实验：**对同一请求分别使用 1、2、4 线程，板端 CLI 耗时为 **2290.97、1233.11、659.28 秒**，1→4 线程为 **3.48×**。2 线程结果复用上述基线；每个线程设置只有一次观测，不能推断整体吞吐或稳定加速比。详见[线程实验报告](experiments/RM03_Q37804_THREAD_SWEEP.md)。

- **后续 PS+PL 集成：**在 RM10 的两个同运行时配对请求中，纯 CPU→PS+PL 的完整请求耗时分别为 **368.51→285.53 秒**和 **822.35→619.70 秒**（约 1.29× / 1.33×）。实验报告与适用范围见[最新分支的 RM11 汇总](https://github.com/Zhihong0615/kv260-vlm/blob/codex/rm13-integration/experiments/rm11/RM11_MILESTONE_RESULTS.md)。

## 复现与使用边界

从 [`env/model_conversion.md`](env/model_conversion.md) 和 [`env/llama_cpp_build.md`](env/llama_cpp_build.md) 查看固定版本与主机准备记录，再阅读上述实验报告、运行前检脚本和契约测试。模型权重、完整数据集和板卡环境需要自行准备；仓库中的报告可以用于检查参数、输入哈希、测试口径及结果限制。

板端运行需要获得设备使用权限，并通过当次的资源、进程、输入哈希与恢复条件检查。请勿把报告中的单次实验数字解释为生产服务指标。本项目尚未提供公开推理 API 或持续运行服务；PS+PL 的板端结果是实验性请求，不代表产品吞吐或泛化性能。
