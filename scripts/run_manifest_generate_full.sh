#!/usr/bin/env bash
# Full 7-phase run with checkpoints for crash recovery.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WAYFINDER_ROOT="$HOME/Documents/dev/wayfinder"
SEED="$WAYFINDER_ROOT/out/manifest-generate-ingestion/artisan-context-seed.json"
OUTPUT_DIR="$WAYFINDER_ROOT/out/manifest-generate-ingestion"
CHECKPOINT_DIR="$OUTPUT_DIR/checkpoints"

# Activate startd8-sdk venv (creates if needed, cd's into SDK_ROOT)
# shellcheck disable=SC1091
source "$SCRIPT_DIR/_activate_sdk_venv.sh"

python3 scripts/run_artisan_workflow.py \
    --seed "$SEED" \
    --project-root "$WAYFINDER_ROOT" \
    --output-dir "$OUTPUT_DIR" \
    --checkpoint-dir "$CHECKPOINT_DIR" \
    --auto-commit \
    --cost-budget 15.00 \
    -v
