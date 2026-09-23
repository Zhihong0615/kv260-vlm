# KV260 CPU-only TextVQA 原图问答三请求开发验证协议（草案）

状态：**DRAFT / 未执行 / 非正式质量或性能评测**，2026-09-23。适用时点是合成 `text_alpha.png` 单请求已在 KV260 上取得完整、可核验的 `SYNTHETIC_WIRING_PASS` 原始证据之后。本文件只规划随后三个 TextVQA v0.5.1 **validation 开发集**原图请求；没有连接板卡、传图、修改运行器或运行推理。若合成请求未通过，或其远端收尾/回传证据不完整，此协议不启动。

## 目的与已知边界

目标是检查固定 MiniCPM-V 4.6 Q4_K_M + F16 mmproj 的板端 CPU 路径能否依次读取三张不同的原始 JPEG、消费各自问题并返回文本，同时记录资源和失败。三张图已经用于 host 开发分析，答案可在开发 manifest 中读到；它们不是 held-out 样本。三次不同问题的返回文本也不能单独证明视觉内容敏感性；任务书 §6.1 所需的同问异图、空白图和约 10 个接线检查请求应在下一版独立执行。

现有板端 `scripts/run_board_cpu_p2_single.py` **仅支持合成 ALPHA**：其图片、问题、`-n 8` 和答案判定均硬编码。不能通过替换板端同名文件或改 manifest 来复用该入口。真实图运行前须有一个另行版本化、静态复审的 TextVQA runner，保留合成 runner 的构建证明、远端互斥、双层超时、失败留痕和稳定回传机制；本草案不声称该 runner 已实现。

主机侧分离 stdout/stderr 的答案、图像事件及标签联结 adapter 已另写为 `scripts/parse_board_textvqa_pilot.py`，输入 schema 和失败分母在 `experiments/derived/kv260_cpu_p2_textvqa_output_contract.md`。它在一题 host 开发图像的版本化 rehearsal 中可解析答案和非零图像编码/解码事件；独立代码复审尚未完成，真实图 runner 也未实现。执行版须在该复审后冻结 adapter SHA，不能直接套用 host 旧的合并流提取器或把标签放到板端。

## 固定开发输入与选择依据

唯一输入源为 `datasets/textvqa_v0.5.1_dev_50_seed20260923/manifest.json`（SHA-256 `62c32317029e40895ffd8e476e8a845416dac9d1d9490dfd6efb5f28a4374962`）中的三行。顺序预定为 host 日志已观察到的 3、5、7 次图像编码事件，作为视觉路径多样性的接线探针；次数是 **host 后处理观察**，不是经证实的板端预调度特征，也不能据此解释延迟因果关系。选择与板端回答、板端耗时无关；任何失败后不换成“较容易”图片。

| 顺序 | TextVQA question ID | 原始 image ID / 板端文件名 | 原始图像 SHA-256 | 字节 | host 编码事件 |
| ---: | ---: | --- | --- | ---: | ---: |
| 1 | 38299 | `61715b8521ae5d6a` / `61715b8521ae5d6a.jpg` | `4365f84b5d2cbc5c740bafde088b1aeaf5c7b8326c8b9b5bfe2a529f9bc7a256` | 272,693 | 3 |
| 2 | 37804 | `58d543df7eab2bfc` / `58d543df7eab2bfc.jpg` | `3b62a66c20953428d08575fd4ab6caf98c80d942aaae0311a73d2b6c4cdf861f` | 303,977 | 5 |
| 3 | 35419 | `004b75d1299e653c` / `004b75d1299e653c.jpg` | `f703a5ce6bbf7c1aa1dd11fda26a7a30323913d404d771d51deba387c840c5f6` | 129,904 | 7 |

问题字符串逐字取自上述 manifest 的对应 `samples[*].question`，不人工转写或修正语法。三张图的 image ID 不同，原始字节哈希也不同。复制到板端普通用户目录 `~/kv260-vlm-p2-cpu/input/textvqa-dev50/` 时保持这些文件名和字节，逐张核对 SHA-256/字节数；不携带答案、OCR sidecar 或标注到板端。OpenImages 旋转元数据检查尚未为正式评测冻结；本接线探针沿用 host 使用的原始字节，不临时旋转、缩图或覆盖模型原生 crop/patch 行为。若发现源图或方向缺陷，记为数据缺陷并停止，不能在同一 run ID 下替换。

三请求的 host 对照来源为 `experiments/raw/textvqa_val_dev50_host_q4_cpu_round01/run.json` 及 `experiments/derived/textvqa_phase_timeline_three_request_comparison_and_raw_audit.md`。host dev50 使用 8 线程；以下板端拟用 2 线程，因此 host 的秒数和答案仅作开发诊断，不是板端速度或逐字一致性的验收阈值。

## 待冻结的执行配置

- 模型 GGUF SHA-256 `8795741e15ae9ebb1244806da59bcc791453a00c21e9b8075c98fb0827829773`；mmproj SHA-256 `ede8c22756385623c0ddd84512183bc71490f98fa2eda2983a8b7de557e5c293`；runtime commit `7ab4ee7baad2d920464cbacfad4f4b07cf111fd2`。使用已有板端 `cpu_build_attestation_v1.json` 绑定的 AArch64 Release CLI/本地库，运行前重新核验其哈希、ELF/动态链接和 CPU-only 配置。若二进制或参数改变，另立版本与 run ID。
- prompt 精确模板来自 host `scripts/run_textvqa_subset.py`：`Answer the following question based only on the image. Give a short, direct answer.\nQuestion: {question}\nAnswer:`。`{question}` 用 manifest 原文替换；实际完整字符串写入每个原始 `command.json`。
- 将 pinned CLI 子进程环境中的 `MTMD_TEST_RESPONSE_MARKER` 明确移除，并在 `command.json` 记录该动作及启动前是否存在；它会通过 `LOG` 污染 stdout。答案从该 CLI 的**独立 stdout** 按版本化 adapter 的严格单轮格式提取，stderr 仅用于图像事件与诊断。主机侧按 manifest SHA、question ID、image ID 和原图哈希联结十条标签，板端不传标签。
- 每张图开启**新的 CLI 进程**。固定参数：`-t 2 -tb 2 -c 4096 -n 48 --seed 42 --temp 0 --top-p 1 --top-k 0 --device none -ngl 0 --no-mmproj-offload --no-warmup --perf -lv 4`；只改变图片路径和问题。`-n 48` 是最大输出数，按正常 EOS/停止条件结束，不强迫生成 48 token。实际输出 token 数、EOS/反提示停止原因及是否触及上限仅在有独立可靠事件时填写；普通 CLI 若无法提供则写 `UNAVAILABLE`，不把 libllama eval runs 当作输出 token 数，不把正常退出推断为 EOS。模型的 `--no-nextn` 已体现在冻结的 GGUF 身份中。
- 每次 CLI 外层 `timeout --verbose --signal=TERM --kill-after=10s 300s`，`/usr/bin/time -v` 直接包裹 CLI；远端一次性脚本 watchdog 540 秒、主机 SSH 等待上限 600 秒。`wrapper_returncode`、`time_child_exit_status`、资源文件及信号/超时歧义须分开保存。只有二者为 0 且资源字段完整时，`process_peak_rss_kib` 才可称完整请求峰值。
- 三次 run ID 各自唯一、原始目录 append-only；建议 `kv260_cpu_p2_tvqa_q38299_r01`、`...q37804_r01`、`...q35419_r01`，实际 ID 在开始前冻结。每次只一个板端进程，沿用远端 `flock`，并记录执行者确认的短时独占窗口与引用。传图、模型暂存、SSH 连接和日志回传不纳入模型请求计时。

## 每次启动门槛与预算停止规则

1. 必须先检查合成 ALPHA 的完整通过证据、TextVQA runner 独立静态复审、输入及证明哈希；任一缺失不启动。板端无构建/其他 VLM/PL/XRT 研究任务，Jupyter 保持 active，系统更新已自然退出。不得停止系统升级、Jupyter、starter-kit 应用或用户作业来制造空闲。
2. 每个请求之前重新进行只读实时预检，并在 CLI 前再次检查占用。当前合成 runner 的保守门槛是 `MemAvailable ≥ 2,750,000 KiB`、`CmaFree ≥ 700,000 KiB`、swap 为 0、用户目录可用 ≥ 1 GiB、load1 ≤ 1.5、无选定忙进程及其他进程 2 秒采样 < 0.25 核。未来若 CPU-only CMA 规则被**版本化修订且独立复核**，才按该新规则执行；本草案不放宽现行门槛。记录 pre/post `/proc/meminfo`、`/proc/vmstat`、服务/进程、频率及可读温度；不可读项标 `UNAVAILABLE`，不能填估计值。现有方案没有运行中的连续采样或已审阅的自动中止阈值，故不能声称请求期间余量始终安全；post 快照中的资源/服务恶化只用于停止**后续**请求。若要在当前最长 300 秒请求中主动中止，应先另版冻结监测频率、指标、信号和阈值并复审。
3. **上限三个真实图 CLI 启动，每次最多 300 秒，合计最多 900 秒 CLI 占用。**一次短时独占窗口最多一个请求；为每个窗口预留远端/主机 watchdog 和清理时间，窗口不够则不启动。三次不排成连续高负载或自动重试。两个额外案例若将来需要，必须在任何新案例启动前另版冻结选择和预算，不因本批答案或速度临时扩展。
4. 按表中顺序推进。任一请求超时、OOM/新 `oom_kill`、活动换页、资源/服务恶化、互斥失效、输出/图像处理证据缺失、远端收尾不明或原始回传不完整，停止余下请求并保留所有失败文件；原因消除后也不复用 run ID。若首个真实图的完整进程时间接近 300 秒、或资源余量显著低于合成检查后的状态，先用实测重估其余窗口，不自动延长超时或削减图像、crop、上下文/输出预算。超出本任务书普通 P2 的长时间连续压力负载须先走相应阶段授权。

## 原始证据与结果分母

每个预定案例保存：run ID、项目及 runtime commit/源码状态、环境清单与模型/构建证明哈希、完整命令/prompt、问题/image ID、原图/模型/mmproj 的板端核验、CPU 参数、板卡占用确认、pre/post 预检、CLI 启动/结束的板端单调时钟及 UTC、独立 stdout/stderr、`/usr/bin/time` 文件、外层 wrapper 状态、实际生成文本/解析状态、可读的 image decode/MTMD encode 记录、输出 token/停止信息、RSS/swap/页故障与 OOM 增量、回传完成标志和主机/板端逐文件哈希清单。传输失败、未能确认远端子进程结束时标 `REMOTE_STATE_UNKNOWN`/证据不完整，不把部分日志算成功。原始结果不覆盖；derived 汇总可重建。

报告同时给出 **计划 3、CLI 实际启动数、正常退出数、可解析回答数、可核验原图处理数**，以及每个失败原因。启动后超时/OOM/空答/无法解析仍属于 *attempted* 分母，开发诊断评分按冻结提取规则给空字符串/0 分；预检拦截且 CLI 未启动的案例列为 *not attempted*，令三请求 pilot **未完成**，不能把它们混入已尝试请求的质量分母。原图字节、方向或其他数据缺陷若在 CLI 启动前发现，列 `not attempted/data_defect`；若启动后才发现，保留在 `attempted/data_defect` 失败类别，绝不从已尝试分母中移走。本 pilot 的方向检查尚未冻结，只保留原始字节做接线探针，不构成正式图像正确性验收。若第 1 次失败，应写成“已尝试 1/预定 3；2 未开始”，不能写成成功率 0/3 或删掉失败。

三题均需有各自**新建且不可覆盖**的原始 `result.json` 状态记录。若第一题失败后按停止规则不启动后两题，协调入口在停止时为这两个尚不存在的原始目录各写 `schema="kv260_cpu_p2_textvqa_execution_v1"`、固定 qid、`cli_started=false`、`non_start_reason="PREVIOUS_CASE_STOP_RULE"`、停止事件/先前 run ID 和 UTC；不创建板端运行目录、不伪造 stdout、模型运行或资源测量。预检拦截的案例用同一结构记录具体原因。只有这样，主机 adapter 才能把计划三题完整区分为 1 attempted/2 not attempted；缺少某题 `result.json` 时 `attempted` 保持未知、pilot 状态为证据不完整，不能凭目录缺失断言“未开始”。未来真实图 runner/协调器须实现并独立复审此状态写入，不能事后改写已有原始记录。

`image_processing_verified` 的待执行谓词来自固定源码与分离流契约：唯一 `--image` 路径对应 manifest qid/image ID 和 CLI 前校验的原图字节/SHA；该次 CLI 正常退出且回传完整；同一原始 stderr 中至少有一组有序、正数的 MTMD 编码完成和 `n_tokens_batch>0` 的图像解码完成事件，没有未配对事件或 ERROR 级日志。host 的 3/5/7 编码次数只是描述，不是板端通过阈值。这个标签是源码控制流加日志的接线推断，不证明图像内容感知正确；若事件格式不符或绑定缺失，标 false 并停止后续请求。具体字段/哈希与解析失败判定由 `experiments/derived/kv260_cpu_p2_textvqa_output_contract.md` 定义，须经独立复审并由专用 runner 实际产生。

仅在三题原始状态及所有已启动请求的输出和失败状态锁定后，主机侧用现有 pinned MMF TextVQA scorer 做**逐题开发诊断**；不在板端使用参考答案修正输出，也不靠已知答案选最佳一轮。可列三题 soft accuracy 与 host 对应预测/标准化结果，但不报告三题总体质量等价、置信区间、p95/p99、板端吞吐、PL 收益或 TextVQA 官方 `test-std` 分数。该 pilot 对正式 held-out split 无贡献；正式质量样本、评分 parity、失败规则和预算见 `datasets/evaluation_protocol_draft.md`，须先冻结再运行。

## 冷进程与在线计时标签

本 pilot 的可直接取得的主时间是**每题 fresh-process wall**：从启动 CLI 包装器到进程退出，包括模型载入、OS page fault、原图读取、processor、生成和收尾；不包括先前 rsync、SSH 调度与回传。没有清 page cache，故“新进程”不等于“冷存储”。`--perf` 的模型加载/prompt/decode内部计数只作辅助，可能与其他阶段重叠，不相加为端到端分解。现有普通 CLI 尚无板端 `t_0`（原图和问题已就绪、开始处理）与首 token 单调时钟埋点，因而本 pilot **不产生**任务书 §13.1 的在线请求时延或 TTFT，也不与 host 独占时间线的 online 数字直接比较。常驻进程/热请求需要独立 runner、固定无图像 embedding/答案缓存的协议和新 run ID，不能把这里后两次 fresh CLI 称为热请求。

## 来源与推进条件

依据：任务书 v3 §§6.1、6.3、13、16；`datasets/evaluation_protocol_draft.md`；host dev50 原始 run、评分与三请求时间线；`experiments/derived/kv260_cpu_p2_single_request_runner_protocol.md`、`reviews/board_cpu_p2_runner_final_review.md`、`handoff/board_cpu_cma_gate_review.md`。现时板端只完成 CPU build/loader/输入哈希核验，尚无本协议的任何真实图板测。下一步先等待合成 ALPHA 完整成功与实时门槛自然放行，再实现并独立复审专用真实图 runner，随后才冻结本草案为执行版。
