# E03 preflight validation hardening — independent review

- **review_mode:** independent static source review
- **reviewer_role:** independent reviewer
- **Verdict:** PASS
- **Findings:** P0: 0 · P1: 0 · P2: 0
- **Frozen target:** `9c048ce95400a8156c919dd0d0bb4279cace47cc`
- **Required direct parent:** `c550d3fe7e5272e6fee42d259d7f861b55ea4b2a`
- **Reviewer branch:** `agent/R06-E03-review`

## Identity and hashes

The E03 target worktree was clean at the target SHA, with the required direct parent. Its diff modifies only `scripts/run_board_cpu_p2_textvqa.py` and adds the E03 handoff. The R06 reviewer worktree started clean at the exact target.

R06 brief SHA-256: `047c54113bf7eb108fa157a7270b97845a10c2fdbc3d5ecfe26ad1663b3ec56b`; activation SHA-256: `22ccaafdf3006e71c183e1d940ed88b89e1357032e356028c5749ee30bd8b27c`; five-entry manifest SHA-256: `8fc8b41e33da2f1fcbe99aa10b7cabcadcf9d99dca03f44e5c1aa465510f1ca9`. All five manifest entries passed from the E03 repository root. E03 task brief SHA-256: `aef22eb90cf13f0e73c612000d70dc319df2169c9e9c7a15945e99b0d189eca8`; E03 activation SHA-256: `815c7b2eddd196e42b7220a6688c12086a67cb4a21a27742fbd4d3bd258cb570`.

| Manifest entry | SHA-256 |
|---|---|
| `scripts/board_cpu_preflight_remote.py` | `2366b7f5291fbb51e859e943a7453baa033cf41ed64668017689d97ddc9db959` |
| `scripts/run_board_cpu_p2_textvqa.py` | `aa44a21e98ed6bbded3681ba80f3f2f81ed5496dabf6b1f5a726f413e7270528` |
| `reviews/E02_runner_remediation_independent_review.md` | `eea470af204912ac116a18f8581ace7be28356a520ca94644b02ab60e904cc8c` |
| `orchestration/handoffs/E02_runner_remediation_handoff.md` | `3da825485a0d3f25616b63a48221af5b76821b364507c6fc4e46590b40c467bc` |
| `orchestration/handoffs/E03_runner_validation_hardening_handoff.md` | `b6151a144f3b4decba3f4507c479bffd625feb8c71b9e37d32d1d2c4b60000d6` |

## Static behavior review

- **Load parsing:** Both parsers convert the first load token to float, then reject non-finite or negative values as `LOAD_STATE_UNKNOWN`; malformed tokens and missing values reaching the parser take the same path. Host parsing is at `scripts/run_board_cpu_p2_textvqa.py:115-122`; the embedded worker parser is at `:456-459`. The host main also rejects a missing/non-string `loadavg` field through its structured `preflight_invalid` path at `:1016-1026`.
- **Threshold and ordering:** Finite nonnegative values retain the configured threshold: values above `MAX_LOAD1` (1.5, line 49) add `LOAD`; equality and lower values pass the load check. The host records a blocked preflight and nonstart records before image-directory creation or staging (`:1031-1043`). The embedded worker returns `PRECHECK_BLOCKED` when either its initial or pre-CLI snapshot has gate reasons (`:509-523`, `:563-567`), before `Popen` (`:601-604`). If reading the worker snapshot itself raises, the outer prelaunch exception path records a nonstart at `:647-661`.
- **CPU-row validation:** `cpu_rows_well_formed` is false for a wrong container, non-dict rows, missing/wrong-typed required fields, invalid counters/intervals, and non-finite or negative CPU values (`:151-167`). The busy-core threshold branch is guarded by that flag (`:183-187`), so malformed rows are not indexed. Valid rows retain unique-PID and preflight-PID checks (`:168-173`), the sample state/wait/interval/error checks (`:174-182`), and the `>= 0.25` busy-core threshold for other PIDs (`:183-187`). Reasons reach the structured preflight block and nonstart path before staging (`:1031-1043`).

The E03 handoff accurately limits the change to validation hardening. E01 P2-5/6/7, fixed review paths, ALPHA proof, live resource checks, external owner window, and other execution gates remain open; P3 remains `NO_GO_NOW`. This review establishes no board readiness.

No tests, syntax checks, dry plans, benchmarks, target-code execution, SSH, board access, inference, answer/annotation reads, or GitHub actions were performed.
