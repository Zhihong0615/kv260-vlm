# RM13 final campaign handoff (live snapshot)

Updated UTC: 2026-09-26T13:55Z

- Run ID: `rm13_final200_qsim_20260926_r01`
- State: actively running; do not start another runner.
- Runner PID: `204311`; two CLI workers are spawned under it.
- Completed: `152/1400`; journal counts `156 attempt_started`, `152 case_completed` (append-only).
- Current block: `original` (the first frozen configuration). All completed cases have returned `rc=0` and parsed successfully; no failures observed.
- Raw journal: `experiments/rm13/data/raw/rm13_final200_qsim_20260926_r01/events.jsonl`
- Logs/resource records: `experiments/rm13/data/raw/rm13_final200_qsim_20260926_r01/logs/`
- MemAvailable: about 19 GiB; SwapFree about 3.6 GiB at snapshot.
- Pinned CLI SHA-256: `44dfe61a953ec51f91f2bf4724353c9beab5c31c356022956ec972b54d94f6f3`
- Pinned `libggml-cpu.so.0.24.0` SHA-256: `00c207ecbf5cc160fc40d0664a7d54ca0fd1d05fd409a4db8be2a22eed5546b9`
- Frozen split SHA-256: `5b798932b1ad08c85c6328cceab046f191e9dfbbc0a2df01f971f523eeb2e7b6`
- Frozen gate SHA-256: `3fc90a42b75b49198db6e90ea38809fc157ce657834be2cf1b12c01baeae0648`

If the runner exits or is intentionally paused, wait for memory clearance and ensure no runner/CLI remains before resuming. Resume with the same run ID and flags plus `--resume` from `/home/zhiro/research/kv260-vlm-workers/RM13-data-scorer`:

```sh
python3 experiments/rm13/scripts/run_quality.py \
  --cli /home/zhiro/research/kv260-vlm-workers/RM13-Q-quality/work/llama.cpp-rm13/build-rm13/bin/llama-mtmd-cli \
  --manifest experiments/rm13/data/textvqa_v0.5.1_calibration20_final200/manifest.json \
  --split final_test --final-test-approved \
  --run-id rm13_final200_qsim_20260926_r01 \
  --qcache-dir /home/zhiro/research/kv260-vlm-workers/RM13-data-scorer/experiments/rm13/data/qcache-final \
  --runtime-source-sha256 f9efcc80ccef45404b7549757c0eb3b16f6f876e2f912b065eefd89031affdc1 \
  --jobs 2 --resume
```

Do not inspect held-out scores until the predeclared checkpoint: all `200` original + `200` W4A8_both + `200` W8A8_both cases complete (`600/1400`). No runtime, gate, split, scorer, or runner edits during the live run.
