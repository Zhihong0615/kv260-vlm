#!/usr/bin/env bash
# Project-local fallback for hosts where sudo apt is unavailable.
# It is intentionally opt-in and does not modify ~/.bashrc.
set -u
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PATH="$PROJECT_ROOT/.venv-hosttools/bin:$PROJECT_ROOT/tools/ccache-root/usr/bin:$PATH"
export LD_LIBRARY_PATH="$PROJECT_ROOT/tools/ccache-root/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
echo "Project-local host tools enabled: cmake=$(command -v cmake || true) ninja=$(command -v ninja || true) ccache=$(command -v ccache || true)"
