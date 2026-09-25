# RM10 full-system route

This route reuses the RM09 static-extent KV260 PS, AXI-Lite control, three
HLS AXI4 masters, SmartConnect, HP0 DDR, and AXI Performance Monitor topology.
Only the HLS IP implementation changes. The PL0 request remains 100 MHz, the
measured board clock used by the RM09 static baseline. The device must resolve
to `xck26-sfvc784-2LV-c`.

The run consumes a frozen HLS export from `RM10_IP_REPO`. Before synthesis the
runner records SHA-256 for every IP package file. It produces a full Vivado
synthesis, placement, routing, bitstream, XSA validation, timing, utilization,
clock, route, DRC, methodology, congestion, and critical-path record. The
runner does not load the generated image on a board.

Run after the numeric gate has passed and the pinned IP export is available:

```bash
RM10_IP_REPO=/absolute/path/to/frozen/ip \
  scripts/rm10/run_full_system.sh
```

By default, the generated project is under `experiments/rm10_route/build/`
and the report and package manifest are copied to
`experiments/rm10_route/evidence/full_system/`. The build tree is local and
ignored by Git. The results document records the IP/source identity, resource
totals including CLB sites and BRAM/URAM, 100 MHz timing slack, routed-frequency
interpretation, congestion, critical path, bitstream and XSA checksums, and any
implementation warnings or errors.

The original A-rescue route is archived as `PROVISIONAL_INVALID` because its
HLS schedule places an accumulator load and store five stages apart while the
bound FP32 adder latency is seven cycles. It must not be loaded. To route a
corrected package while retaining the original evidence, set distinct output
directories:

```bash
RM10_IP_REPO=/absolute/path/to/corrected/ip \
RM10_SYSTEM_ROOT="$PWD/experiments/rm10_route/build/corrected_candidate" \
RM10_EVIDENCE_ROOT="$PWD/experiments/rm10_route/evidence/corrected_candidate" \
  scripts/rm10/run_full_system.sh
```

Start that run only after the corrected source/IP is frozen and its recurrence
correctness is explicitly validated.

The corrected ten-bank candidate completed its own full-system route after the
five-bank package was rejected by recurrence auditing. See
[`RM10_CORRECTED_ROUTE_RESULTS.md`](RM10_CORRECTED_ROUTE_RESULTS.md) for the
frozen source/IP identities, numeric and RTL co-simulation gates, routed
resource/timing/congestion reports, bitstream/XSA hashes, and the separate
corrected-candidate evidence directory. The corrected route passed 100 MHz
setup and hold timing, but board testing and request-level validation remain
separate from this route task.
