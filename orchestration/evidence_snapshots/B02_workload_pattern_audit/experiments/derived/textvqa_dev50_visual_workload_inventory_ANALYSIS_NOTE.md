# TextVQA dev50 recorded visual workload inventory

This is a read-only reanalysis of the existing 50-request host CPU baseline. The log's ordered `n_tokens_batch` sequence is a post-processor image-encode observation, not yet a proven pre-dispatch selector feature. Request wall times include loading and generated-output differences.

Source run SHA-256: `d92fa666e25ad8fb2b9e06d03c806cda890319664bed4fc503f1837bcf066050`. Dataset manifest SHA-256: `62c32317029e40895ffd8e476e8a845416dac9d1d9490dfd6efb5f28a4374962`. Script SHA-256: `004b5fb22014b87b10ba881b13610c04077a756de4e02c3733b55354ef3666e0`.

| Ordered image batch token counts | Requests | Existing allocator traces | First untraced development example |
|---|---:|---|---:|
| 60, 64, 64 | 1 | 38169 | none |
| 66, 64, 64 | 4 | 38299 | 37221 |
| 60, 60, 60, 60, 60 | 1 | none | 35950 |
| 63, 63, 63, 63, 63 | 16 | none | 34609 |
| 70, 70, 70, 70, 70 | 22 | 37804, 37852 | 34699 |
| 63, 63, 63, 63, 63, 63, 63 | 1 | none | 35419 |
| 64, 70, 70, 70, 70, 70, 70 | 5 | none | 35005 |

Deterministic additional development probes for previously unseen patterns: 35950, 34609, 35419, 35005. The rule selects the smallest untraced question ID in each uncovered exact token pattern. These four cases should be rechecked for image identity and runtime metadata before any heavy timing; they do not define the final evaluation split.

Seven exact patterns occurred in dev50; the four allocator-traced requests cover three patterns. An exact pattern may include different raw image dimensions. The JSON contains each request's dimensions, source log/image hashes, and runtime prompt count for audit. Runtime prompt count is descriptive and may include multimodal tokens; it is not a selector feature validated at the required boundary.

No new inference, board action, or held-out data use was performed for this inventory.
