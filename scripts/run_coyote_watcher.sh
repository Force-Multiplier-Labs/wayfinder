#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# HOWL Watcher — Human-Orchestrated Watchdog Loop
#
# Starts the Coyote error watcher that monitors for errors and triggers
# the HOWL pipeline when issues are detected.
#
# When Coyote detects an error, it HOWLs — triggering a 5-stage AI pipeline:
#   1. Investigate — Root cause analysis
#   2. Design — Fix specification
#   3. Implement — Code generation
#   4. Test — Validation
#   5. Learn — Lessons extraction
#
# Usage:
#   # Start watcher in foreground (Ctrl+C to stop):
#   ./scripts/run_coyote_watcher.sh
#
#   # Start watcher in background:
#   ./scripts/run_coyote_watcher.sh &
#
#   # Custom options:
#   POLL_INTERVAL=5 AUTO_APPLY=1 ./scripts/run_coyote_watcher.sh
# ---------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WAYFINDER_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUTPUT_DIR="${OUTPUT_DIR:-$WAYFINDER_ROOT/out/manifest-generate-ingestion}"
POLL_INTERVAL="${POLL_INTERVAL:-10}"
# Project root for startd8-sdk error store (where .startd8/task_errors/ lives)
PROJECT_ROOT="${PROJECT_ROOT:-$HOME/Documents/dev/startd8-sdk}"

# Activate wayfinder venv (creates via uv if needed)
# shellcheck disable=SC1091
source "$SCRIPT_DIR/_activate_wayfinder_venv.sh"

# --- Coyote dev-mode env vars ---
export COYOTE_AUTO_PROCEED=true
export COYOTE_CONTEXTCORE_ENABLED=true
export COYOTE_OTEL_ENDPOINT="${COYOTE_OTEL_ENDPOINT:-localhost:4317}"
export COYOTE_OTEL_SERVICE_NAME="${COYOTE_OTEL_SERVICE_NAME:-contextcore-coyote}"
export COYOTE_LLM_PROVIDER="${COYOTE_LLM_PROVIDER:-anthropic}"
export COYOTE_LLM_MODEL="${COYOTE_LLM_MODEL:-claude-sonnet-4-20250514}"
# Ensure API key is set
: "${ANTHROPIC_API_KEY:?Set ANTHROPIC_API_KEY before running the watcher}"

# HOWL banner pause (seconds to display before starting pipeline)
HOWL_PAUSE="${HOWL_PAUSE:-10}"

# --- Build watcher args ---
WATCHER_ARGS=(
    --output-dir "$OUTPUT_DIR"
    --poll-interval "$POLL_INTERVAL"
    --project-root "$PROJECT_ROOT"
    --howl-pause "$HOWL_PAUSE"
    --verbose
)

# Optional: auto-apply generated code to disk
if [ "${AUTO_APPLY:-0}" = "1" ]; then
    WATCHER_ARGS+=(--auto-apply)
fi

# Optional: bypass skip filter
if [ "${FORCE:-0}" = "1" ]; then
    WATCHER_ARGS+=(--force)
fi

# Observe mode (default ON for tuning — set OBSERVE=0 to enable pipeline)
if [ "${OBSERVE:-1}" != "0" ]; then
    WATCHER_ARGS+=(--observe)
fi

# Optional: custom severity
if [ -n "${SEVERITY:-}" ]; then
    WATCHER_ARGS+=(--severity "$SEVERITY")
fi

# Clean up previous result files so watcher doesn't exit immediately
rm -f "$OUTPUT_DIR/workflow-result.json" "$OUTPUT_DIR/implement-workflow-result.json" 2>/dev/null

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  🐺 HOWL — Human-Orchestrated Watchdog Loop                   ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "Output dir:     $OUTPUT_DIR"
echo "Project root:   $PROJECT_ROOT"
echo "Poll interval:  ${POLL_INTERVAL}s"
echo "HOWL pause:     ${HOWL_PAUSE}s (set HOWL_PAUSE=0 to skip banner delay)"
echo "OTel endpoint:  $COYOTE_OTEL_ENDPOINT"
echo "LLM model:      $COYOTE_LLM_MODEL"
echo "Auto-apply:     ${AUTO_APPLY:-0}"
echo "Observe mode:   ${OBSERVE:-1} (set OBSERVE=0 to enable pipeline)"
echo ""
if [ "${OBSERVE:-1}" != "0" ]; then
echo "OBSERVE MODE: logging ALLOW/DENY verdicts only — pipeline is OFF"
echo "  Set OBSERVE=0 to enable the HOWL pipeline"
else
echo "When errors are detected, Coyote will HOWL:"
echo "  1. Investigate → 2. Design → 3. Implement → 4. Test → 5. Learn"
fi
echo ""

cd "$WAYFINDER_ROOT"
exec python3 scripts/watch_artisan_errors.py "${WATCHER_ARGS[@]}"
