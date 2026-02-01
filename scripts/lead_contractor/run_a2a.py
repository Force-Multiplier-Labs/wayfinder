#!/usr/bin/env python3
"""
Run Lead Contractor workflow for Phase 4: A2A Protocol Alignment features.

Usage:
    python3 scripts/lead_contractor/run_a2a.py
    python3 scripts/lead_contractor/run_a2a.py --group naming
    python3 scripts/lead_contractor/run_a2a.py --group state --feature 1
    python3 scripts/lead_contractor/run_a2a.py --list
"""

import argparse
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.lead_contractor.runner import run_features
from scripts.lead_contractor.tasks import (
    NAMING_FEATURES,
    STATE_FEATURES,
    DISCOVERY_FEATURES,
    PARTS_FEATURES,
    A2A_ADAPTER_FEATURES,
)

FEATURE_GROUPS = {
    "naming": ("4.1 Naming Conventions", NAMING_FEATURES),
    "state": ("4.2 State Model", STATE_FEATURES),
    "discovery": ("4.3 AgentCard & Discovery", DISCOVERY_FEATURES),
    "parts": ("4.4 Part Model", PARTS_FEATURES),
    "adapter": ("4.5 A2A Adapter", A2A_ADAPTER_FEATURES),
}


def main():
    parser = argparse.ArgumentParser(
        description="Run Lead Contractor for Phase 4: A2A Protocol Alignment"
    )
    parser.add_argument(
        "--group", "-g",
        choices=list(FEATURE_GROUPS.keys()) + ["all"],
        default="all",
        help="Feature group to run"
    )
    parser.add_argument(
        "--feature", "-f",
        type=int,
        help="Run specific feature within group"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List available features"
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

    args = parser.parse_args()

    if args.list:
        print("Phase 4: A2A Protocol Alignment Features")
        print("=" * 60)
        total = 0
        for group_name, (display_name, features) in FEATURE_GROUPS.items():
            print(f"\n{display_name} (--group {group_name})")
            for i, f in enumerate(features, 1):
                print(f"  {i}. {f.name}")
            total += len(features)
        print(f"\nTotal: {total} features")
        return

    # Collect features based on arguments
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

    print("=" * 60)
    print("Phase 4: A2A Protocol Alignment - Lead Contractor Workflow")
    print("=" * 60)
    print(f"\nFeatures to run: {len(features)}")
    for f in features:
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
