# KV260 CPU-only TextVQA 三题 pilot：分离流与主机评分契约 v2

状态：**主机 adapter 修订并重算 round02；板端三题未执行。当前代码只有本地定向检查和 Builder 自查，独立复审未完成。**本版回应 `reviews/kv260_cpu_p2_textvqa_output_contract_independent_review.md` 的 P1 三项和 P2 证据口径。后续又收紧直接子目录、递归标签/符号链接检查、marker 前态、未启动字段矛盾检查、非启动先前 run 约束、执行前后资源与图像完整性，以及板端构建/ELF/动态链接证明；旧契约和早期派生保持历史原样；当前主机开发复算是 `textvqa_split_stream_rehearsal_host_round02_scored_v7.json`。

脚本 `scripts/parse_board_textvqa_pilot.py` 当前 SHA-256 为 `47eb6b5a06a98f75992a0df0d7f5de2edad8bea246cdd2732d69d9ea3224c872`。它只读 `experiments/raw/` 内 case 文件、冻结的开发 manifest、pinned MMF scorer 和板端构建证明；输出用独占创建写到新的 `experiments/derived/*.json`。manifest SHA-256 必须为 `62c32317029e40895ffd8e476e8a845416dac9d1d9490dfd6efb5f28a4374962`；qid 固定为 38299、37804、35419。参考答案仅从**主机** manifest 加入评分，板端 raw JSON 不许含标签字段。评分只供开发诊断。当前 adapter 的主机侧复算、非启动矛盾和图像事件定向检查已通过；**独立复审仍是板端评分门的阻塞项**。

## 模式与分母

`--mode pilot` 要求全部三个 qid 的独立原始目录，目录必须是 `experiments/raw/` 的直接子目录，完整名称精确为 `kv260_cpu_p2_tvqa_q38299_r01`、`...q37804_r01`、`...q35419_r01`；同一目录不能复用。实际 run ID 若在执行前另版冻结，须更新 adapter/契约并复审，不能临时把任意目录当板端案例。`--mode rehearsal` 只允许一题位于 `experiments/raw/` 下的直接子目录。调用示例：

```bash
python3 scripts/parse_board_textvqa_pilot.py --mode pilot \
  --case 38299=experiments/raw/kv260_cpu_p2_tvqa_q38299_r01 \
  --case 37804=experiments/raw/kv260_cpu_p2_tvqa_q37804_r01 \
  --case 35419=experiments/raw/kv260_cpu_p2_tvqa_q35419_r01 \
  --output experiments/derived/kv260_cpu_p2_tvqa_pilot_r01_scored.json
```

每个目录的 `result.json` 必须给 `schema="kv260_cpu_p2_textvqa_execution_v1"`、qid 和布尔 `cli_started`。未启动状态还必须有 UTC `non_start_at_utc`，以及 `prior_run_id`（没有先前停止请求时置 `null`）。`non_start_reason` 只接受 `PREFLIGHT_BLOCKED`、`OWNER_WINDOW_UNAVAILABLE`、`PRIOR_CASE_FAILED`、`PRIOR_CASE_STOP_RULE`、`PRIOR_CASE_UNRESOLVED`、`INPUT_UNAVAILABLE`、`REVIEW_GATE_MISSING`、`RUNNER_ABORTED_BEFORE_SPAWN`。三种 `PRIOR_CASE_*` 原因要指向顺序更早的固定 qid run ID；其他未启动原因不允许带先前 run ID。如果 `cli_started=false` 却出现任何执行专属字段（包括启动/结束时间、文件哈希、timeout、wrapper/子进程退出状态、完成标记、spawn/capture 证据、runner 哈希或远端目录），或有非空 stdout/stderr/resource，状态变为 `attempted=null` 和 `ATTEMPT_STATE_INVALID`，**绝不从分母移除已启动迹象**。在早退前也递归扫描该目录内每个 raw JSON 的禁带标签键，并拒绝符号链接；已知三个 schema 还执行顶层字段允许列表。大小写、下划线等规范化后的 `answer`、`reference`、`groundtruth`、`label`、`annotation` 等键均拒绝。任意自由文本里的泄露仍需 runner 源码审阅，静态键检查不能证明不存在。

`cli_started=true` 后，即使所有其余证据失败，也保留在 *attempted* 分母，预测为空串、soft accuracy 0。缺失/损坏 `result.json` 或状态矛盾时，尝试数及质量分母为 `null`，需要人工还原，不能当 `not attempted`。报告计划数 3、实际尝试数、正常退出数、可解析数、图像处理证据通过数及逐题错误；未启动案例不获分数。`pilot_coverage_complete` 只说明三题均已启动，并不代表质量、在线延迟或 PL 验收。

## 已启动案例的原始 schema

目录必须包含 `command.json`、`input_verification.json`、`artifact_verification.json`、`preflight_before.json`、`preflight_after.json`、`image_post_verification.json`、独立字节流 `stdout.log`/`stderr.log` 和 `resource.txt`。`result.json` 逐字节绑定所有这些回传文件，并含相应 SHA 键；还需 `started_at_utc`、`wrapper_returncode`、`time_child_exit_status`、布尔 `execution_complete`/`raw_copy_complete`。adapter 重算这些哈希，核对前后资源闸门和图像运行后 SHA，并核对原图 `question_id + image_id + SHA-256 + bytes` 与冻结 manifest 中唯一项及预启动时间顺序。

`command.json` schema 为 `kv260_cpu_p2_textvqa_command_v1`，含 qid、image ID、manifest/runtime/model/mmproj/CLI SHA、图像路径/SHA/字节、实际传给 wrapper 的完整字符串 `argv`、工作目录、写入时间和明确的环境记录。`input_verification.json` schema 为 `kv260_cpu_p2_textvqa_input_verification_v1`，含同一 qid/image ID/图像路径/SHA/字节、`verification_returncode=0`、`verified_before_cli=true`、`verified_at_utc`；pilot 的 `verification_scope` 须为 `board_filesystem_prelaunch`，主机预演为 `host_filesystem_prelaunch`。两个 UTC 时间不得晚于 `result.json.started_at_utc`。`command.environment` 必须明确 `MTMD_TEST_RESPONSE_MARKER="UNSET"`、`marker_removed_before_launch=true`，并以布尔值记录 `marker_was_present_before_removal`；runner 必须真的从 CLI 子进程环境删除变量。仅凭 stdout 看不到 marker 不构成环境归因。

适配器比较**整个 argv 数组**，包括 timeout/time 包装、资源文件、CLI、`-m`、`--mmproj`、唯一 `--image`、manifest 精确问题 prompt、全部固定 CPU/采样/日志参数和相对次序。pilot 路径锚定 `/home/ubuntu/kv260-vlm-p2-cpu/`：CLI `build-cpu/bin/llama-mtmd-cli`，模型/mmproj `input/`，三张原图 `input/textvqa-dev50/`，资源文件 `runs/<冻结 run ID>/resource.txt`；外层 `timeout --verbose --signal=TERM --kill-after=10s 300s`，内层 `/usr/bin/time -v -o ...`。主机 rehearsal 使用固定本地文件路径与 60 秒/5 秒 kill-after。额外或重复的模型、图像、prompt、CPU、采样、输出、日志选项均不接受。模型和 mmproj SHA 固定为 `8795741e15ae9ebb1244806da59bcc791453a00c21e9b8075c98fb0827829773` 与 `ede8c22756385623c0ddd84512183bc71490f98fa2eda2983a8b7de557e5c293`。

pilot 额外需要 `artifact_verification.json`（schema `kv260_cpu_p2_textvqa_artifact_verification_v1`）：qid、runtime commit、`verification_returncode=0`、`verified_before_cli=true`、`verification_scope="board_filesystem_prelaunch"`、`verified_at_utc`、CLI/模型/mmproj 的**预运行板端路径与 SHA**、`cpu_build_attestation_sha256`；其文件 SHA 由 `result.json.artifact_verification_json_sha256` 绑定。资源快照使用 schema `kv260_cpu_p2_textvqa_runtime_preflight_v1`，只在固定 `MemAvailable`、CMA、无 swap、Jupyter、磁盘、负载和 updater 门槛全部满足时填空 `gate_reasons`。`image_post_verification.json` 必须在 CLI 退出后重新检查原图的 SHA/字节与输入一致。`result.json` 还要求对应的文件 SHA、正整数 `spawn_pid`、按无空格 UTF-8 JSON argv 数组计算的 `spawn_argv_sha256`、`stdout_stderr_same_child_capture=true`、匹配的 `remote_run_dir`、`remote_process_cleanup_verified=true`，以及与专用 `scripts/run_board_cpu_p2_textvqa.py` 实际文件一致的 `runner_sha256`。完整的执行专属字段集合在 `cli_started=false` 状态下一律矛盾。CLI 启动后 runner 异常时尽量保留 attempted partial result；不完整流或后置证据会被记为 attempted-unscorable，无法证明远端收尾/清单则保留为未知状态，停止后续题目。runner 静态复审应确认这些值来自一次真实 `Popen` 与同一子进程的两个独立文件描述符，而非事后自述。

这些哈希与路径检查证明**原始记录内部一致，并联结预运行构建/文件校验记录**。主机 adapter 不连接板端，无法单凭 JSON 证明操作系统实际执行的是记录中的 ELF，也无法给没有 PID 的 stderr 每行作独立进程归属。该事实需由专用 runner 的源码、过程捕获和远端收尾记录共同审核。预运行 SHA 不能单独证明 CLI 打开图像瞬间的字节；执行版应保持输入不可变并增加运行后 SHA 证据。缺失这些前提时，输出不得表述成已独立证明执行文件或图像内容。

当前 runner SHA-256 为 `1fa965ed6b79657cd87e72319adc89aecc5d4378c570075ef45bf3c2dd915a98`；主机入口、内嵌远端 worker 与远端状态探针语法已分别编译。主机预检/图像暂存失败写明确未启动状态；远端 `Popen` 后的异常保留 attempted 记录，只在退出和进程清理可验证时封存原始清单。runner 的 dry plan r03 仅为本机规划记录，没有 SSH 或板端访问。执行门前必须有成功的合成 `ALPHA`、当前 adapter 与 runner SHA 的独立静态复审、明确 owner window 和当时通过的 live resource gate；review 文本必须标记 `review_mode: independent_static` 与 `reviewer_role: independent_reviewer`。当前独立复审文件与 ALPHA 均缺失，故执行不放行。

## stdout、图像事件与不可见字段

pinned `runtime/llama.cpp` commit `7ab4ee7baad2d920464cbacfad4f4b07cf111fd2` 中，`GGML_LOG_LEVEL_NONE` 的生成文本经 stdout，INFO 图像事件经 stderr。单轮 stdout 只接受 `\n<非空答案>\n\n` 或 `\n<非空答案>\n\n\n`；答案本体不得以换行起止，不能是空串、控制字符、超长输出或日志行。前后普通空格可在抽取后 trim。此前过宽的形态 `\n\n3\n\n`、`\n3\n\n\n\n\n` 现均失败。原始 stdout/stderr 绝不能合并或经过 shell 重定向混流。

stderr 状态机按 pinned INFO 格式配对 `encoding mtmd batch, n_chunks = ...` / `mtmd batch encoding done in ... ms` 及 `decoding image batch i/total, n_tokens_batch > 0` / `image decoded (batch i/total) in ... ms`。编码未完成时不接受 image decode，decode 批次未完成时不接受新编码；同一 decode 组编号必须从 1 递增到固定 total，且一批编码可覆盖多个 media chunk、一个 chunk 可以有多个 decode batch。它以 `n_chunks` 为可消费的媒体 chunk 数，不强制 encode/decode 组数 1:1；未配对、重叠、进度回退或 ERROR 级日志使 `image_processing_verified=false`。CLI 的 `load_media` 失败则不会进入后续图像编码；因此命令/预启动 SHA 和同次非零图像编码与解码形成**源码控制流上的接线推断**，仍不证明模型确实理解图片。host 的 3/5/7 编码次数不作板端阈值。

普通 CLI 没有可靠的实际生成 token 数、EOS/antiprompt 原因或触及 `-n 48` 事件。adapter 将 `output_token_count`、`stop_reason_eos_or_antiprompt`、`max_new_tokens_hit` 固定为 `UNAVAILABLE`；正常退出、文本长度和 libllama eval runs 都不能替代这些字段。

## 只读复算的主机证据

原始 `experiments/raw/textvqa_split_stream_rehearsal_host_round02/` 未覆盖。它在创建子进程前从环境删除 `MTMD_TEST_RESPONSE_MARKER` 并记录原先变量不存在；同一张 qid38299 开发 JPEG、2 线程、60 秒上限，进程耗时 **10.853 s**，wrapper 和 `/usr/bin/time` child 均退出 0。新版派生 `experiments/derived/textvqa_split_stream_rehearsal_host_round02_scored_v7.json` 按当前 adapter SHA 重新读原始文件：attempted 1、正常退出 1、可解析 1、图像处理证据通过 1，stdout 预测 `3`，stderr 有 3 组完成编码、3 组完成 image decode、正数 image embedding token 批次合计 194；主机开发标签十条均为 `13`，soft accuracy **0.0**。此版本拒绝原始目录符号链接、递归查标签键、验证 marker 前态、拒绝完整启动字段集合与 false 状态并存，并校验冻结 pilot 目录/完整 argv/构建和板端动态链接证据。当前定向检查包括 false-start 矛盾、合法未启动、encode/decode 顺序和历史 rehearsal 重算；均为本地主机纯函数/复算检查。以上仅验证主机分离流解析/标签联结，**没有板端三题结果**，且当前 adapter/runner 独立代码复审仍待完成。round01 仍仅作流形态观察，因为缺少启动时 marker 删除与完整 schema。
