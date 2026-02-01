#!/usr/bin/env python3
"""
Run Lead Contractor workflow for VSCode Extension Assembly tasks.

These tasks take the generated feature code and assemble it into
a complete, compilable VSCode extension structure.

Usage:
    python3 scripts/lead_contractor/run_vscode_assembly.py
    python3 scripts/lead_contractor/run_vscode_assembly.py --feature 1
    python3 scripts/lead_contractor/run_vscode_assembly.py --list
"""

import argparse
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.lead_contractor.runner import run_features
from scripts.lead_contractor.tasks.vscode_assembly import ASSEMBLY_FEATURES


def main():
    parser = argparse.ArgumentParser(
        description="Run Lead Contractor for VSCode Extension Assembly"
    )
    parser.add_argument(
        "--feature", "-f",
        type=int,
        help=f"Run specific feature (1-{len(ASSEMBLY_FEATURES)})"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List available assembly tasks"
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
        print("VSCode Extension Assembly Tasks:")
        print()
        for i, feature in enumerate(ASSEMBLY_FEATURES, 1):
            print(f"  {i}. {feature.name}")
        print()
        print("Run order:")
        print("  1. PackageConfig  - package.json, tsconfig.json, etc.")
        print("  2. CoreModules    - types.ts, config.ts, logger.ts, cache.ts")
        print("  3. Providers      - Context loading from local/CLI/K8s")
        print("  4. Mapping        - File-to-context mapping")
        print("  5. UI             - Status bar, side panel, decorations")
        print("  6. Commands       - Commands + extension.ts entry point")
        print("  7. Resources      - SVG icons + README.md")
        return

    features = ASSEMBLY_FEATURES
    if args.feature:
        if 1 <= args.feature <= len(ASSEMBLY_FEATURES):
            features = [ASSEMBLY_FEATURES[args.feature - 1]]
        else:
            print(f"Invalid feature number. Use 1-{len(ASSEMBLY_FEATURES)}")
            sys.exit(1)

    print("=" * 60)
    print("VSCode Extension Assembly - Lead Contractor Workflow")
    print("=" * 60)
    print(f"\nTasks to run: {len(features)}")
    for f in features:
        print(f"  - {f.name}")
    print()

    results = run_features(
        features,
        verbose=not args.quiet,
        stop_on_error=args.stop_on_error,
    )

    # Print summary
    print()
    print("=" * 60)
    print("ASSEMBLY SUMMARY")
    print("=" * 60)

    total_cost = sum(r.total_cost for r in results)
    successful = sum(1 for r in results if r.success)

    print(f"Tasks completed: {successful}/{len(results)}")
    print(f"Total cost: ${total_cost:.4f}")
    print()
    print("Output directory: generated/phase3/vscode_assembly/")
    print()

    if successful == len(results):
        print("Next steps:")
        print("  1. Review generated files in generated/phase3/vscode_assembly/")
        print("  2. Create extension directory: mkdir -p extensions/vscode/src")
        print("  3. Copy files to correct locations")
        print("  4. Run: cd extensions/vscode && npm install && npm run compile")
        print("  5. Test: Press F5 in VSCode to launch Extension Development Host")

    # Exit with error if any failed
    if any(not r.success for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
