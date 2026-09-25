# RM08 llama.cpp runtime patch

`llama.cpp-kv260-ffn-down.patch` preserves the five commits on the opt-in
KV260 FFN-down runtime branch. It applies to upstream llama.cpp commit
`7ab4ee7baad2d920464cbacfad4f4b07cf111fd2` with `git am`.

- Final patched commit in the local runtime worktree: `7c9c159`.
- Patch SHA-256: `ce8d50e72a131e2b910ade74504164700e436ad2b5d610849a3d3c6d463168a6`.
- The KV260 QID 37804 run used the library and command hashes recorded in
  [`../evidence/rm08-vlm-q37804-20260925T063228Z/run_status.txt`](../evidence/rm08-vlm-q37804-20260925T063228Z/run_status.txt).

The runtime worktree's `origin` is the upstream `ggml-org/llama.cpp` repository.
This project keeps the patch here to preserve the exact tested backend code.
