---
review_mode: independent_static
reviewer_role: independent_reviewer
parser_sha256: 06fa1518ed240d75d3c2ad90f9c41ca545f2b041182957130219c1293a44a752
tests_sha256: 13a822c1d8694bdf4bb3faf54ef7e94f1b3d58de1e30298929ea44250010cb58
p0_count: 0
p1_count: 0
p2_count: 1
---

# KV260 CPU-only TextVQA adapter v2 independent static review

Review date: 2026-09-23. Scope: the requested parser and focused contract tests, plus read-only inspection of the runner's receipt producer and previous-case reassessment call path. The two requested SHA-256 values were checked and match. No tests, SSH, board commands, inference, or reviewed-source edits were performed.

## Verdict

**P0: 0; P1: 0; P2: 1.** The previous two P1 defects are repaired in these exact parser/test hashes. The adapter's pilot integrity gate is suitable for the runner review gate, with one low-priority type-hardening item recorded below.

## Checks that passed

- `has_label_keys()` now exempts the normalized `answer_parse_ok` metadata key while recursively checking its child. This makes the runner's boolean assessment fields compatible with `inspect_raw_json_labels()` and still catches nested keys such as `reference`. The focused tests exercise the normal boolean, a true ground-truth key, and a nested reference key.
- Repeat assessment is compatible with the runner's current record shape: the runner writes `runner_host_assessment.json` and `runner_record_final.json` after the first assessment, and `assess_previous()` reparses that raw directory before starting the next qid. The current boolean `answer_parse_ok` field no longer makes that second parse fail the label-key scan. Host-only records remain outside the fixed board completion manifest.
- Pilot parsing now requires `completion.json` and `host_copy_verification.json`. The completion verifier checks a fixed schema and qid-specific run ID, UTC timestamp, positive non-boolean worker PID, the exact frozen board-file set, safe fixed basenames, regular non-symlink files, exact metadata keys, byte lengths, and SHA-256 for every listed board file, including `result.json`. The completion file itself is returned as a digest rather than incorrectly self-included in its manifest.
- The host receipt is checked against the qid/run ID, the computed completion JSON digest, `board_files_verified is True`, and the exact sorted list of board files plus `completion.json`; its timestamp must parse as UTC. The runner producer first validates copied files against the board manifest, then writes this receipt. The parser places the verified completion digest and manifest-verification status in its derived case record.
- The mutation test changes both `stdout.log` and the `result.json` self-reported stdout digest while leaving the board completion manifest untouched; manifest validation rejects the change. This closes the previous self-consistency-only scoring path.
- Attempt-state handling remains conservative: confirmed non-starts are excluded, contradictory or missing attempt state remains unknown, and once `cli_started` is true, missing or invalid evidence retains an empty prediction and zero score in the attempted denominator. Pilot aggregation sets the denominator to unknown if any case's attempt state is unknown.

## P2 finding

### P2-1 — The safe metadata exception does not enforce the boolean type of `answer_parse_ok`

`has_label_keys()` exempts every value under normalized key `answerparseok` and only searches nested dictionary/list keys. Therefore `has_label_keys({"answer_parse_ok": "ground truth text"})` returns false, even though the runner's current contract uses this field as a boolean. The present runner output is safe, and this is not a current-workflow blocker; constraining the exception to a boolean would make the label scan robust against malformed or repurposed host metadata.

**Recommended hardening:** permit this exception only when the value is a `bool`; otherwise report a raw JSON contract error. Add a test for a non-boolean value alongside the existing boolean and nested-reference cases.

## Evidence limits

The completion and receipt checks establish an internally consistent local copy against the board-produced manifest and tie the receipt to the completion digest. These are unkeyed hashes and JSON records, not signatures; by themselves they do not prove resistance to a coordinated rewrite of the completion file, receipt, and all copied files. No board evidence is implied by this static review.
