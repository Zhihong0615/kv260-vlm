# Host exclusive timeline: three development requests

This is a comparison of three selected TextVQA development requests, each with three ordinary and three instrumented fresh CPU CLI processes in alternating order. All 18 processes exited successfully and matched their own frozen answer. All runs used the same copied MTMD CLI source SHA-256 `913eac0c6f943925a5eb1f3c4cad279bd8d29f00215708355e1b53bee32960fc` and binary SHA-256 `53b10837fb0fc7ce3a1fe2291a6ec0d3b62ddeffc2dfbc39b53dfc6a1205d09a`, linked to pinned runtime `7ab4ee7baad2d920464cbacfad4f4b07cf111fd2`. The pinned runtime checkout was clean after the runs.

The online start is the adjacent `CLOCK_MONOTONIC_RAW` boundary immediately before `media_file_read_and_decode`, after model/context initialization. This host proxy follows the taskbook §13.1 request boundary more closely than the cold `main` entry marker. The model load and CLI setup remain separate. Times below are medians across the three instrumented processes for each question; phase medians are not additive across runs.

| Question | Image encoder calls per trace | Online input to done (ms) | Online input to first visible token (ms) | Combined vision + projector encode (ms) | Image embedding prefill (ms) | Text prefill (ms) | Paired process-wall change median |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 37804 | 5 | 7,194.450 | 7,172.008 | 6,082.813 | 828.958 | 202.142 | −0.470% |
| 38299 | 3 | 3,820.930 | 3,801.911 | 3,198.225 | 445.782 | 153.298 | −0.669% |
| 35419 | 7 | 8,583.712 | 8,509.165 | 7,246.250 | 1,017.358 | 227.707 | +0.482% |

The different image encoder call counts are observed source-level batch counts for these requests, not a claim that batch count alone explains the wall-time differences. Paired changes for the two new runs ranged from −7.13% to +0.85% (qid 38299) and −3.71% to +4.89% (qid 35419). Three pairs per question are too few to establish a stable observer overhead. The combined encoder span includes graph setup, vision, projector, scheduler work and embedding copy; its components are not disjoint at the public API boundary. No board, PL, physical DDR, or tensor-payload evidence is implied. The trace records decode-call count, but not actual output token count or EOS versus antiprompt stop reason.

## Independent raw-trace adjacency check for the two new requests

A separate direct JSONL parser, independent of `scripts/analyze_phase_timeline_probe.py`, recomputed each span's duration, checked every `end_ns == next.start_ns`, matched the sum to the first/last timestamps and the trace end record, verified trace SHA against `run.json`, and summed the online subset from media-load start to `request_end`. It also checked that `first_token_emitted` lay between online start and request end. All six traces passed.

| Question | Trace process | Raw trace SHA-256 | Spans | Encoder calls | Online sum equals wall |
| ---: | ---: | --- | ---: | ---: | --- |
| 38299 | 02 | `048fba57bb374512fd74e9c680cebbfc38e3295c9c663c53ea9c1ae5241775b7` | 51 | 3 | yes |
| 38299 | 04 | `ca1fb2a288b771f3bdc0ae5030adc45bf564134f8c61a98681c468672c2436e7` | 51 | 3 | yes |
| 38299 | 06 | `29ecb37a4febd31d3820603f1ab8675eccfcc332f54a802aff09430966690050` | 51 | 3 | yes |
| 35419 | 02 | `aa6c8c5adf6b31e568b81101584c29befa3b613204047ad2546bb186f06e1791` | 103 | 7 | yes |
| 35419 | 04 | `7c24bbabd14161c71adbcbe4b87fb22a415e42082688bdba9a0c43142e18cb06` | 103 | 7 | yes |
| 35419 | 06 | `4bc47b4ab192a293d098bea32a2077a4ad6015a7a50a1ab77f9e8afca84ec24a` | 103 | 7 | yes |

Raw manifests and analysis JSON SHA-256:

| Question | `run.json` SHA-256 | `analysis_online2.json` SHA-256 |
| ---: | --- | --- |
| 37804 | `3e2fe7404389f195fdd44bae553dbdafee56cd449bf5ca8475135c1e618f767a` | `4131a7119b09401c89d0beef9ae04ce2b5c6621d246081a7a78da0c53e320d73` |
| 38299 | `873f285893482aadc8ffaae65e4bf0e1cae93f03892697d0a9993f6bf035738a` | `63853d001d836ac0e1f3639940965518b3c8cca775b1be2141c9bd352ad32c4f` |
| 35419 | `506f4b9fbbb0bdaade89428df2ebe40f52e88218c0c779dd22bf959e6bcac81f` | `c1e614406abefd16dd8e7c1fc9aad779e6194e89abf01f2117b4c6416a37af34` |
