# KV260 VLM environment acceptance review

Date: 2026-09-23 (Asia/Shanghai)

Result: **PASS for the completed environment round**. Independent read-only
review confirmed the real HLS/Vivado reports and artifacts, four model hashes,
KV260 base status, and the later successful full postcheck. Wi-Fi/campus network
configuration is a separate subsequent round and is not covered by this PASS.

## Acceptance evidence

| Area | Result | Evidence |
|---|---|---|
| AMD tool versions | PASS | Vivado 2024.2 build 5239630; Vitis 2024.2 build 5238363; Vitis HLS 2024.2 build 5238294 |
| K26 device database | PASS | 2 `xck26` parts returned by Vivado |
| KV260 board database | PASS | 3 board parts returned; smoke test used `xilinx.com:kv260_som:part0:1.4` |
| Host check | PASS | `scripts/check_host_env.sh` returned 0 |
| HLS C simulation | PASS | Testbench printed `vector_add C simulation: PASS` |
| HLS C synthesis | PASS | Real `vector_add_csynth.rpt`; estimated Fmax 273.97 MHz |
| HLS IP export | PASS | `export.zip` generated and `unzip -t` found no errors |
| Vivado implementation | PASS | `write_bitstream Complete!`; nonempty 7,797,818-byte Xilinx bitstream |
| Vivado DRC | PASS | 0 errors and 0 critical warnings |
| Vivado timing | PASS | Setup WNS 5.884 ns; hold WHS 0.002 ns; 0 failing endpoints |
| Vivado reports | PASS | Real DRC, utilization and timing reports retained under `env/vivado_smoke_test/evidence/` |
| Model environment | PASS | `scripts/check_model_env.sh` returned 0 |
| Model integrity | PASS | `sha256sum -c models/SHA256SUMS` verified the checkpoint and all three GGUF artifacts |
| KV260 SSH | PASS | Existing host `kria` is reachable with key authentication |
| FPGA Manager / CMA | PASS | `fpga0` present; `CmaTotal` 1,024,000 kB |
| XRT device | PASS | KV260 revB; XRT device reports Ready |
| `xmutil listapps` | PASS | Exact `sudo -n /usr/bin/xmutil listapps` returned `k26-starter-kits` |
| Least privilege | PASS | Only the exact read-only `listapps` command is NOPASSWD; no load/unload/bootfw-update grant |

The final orchestrated command `scripts/post_install_amd_2024_2.sh` reran the
host check, HLS test, Vivado implementation, model check, four hashes and board
check in sequence and exited 0 with:

```text
POSTCHECK host=0 hls=0 vivado=0 model=0 hashes=0 kv260=0
AMD 2024.2 install and full environment acceptance: PASS
```

## Warning assessment

The HLS flow warns that the legacy `vitis_hls` executable is deprecated and
that one bundled JRE lookup path is absent; synthesis and Vivado IP export both
completed, and the exported ZIP passed an archive-integrity test. Vivado also
reports warnings for unrelated Versal board definitions whose devices were not
installed, plus routed-design warnings in generated IP. The selected K26 part
and KV260 board are present, implementation completed, bitstream DRC has zero
errors, and setup/hold timing both pass. No warning was reclassified as a
success without checking its downstream artifact.

## Safety and scope

No bitstream or application was loaded onto the KV260. The board image,
bootloader, boot partition, QSPI, DTBO and active FPGA design were not changed.
The sole board-side change is the audited sudoers file that permits the exact
read-only `xmutil listapps` command. No system upgrade was performed.

## Independent review

Status: `PASS with two documentation/checker follow-ups`, reviewed on
2026-09-23 by a separate read-only reviewer. The reviewer confirmed that the
HLS IP archive and reports and the Vivado bitstream/reports match their build
originals, their retained SHA256SUMS pass, the four model hashes and manifest
match, and the board reports Device Ready. It independently observed the
sudoers file as `root:root 0440`; its no-escalation constraint prevented a
live reread of the rule or a live `sudo -n xmutil listapps`, so that part relies
on the recorded interactive validation and the later successful host check.

The original automatic postcheck service failed at 09:05:58, after the
installer finished at 09:05:38, because AMD's settings script read an unset
`PYTHONPATH` under `set -u`. This is an authentic earlier failed run, not a
contradiction of the later success. The setup helper was fixed, then HLS,
Vivado, model and board checks ran manually from 09:27 to 09:32 and produced
the full PASS quoted above. The old transient service still displays `failed`;
its status has not been rewritten to imply that it passed.

The reviewer also found that `scripts/check_kv260_env.sh` initially accepted
any nonempty, error-free `listapps` output. It was tightened to require the
actual `k26-starter-kits` application row and header; this checker was rerun
read-only after the revision.
