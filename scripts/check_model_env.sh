#!/usr/bin/env bash
set -u

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
failures=0
pass() { printf 'PASS %-24s %s\n' "$1" "$2"; }
fail() { printf 'FAIL %-24s %s\n' "$1" "$2"; failures=$((failures + 1)); }

venv_python="$PROJECT_ROOT/.venv-model/bin/python"
if [[ -x "$venv_python" ]] && "$venv_python" -m pip --version >/dev/null 2>&1; then
  pass Python_venv "$venv_python (pip available)"
  declare -A package_modules=(
    [numpy]=numpy
    [Pillow]=PIL
    [safetensors]=safetensors
    [sentencepiece]=sentencepiece
    [protobuf]=google.protobuf
    [huggingface-hub]=huggingface_hub
    [transformers]=transformers
    [torch]=torch
  )
  declare -A requirement_names=(
    [Pillow]=pillow
    [huggingface-hub]=huggingface_hub
  )
  while IFS= read -r distribution; do
    module="${package_modules[$distribution]}"
    if "$venv_python" -c "import $module" >/dev/null 2>&1; then
      actual="$($venv_python -c "from importlib.metadata import version; print(version('$distribution'))")"
      requirement_name="${requirement_names[$distribution]:-$distribution}"
      expected="$(awk -F '==' -v d="$requirement_name" '$1 == d {print $2}' "$PROJECT_ROOT/env/requirements-model.txt")"
      if [[ "$actual" == "$expected" ]]; then pass "pkg:$distribution" "$actual"; else fail "pkg:$distribution" "got $actual expected $expected"; fi
    else
      fail "pkg:$distribution" not-importable
    fi
  done < <(printf '%s\n' numpy Pillow safetensors sentencepiece protobuf huggingface-hub transformers torch)
else
  fail Python_venv "missing"
fi

manifest="$PROJECT_ROOT/models/manifests/model_manifest.json"
[[ -f "$manifest" ]] && pass model_manifest "$manifest" || fail model_manifest missing
gguf_count="$(find "$PROJECT_ROOT/models/gguf" -maxdepth 1 -type f -name '*.gguf' 2>/dev/null | wc -l)"
[[ "$gguf_count" -gt 0 ]] && pass GGUF "$gguf_count file(s)" || fail GGUF none
mmproj_count="$(find "$PROJECT_ROOT/models/gguf" -maxdepth 1 -type f -iname '*mmproj*.gguf' 2>/dev/null | wc -l)"
[[ "$mmproj_count" -gt 0 ]] && pass mmproj "$mmproj_count file(s)" || fail mmproj none
[[ -f "$PROJECT_ROOT/models/SHA256SUMS" ]] && pass SHA256SUMS present || fail SHA256SUMS missing
if [[ -f "$PROJECT_ROOT/models/SHA256SUMS" ]]; then
  if (cd "$PROJECT_ROOT" && sha256sum -c models/SHA256SUMS >/dev/null); then
    pass artifact_hashes "SHA256SUMS verified"
  else
    fail artifact_hashes "SHA256SUMS mismatch"
  fi
fi

if [[ "$failures" -eq 0 ]]; then
  echo "Model environment: PASS"
  exit 0
fi
echo "Model environment: FAIL ($failures check(s))"
exit 1
