---
review_mode: independent_static
reviewer_role: independent_reviewer
parser_sha256: 48c834d6b803eb6a06f4be39f287913c461701ec606956c66493fe7f10d7e209
runner_context_sha256: 0ff88fd1780fa52ae5a30a6a47fe89827887d4360e20a14e9dc3269e6fb6ba92
target_commit: 6b4a3d5af46f7b44069a1a7d36e5bad88167b960
required_direct_parent: ada49814f53f3c16b3e36383dcee65cb93473118
test_sha256: a7ef837fc5a16129ce3fbe6d377ad5360b0a0d38423879c489ba275c014b9a23
source_manifest_sha256: 5396cca3e5576bc40bf8ac21f945afc9922bcea7f306ebcc6b68cc823e7da1a7
verdict: PASS_WITH_P2_FINDINGS
P0: 0
P1: 0
P2: 1
---

# Independent exact-target review: TextVQA parser contracts

## Verdict

**PASS_WITH_P2_FINDINGS** for parser SHA-256 `48c834d6b803eb6a06f4be39f287913c461701ec606956c66493fe7f10d7e209` at commit `6b4a3d5af46f7b44069a1a7d36e5bad88167b960`, directly based on `ada49814f53f3c16b3e36383dcee65cb93473118`. The two R14 production findings are fixed in the inspected source. I found no P0 or P1 issue. One P2 finding concerns how strongly the new AST test proves its source contract; it does not describe an unguarded QID read in this exact parser.

P0: 0
P1: 0
P2: 1

This meets the parser gate's P0/P1-free criterion for the exact parser hash. It is not a board-readiness verdict and does not authorize execution.

## Frozen inputs and method

The reviewer worktree was `/home/zhiro/research/kv260-vlm-workers/R17-E12-parser-review`, branch `agent/R17-E12-parser-review`. Before source review and test execution, I verified the clean worktree, exact target commit and parent, task brief and activation, source manifest SHA-256 `5396cca3e5576bc40bf8ac21f945afc9922bcea7f306ebcc6b68cc823e7da1a7`, and every entry in that manifest. All entries passed `sha256sum -c`. The frozen inputs include the E12 parser, focused test and handoff, runner context, R14 report and preserved audit copy, R14 handoff, R16 runner audit, task briefs, and taskbook.

I compared the complete E12 parser/test/handoff diff with its parent, traced each current JSON `question_id` read in the parser, and reviewed the two R14 findings against the production helpers and call sites. I did not invoke the parser or runner, inspect manifest answers or annotations, or access raw-run data, a board, SSH, network, runtime, inference, benchmark, reboot, or bitstream tools.

## R14 finding 1: `answer_parse_ok` label-key bypass

The scanner now exempts normalized `answerparseok` only when its value is a Python `bool`, which is the type produced for a JSON boolean by the standard JSON decoder. A string such as `"true"` or `"label text"`, numeric value, null, list, or object under that key returns label-bearing/invalid. The recursive traversal remains active for all other keys, so nested suspicious label keys continue to be rejected. The scanner still examines every raw JSON file and the state, command, and input records at their existing call sites.

This closes the R14 scalar-text bypass at source level. No raw JSON artifact was opened or validated in this review.

## R14 finding 2: float-equal and boolean QIDs

`qid_matches` accepts only `int` values that are not `bool`, then compares the integer to the expected QID. Thus an integer pilot QID passes while `38299.0`, `True` for `1`, and `False` for `0` fail.

I traced all current JSON QID checks. Strict matching is used for the host-copy receipt, execution state, optional non-start records, command/input records, artifact verification, post-run image verification, and selection of manifest samples into the pilot map. The additional command/input identity check uses the same helper. The completion record binds its expected run ID as a string and has no JSON `question_id` field to compare. The current direct `get("question_id")` and `record["question_id"]` accesses are all syntactically inside the relevant `qid_matches` call.

## Test fidelity and P2 finding

The focused test parses the production parser source, extracts the actual `has_label_keys` and `qid_matches` function definitions, and executes those definitions with synthetic Python values. It covers both JSON-boolean cases, non-boolean values beneath `answer_parse_ok`, recursive nested label keys, integer acceptance, float-equal rejection, and bool-as-int rejection. It reads no answer or annotation data. The source-contract test scans direct literal `.get("question_id")` and `["question_id"]` reads. Manual source review confirmed that it covers every such current parser read, including manifest mapping.

**P2 — AST guard checks containment, not the exact value argument.** The test marks a read guarded when it appears anywhere inside a `qid_matches` call's AST subtree. A future expression could put an unrelated `question_id` read elsewhere among that call's arguments and still satisfy this containment check without passing that read as the value being compared. The exact E12 parser has no such case: static tracing confirms every current read is the helper's first argument. The test's literal-key scan also does not cover dynamically constructed key names; none occur in the current parser. A follow-up can make the test assert the specific helper argument relationship or walk parent nodes.

## Unrelated parser contracts and scope

The parser diff is limited to the safe-metadata value check, the new strict QID helper, and the targeted QID comparison/manifest-selection call sites. The reviewed diff does not change scoring, answer extraction, resource gates, the runner, schemas, paths, board behavior, or evaluation logic. The focused test and E12 handoff are the only other E12 paths.

The original R14 audit report at `reviews/audit/R14_adapter_PASS_WITH_P2_FINDINGS_20260924.md` matched its pinned SHA-256 and was not modified. This report replaces only the fixed parser review path.

## Independent test record

Exactly one authorized invocation was run in the frozen reviewer worktree:

```text
$ python3 -m unittest discover -s tests -p test_p2_parser_label_qid_contract.py
......
----------------------------------------------------------------------
Ran 6 tests in 0.012s

OK
```

Exit code: 0. This is a source/helper-level synthetic test result only; it is not parser execution or real-artifact validation.

## Limitations

The verdict applies only to the exact source hashes above and the focused synthetic test. It does not validate concrete raw-run artifacts, parser behavior on a board-derived run, manifest contents, runtime behavior, inference quality, or benchmark results. No board state, owner window, or execution authorization was checked. P3 remains `NO_GO_NOW`; no board-readiness claim is made.
