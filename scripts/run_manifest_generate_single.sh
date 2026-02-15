#!/usr/bin/env bash
# Run the artisan workflow for a single feature (or comma-separated list).
#
# Usage:
#   ./scripts/run_manifest_generate_single.sh PI-001
#   ./scripts/run_manifest_generate_single.sh PI-001,PI-002
#   ./scripts/run_manifest_generate_single.sh PI-005 --resume   # resume after crash
#   ./scripts/run_manifest_generate_single.sh PI-005 --dry-run  # dry-run only
set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Usage: $0 <TASK-ID>[,<TASK-ID>...] [extra args...]"
    echo ""
    echo "Examples:"
    echo "  $0 PI-001                   # Run PI-001 through all 7 phases"
    echo "  $0 PI-001,PI-002            # Run two tasks"
    echo "  $0 PI-005 --resume          # Resume PI-005 after crash"
    echo "  $0 PI-005 --dry-run         # Dry run only"
    echo "  $0 PI-010 --stop-after design  # Design only"
    exit 1
fi

TASK_FILTER="$1"
shift  # remaining args passed through

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
    --task-filter "$TASK_FILTER" \
    --auto-commit \
    --cost-budget 15.00 \
    -v \
    "$@"
