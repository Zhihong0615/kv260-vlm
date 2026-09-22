#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$PROJECT_ROOT/.venv-model/bin/python"
MODEL_DIR="$PROJECT_ROOT/models/hf/MiniCPM-V-4.6"
GGUF_DIR="$PROJECT_ROOT/models/gguf"
GGUF_F16="$GGUF_DIR/MiniCPM-V-4.6-f16.gguf"
MMPROJ="$GGUF_DIR/mmproj-MiniCPM-V-4.6-f16.gguf"
GGUF_Q4="$GGUF_DIR/MiniCPM-V-4.6-Q4_K_M.gguf"
REVISION="36f34a661a4bd35d0dc2294cb044d2584646c7d3"
CHECKPOINT_BYTES=2600957528
CHECKPOINT_SHA256=aa67da5820411176d0f9593a00265bc25a73c45f62dc5a605a93b1b5516a0d34

if [[ ! -x "$PYTHON" ]]; then
  echo "BLOCKED: .venv-model is unavailable" >&2
  exit 1
fi
if [[ ! -f "$MODEL_DIR/model.safetensors" ]]; then
  echo "BLOCKED: fixed-revision checkpoint is not fully downloaded" >&2
  exit 1
fi
if [[ "$(stat -c '%s' "$MODEL_DIR/model.safetensors")" != "$CHECKPOINT_BYTES" ]]; then
  echo "FAIL: checkpoint byte size does not match fixed revision" >&2
  exit 1
fi
if [[ "$(sha256sum "$MODEL_DIR/model.safetensors" | awk '{print $1}')" != "$CHECKPOINT_SHA256" ]]; then
  echo "FAIL: checkpoint SHA256 does not match fixed revision" >&2
  exit 1
fi
if ! grep -q '"transformers_version": "5.7.0"' "$MODEL_DIR/config.json"; then
  echo "FAIL: checkpoint config does not report transformers 5.7.0" >&2
  exit 1
fi

mkdir -p "$GGUF_DIR"
"$PYTHON" "$PROJECT_ROOT/runtime/llama.cpp/convert_hf_to_gguf.py" \
  "$MODEL_DIR" --outfile "$GGUF_F16" --outtype f16 --use-temp-file
"$PYTHON" "$PROJECT_ROOT/runtime/llama.cpp/convert_hf_to_gguf.py" \
  "$MODEL_DIR" --outfile "$MMPROJ" --outtype f16 --mmproj --use-temp-file

"$PROJECT_ROOT/runtime/llama.cpp/build/bin/llama-quantize" \
  "$GGUF_F16" "$GGUF_Q4" Q4_K_M

conversion_command="$(printf '%s' 'scripts/build_model_artifacts.sh: convert_hf_to_gguf f16 + --mmproj; llama-quantize Q4_K_M')"
"$PYTHON" "$PROJECT_ROOT/scripts/write_model_manifest.py" \
  --hf-repo openbmb/MiniCPM-V-4.6 \
  --revision "$REVISION" \
  --processor-revision "$REVISION" \
  --checkpoint "$MODEL_DIR/model.safetensors" \
  --gguf "$GGUF_F16" \
  --mmproj "$MMPROJ" \
  --quantized "$GGUF_Q4" \
  --quantization Q4_K_M \
  --conversion-command "$conversion_command"

sha256sum "$GGUF_F16" "$MMPROJ" "$GGUF_Q4"
