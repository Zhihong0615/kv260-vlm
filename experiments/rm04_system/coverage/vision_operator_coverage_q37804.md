# Vision operator coverage map — QID 37804

Input inventory SHA-256: `d7ff1e08955e4b8d3b0598f957ecbbdbf970da01055190ad5c79270712ef4082`.
Observed 855 vision MUL_MAT graph nodes; dtype split: `{"f16 x f16 -> f32": 5, "f16 x f32 -> f32": 850}`.
Nominal vision work: 1.204542 TMAC. Per-family CPU seconds below are only a proportional proxy from the measured 590.348s board vision timer; no family was timed independently.

Dynamic8’s direct point is F16×F32→F32, K=1152, M=4304, N=1120 with contiguous GGML strides. Compile-time shape changes retain the same arithmetic datapath but need their own synthesis and numeric checks.

| Class | MAC share | MAC-proportional board CPU proxy |
|---|---:|---:|
| supported with parameter change | 71.887% | 424.38s |
| directly supported | 16.136% | 95.26s |
| requires different datapath | 11.840% | 69.90s |
| not worth offloading | 0.137% | 0.81s |

The CSV provides shape, dtype, family, call count, MAC, proxy and class for each aggregated shape family.
