# MiniCPM-V 4.6 conversion

状态：`PASS`。

固定输入：

- Repo: `openbmb/MiniCPM-V-4.6`
- Revision: `36f34a661a4bd35d0dc2294cb044d2584646c7d3`
- Processor revision: same revision
- llama.cpp commit: `7ab4ee7baad2d920464cbacfad4f4b07cf111fd2`
- Transformers: `5.7.0`
- CPU-only torch: `2.9.1+cpu`

正式转换命令已封装在：

```bash
~/research/kv260-vlm/scripts/build_model_artifacts.sh
```

该脚本在 checkpoint 文件大小与 SHA256 核验后执行，已生成：

- `models/gguf/MiniCPM-V-4.6-f16.gguf` — 1,516,275,968 bytes
- `models/gguf/mmproj-MiniCPM-V-4.6-f16.gguf` — 1,108,747,008 bytes
- `models/gguf/MiniCPM-V-4.6-Q4_K_M.gguf` — 529,101,696 bytes

`models/manifests/model_manifest.json` 已记录 revision、processor revision、llama.cpp commit、转换环境、命令、量化格式和每个 artifact 的 SHA256。
输入 checkpoint 也纳入 manifest，固定大小为 2,600,957,528 bytes，SHA256 为 `aa67da5820411176d0f9593a00265bc25a73c45f62dc5a605a93b1b5516a0d34`；当前 `SHA256SUMS` 的四项均为 `OK`。
