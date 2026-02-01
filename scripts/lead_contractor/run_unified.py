#!/usr/bin/env python3
"""
Run Lead Contractor workflow for Phase 4: Unified Protocol Alignment.

Combines OTel GenAI semantic conventions and A2A protocol alignment into
a single execution plan with 9 phases and 27 tasks.

Usage:
    python3 scripts/lead_contractor/run_unified.py
    python3 scripts/lead_contractor/run_unified.py --phase 1
    python3 scripts/lead_contractor/run_unified.py --phase 2 --task 1
    python3 scripts/lead_contractor/run_unified.py --list
"""

import argparse
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.lead_contractor.runner import run_features

# Phase imports
from scripts.lead_contractor.tasks.unified_foundation import FOUNDATION_FEATURES
from scripts.lead_contractor.tasks.unified_api import API_FEATURES
from scripts.lead_contractor.tasks.a2a_state import STATE_FEATURES
from scripts.lead_contractor.tasks.unified_otel import CORE_OTEL_FEATURES, EXTENDED_OTEL_FEATURES
from scripts.lead_contractor.tasks.a2a_discovery import DISCOVERY_FEATURES
from scripts.lead_contractor.tasks.a2a_parts import PARTS_FEATURES
from scripts.lead_contractor.tasks.a2a_adapter import A2A_ADAPTER_FEATURES
from scripts.lead_contractor.tasks.unified_docs import DOCS_FEATURES

PHASES = {
    1: ("Foundation", FOUNDATION_FEATURES),
    2: ("API Facades", API_FEATURES),
    3: ("State Model", STATE_FEATURES),
    4: ("Core OTel Attributes", CORE_OTEL_FEATURES),
    5: ("Discovery", DISCOVERY_FEATURES),
    6: ("Part Model", PARTS_FEATURES),
    7: ("Extended OTel Attributes", EXTENDED_OTEL_FEATURES),
    8: ("A2A Adapter", A2A_ADAPTER_FEATURES),
    9: ("Documentation", DOCS_FEATURES),
}


def main():
    parser = argparse.ArgumentParser(
        description="Run Lead Contractor for Unified Protocol Alignment"
    )
    parser.add_argument(
        "--phase", "-p",
        type=int,
        choices=list(PHASES.keys()),
        help="Run specific phase (1-9)"
    )
    parser.add_argument(
        "--task", "-t",
        type=int,
        help="Run specific task within phase"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List all phases and tasks"
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
        print("Phase 4: Unified Protocol Alignment")
        print("=" * 70)
        print("\nCombines OTel GenAI semantic conventions and A2A protocol alignment.\n")
        total = 0
        for phase_num, (phase_name, features) in PHASES.items():
            print(f"Phase {phase_num}: {phase_name} (--phase {phase_num})")
            for i, f in enumerate(features, 1):
                print(f"  {phase_num}.{i} {f.name}")
            total += len(features)
            print()
        print(f"Total: {total} tasks across {len(PHASES)} phases")
        print("\nEstimated cost: $3.50 - $5.00")
        return

    # Collect features based on arguments
    features = []
    if args.phase:
        phase_name, phase_features = PHASES[args.phase]
        if args.task:
            if 1 <= args.task <= len(phase_features):
                features = [phase_features[args.task - 1]]
            else:
                print(f"Invalid task number. Phase {args.phase} has {len(phase_features)} tasks.")
                sys.exit(1)
        else:
            features = phase_features
    else:
        # Run all phases in order
        for _, phase_features in PHASES.values():
            features.extend(phase_features)

    print("=" * 70)
    print("Phase 4: Unified Protocol Alignment - Lead Contractor Workflow")
    print("=" * 70)
    print("\nThis plan combines:")
    print("  - OTel GenAI semantic conventions (span attributes)")
    print("  - A2A protocol alignment (API design, discovery, interop)")
    print()
    print(f"Tasks to run: {len(features)}")
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
    print("=" * 70)
    print("Summary")
    print("=" * 70)

    success_count = sum(1 for r in results if r.success)
    fail_count = len(results) - success_count

    print(f"Total: {len(results)}")
    print(f"Passed: {success_count}")
    print(f"Failed: {fail_count}")

    if fail_count > 0:
        print("\nFailed tasks:")
        for r in results:
            if not r.success:
                print(f"  - {r.feature_name}: {r.error or 'Unknown error'}")
        sys.exit(1)
    else:
        print("\nAll tasks completed successfully!")


if __name__ == "__main__":
    main()
