# Runtime shape visibility audit for the H1/H3 dispatch assumptions

Date: 2026-09-23  
Evidence level: pinned-source audit only. No custom backend, PS-PL job, board inference, build, or timing was performed.

## Source identity

The read-only runtime checkout is llama.cpp commit `7ab4ee7baad2d920464cbacfad4f4b07cf111fd2`. SHA-256 values:

| File | SHA-256 |
|---|---|
| `runtime/llama.cpp/ggml/src/ggml-backend.cpp` | `2dd6a572f087a1fddaa52dbf2378b777cd21752f4b2a1292c8da3bcb05fbcfd9` |
| `runtime/llama.cpp/ggml/src/ggml-backend-impl.h` | `683e0583268e91e1f50b4ffc416b6523e0cec2dfdb3984c89792bda29e32566b` |
| `runtime/llama.cpp/ggml/include/ggml-backend.h` | `46d84cb998105f871240864fd0f55446939a2fe86c5c281afa63a010fb1f65a2` |
| `runtime/llama.cpp/src/llama-context.cpp` | `21340d0540c6ca98b78b733906f026a7ded450b283e47c3d1c9a84a19de43132` |
| `runtime/llama.cpp/tools/mtmd/clip.cpp` | `f50b204fa1bd4138c53d041663bbaf1472bab3af3407b95a8023429eb14e51ce` |

The applicable `runtime/llama.cpp/AGENTS.md` was read. This audit leaves the upstream checkout unchanged.

## What the pinned source establishes

1. `llama_context::graph_reserve` builds a model graph before calling scheduler reserve/split in `src/llama-context.cpp:2524-2536`.
2. The MTMD vision path builds its graph and calls `ggml_backend_sched_alloc_graph` before setting graph inputs and running it in `tools/mtmd/clip.cpp:4436-4444`.
3. `ggml_backend_sched_alloc_graph` calls `ggml_backend_sched_split_graph` before scheduler compute-buffer allocation (`ggml/src/ggml-backend.cpp:1992-2006`). The split routine asks whether candidate backends support individual graph nodes. That call passes the `ggml_tensor` node to the backend's `supports_op` callback (`ggml-backend.cpp:1058-1066`, `1222-1243`; device interface is declared in `ggml/src/ggml-backend-impl.h:204-205`).
4. The callback receives the operation tensor, so it can inspect its operator, type, dimensions, strides, and source tensors before that graph's scheduler compute-buffer allocation. The split may ask support more than once for a node while assigning and upgrading backends; this is an eligibility interface, not a one-shot timing hook. The backend's `graph_compute` callback also receives a `ggml_cgraph *` (`ggml-backend-impl.h:121-146`), so an implementation can make a conventional shape-keyed mode choice while traversing the graph. The public scheduler API describes split, compute-buffer allocation, and compute as separate calls (`ggml/include/ggml-backend.h:339-351`).

## Interpretation and limits

- **Shape visibility is available in the pinned source path.** N is not an inherently unavailable selector for an eligible `MUL_MAT` backend: it is part of the graph node before backend splitting and scheduler compute-buffer allocation. This does not claim that the graph's own metadata or other host-side storage has not already been allocated.
- **This does not establish a new policy.** Reading N and mapping it to a tile/mode is an ordinary shape-keyed static rule. H1 must beat the best fixed tile, per-phase tile, and fixed bucket using the same shape information.
- **The API is not proof of PL execution or a new policy.** `supports_op` returns only eligibility; the `graph_compute` hook could implement a normal N-to-mode lookup. No project PS-PL backend exists, and source does not prove that a future backend will select a descriptor from N, that a board trace preserves N, or that changing N changes the physical tail cost.
- **Graph construction details matter.** Processor/crop behavior and the graph builder determine the actual tensors. Host metadata traces confirm observed graph-node dimensions for four selected requests, but do not establish hardware transactions, tail work, or board timing.
- **No source edit was made.** The runtime repository remains at the pinned commit and is read-only for this autonomous task.

## Consequence for H1

Remove “N may not be exposed at dispatch” as a primary research-gap argument. For the observed N=60/64/66/70 family, a shape lookup is implementable before scheduler compute-buffer allocation and the fixed T=8 analytical screen already leaves only about 2.7% padded-column overhead. H1 survives only if a real K26 implementation shows a repeatable per-request cost after the strongest fixed-tile/bucket controls, and the added cost cannot be explained away by ordinary shape dispatch or by measurement noise. Until then, H1 is a falsification target, not a contribution claim.
