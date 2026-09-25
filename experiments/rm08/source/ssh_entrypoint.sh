#!/usr/bin/env bash
set -euo pipefail
deploy="${RM08_DEPLOY_DIR:-/tmp/rm08-deploy}"
bash "$deploy/first_load_smoke.sh" "$deploy/kv260-rm07-bounded-k16"
bash "$deploy/run_board_benchmarks.sh"
