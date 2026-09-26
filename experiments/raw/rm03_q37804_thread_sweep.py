#!/usr/bin/env python3
"""RM02 one-off host wrapper around the frozen remote CPU request worker."""
from __future__ import annotations
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "scripts/vendor")]
import run_board_cpu_p2_textvqa as runner

runner.ORDER = (38299, 37804, 35419)
THREADS = int(os.environ.get("RM03_THREADS", "1"))
RUN_ID = os.environ.get("RM03_RUN_ID", "kv260_cpu_p2_tvqa_q37804_rm03_t1")
if THREADS not in (1, 4):
    raise ValueError("RM03_THREADS must be 1 or 4")
runner.RUN_IDS = {38299: "kv260_cpu_p2_tvqa_q38299_r02",
                  37804: RUN_ID,
                  35419: "kv260_cpu_p2_tvqa_q35419_r03"}
# RM02 authorization: a load-only monitor result is advisory after a direct
# board conflict check; keep the resource/process/service gates intact.
runner.MAX_LOAD1 = 4.0
_expected_argv = runner.expected_argv

def expected_argv(qid, sample, board_run_dir):
    argv = _expected_argv(qid, sample, board_run_dir)
    if qid == 37804:
        argv[argv.index("-t") + 1] = str(THREADS)
        argv[argv.index("-tb") + 1] = str(THREADS)
    return argv

runner.expected_argv = expected_argv


def load_direct_adapter():
    spec = importlib.util.spec_from_file_location("rm02_textvqa_adapter", runner.PARSER_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    from m4c_evaluators import TextVQAAccuracyEvaluator
    evaluator = TextVQAAccuracyEvaluator()

    class DirectAdapter:
        @staticmethod
        def verify_board_completion_manifest(raw_dir: Path, qid: int) -> str:
            path = raw_dir / "completion.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            run_id = runner.RUN_IDS[qid]
            if data.get("schema") != "kv260_cpu_p2_textvqa_board_completion_v1" or data.get("run_id") != run_id:
                raise ValueError("board completion identity mismatch")
            manifest = data.get("manifest")
            if not isinstance(manifest, dict) or set(manifest) != module.PILOT_BOARD_FILE_NAMES:
                raise ValueError("board completion file set mismatch")
            for name, meta in manifest.items():
                target = raw_dir / name
                if target.is_symlink() or not target.is_file() or target.stat().st_size != meta.get("bytes"):
                    raise ValueError("board completion file missing or size mismatch: " + name)
                digest = hashlib.sha256(target.read_bytes()).hexdigest()
                if digest != meta.get("sha256"):
                    raise ValueError("board completion hash mismatch: " + name)
            return hashlib.sha256(path.read_bytes()).hexdigest()

        @staticmethod
        def inspect_case(qid, raw_dir, sample, manifest, manifest_sha, manifest_path, ev, mode):
            errors = []
            try:
                state = json.loads((raw_dir / "result.json").read_text())
                command = json.loads((raw_dir / "command.json").read_text())
                artifact = json.loads((raw_dir / "artifact_verification.json").read_text())
                inputs = json.loads((raw_dir / "input_verification.json").read_text())
                image_post = json.loads((raw_dir / "image_post_verification.json").read_text())
                stdout = (raw_dir / "stdout.log").read_bytes()
                stderr = (raw_dir / "stderr.log").read_bytes()
                events = module.inspect_events(stderr.decode("utf-8", errors="strict"))
                candidate, parse_error = module.extract_stdout(stdout)
                expected_argv = runner.expected_argv(qid, sample,
                    f"{runner.BOARD_BASE}/runs/{runner.RUN_IDS[qid]}")
                if command.get("argv") != expected_argv:
                    errors.append("CPU_ONLY_ARGV_MISMATCH")
                if (command.get("question_id") != qid or command.get("image_sha256") != sample["image_sha256"] or
                    inputs.get("image_sha256") != sample["image_sha256"] or
                    artifact.get("question_id") != qid or artifact.get("verified_before_cli") is not True or
                    image_post.get("image_sha256") != sample["image_sha256"]):
                    errors.append("REQUEST_INPUT_BINDING_MISMATCH")
                clean = (state.get("cli_started") is True and state.get("wrapper_returncode") == 0 and
                         state.get("time_child_exit_status") == 0 and state.get("execution_complete") is True and
                         state.get("raw_copy_complete") is True and
                         state.get("remote_process_cleanup_verified") is True)
                if not clean:
                    errors.append("CLI_OR_CLEANUP_NOT_CLEAN")
                if not events.get("event_predicate_pass"):
                    errors.append("IMAGE_EVENTS_NOT_VERIFIED")
                if parse_error:
                    errors.append(parse_error)
                accuracy = ev.eval_pred_list([{"pred_answer": candidate, "gt_answers": sample["answers"]}]) if not parse_error else None
                answer_ok = parse_error is None
                image_ok = clean and not any(x.endswith("MISMATCH") for x in errors) and events.get("event_predicate_pass") is True
                status = "DIRECT_CPU_MEASURED" if answer_ok and image_ok else "DIRECT_CPU_ATTEMPTED_UNSCORABLE"
                record = {
                    "schema": "kv260_cpu_p2_textvqa_direct_assessment_v1", "question_id": qid,
                    "run_id": runner.RUN_IDS[qid], "image_id": sample["image_id"],
                    "image_sha256": sample["image_sha256"], "status": status,
                    "answer_parse_ok": answer_ok, "image_processing_verified": image_ok,
                    "prediction": candidate, "host_textvqa_soft_accuracy": accuracy,
                    "event_summary": events, "errors": errors,
                    "remote_result_sha256": hashlib.sha256((raw_dir / "result.json").read_bytes()).hexdigest(),
                    "direct_wrapper_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                }
                local_record = raw_dir / "direct_request_assessment.json"
                if not local_record.exists():
                    runner.write_json(local_record, record)
                return {"question_id": qid, "attempted": True, "status": status,
                        "answer_parse_ok": answer_ok, "image_processing_verified": image_ok,
                        "prediction": candidate, "soft_accuracy": accuracy, "errors": errors}
            except (OSError, ValueError, KeyError, TypeError, UnicodeDecodeError) as exc:
                return {"question_id": qid, "attempted": True, "status": "DIRECT_CPU_ATTEMPTED_UNSCORABLE",
                        "answer_parse_ok": False, "image_processing_verified": False,
                        "prediction": "", "soft_accuracy": 0.0,
                        "errors": [type(exc).__name__ + ": " + str(exc)]}

    return DirectAdapter(), evaluator


runner.load_adapter = load_direct_adapter
raise SystemExit(runner.main())
