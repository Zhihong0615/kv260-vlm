# Operator metadata trace pilot

Source run: `textvqa_optrace_probe_host_q4_round01`; source run SHA-256 `6e74ceecfda97a82b6b096cff06b9705be64170e8f60496364f2e6f5bb46c16f`.

The project-local MTMD CLI copy records graph node phase, op name, tensor names, shapes, strides, dtypes, and logical input/output payload bytes for one real TextVQA development request. It records no tensor values and leaves upstream `runtime/llama.cpp` unchanged. The callback returns false on every node, preserving scheduler graph batching; it does not request per-node synchronization or tensor readback.

Three interleaved metadata-trace runs observed 8406 distinct phase/op/input-output signatures. Node observations across the three runs: `{"image_embedding_prefill": 21165, "text_prefill": 25398, "token_decode": 4233, "vision_encoder": 13710}`.

The trace is metadata, not a per-op timing profile. Its input/output byte counts are logical tensor sizes and must not be interpreted as measured DDR traffic or peak live storage. The callback has overhead; in this small fixed-order n=3 comparison the median fresh-process wall was 8.329 s with metadata collection and 8.360 s without it, a median paired change of -0.37%. This does not establish that the observer is free.

Per-op elapsed time, non-overlapping phase decomposition, active tensor live ranges, and a complete memory ledger remain open. No KV260 or PL work was performed.
