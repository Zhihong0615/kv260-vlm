# RM10 warm rerun — load blocked before VLM execution

- Run directory: `/home/ubuntu/kv260-vlm-p2-cpu/runs/rm10-a-ra-q37804-20260926T081456Z`.
- `xmutil unloadapp` removed starter-kit, but `xmutil loadapp kv260-rm10-a-ra` returned `load Error: -1`; HLS/APM UIOs never appeared. No tensor benchmark or VLM request ran in this attempt.
- Board `dfx-mgrd` journal immediately before load repeatedly reports `ERROR:add_to_watch():554 no room to add more watch`, followed by `ERROR:load_accelerator():290 Check the supported type of base/accel`. The board package is `dfx-mgr 2023.1+5918fb3`; [that exact upstream source](https://github.com/Xilinx/dfx-mgr/blob/5918fb3406d828693cca484b77229ffd031b5dc4/src/daemon_helper.c#L542-L555) emits the watch error when its fixed `MAX_WATCH=500` in-memory array has no free entry. The evidence supports a DFX package-registration failure, not a failed RM10 computation.
- EXIT recovery loaded `k26-starter-kits` successfully. The board reported FPGA manager `operating`, FCLK0 `99,999,999 Hz`, and no rollback timer remained. The attempt has **no latency observation** and must be excluded from RM10 performance comparisons.
- Next action: one guarded DFX service recovery and warm candidate rerun using `boardprep/recover_dfx_and_run_candidate.sh`; it validates default starter-kit, unloads it, restarts `dfx-mgr.service` (which reloads the default app), verifies starter-kit/clock/manager, then enters the existing RM10 experiment script. This was staged but had not been executed when this note was written.

Raw evidence: `driver.log`, `restore.log`, `dfx-mgr-journal.txt` in this directory.
