# Captured operand provenance

The W/X/Y files were read in place from:

`/home/zhiro/research/kv260-vlm-workers/RM11-A-unified/experiments/rm11_unified_ffn/evidence/board_capture/q37804-cpu/results/`

The copied `tensors.sha256` entries are relative to that `results/` directory.
Before the probe, `sha256sum -c tensors.sha256` was run there and verified all
nine W/X/Y payload files. Manifest SHA-256:
`65a81331f1572f6af339e29e896da277491fa07eb488df1d18bb053921b9f790`.
The tensor payloads remain in the RM11 evidence directory and are not copied
into this branch.
