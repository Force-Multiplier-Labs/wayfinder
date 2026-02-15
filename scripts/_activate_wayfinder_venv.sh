#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Shared helper: activate the wayfinder venv, creating it via uv if needed.
#
# Source this file from any script that runs wayfinder/contextcore commands:
#   source "$(dirname "$0")/_activate_wayfinder_venv.sh"
#
# After sourcing, the wayfinder venv is active.  The working directory is
# unchanged (caller decides where to cd).
# ---------------------------------------------------------------------------

WAYFINDER_ROOT="${WAYFINDER_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

if [ ! -d "$WAYFINDER_ROOT/.venv" ]; then
    echo "Creating wayfinder venv via uv ..."
    (cd "$WAYFINDER_ROOT" && uv sync --all-packages --all-extras)
fi

# Activate the venv so python3/pip3 resolve to the project interpreter
# shellcheck disable=SC1091
source "$WAYFINDER_ROOT/.venv/bin/activate"
