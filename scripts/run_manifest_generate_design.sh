#!/usr/bin/env bash
# Design half only: PLAN → SCAFFOLD → DESIGN (no code generation).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WAYFINDER_ROOT="$HOME/Documents/dev/wayfinder"
SEED="$WAYFINDER_ROOT/out/manifest-generate-ingestion/artisan-context-seed.json"
OUTPUT_DIR="$WAYFINDER_ROOT/out/manifest-generate-ingestion"

# Activate startd8-sdk venv (creates if needed, cd's into SDK_ROOT)
# shellcheck disable=SC1091
source "$SCRIPT_DIR/_activate_sdk_venv.sh"

python3 scripts/run_artisan_workflow.py \
    --seed "$SEED" \
    --project-root "$WAYFINDER_ROOT" \
    --output-dir "$OUTPUT_DIR" \
    --stop-after design \
    --cost-budget 5.00 \
    -v
