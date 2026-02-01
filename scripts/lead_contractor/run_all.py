#!/usr/bin/env python3
"""
Run Lead Contractor workflow for all Phase 3 features.

Usage:
    python3 scripts/lead_contractor/run_all.py
    python3 scripts/lead_contractor/run_all.py --group graph
    python3 scripts/lead_contractor/run_all.py --list
"""

import argparse
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.lead_contractor.runner import run_features
from scripts.lead_contractor.tasks import (
    GRAPH_FEATURES,
    LEARNING_FEATURES,
    VSCODE_FEATURES,
)

FEATURE_GROUPS = {
    "graph": GRAPH_FEATURES,
    "learning": LEARNING_FEATURES,
    "vscode": VSCODE_FEATURES,
}


def main():
    parser = argparse.ArgumentParser(
        description="Run Lead Contractor for all Phase 3 features"
    )
    parser.add_argument(
        "--group", "-g",
        choices=["graph", "learning", "vscode"],
        help="Run only a specific feature group"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List all available features"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Reduce output verbosity"
    )
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Stop on first error"
    )
    parser.add_argument(
        "--python-only",
        action="store_true",
        help="Run only Python features (graph + learning)"
    )
    parser.add_argument(
        "--typescript-only",
        action="store_true",
        help="Run only TypeScript features (vscode)"
    )

    args = parser.parse_args()

    if args.list:
        print("Phase 3 Features:")
        print()
        print("Knowledge Graph (Python):")
        for i, f in enumerate(GRAPH_FEATURES, 1):
            print(f"  {i}. {f.name}")
        print()
        print("Agent Learning Loop (Python):")
        for i, f in enumerate(LEARNING_FEATURES, 1):
            print(f"  {i}. {f.name}")
        print()
        print("VSCode Extension (TypeScript):")
        for i, f in enumerate(VSCODE_FEATURES, 1):
            print(f"  {i}. {f.name}")
        print()
        print(f"Total: {len(GRAPH_FEATURES) + len(LEARNING_FEATURES) + len(VSCODE_FEATURES)} features")
        return

    # Collect features based on arguments
    features = []

    if args.group:
        features = FEATURE_GROUPS[args.group]
    elif args.python_only:
        features = GRAPH_FEATURES + LEARNING_FEATURES
    elif args.typescript_only:
        features = VSCODE_FEATURES
    else:
        features = GRAPH_FEATURES + LEARNING_FEATURES + VSCODE_FEATURES

    print("=" * 60)
    print("Phase 3 Strategic - Lead Contractor Workflow")
    print("=" * 60)
    print(f"\nFeatures to run: {len(features)}")

    # Group by type for display
    python_features = [f for f in features if not f.is_typescript]
    ts_features = [f for f in features if f.is_typescript]

    if python_features:
        print("\nPython features:")
        for f in python_features:
            print(f"  - {f.name}")

    if ts_features:
        print("\nTypeScript features:")
        for f in ts_features:
            print(f"  - {f.name}")

    print()

    results = run_features(
        features,
        verbose=not args.quiet,
        stop_on_error=args.stop_on_error,
    )

    # Summary
    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)

    success_count = sum(1 for r in results if r.success)
    fail_count = len(results) - success_count

    print(f"Total: {len(results)}")
    print(f"Passed: {success_count}")
    print(f"Failed: {fail_count}")

    if fail_count > 0:
        print("\nFailed features:")
        for r in results:
            if not r.success:
                print(f"  - {r.feature_name}: {r.error or 'Unknown error'}")
        sys.exit(1)
    else:
        print("\nAll features completed successfully!")


if __name__ == "__main__":
    main()
