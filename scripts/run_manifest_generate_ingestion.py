#!/usr/bin/env python3
"""
Run PlanIngestionWorkflow for the contextcore manifest generate plan.

This script ingests the wayfinder-contextcore-manifest-generate-plan.md
and produces artifacts for the startd8-sdk artisan workflow, enriched
with context from the ContextCore manifest export.

Usage:
    python3 scripts/run_manifest_generate_ingestion.py [options]

Options:
    --dry-run           Preview without running (validate only)
    --force-route       Force route: 'prime' or 'artisan' (default: auto)
    --review-rounds N   Number of architectural review rounds (default: 2)
    --max-cost N        Maximum cost in USD (default: 5.00)
    --output-dir PATH   Output directory (default: out/manifest-generate-ingestion)

Outputs:
    - PLAN-ingested.md: Refined plan document with architectural review
    - artisan-context-seed.json: Context seed for artisan workflow
    - review-config.json: Architectural review configuration
    - .startd8/plan_ingestion_state.json: Workflow state checkpoint

Virtual Environment:
    This script automatically activates the startd8-sdk virtual environment
    if it exists. You can override this by setting STARTD8_SDK_PATH or by
    activating your preferred environment before running.
"""

import argparse
import os
import sys
import time
from pathlib import Path


def setup_virtual_environment():
    """
    Activate the startd8-sdk virtual environment if needed.
    
    Priority order:
    1. If already in a virtual environment, use it
    2. If STARTD8_SDK_PATH is set, use that
    3. Try to find and activate startd8-sdk/.venv
    4. Fall back to adding startd8-sdk/src to sys.path
    """
    script_dir = Path(__file__).resolve().parent
    wayfinder_root = script_dir.parent
    startd8_sdk_root = wayfinder_root.parent / "startd8-sdk"
    startd8_venv = startd8_sdk_root / ".venv"
    startd8_src = startd8_sdk_root / "src"
    
    # Check if we're already in a virtual environment
    in_venv = sys.prefix != sys.base_prefix
    
    # Check if STARTD8_SDK_PATH is set
    sdk_path_env = os.environ.get("STARTD8_SDK_PATH")
    
    if sdk_path_env:
        # User explicitly set the path, use it
        sys.path.insert(0, sdk_path_env)
        return {
            "method": "STARTD8_SDK_PATH environment variable",
            "path": sdk_path_env,
            "venv_active": in_venv,
        }
    
    if in_venv:
        # Already in a venv, just add the src path
        if startd8_src.exists():
            sys.path.insert(0, str(startd8_src))
            return {
                "method": "existing virtual environment + src path",
                "path": str(startd8_src),
                "venv_active": True,
                "venv_path": sys.prefix,
            }
    
    # Try to activate startd8-sdk venv by adding its site-packages
    if startd8_venv.exists():
        # Find the site-packages directory
        if sys.platform == "win32":
            site_packages = startd8_venv / "Lib" / "site-packages"
        else:
            # macOS/Linux: find python version directory
            lib_dir = startd8_venv / "lib"
            if lib_dir.exists():
                python_dirs = [d for d in lib_dir.iterdir() if d.name.startswith("python")]
                if python_dirs:
                    site_packages = python_dirs[0] / "site-packages"
                else:
                    site_packages = None
            else:
                site_packages = None
        
        if site_packages and site_packages.exists():
            # Add site-packages to sys.path (simulates venv activation for imports)
            sys.path.insert(0, str(site_packages))
            # Also add the src directory
            if startd8_src.exists():
                sys.path.insert(0, str(startd8_src))
            return {
                "method": "startd8-sdk .venv site-packages",
                "path": str(startd8_src),
                "venv_path": str(startd8_venv),
                "site_packages": str(site_packages),
                "venv_active": False,  # Not truly activated, just path added
            }
    
    # Fall back to just adding src path
    if startd8_src.exists():
        sys.path.insert(0, str(startd8_src))
        return {
            "method": "startd8-sdk/src path only (no venv)",
            "path": str(startd8_src),
            "venv_active": False,
        }
    
    return {
        "method": "none",
        "error": f"Could not find startd8-sdk at {startd8_sdk_root}",
    }


# Setup environment before imports
VENV_INFO = setup_virtual_environment()

try:
    from startd8.workflows.builtin.plan_ingestion_workflow import PlanIngestionWorkflow
except ImportError as e:
    print(f"Error: Cannot import startd8.")
    print(f"  Environment setup: {VENV_INFO.get('method', 'unknown')}")
    if 'path' in VENV_INFO:
        print(f"  Tried path: {VENV_INFO['path']}")
    if 'error' in VENV_INFO:
        print(f"  Setup error: {VENV_INFO['error']}")
    print(f"  Import error: {e}")
    print()
    print("Solutions:")
    print("  1. Activate startd8-sdk venv: source ~/Documents/dev/startd8-sdk/.venv/bin/activate")
    print("  2. Set STARTD8_SDK_PATH: export STARTD8_SDK_PATH=~/Documents/dev/startd8-sdk/src")
    print("  3. Install startd8 in current env: pip install -e ~/Documents/dev/startd8-sdk")
    sys.exit(1)

# === Paths ===
SCRIPT_DIR = Path(__file__).resolve().parent
WAYFINDER_ROOT = SCRIPT_DIR.parent
CONTEXTCORE_ROOT = WAYFINDER_ROOT.parent / "ContextCore"

# Input: The plan document to ingest
PLAN_FILE = WAYFINDER_ROOT / "docs" / "plans" / "wayfinder-contextcore-manifest-generate-plan.md"

# Context files from ContextCore export (enriches the review)
CONTEXT_FILES = [
    WAYFINDER_ROOT / "out" / "contextcore-export" / "wayfinder-artifact-manifest.yaml",
    WAYFINDER_ROOT / "out" / "contextcore-export" / "wayfinder-projectcontext.yaml",
    WAYFINDER_ROOT / ".contextcore.yaml",
]

# Onboarding metadata (added when present; includes artifact_types, checksums, schema)
ONBOARDING_METADATA_PATH = WAYFINDER_ROOT / "out" / "contextcore-export" / "onboarding-metadata.json"

# Default output directory
DEFAULT_OUTPUT_DIR = WAYFINDER_ROOT / "out" / "manifest-generate-ingestion"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run plan ingestion for contextcore manifest generate command",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate config and show plan without running",
    )
    parser.add_argument(
        "--force-route",
        choices=["prime", "artisan"],
        default=None,
        help="Force routing to prime or artisan (default: auto based on complexity)",
    )
    parser.add_argument(
        "--review-rounds",
        type=int,
        default=2,
        help="Number of architectural review rounds (default: 2)",
    )
    parser.add_argument(
        "--review-quality-tier",
        choices=["flagship", "standard", "fast"],
        default="flagship",
        help="Quality tier for architectural review (default: flagship)",
    )
    parser.add_argument(
        "--max-cost",
        type=float,
        default=5.00,
        help="Maximum cost in USD (default: 5.00)",
    )
    parser.add_argument(
        "--warn-cost",
        type=float,
        default=1.00,
        help="Warn when cost exceeds this threshold (default: 1.00)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--no-context",
        action="store_true",
        help="Skip ContextCore context files (run without enrichment)",
    )
    parser.add_argument(
        "--generate-task-tracking",
        action="store_true",
        help="Generate ContextCore task tracking artifacts",
    )
    parser.add_argument(
        "--project-id",
        default="wayfinder",
        help="Project ID for task tracking (default: wayfinder)",
    )
    parser.add_argument(
        "--emit-provenance",
        action="store_true",
        default=True,
        help="Write provenance.json with full audit trail (default: True)",
    )
    parser.add_argument(
        "--no-provenance",
        action="store_true",
        help="Skip writing provenance.json",
    )
    return parser.parse_args()


def on_progress(current: int, total: int, msg: str) -> None:
    """Progress callback for workflow steps."""
    print(f"  [{current}/{total}] {msg}")


def capture_ingestion_provenance(
    args,
    context_files: list,
    config: dict,
    venv_info: dict,
    start_time,
    result=None,
) -> dict:
    """
    Capture comprehensive provenance metadata for the ingestion run.
    
    Returns:
        Dict with provenance metadata suitable for JSON serialization.
    """
    import hashlib
    import socket
    import getpass
    import subprocess
    from datetime import datetime
    
    def get_file_checksum(file_path: str) -> str:
        """Compute SHA-256 checksum of a file."""
        try:
            hasher = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            return None
    
    def get_git_info(file_path: str) -> dict:
        """Get git context for a file."""
        try:
            repo_dir = Path(file_path).resolve().parent
            
            def run_git(args):
                result = subprocess.run(
                    ["git"] + args,
                    cwd=str(repo_dir),
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                return result.stdout.strip() if result.returncode == 0 else None
            
            return {
                "commitSha": run_git(["rev-parse", "HEAD"]),
                "branch": run_git(["rev-parse", "--abbrev-ref", "HEAD"]),
                "isDirty": bool(run_git(["status", "--porcelain"])),
                "remoteUrl": run_git(["remote", "get-url", "origin"]),
            }
        except Exception:
            return None
    
    now = datetime.now()
    duration_ms = int((now - start_time).total_seconds() * 1000) if start_time else None
    
    # Build provenance
    provenance = {
        "schemaVersion": "1.0.0",
        "generatedAt": now.isoformat(),
        "durationMs": duration_ms,
        
        # Invocation
        "invocation": {
            "script": str(Path(__file__).resolve()),
            "cliArgs": sys.argv,
            "cliOptions": {
                "dryRun": args.dry_run,
                "forceRoute": args.force_route,
                "reviewRounds": args.review_rounds,
                "reviewQualityTier": args.review_quality_tier,
                "maxCost": args.max_cost,
                "warnCost": args.warn_cost,
                "outputDir": str(args.output_dir),
                "noContext": args.no_context,
                "generateTaskTracking": args.generate_task_tracking,
                "projectId": args.project_id,
            },
        },
        
        # Environment
        "environment": {
            "hostname": socket.gethostname(),
            "username": getpass.getuser(),
            "workingDirectory": os.getcwd(),
            "pythonVersion": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "venvSetup": venv_info,
        },
        
        # Inputs
        "inputs": {
            "planFile": {
                "path": str(PLAN_FILE),
                "checksum": get_file_checksum(str(PLAN_FILE)),
                "git": get_git_info(str(PLAN_FILE)),
            },
            "contextFiles": [
                {
                    "path": cf,
                    "checksum": get_file_checksum(cf),
                }
                for cf in context_files
            ],
        },
        
        # Workflow config
        "workflowConfig": config,
    }
    
    # Add result info if available
    if result:
        provenance["result"] = {
            "success": result.success,
            "error": result.error,
        }
        if result.metrics:
            provenance["result"]["metrics"] = {
                "totalCost": result.metrics.total_cost,
                "inputTokens": result.metrics.input_tokens,
                "outputTokens": result.metrics.output_tokens,
                "stepCount": result.metrics.step_count,
            }
        if result.output:
            provenance["outputs"] = {
                "planDocumentPath": result.output.get("plan_document_path"),
                "contextSeedPath": result.output.get("context_seed_path"),
                "reviewConfigPath": result.output.get("review_config_path"),
                "route": result.output.get("route"),
                "complexityScore": result.output.get("complexity_composite"),
            }
    
    return provenance


def merge_onboarding_into_seed(
    seed_path: str,
    onboarding_path: Path,
    export_dir: Path,
    wayfinder_root: Path,
) -> bool:
    """
    Merge onboarding-metadata.json into artisan-context-seed.json.

    Adds artifact_manifest_path, project_context_path, checksums to artifacts,
    and onboarding section with artifact_types, output_path_conventions,
    semantic_conventions for downstream generators.

    Uses paths relative to wayfinder root for portability.

    Returns True if merge was performed.
    """
    import json

    if not onboarding_path.exists():
        return False

    try:
        seed_data = json.loads(Path(seed_path).read_text(encoding="utf-8"))
        onboarding_data = json.loads(onboarding_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"  Warning: Could not merge onboarding: {e}")
        return False

    # Paths relative to wayfinder root for portability
    artifact_manifest_path = onboarding_data.get("artifact_manifest_path", "")
    project_context_path = onboarding_data.get("project_context_path", "")
    try:
        rel_export = export_dir.resolve().relative_to(wayfinder_root.resolve())
        artifact_manifest_rel = str(rel_export / artifact_manifest_path)
        project_context_rel = str(rel_export / project_context_path)
    except ValueError:
        artifact_manifest_rel = str(export_dir / artifact_manifest_path)
        project_context_rel = str(export_dir / project_context_path)

    # Extend artifacts section
    if "artifacts" not in seed_data:
        seed_data["artifacts"] = {}
    seed_data["artifacts"]["artifact_manifest_path"] = artifact_manifest_rel
    seed_data["artifacts"]["project_context_path"] = project_context_rel
    # Context file checksums for drift detection
    if "artifact_manifest_checksum" in onboarding_data:
        seed_data["artifacts"]["artifact_manifest_checksum"] = onboarding_data[
            "artifact_manifest_checksum"
        ]
    if "project_context_checksum" in onboarding_data:
        seed_data["artifacts"]["project_context_checksum"] = onboarding_data[
            "project_context_checksum"
        ]

    # Plan vs context note when artifact counts differ (item 3)
    plan_vs_context_note = None
    coverage = onboarding_data.get("coverage", {})
    manifest_artifact_count = coverage.get("totalRequired", 0) or len(
        coverage.get("gaps", [])
    )
    if manifest_artifact_count > 0:
        # Heuristic: plan often mentions "77" or "7 × 11" for Online Boutique
        plan_text = json.dumps(seed_data.get("plan", {}))
        if "77" in plan_text or "7 × 11" in plan_text:
            plan_vs_context_note = (
                f"Plan describes generic Online Boutique (77 artifacts). "
                f"Context has {manifest_artifact_count} artifacts for this project. "
                f"Use artifact_manifest_path and onboarding.artifact_types for actual count."
            )
    if plan_vs_context_note:
        seed_data["plan_vs_context_note"] = plan_vs_context_note

    # Add onboarding section for generators
    seed_data["onboarding"] = {
        "artifact_types": onboarding_data.get("artifact_types", {}),
        "output_path_conventions": onboarding_data.get(
            "output_path_conventions", {}
        ),
        "parameter_schema": onboarding_data.get("parameter_schema", {}),
        "semantic_conventions": onboarding_data.get(
            "semantic_conventions"
        ),
        "source_checksum": onboarding_data.get("source_checksum"),
        "artifact_manifest_checksum": onboarding_data.get(
            "artifact_manifest_checksum"
        ),
        "project_context_checksum": onboarding_data.get(
            "project_context_checksum"
        ),
    }

    Path(seed_path).write_text(
        json.dumps(seed_data, indent=2, default=str), encoding="utf-8"
    )
    return True


def write_provenance(provenance: dict, output_dir: Path) -> str:
    """Write provenance to JSON file."""
    import json
    
    provenance_path = output_dir / "ingestion-provenance.json"
    with open(provenance_path, "w", encoding="utf-8") as f:
        json.dump(provenance, f, indent=2, default=str)
    
    return str(provenance_path)


def main():
    from datetime import datetime
    
    args = parse_args()
    start_time = datetime.now()

    # Validate inputs
    if not PLAN_FILE.exists():
        print(f"Error: Plan file not found: {PLAN_FILE}")
        sys.exit(1)

    # Collect existing context files (include onboarding-metadata.json when present)
    context_files = []
    if not args.no_context:
        for cf in CONTEXT_FILES:
            if cf.exists():
                context_files.append(str(cf))
            else:
                print(f"  Warning: Context file not found: {cf}")
        if ONBOARDING_METADATA_PATH.exists():
            context_files.append(str(ONBOARDING_METADATA_PATH))
        elif context_files:
            print(
                f"  Hint: Run contextcore manifest export (from ContextCore repo) with "
                f"-p wayfinder/.contextcore.yaml -o wayfinder/out/contextcore-export to generate "
                f"onboarding-metadata.json for seed enrichment"
            )

    # Build config
    config = {
        "plan_path": str(PLAN_FILE),
        "output_dir": str(args.output_dir),
        "review_rounds": args.review_rounds,
        "review_quality_tier": args.review_quality_tier,
        "warn_cost_usd": args.warn_cost,
        "max_cost_usd": args.max_cost,
    }

    if args.force_route:
        config["force_route"] = args.force_route

    if context_files:
        config["context_files"] = ",".join(context_files)

    if args.generate_task_tracking:
        config["generate_task_tracking"] = True
        config["project_id"] = args.project_id

    # Initialize workflow
    workflow = PlanIngestionWorkflow()

    # Validate
    validation = workflow.validate_config(config)
    if not validation.valid:
        print(f"Configuration errors:")
        for err in validation.errors:
            print(f"  - {err}")
        sys.exit(1)

    # Determine if provenance should be emitted
    emit_provenance = args.emit_provenance and not args.no_provenance

    # Print summary
    print("=" * 60)
    print("ContextCore Manifest Generate - Plan Ingestion")
    print("=" * 60)
    print(f"Plan:          {PLAN_FILE.name}")
    print(f"Output:        {args.output_dir}")
    print(f"Route:         {args.force_route or 'auto (based on complexity)'}")
    print(f"Review rounds: {args.review_rounds}")
    print(f"Quality tier:  {args.review_quality_tier}")
    print(f"Max cost:      ${args.max_cost:.2f}")
    print(f"Provenance:    {'enabled' if emit_provenance else 'disabled'}")
    if context_files:
        print(f"Context files: {len(context_files)}")
        for cf in context_files:
            print(f"  - {Path(cf).name}")
    print(f"Environment:   {VENV_INFO.get('method', 'unknown')}")
    print()

    if args.dry_run:
        print("DRY RUN - Configuration validated, not executing.")
        if emit_provenance:
            # Show what provenance would look like
            provenance = capture_ingestion_provenance(
                args=args,
                context_files=context_files,
                config=config,
                venv_info=VENV_INFO,
                start_time=start_time,
                result=None,
            )
            print("\nProvenance preview (partial):")
            print(f"  Generated at: {provenance['generatedAt']}")
            print(f"  Hostname: {provenance['environment']['hostname']}")
            print(f"  Plan checksum: {provenance['inputs']['planFile']['checksum'][:16]}...")
            if provenance['inputs']['planFile'].get('git'):
                git = provenance['inputs']['planFile']['git']
                print(f"  Git: {git.get('branch')}@{git.get('commitSha', '')[:8]}")
        print("\nTo run for real, remove --dry-run flag.")
        sys.exit(0)

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Run workflow
    print("Starting plan ingestion workflow...")
    print()

    t0 = time.time()
    result = workflow.run(
        config=config,
        agents=None,
        on_progress=on_progress,
        dry_run=False,
    )
    elapsed = time.time() - t0

    # Print results
    print()
    print("=" * 60)
    status = "SUCCEEDED" if result.success else "FAILED"
    print(f"Workflow {status} in {elapsed:.1f}s")
    print("=" * 60)

    if result.metrics:
        print(f"  Cost:   ${result.metrics.total_cost:.4f}")
        print(f"  Tokens: {result.metrics.input_tokens:,} in / {result.metrics.output_tokens:,} out")
        print(f"  Steps:  {result.metrics.step_count}")

    # Capture and write provenance
    provenance_path = None
    if emit_provenance:
        provenance = capture_ingestion_provenance(
            args=args,
            context_files=context_files,
            config=config,
            venv_info=VENV_INFO,
            start_time=start_time,
            result=result,
        )
        provenance_path = write_provenance(provenance, args.output_dir)
        print(f"\n  Provenance: {provenance_path}")

    if result.success and result.output:
        print(f"\nOutputs:")
        for key, value in result.output.items():
            if isinstance(value, str) and len(value) > 80:
                value = value[:77] + "..."
            print(f"  {key}: {value}")

        # Merge onboarding metadata into seed when present
        context_seed = result.output.get("context_seed_path")
        export_dir = WAYFINDER_ROOT / "out" / "contextcore-export"
        if context_seed and ONBOARDING_METADATA_PATH.exists():
            if merge_onboarding_into_seed(
                context_seed,
                ONBOARDING_METADATA_PATH,
                export_dir,
                WAYFINDER_ROOT,
            ):
                print(f"\n  Merged onboarding metadata into seed")

        # Print next steps
        print("\n" + "=" * 60)
        print("Next Steps")
        print("=" * 60)
        
        context_seed = result.output.get("context_seed_path")
        if context_seed:
            print(f"\n1. Review the context seed:")
            print(f"   cat {context_seed}")
            if provenance_path:
                print(f"\n   Review provenance:")
                print(f"   cat {provenance_path}")
            print(f"\n2. Run the artisan workflow (design phase):")
            print(f"   python3 ~/Documents/dev/startd8-sdk/scripts/run_artisan_design_only.py \\")
            print(f"       --seed {context_seed} \\")
            print(f"       --output-dir {args.output_dir}/artisan-design")
            print(f"\n3. After review, run implementation:")
            print(f"   python3 ~/Documents/dev/startd8-sdk/scripts/run_artisan_implement_only.py \\")
            print(f"       --handoff {args.output_dir}/artisan-design/design-handoff.json")

    if result.error:
        print(f"\nError: {result.error}")
        for step in result.steps:
            if step.error:
                print(f"  Step {step.step_name}: {step.error}")

    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()
