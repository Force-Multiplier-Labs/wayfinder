#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Shared helper: activate the startd8-sdk venv, creating it if needed.
#
# Source this file from any script that runs startd8-sdk commands:
#   source "$(dirname "$0")/_activate_sdk_venv.sh"
#
# After sourcing, the shell is cd'd into SDK_ROOT with the venv active.
# ---------------------------------------------------------------------------

SDK_ROOT="${SDK_ROOT:-$HOME/Documents/dev/startd8-sdk}"

if [ ! -d "$SDK_ROOT" ]; then
    echo "ERROR: startd8-sdk not found at $SDK_ROOT" >&2
    echo "Set SDK_ROOT to the correct path." >&2
    exit 1
fi

cd "$SDK_ROOT"

if [ ! -d .venv ]; then
    echo "Creating venv at $SDK_ROOT/.venv ..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip3 install -e ".[all,dev]"
else
    source .venv/bin/activate
fi
