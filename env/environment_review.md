# KV260 VLM environment review

Date: 2026-09-22 (Asia/Shanghai)

This is the final read-only review, including the independent Reviewer Agent
task `01a0c8fe-f4d5-74d3-8359-a8f5f6432948`. The overall result is
**PARTIAL / BLOCKED**: the CPU/model preparation is ready, but the complete
KV260 FPGA development environment cannot be marked PASS until the AMD 2024.2
toolchain and board database are installed and the smoke tests run.

## PASS

- Host: Ubuntu 24.04.5 LTS, x86_64.
- Project-local CMake 3.31.6, Ninja 1.11.1.4, and ccache 4.9.1 fallback.
- llama.cpp is locked to commit `7ab4ee7baad2d920464cbacfad4f4b07cf111fd2`;
  `llama-cli`, `llama-server`, and `llama-mtmd-cli` Release builds pass `--help`.
- Project-local Python environment and locked model dependencies pass `pip check`.
- MiniCPM-V-4.6 is fixed to revision
  `36f34a661a4bd35d0dc2294cb044d2584646c7d3`.
- The input checkpoint is validated before conversion: 2,600,957,528 bytes,
  SHA256 `aa67da5820411176d0f9593a00265bc25a73c45f62dc5a605a93b1b5516a0d34`.
- F16 GGUF, F16 mmproj, and Q4_K_M GGUF were generated. The checkpoint and all
  three outputs are recorded in `models/manifests/model_manifest.json` and
  `models/SHA256SUMS`; all four hashes verify.
- Existing KV260 evidence: SSH transport, FPGA Manager, CMA, and XRT device
  readiness passed. The board image, boot files, QSPI, DTBO, and active
  bitstream were not modified.

## BLOCKED or UNKNOWN

- Vivado 2024.2, Vitis 2024.2, and Vitis HLS 2024.2 are not installed; the
  official installer was not available locally.
- K26 device database and KV260 board files cannot be queried without Vivado.
- HLS and Vivado smoke tests are scaffolded but have not produced real reports,
  a bitstream, utilization data, or timing data.
- `xmutil listapps` is blocked by the board-side `/tmp/dfx-mgrd.socket`
  permission/daemon boundary; board `sudo` credentials are required.
- Host package installation is also blocked in this non-interactive session by
  the host `sudo` password prompt. No system upgrade was attempted.
- The current end-to-end VLM inference path has not been claimed as PASS.

## Closure steps

1. In an interactive terminal, install the AMD/Xilinx 2024.2 toolchain and
   required host packages without performing an OS release upgrade.
2. Source the 2024.2 settings, verify Vivado/Vitis/Vitis HLS versions, and
   query the K26 device and KV260 board part.
3. Run the HLS and Vivado smoke tests and preserve their reports.
4. Use appropriate board-side authorization to re-run `xmutil listapps`; do
   not change the board image merely to bypass this check.

