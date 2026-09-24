# P2 CPU TextVQA Execution Readiness Map

Updated: 2026-09-24  
Scope: offline, read-only inspection of the integrated coordinator tree and fixed runner gates. No runner invocation, dry plan, test, board/SSH action, inference, or answer/annotation inspection was performed.

## Frozen software subjects

The current coordinator tree has these source hashes:

| Subject | SHA-256 | Role in the gate |
|---|---|---|
| `scripts/run_board_cpu_p2_textvqa.py` | `8f07232ef2bcfe78e3f5cd331273796de6db87402a8e502ca4980dc89682c577` | Real-image CPU runner; current SHA must be named by the runner review. |
| `scripts/parse_board_textvqa_pilot.py` | `0e28f81cc26ec47cfe2488c680623c74accd1bef92d9a4f3a31ae2fa73ba3b8d` | Output adapter/parser; current SHA must be named by the adapter review. |
| `scripts/board_cpu_preflight_remote.py` | `16d5bf8a2158dd16f409fb6708fe60440cc95585e98f41044ce5732b192c9616` | Read-only board preflight source; runner pins this SHA. |

`review_gate()` accepts only a review file at the configured path whose body contains the exact subject SHA, `review_mode: independent_static`, `reviewer_role: independent_reviewer`, and explicit `P0: 0` and `P1: 0` fields; `SELF_REVIEW_ONLY` is rejected. The fixed paths are:

- Adapter: `reviews/kv260_cpu_p2_textvqa_output_contract_v2_independent_review.md`
- Runner: `reviews/board_cpu_p2_textvqa_runner_independent_review.md`

The primary evidence checkout contains reviews at those paths, but they bind parser SHA `06fa1518ed240d75d3c2ad90f9c41ca545f2b041182957130219c1293a44a752` and runner SHA `2b6e38daa0f1cc1b720072dd3872bdfb3f4fa1c4a7b0d36c0baab0c6567f389f`. They do not bind the current coordinator subjects. The configured paths are absent in this coordinator tree. R13 reviews E10's ordered-stop remediation and is not a substitute for either review.

## Gate inventory

| Gate | Exact evidence / condition | Current evidence | State and owner |
|---|---|---|---|
| Current adapter review | Fixed adapter review path; exact parser SHA above; required independent-static fields and P0/P1 zero. | R14 is integrated at the fixed path and binds the exact parser and runner hashes. Verdict `PASS_WITH_P2_FINDINGS`: P0=0, P1=0, P2=2. The findings are (a) scalar label text under `answer_parse_ok` can pass the raw JSON label-key scan and (b) numeric QID equality does not enforce integer JSON type. | **REVIEW GATE PASS WITH P2 FINDINGS.** Preserve both findings in any execution decision; changing the parser requires a new current-SHA review. |
| Current runner review | Fixed runner review path; exact runner SHA above; required independent-static fields and P0/P1 zero. | R15 is integrated at the fixed path and binds the exact current runner SHA. Verdict `BLOCKED`: P0=0, P1=1, P2=3. P1: the post-staging remote process sample can silently omit `/proc` read failures or PIDs appearing/disappearing/reused across samples, then reach CLI launch without `PROCESS_STATE_UNKNOWN`. P2s concern cleanup/status scan errors, cross-invocation owner-window reuse, and undurable later non-start conflicts. | **REVIEW GATE FAILS CLOSED.** E11 is scoped only to the P1; preserve the three P2s as explicit residual findings. |
| Frozen development manifest | Runner expects `datasets/textvqa_v0.5.1_dev_50_seed20260923/manifest.json`, pinned SHA `62c32317029e40895ffd8e476e8a845416dac9d1d9490dfd6efb5f28a4374962`, and the frozen manifest kind. `load_manifest()` reads its answer records. | File exists in the immutable primary checkout as an untracked (`??`) file and is absent from the coordinator tree. A Git worktree will not carry it. No manifest contents or answers were inspected. | **OPEN for a coordinator-root execution.** The eventual execution root must provide the pinned input under the expected path through a controlled, hash-checked data-staging procedure; do not copy or inspect answer data as part of the current review tasks. |
| CPU build attestation | Runner expects `experiments/raw/kv260_cpu_p2_baseline_round01/cpu_build_attestation_v1.json`, pinned SHA `48cfe4fa9c5a4647ecb193ca91c6eaa07a539abd8addb2407ec14bf4d87755c2`, schema `kv260_cpu_p2_build_attestation_v1`, pinned runtime commit, successful build, and pinned CLI SHA. | File exists in the immutable primary checkout as an untracked (`??`) file and is absent from the coordinator tree. A Git worktree will not carry it. Its contents were not copied. | **OPEN for a coordinator-root execution.** Stage only through a controlled, hash-checked evidence procedure; primary checkout remains immutable. |
| Read-only preflight source | `scripts/board_cpu_preflight_remote.py` must match the pinned source SHA. | Present in coordinator and hash matches. | **SOURCE PASS only.** Does not establish current board state. |
| Synthetic ALPHA proof | `--alpha-proof` must name a non-symlink direct child of `experiments/raw` containing `run.json`, `remote_status.json`, `raw_copy_manifest.json`, and `board_complete_snapshot/result.json`. The proof must establish one clean copied board request: synthetic pass status, `board_inference_attempted: true`, remote COMPLETE, copy return code 0/no mismatch, valid completion marker, nonempty copy manifest, successful wrapper and `time` child, verified process cleanup, and an inference start timestamp. | Coordinator raw root has no such proof. Primary raw root has host smoke ALPHA directories, but their recorded files do not include the required board run/status/copy/completion proof set. | **OPEN.** Requires a separately authorized synthetic board request and later evidence review; no such action is authorized here. |
| Owner window and execution intent | `--execute` requires one `--qid`, `--owner-window-confirmed`, nonempty `--owner-window-ref`, and `--alpha-proof`. The ref must identify the actual inference-specific reservation/owner record. | No current inference-specific owner window or execution authorization is recorded. | **OPEN.** User/board owner must provide explicit bounded authorization and reservation evidence before any board-facing operation. |
| Live resource/service gate | Fresh host and remote checks require AArch64/4 CPUs; `MemAvailable >= 2,750,000 KiB`; `CmaFree >= 700,000 KiB`; zero swap; home free space >=1 GiB; load1 <=1.5; allowed process/service states; valid timeout identity and process CPU samples. Remote worker repeats the checks immediately before spawn. | Post-reboot snapshots from 2026-09-23 passed the then-current CPU-runner CMA floor. They are historical; no current check was made in this readiness pass. | **OPEN.** Fresh checks belong only inside a separately authorized execution window. |
| P3 research image / bitstream | Separate image identity, owner reservation, verified physical recovery path, known-good rollback target, image-specific plan, and stage-specific approval. | No research image/bitstream exists; D01 runbook marks recovery and ownership unknown. | **NO_GO_NOW.** Separate from the CPU-only P2 pilot and not advanced by any P2 review. |

## Sequence and decision rule

1. R14 and R15 are integrated. R14 meets the review schema with two P2 findings; R15 blocks the current runner with one P1 and three P2s. E11 addresses only R15's P1, followed by exact-target R16 review.
2. Before using this coordinator tree as an execution root, resolve the manifest and build-attestation path gap through an approved evidence-staging method that preserves the immutable primary checkout and answer-data handling limits.
3. Keep synthetic ALPHA, live resource checks, and the inference-specific owner window as external board gates. Do not run a dry plan as a substitute for any of them.
4. Even if all P2 gates pass, execute no board request until the user has explicitly authorized the bounded CPU-only inference and the board owner window is recorded. Keep P3 `NO_GO_NOW`.

The current outcome is **NOT READY FOR BOARD EXECUTION**. Source-level P2-7 closure through E09/E10/R13 remains limited to source and local fake-test evidence.
