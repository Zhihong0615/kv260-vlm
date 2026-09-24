---
review_mode: independent_static
reviewer_role: independent_reviewer
parser_sha256: 0e28f81cc26ec47cfe2488c680623c74accd1bef92d9a4f3a31ae2fa73ba3b8d
runner_sha256: 8f07232ef2bcfe78e3f5cd331273796de6db87402a8e502ca4980dc89682c577
base_commit: ad51e2784fbbc0697232ed265e49d2e804f18b9d
verdict: PASS_WITH_P2_FINDINGS
P0: 0
P1: 0
P2: 2
---

# Independent R14 review: current TextVQA adapter

## Scope and method

Reviewed the frozen parser `scripts/parse_board_textvqa_pilot.py` and the relevant runner producer/consumer path in `scripts/run_board_cpu_p2_textvqa.py`. The assigned branch, base, clean worktree, source-manifest digest, and every listed source digest matched the R14 activation record before source review. The parser digest is the exact required target.

The review was static and source-only. It traced board completion-manifest creation, host-copy verification, adapter validation, and the conditions that permit a parsed prediction and score. No parser or runner code was executed; no tests, dry plan, answer/annotation contents, board, runtime, or external service were accessed.

## Findings

### P2 — Label-key scan can accept scalar label text in raw JSON

`has_label_keys` exempts normalized `answerparseok` from the suspicious-key test, then recurses into its value. Scalar leaves are not inspected, so a string value is treated as safe. `inspect_raw_json_labels` scans every JSON file but does not restrict raw JSON filenames to an allowed set or schema. A syntactically valid extra JSON file, or an altered host assessment JSON, can therefore carry label text under `answer_parse_ok` without producing a label error; the adapter can continue to score if the other evidence passes. The runner's normal assessment producer writes a boolean here, but the parser does not enforce that for this unmanifested host record.

References: `scripts/parse_board_textvqa_pilot.py:453-469`, `531-546`; runner producer: `scripts/run_board_cpu_p2_textvqa.py:1441-1443`.

### P2 — QID equality checks do not enforce an integer JSON type

The parser compares `question_id` values to the integer `qid` using equality, including in the execution record and host-copy receipt. JSON `38299.0` compares equal to integer `38299` in Python, so such a malformed typed identity passes these checks. The runner emits integer QIDs, and this does not permit a different numeric QID to be substituted, but strict malformed-record rejection should also enforce the expected integer type.

References: `scripts/parse_board_textvqa_pilot.py:732-734`, `514-528`; runner producer: `scripts/run_board_cpu_p2_textvqa.py:1418-1423`.

## Completion and receipt assessment

For pilot mode, the parser requires a completion record, exact completion keys and schema, the expected run ID, a UTC timestamp, and a positive non-boolean worker PID. It requires the exact frozen board-file name set; each entry has exactly byte-count and SHA fields, and each corresponding direct-child file is checked for symlink status, regular-file status, size, and SHA-256. The host receipt has an exact key set and is checked for schema, QID, run ID, completion-file digest, a literal `true` verification flag, the expected sorted filename list, and a UTC timestamp. The runner creates that receipt only after its local copy verification loop succeeds, and the parser repeats verification before accepting it.

Malformed or incomplete required files stop the attempted case before answer parsing. The runner's previous-case assessment and current-case score both consume the same parser result and require `answer_parse_ok` plus `image_processing_verified` before treating the case as passed.

## Exact-target verdict

**PASS_WITH_P2_FINDINGS** for the exact parser SHA above: the completion-manifest and host-copy handoff checks are structurally consistent with the runner producer, and no P0 or P1 issue was identified. The parser does not fully meet a strict interpretation of rejecting every label-bearing raw JSON record or every incorrectly typed QID, as detailed in the two P2 findings. This verdict is limited to this static source review and is not a board-readiness or owner-window attestation.

## Limitations

This review did not execute code or validate concrete raw-run artifacts. It does not establish board state, runtime behavior, inference quality, or whether a particular host copy is authentic beyond the checks visible in the reviewed source.
