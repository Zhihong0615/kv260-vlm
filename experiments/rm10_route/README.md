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
