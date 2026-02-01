#!/usr/bin/env python3
"""
Unified CLI for Lead Contractor workflow.

Usage:
    python3 scripts/lead_contractor/cli.py run graph
    python3 scripts/lead_contractor/cli.py run learning --feature 1
    python3 scripts/lead_contractor/cli.py run vscode
    python3 scripts/lead_contractor/cli.py run all
    python3 scripts/lead_contractor/cli.py list
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
from scripts.lead_contractor.config import (
    LEAD_AGENT,
    DRAFTER_AGENT,
    MAX_ITERATIONS,
    PASS_THRESHOLD,
    OUTPUT_DIR,
)

FEATURE_GROUPS = {
    "graph": ("Knowledge Graph", GRAPH_FEATURES),
    "learning": ("Agent Learning Loop", LEARNING_FEATURES),
    "vscode": ("VSCode Extension", VSCODE_FEATURES),
}


def cmd_list(args):
    """List all available features."""
    print("Phase 3 Strategic Features")
    print("=" * 60)

    total = 0
    for group_name, (display_name, features) in FEATURE_GROUPS.items():
        lang = "TypeScript" if features[0].is_typescript else "Python"
        print(f"\n{display_name} ({lang}) - run with: --group {group_name}")
        for i, f in enumerate(features, 1):
            print(f"  {i}. {f.name}")
        total += len(features)

    print()
    print(f"Total: {total} features")
    print()
    print("Configuration:")
    print(f"  Lead Agent:    {LEAD_AGENT}")
    print(f"  Drafter Agent: {DRAFTER_AGENT}")
    print(f"  Max Iterations: {MAX_ITERATIONS}")
    print(f"  Pass Threshold: {PASS_THRESHOLD}")
    print(f"  Output Dir:    {OUTPUT_DIR}")


def cmd_run(args):
    """Run the Lead Contractor workflow."""
    # Collect features
    features = []

    if args.group == "all":
        for _, group_features in FEATURE_GROUPS.values():
            features.extend(group_features)
    else:
        display_name, group_features = FEATURE_GROUPS[args.group]

        if args.feature:
            if 1 <= args.feature <= len(group_features):
                features = [group_features[args.feature - 1]]
            else:
                print(f"Invalid feature number. Use 1-{len(group_features)}")
                sys.exit(1)
        else:
            features = group_features

    # Filter by language if specified
    if args.python_only:
        features = [f for f in features if not f.is_typescript]
    elif args.typescript_only:
        features = [f for f in features if f.is_typescript]

    if not features:
        print("No features to run with given filters.")
        sys.exit(1)

    # Display header
    print("=" * 60)
    print("Lead Contractor Workflow")
    print("=" * 60)
    print()
    print(f"Lead Agent:    {LEAD_AGENT}")
    print(f"Drafter Agent: {DRAFTER_AGENT}")
    print(f"Max Iterations: {MAX_ITERATIONS}")
    print(f"Pass Threshold: {PASS_THRESHOLD}")
    print()
    print(f"Features to run: {len(features)}")
    for f in features:
        lang = "TS" if f.is_typescript else "Py"
        print(f"  [{lang}] {f.name}")
    print()

    # Run workflow
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


def cmd_config(args):
    """Show current configuration."""
    print("Lead Contractor Configuration")
    print("=" * 60)
    print()
    print(f"Lead Agent:      {LEAD_AGENT}")
    print(f"Drafter Agent:   {DRAFTER_AGENT}")
    print(f"Max Iterations:  {MAX_ITERATIONS}")
    print(f"Pass Threshold:  {PASS_THRESHOLD}")
    print(f"Output Directory: {OUTPUT_DIR}")
    print()
    print("Feature Groups:")
    for group_name, (display_name, features) in FEATURE_GROUPS.items():
        lang = "TypeScript" if features[0].is_typescript else "Python"
        print(f"  {group_name}: {len(features)} {lang} features")


def main():
    parser = argparse.ArgumentParser(
        description="Lead Contractor workflow CLI for Phase 3 features",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 scripts/lead_contractor/cli.py list
  python3 scripts/lead_contractor/cli.py run graph
  python3 scripts/lead_contractor/cli.py run learning --feature 1
  python3 scripts/lead_contractor/cli.py run vscode --stop-on-error
  python3 scripts/lead_contractor/cli.py run all --python-only
  python3 scripts/lead_contractor/cli.py config
"""
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # list command
    list_parser = subparsers.add_parser("list", help="List available features")
    list_parser.set_defaults(func=cmd_list)

    # config command
    config_parser = subparsers.add_parser("config", help="Show configuration")
    config_parser.set_defaults(func=cmd_config)

    # run command
    run_parser = subparsers.add_parser("run", help="Run the Lead Contractor workflow")
    run_parser.add_argument(
        "group",
        choices=["graph", "learning", "vscode", "all"],
        help="Feature group to run"
    )
    run_parser.add_argument(
        "--feature", "-f",
        type=int,
        help="Run specific feature number within group"
    )
    run_parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Reduce output verbosity"
    )
    run_parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Stop on first error"
    )
    run_parser.add_argument(
        "--python-only",
        action="store_true",
        help="Run only Python features"
    )
    run_parser.add_argument(
        "--typescript-only",
        action="store_true",
        help="Run only TypeScript features"
    )
    run_parser.set_defaults(func=cmd_run)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
