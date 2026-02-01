#!/usr/bin/env python3
"""
Run Lead Contractor workflow for Knowledge Graph features.

Usage:
    python3 scripts/lead_contractor/run_graph.py
    python3 scripts/lead_contractor/run_graph.py --feature 1
    python3 scripts/lead_contractor/run_graph.py --list
"""

import argparse
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.lead_contractor.runner import run_features
from scripts.lead_contractor.tasks.graph import GRAPH_FEATURES


def main():
    parser = argparse.ArgumentParser(
        description="Run Lead Contractor for Knowledge Graph features"
    )
    parser.add_argument(
        "--feature", "-f",
        type=int,
        help="Run specific feature (1-4)"
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
        print("Knowledge Graph Features:")
        for i, feature in enumerate(GRAPH_FEATURES, 1):
            print(f"  {i}. {feature.name}")
        return

    features = GRAPH_FEATURES
    if args.feature:
        if 1 <= args.feature <= len(GRAPH_FEATURES):
            features = [GRAPH_FEATURES[args.feature - 1]]
        else:
            print(f"Invalid feature number. Use 1-{len(GRAPH_FEATURES)}")
            sys.exit(1)

    print("=" * 60)
    print("Knowledge Graph - Lead Contractor Workflow")
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

    # Exit with error if any failed
    if any(not r.success for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
