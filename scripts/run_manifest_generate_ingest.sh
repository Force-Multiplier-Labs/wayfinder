#!/usr/bin/env bash
# Re-generate the artisan context seed from the wayfinder manifest-generate plan.
#
# This runs PlanIngestionWorkflow with:
#   - Option A: explicit contextcore_yaml path
#   - Option B: project_root for auto-discovery fallback
#
# The generated seed includes architectural_context (from .contextcore.yaml v2)
# and design_calibration (depth tiers from SizeEstimator).
#
# Usage:
#   ./scripts/run_manifest_generate_ingest.sh
#   ./scripts/run_manifest_generate_ingest.sh --dry-run
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WAYFINDER_ROOT="$HOME/Documents/dev/wayfinder"
PLAN="$WAYFINDER_ROOT/docs/plans/wayfinder-contextcore-manifest-generate-plan.md"
OUTPUT_DIR="$WAYFINDER_ROOT/out/manifest-generate-ingestion"
CONTEXTCORE_YAML="$WAYFINDER_ROOT/.contextcore.yaml"

# Activate startd8-sdk venv (creates if needed, cd's into SDK_ROOT)
# shellcheck disable=SC1091
source "$SCRIPT_DIR/_activate_sdk_venv.sh"

# Pass --dry-run or other args through
EXTRA_ARGS=("$@")

python3 -c "
import sys, time
from pathlib import Path

sys.path.insert(0, str(Path('src').resolve()))
from startd8.workflows.builtin.plan_ingestion_workflow import PlanIngestionWorkflow

workflow = PlanIngestionWorkflow()

config = {
    'plan_path': '$PLAN',
    'output_dir': '$OUTPUT_DIR',
    'force_route': 'artisan',
    'review_rounds': 2,
    'review_quality_tier': 'flagship',
    'warn_cost_usd': 1.00,
    'max_cost_usd': 5.00,
    # Option A: explicit path to v2 manifest
    'contextcore_yaml': '$CONTEXTCORE_YAML',
    # Option B: project root for auto-discovery fallback
    'project_root': '$WAYFINDER_ROOT',
}

validation = workflow.validate_config(config)
if not validation.valid:
    print(f'Validation errors: {validation.errors}')
    sys.exit(1)

dry_run = '--dry-run' in sys.argv

def on_progress(current, total, msg):
    print(f'  [{current}/{total}] {msg}')

print(f'Plan:             {Path(config[\"plan_path\"]).name}')
print(f'Route:            artisan (forced)')
print(f'Output:           {config[\"output_dir\"]}')
print(f'ContextCore YAML: {config[\"contextcore_yaml\"]}')
print(f'Project Root:     {config[\"project_root\"]}')
print(f'Dry run:          {dry_run}')
print()

t0 = time.time()
result = workflow.run(config=config, agents=None, on_progress=on_progress, dry_run=dry_run)
elapsed = time.time() - t0

print(f'\nWorkflow {\"SUCCEEDED\" if result.success else \"FAILED\"} in {elapsed:.1f}s')

if result.metrics:
    print(f'  Cost:   \${result.metrics.total_cost:.4f}')
    print(f'  Tokens: {result.metrics.input_tokens:,} in / {result.metrics.output_tokens:,} out')

if result.success and result.output:
    print(f'\nOutputs:')
    for key, value in result.output.items():
        print(f'  {key}: {value}')

if result.error:
    print(f'\nError: {result.error}')
    for step in result.steps:
        if step.error:
            print(f'  Step {step.step_name}: {step.error}')

sys.exit(0 if result.success else 1)
" "${EXTRA_ARGS[@]}"
