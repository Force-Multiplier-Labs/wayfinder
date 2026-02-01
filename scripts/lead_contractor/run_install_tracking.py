#!/usr/bin/env python3
"""
Run Lead Contractor workflow for Installation Tracking & Resume Plan.

Implements the plan from docs/INSTALLATION_TRACKING_PLAN.md to transform
ContextCore installation into a resumable, observable, self-healing system.

Features:
  1. State File Infrastructure - install-state.sh with state management functions
  2. Step Executor Framework - Idempotent step execution pattern
  3. CLI Entry Point - create-cluster.sh with --resume/--repair/--status/--reset
  4. Metric Emission - curl-based metric push to Mimir (Python-free)
  5. Repair Mode - Step verification and recovery logic
  6. Dashboard Enhancement - Add step progress visualization panels

Usage:
    # Activate venv first
    cd ~/Documents/dev/ContextCore
    source .venv/bin/activate

    # List all features
    python3 scripts/lead_contractor/run_install_tracking.py --list

    # Run all features
    python3 scripts/lead_contractor/run_install_tracking.py

    # Run specific feature (1-6)
    python3 scripts/lead_contractor/run_install_tracking.py --feature 1  # State File
    python3 scripts/lead_contractor/run_install_tracking.py --feature 2  # Step Executor
    python3 scripts/lead_contractor/run_install_tracking.py --feature 3  # CLI Entry Point
    python3 scripts/lead_contractor/run_install_tracking.py --feature 4  # Metric Emission
    python3 scripts/lead_contractor/run_install_tracking.py --feature 5  # Repair Mode
    python3 scripts/lead_contractor/run_install_tracking.py --feature 6  # Dashboard

Output:
    Generated code will be saved to: generated/install_tracking/
"""

import argparse
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.lead_contractor.runner import run_features
from scripts.lead_contractor.tasks.install_tracking import INSTALL_TRACKING_FEATURES

# Use dedicated output directory for install tracking
INSTALL_TRACKING_OUTPUT_DIR = Path(__file__).parent.parent.parent / "generated" / "install_tracking"

FEATURE_DESCRIPTIONS = [
    "State File Infrastructure - install-state.sh",
    "Step Executor Framework - step-executor.sh",
    "CLI Entry Point - create-cluster.sh",
    "Metric Emission - install-metrics.sh",
    "Repair Mode - install-repair.sh",
    "Dashboard Enhancement - installation.json",
]


def main():
    parser = argparse.ArgumentParser(
        description="Run Lead Contractor for Installation Tracking & Resume Plan",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 scripts/lead_contractor/run_install_tracking.py --list
  python3 scripts/lead_contractor/run_install_tracking.py --feature 1
  python3 scripts/lead_contractor/run_install_tracking.py --feature 1-3
  python3 scripts/lead_contractor/run_install_tracking.py
        """
    )
    parser.add_argument(
        "--feature", "-f",
        type=str,
        help="Feature number (1-6) or range (e.g., 1-3)"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List all features and exit"
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
        "--force",
        action="store_true",
        help="Force regeneration even if feature already completed successfully"
    )
    parser.add_argument(
        "--no-skip",
        action="store_true",
        dest="no_skip",
        help="Disable skipping of already-completed features (same as --force)"
    )

    args = parser.parse_args()

    if args.list:
        print("Installation Tracking & Resume Plan")
        print("=" * 70)
        print("\nImplements docs/INSTALLATION_TRACKING_PLAN.md\n")
        print("Vision: Transform installation into a resumable, observable,")
        print("        self-healing system with --resume, --repair, --status flags.\n")
        print("Features:")
        for i, (feature, desc) in enumerate(zip(INSTALL_TRACKING_FEATURES, FEATURE_DESCRIPTIONS), 1):
            print(f"  {i}. {desc}")
            print(f"     → {feature.name}")
        print()
        print("Output: Bash scripts for scripts/ and updated Grafana dashboard")
        print()
        print(f"Total: {len(INSTALL_TRACKING_FEATURES)} features")
        print("\nEstimated cost: $1.50 - $2.50")
        return

    # Parse feature selection
    features = []
    if args.feature:
        if "-" in args.feature:
            start, end = args.feature.split("-")
            start_idx = int(start) - 1
            end_idx = int(end)
            if 0 <= start_idx < len(INSTALL_TRACKING_FEATURES) and start_idx < end_idx <= len(INSTALL_TRACKING_FEATURES):
                features = INSTALL_TRACKING_FEATURES[start_idx:end_idx]
            else:
                print(f"Invalid range. Valid range: 1-{len(INSTALL_TRACKING_FEATURES)}")
                sys.exit(1)
        else:
            feature_num = int(args.feature)
            if 1 <= feature_num <= len(INSTALL_TRACKING_FEATURES):
                features = [INSTALL_TRACKING_FEATURES[feature_num - 1]]
            else:
                print(f"Invalid feature number. Valid range: 1-{len(INSTALL_TRACKING_FEATURES)}")
                sys.exit(1)
    else:
        # Run all features
        features = INSTALL_TRACKING_FEATURES

    print("=" * 70)
    print("Installation Tracking & Resume Plan - Lead Contractor Workflow")
    print("=" * 70)
    print()
    print("This plan implements:")
    print("  - Resumable installation (--resume flag)")
    print("  - Installation repair (--repair flag)")
    print("  - Status checking (--status flag)")
    print("  - Observable installation (metrics to Grafana)")
    print()
    print(f"Features to run: {len(features)}")
    for i, f in enumerate(features, 1):
        desc = FEATURE_DESCRIPTIONS[INSTALL_TRACKING_FEATURES.index(f)]
        print(f"  {i}. {f.name}")
        print(f"     {desc}")
    print()

    # Run the workflow
    results = run_features(
        features,
        output_dir=INSTALL_TRACKING_OUTPUT_DIR,
        verbose=not args.quiet,
        stop_on_error=args.stop_on_error,
        skip_existing=not (args.force or args.no_skip),
        force=args.force or args.no_skip,
    )

    # Summary
    print()
    print("=" * 70)
    print("Summary")
    print("=" * 70)

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
        print("\nNext steps:")
        print("  1. Review generated code in generated/install_tracking/")
        print("  2. Move scripts to scripts/ directory")
        print("  3. Make scripts executable: chmod +x scripts/*.sh")
        print("  4. Update Grafana dashboard from generated JSON")
        print("  5. Test: ./scripts/create-cluster.sh --help")


if __name__ == "__main__":
    main()
