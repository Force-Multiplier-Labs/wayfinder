#!/usr/bin/env python3
"""
HOWL Watcher — Human-Orchestrated Watchdog Loop

Watches a running startd8-sdk artisan workflow for errors and triggers
the HOWL pipeline when issues are detected.

When Coyote detects an error, it HOWLs — triggering a 5-stage AI pipeline:
  1. Investigate — Root cause analysis
  2. Design — Fix specification
  3. Implement — Code generation
  4. Test — Validation
  5. Learn — Lessons extraction

Usage:
    # Watch the default output dir (polls every 10s):
    python3 scripts/watch_artisan_errors.py

    # Custom poll interval and output dir:
    python3 scripts/watch_artisan_errors.py \\
        --output-dir out/manifest-generate-ingestion \\
        --poll-interval 5 \\
        --auto-apply

    # One-shot scan (no polling — check once, exit):
    python3 scripts/watch_artisan_errors.py --once
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("watch_artisan_errors")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_OUTPUT_DIR = Path("out/manifest-generate-ingestion")
DEFAULT_POLL_SECONDS = 10
CHECKPOINT_GLOB = "checkpoints/*.checkpoint.json"
WORKFLOW_RESULT_FILE = "workflow-result.json"
IMPLEMENT_RESULT_FILE = "implement-workflow-result.json"
# startd8-sdk unified error store (per ERROR_MONITORING_GUIDE.md)
STARTD8_ERRORS_JSONL = ".startd8/task_errors/errors.jsonl"
STARTD8_ERRORS_DIR = ".startd8/task_errors"


# ---------------------------------------------------------------------------
# Lazy loader for scripts/dev_repair.py (not a package)
# ---------------------------------------------------------------------------
_dev_repair_mod = None


def _load_dev_repair():
    """Lazily load scripts/dev_repair.py via importlib."""
    global _dev_repair_mod
    if _dev_repair_mod is not None:
        return _dev_repair_mod

    dev_repair_path = Path(__file__).resolve().parent / "dev_repair.py"
    if not dev_repair_path.exists():
        raise FileNotFoundError(f"dev_repair.py not found at {dev_repair_path}")

    spec = importlib.util.spec_from_file_location("dev_repair", dev_repair_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {dev_repair_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _dev_repair_mod = mod
    return mod


# ---------------------------------------------------------------------------
# Error extraction
# ---------------------------------------------------------------------------

def extract_checkpoint_errors(output_dir: Path) -> List[Dict[str, Any]]:
    """
    Read checkpoint files and extract phase-level errors.

    Returns a list of dicts:
        {"source": "checkpoint", "phase": str, "error": str,
         "workflow_id": str, "timestamp": str}
    """
    errors: List[Dict[str, Any]] = []
    for cp_path in sorted(output_dir.glob(CHECKPOINT_GLOB)):
        try:
            data = json.loads(cp_path.read_text())
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Cannot read checkpoint %s: %s", cp_path, exc)
            continue

        workflow_id = data.get("workflow_id", cp_path.stem)
        for pr in data.get("phase_results", []):
            if pr.get("error_message"):
                errors.append({
                    "source": "checkpoint",
                    "phase": pr.get("phase", "unknown"),
                    "error": pr["error_message"],
                    "workflow_id": workflow_id,
                    "timestamp": pr.get("end_time", ""),
                    "cost": pr.get("cost", 0),
                })
    return errors


def extract_result_errors(output_dir: Path) -> List[Dict[str, Any]]:
    """
    Read workflow-result.json / implement-workflow-result.json for phase errors.
    """
    errors: List[Dict[str, Any]] = []
    for fname in (WORKFLOW_RESULT_FILE, IMPLEMENT_RESULT_FILE):
        result_path = output_dir / fname
        if not result_path.exists():
            continue
        try:
            data = json.loads(result_path.read_text())
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Cannot read %s: %s", result_path, exc)
            continue

        workflow_id = data.get("workflow_id", "")
        for pr in data.get("phase_results", []):
            if pr.get("error_message"):
                errors.append({
                    "source": fname,
                    "phase": pr.get("phase", "unknown"),
                    "error": pr["error_message"],
                    "workflow_id": workflow_id,
                    "timestamp": pr.get("end_time", ""),
                    "cost": pr.get("cost", 0),
                })
    return errors


def extract_startd8_errors(project_root: Path) -> List[Dict[str, Any]]:
    """
    Read errors from the startd8-sdk unified error store.

    Per ERROR_MONITORING_GUIDE.md, errors are written to:
    - .startd8/task_errors/errors.jsonl (rolling append-only log)
    - .startd8/task_errors/{workflow_id}/*.json (per-error files)

    Returns a list of dicts matching our standard error format.
    """
    errors: List[Dict[str, Any]] = []

    # Read from errors.jsonl (primary source)
    jsonl_path = project_root / STARTD8_ERRORS_JSONL
    if jsonl_path.exists():
        try:
            for line in jsonl_path.read_text().strip().split("\n"):
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Map startd8 error schema to our format
                errors.append({
                    "source": f"startd8:{data.get('source', 'unknown')}",
                    "phase": data.get("source", data.get("context", {}).get("phase", "unknown")),
                    "error": data.get("error_message", "Unknown error"),
                    "workflow_id": data.get("workflow_id", ""),
                    "task_id": data.get("context", {}).get("task_id", ""),
                    "timestamp": data.get("timestamp", ""),
                    "traceback": data.get("traceback", ""),
                    "error_type": data.get("error_type", ""),
                    "context": data.get("context", {}),
                })
        except OSError as exc:
            logger.warning("Cannot read %s: %s", jsonl_path, exc)

    # Also scan per-workflow error directories for any files not in jsonl
    errors_dir = project_root / STARTD8_ERRORS_DIR
    if errors_dir.is_dir():
        for workflow_dir in errors_dir.iterdir():
            if not workflow_dir.is_dir() or workflow_dir.name.startswith("."):
                continue
            for err_file in sorted(workflow_dir.glob("*.json")):
                try:
                    data = json.loads(err_file.read_text())
                except (json.JSONDecodeError, OSError):
                    continue

                errors.append({
                    "source": f"startd8:{data.get('source', 'unknown')}",
                    "phase": data.get("source", data.get("context", {}).get("phase", "unknown")),
                    "error": data.get("error_message", "Unknown error"),
                    "workflow_id": data.get("workflow_id", workflow_dir.name),
                    "task_id": data.get("context", {}).get("task_id", ""),
                    "timestamp": data.get("timestamp", ""),
                    "traceback": data.get("traceback", ""),
                    "error_type": data.get("error_type", ""),
                    "context": data.get("context", {}),
                })

    return errors


def extract_task_errors(output_dir: Path) -> List[Dict[str, Any]]:
    """
    Scan per-task output files for errors.

    Looks for:
    - PI-*-error.json / PI-*-error.txt  (explicit error files)
    - PI-*-result.json with success=false
    - .startd8/task_errors/*.json
    """
    errors: List[Dict[str, Any]] = []

    # Explicit error files
    for err_file in sorted(output_dir.glob("PI-*-error.*")):
        try:
            content = err_file.read_text().strip()
        except OSError:
            continue
        if not content:
            continue

        task_id = err_file.stem.rsplit("-error", 1)[0]
        if err_file.suffix == ".json":
            try:
                data = json.loads(content)
                error_msg = data.get("error", data.get("message", content))
            except json.JSONDecodeError:
                error_msg = content
        else:
            error_msg = content

        errors.append({
            "source": f"task:{task_id}",
            "phase": "implement",
            "error": error_msg,
            "task_id": task_id,
            "timestamp": "",
        })

    # Task result files with success=false
    for res_file in sorted(output_dir.glob("PI-*-result.json")):
        try:
            data = json.loads(res_file.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        if data.get("success") is False and data.get("error"):
            task_id = res_file.stem.rsplit("-result", 1)[0]
            errors.append({
                "source": f"task:{task_id}",
                "phase": data.get("phase", "implement"),
                "error": data["error"],
                "task_id": task_id,
                "timestamp": data.get("timestamp", ""),
            })

    # .startd8/task_errors/ directory
    task_errors_dir = output_dir / ".startd8" / "task_errors"
    if task_errors_dir.is_dir():
        for err_file in sorted(task_errors_dir.glob("*.json")):
            try:
                data = json.loads(err_file.read_text())
            except (json.JSONDecodeError, OSError):
                continue
            if data.get("error"):
                errors.append({
                    "source": f"task_errors:{err_file.stem}",
                    "phase": data.get("phase", "implement"),
                    "error": data["error"],
                    "task_id": data.get("task_id", err_file.stem),
                    "timestamp": data.get("timestamp", ""),
                })

    return errors


# ---------------------------------------------------------------------------
# Dedup key
# ---------------------------------------------------------------------------

def _error_key(err: Dict[str, Any]) -> str:
    """Stable dedup key for an error entry."""
    return f"{err.get('source', '')}::{err.get('phase', '')}::{err.get('error', '')[:200]}"


# ---------------------------------------------------------------------------
# Test workflow filter
# ---------------------------------------------------------------------------

# Workflow IDs that are clearly from test runs, not production.
# Prefixes are matched case-insensitively.
_TEST_WORKFLOW_PREFIXES = ("test-", "test_", "pytest-", "unittest-", "dry-run-")


def _is_test_workflow(err: Dict[str, Any]) -> bool:
    """Return True if the error comes from a test workflow."""
    wf_id = err.get("workflow_id", "")
    return any(wf_id.lower().startswith(p) for p in _TEST_WORKFLOW_PREFIXES)


# ---------------------------------------------------------------------------
# HOWL Banner
# ---------------------------------------------------------------------------

# Configurable pause duration (seconds) when HOWL is triggered
HOWL_BANNER_PAUSE: float = 10.0

HOWL_ASCII_ART = r"""
                         ____________________________________________
                                          H O W L
                         ____________________________________________


                                                                               .o0Oo.
                                                                             o0'    `0o
     Human-Orchestrated Watchdog Loop                                       O'  °°   `O
     ERROR DETECTED                                                         O   °°    O
     Coyote is investigating...                                             `0o    _o0'
     1. Investigate                                                           `~0o0~'
     2. Design
     3. Implement
     4. Test
     5. Learn



              OOOOOOOOOOOOOOOOoooooooowwwwwwwwwwWWWWWWW

          o ˌ
        _/\/\
       / o  |
      <     |
        \   |
     _/     |
  _/      `.`.
 _/   \__ | |
/     /__\ \ \
(  .'\_______)\_|_|
______________________________________________________________________________________________

   inspired by ascii art from DiuaPsi
"""


def show_howl_banner(
    error_summary: str,
    pause_seconds: float = HOWL_BANNER_PAUSE,
) -> None:
    """
    Display the HOWL ASCII banner when the pipeline is triggered.

    Args:
        error_summary: Brief description of the detected error.
        pause_seconds: How long to pause after displaying (0 to skip pause).
    """
    # Clear some space
    print("\n" * 2)
    print(HOWL_ASCII_ART)
    print(f"  Error: {error_summary[:70]}{'...' if len(error_summary) > 70 else ''}")
    print()

    if pause_seconds > 0:
        print(f"  Starting HOWL pipeline in {pause_seconds:.0f} seconds...")
        print("  (Set HOWL_PAUSE=0 to skip this delay)")
        print()
        time.sleep(pause_seconds)


# ---------------------------------------------------------------------------
# Repair dispatch
# ---------------------------------------------------------------------------

def dispatch_repair(
    err: Dict[str, Any],
    auto_apply: bool = False,
    force: bool = False,
    severity: str = "HIGH",
    project_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Feed an extracted error to Coyote dev repair.

    Args:
        err: Extracted error dict with source, phase, error message, etc.
        auto_apply: If True, apply fixes to actual repo files.
        force: If True, bypass skip filter.
        severity: Incident severity level.
        project_root: Root directory of the codebase to fix.

    Returns the repair_from_error() result dict.
    """
    dev_repair = _load_dev_repair()

    error_message = err["error"]
    # Include traceback if available (from startd8 error store)
    traceback = err.get("traceback", "")
    if traceback:
        error_message = f"{error_message}\n\nTraceback:\n{traceback}"

    context: Dict[str, Any] = {
        "labels": {
            "source": err.get("source", "artisan"),
            "phase": err.get("phase", "unknown"),
            "workflow_id": err.get("workflow_id", ""),
        },
    }
    if err.get("task_id"):
        context["labels"]["task_id"] = err["task_id"]
        context["feature_id"] = err["task_id"]

    logger.info(
        "Dispatching repair: phase=%s task=%s error=%.120s...",
        err.get("phase"), err.get("task_id", "—"), err["error"],
    )
    if project_root:
        logger.info("  Codebase context: %s", project_root)

    result = dev_repair.repair_from_error(
        error_message=error_message,
        severity=severity,
        context=context,
        auto_apply=auto_apply,
        force=force,
        project_root=project_root,
    )
    return result


# ---------------------------------------------------------------------------
# Watcher loop
# ---------------------------------------------------------------------------

def scan_once(
    output_dir: Path,
    seen: Set[str],
    auto_apply: bool = False,
    force: bool = False,
    severity: str = "HIGH",
    project_root: Optional[Path] = None,
    howl_pause: float = HOWL_BANNER_PAUSE,
    observe: bool = False,
) -> List[Dict[str, Any]]:
    """
    Scan all error sources once.  Dispatch repairs for new errors.

    Args:
        output_dir: Directory to scan for error files.
        seen: Set of already-processed error keys (for dedup).
        auto_apply: If True, apply fixes to actual repo files.
        force: If True, bypass skip filter.
        severity: Incident severity level.
        project_root: Root directory of the codebase to fix.
        howl_pause: Seconds to pause after showing HOWL banner (0 to skip).
        observe: If True, log filter verdicts but never dispatch pipeline.

    Returns list of repair results for newly-dispatched errors.
    """
    all_errors: List[Dict[str, Any]] = []
    all_errors.extend(extract_checkpoint_errors(output_dir))
    all_errors.extend(extract_result_errors(output_dir))
    all_errors.extend(extract_task_errors(output_dir))

    # Also check startd8-sdk unified error store
    root = project_root or output_dir.parent
    all_errors.extend(extract_startd8_errors(root))

    results: List[Dict[str, Any]] = []
    for err in all_errors:
        key = _error_key(err)
        if key in seen:
            continue
        seen.add(key)

        # Skip errors from test workflows (e.g. pytest-generated workflow runs)
        if _is_test_workflow(err):
            logger.debug(
                "Skipping test workflow error [%s/%s]: %.80s",
                err.get("source"), err.get("workflow_id"), err["error"],
            )
            continue

        # ── Observe mode: evaluate and log, never dispatch ──
        if observe:
            dev_repair = _load_dev_repair()
            verdict = dev_repair.evaluate_error(err["error"])
            tag = "ALLOW" if verdict["allow"] else "DENY"
            logger.info(
                "[OBSERVE] %s [%s/%s]: %s | %.120s",
                tag,
                err.get("source", "?"),
                err.get("phase", "?"),
                verdict["reason"],
                err["error"],
            )
            results.append({"_error": err, "observe": True, **verdict})
            continue

        logger.info(
            "New error detected [%s/%s]: %.120s",
            err.get("source"), err.get("phase"), err["error"],
        )

        # Show the HOWL banner before triggering the pipeline
        show_howl_banner(
            error_summary=err.get("error", "Unknown error"),
            pause_seconds=howl_pause,
        )

        repair_result = dispatch_repair(
            err,
            auto_apply=auto_apply,
            force=force,
            severity=severity,
            project_root=project_root,
        )
        repair_result["_error"] = err
        results.append(repair_result)

        if repair_result.get("skipped"):
            logger.info("  → Skipped: %s", repair_result.get("reason", ""))
        elif repair_result.get("success"):
            logger.info(
                "  → Repair succeeded: run_id=%s changes=%d",
                repair_result.get("run_id"), repair_result.get("code_changes_count", 0),
            )
        else:
            logger.warning(
                "  → Repair failed: %s", repair_result.get("error", "unknown"),
            )

    return results


def watch_loop(
    output_dir: Path,
    poll_interval: float,
    auto_apply: bool = False,
    force: bool = False,
    severity: str = "HIGH",
    project_root: Optional[Path] = None,
    howl_pause: float = HOWL_BANNER_PAUSE,
    observe: bool = False,
) -> None:
    """
    Poll for errors until interrupted or the workflow completes.

    Args:
        output_dir: Directory to scan for error files.
        poll_interval: Seconds between scans.
        auto_apply: If True, apply fixes to actual repo files.
        force: If True, bypass skip filter.
        severity: Incident severity level.
        project_root: Root directory of the codebase to fix.
        howl_pause: Seconds to pause after showing HOWL banner (0 to skip).
        observe: If True, log filter verdicts but never dispatch pipeline.
    """
    seen: Set[str] = set()
    total_dispatched = 0
    total_succeeded = 0
    total_skipped = 0
    total_allow = 0
    total_deny = 0

    root = project_root or output_dir.parent
    mode_label = "OBSERVE mode (logging only, pipeline disabled)" if observe else "ACTIVE mode"
    logger.info(
        "Watching %s for artisan workflow errors (poll every %ds) — %s",
        output_dir, poll_interval, mode_label,
    )
    logger.info("Also watching %s/.startd8/task_errors/ for startd8-sdk errors.", root)
    logger.info("Press Ctrl+C to stop.\n")

    while True:
        results = scan_once(
            output_dir, seen,
            auto_apply=auto_apply,
            force=force,
            severity=severity,
            project_root=root,
            howl_pause=howl_pause,
            observe=observe,
        )

        for r in results:
            if r.get("observe"):
                if r.get("allow"):
                    total_allow += 1
                else:
                    total_deny += 1
            else:
                total_dispatched += 1
                if r.get("skipped"):
                    total_skipped += 1
                elif r.get("success"):
                    total_succeeded += 1

        # Check if workflow is complete
        wf_result = output_dir / WORKFLOW_RESULT_FILE
        impl_result = output_dir / IMPLEMENT_RESULT_FILE
        for rp in (wf_result, impl_result):
            if rp.exists():
                try:
                    data = json.loads(rp.read_text())
                    status = data.get("status", "")
                    if status in ("completed", "failed", "timed_out"):
                        logger.info(
                            "Workflow %s (status=%s). Final scan complete.",
                            data.get("workflow_id", "?"), status,
                        )
                        if observe:
                            logger.info(
                                "Summary (observe): allow=%d deny=%d",
                                total_allow, total_deny,
                            )
                        else:
                            logger.info(
                                "Summary: dispatched=%d succeeded=%d skipped=%d",
                                total_dispatched, total_succeeded, total_skipped,
                            )
                        return
                except (json.JSONDecodeError, OSError):
                    pass

        time.sleep(poll_interval)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Watch artisan workflow for errors and auto-trigger Coyote repair",
    )
    parser.add_argument(
        "--output-dir", "-d",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Artisan workflow output directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--poll-interval", "-p",
        type=float,
        default=DEFAULT_POLL_SECONDS,
        help=f"Seconds between scans (default: {DEFAULT_POLL_SECONDS})",
    )
    parser.add_argument(
        "--auto-apply",
        action="store_true",
        default=False,
        help="Save Coyote-generated code to generated/coyote/",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Bypass Coyote skip filter (repair even auth/infra errors)",
    )
    parser.add_argument(
        "--severity", "-s",
        choices=["LOW", "MEDIUM", "HIGH", "CRITICAL"],
        default="HIGH",
        help="Default severity for dispatched incidents (default: HIGH)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        default=False,
        help="Scan once and exit (no polling)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        default=False,
        help="Enable debug logging",
    )
    parser.add_argument(
        "--project-root", "-r",
        type=Path,
        default=None,
        help="Project root for startd8 error store (default: parent of output-dir)",
    )
    parser.add_argument(
        "--howl-pause",
        type=float,
        default=HOWL_BANNER_PAUSE,
        help=f"Seconds to pause after showing HOWL banner (default: {HOWL_BANNER_PAUSE}, 0 to skip)",
    )
    parser.add_argument(
        "--observe",
        action="store_true",
        default=False,
        help="Observe mode: log ALLOW/DENY verdicts for each error but never dispatch the pipeline. "
             "Use this to tune positive/skip filters before enabling HOWL.",
    )

    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    output_dir = args.output_dir.resolve()
    if not output_dir.is_dir():
        logger.error("Output directory does not exist: %s", output_dir)
        return 1

    project_root = args.project_root.resolve() if args.project_root else output_dir.parent

    if args.once:
        seen: Set[str] = set()
        results = scan_once(
            output_dir, seen,
            auto_apply=args.auto_apply,
            force=args.force,
            severity=args.severity,
            project_root=project_root,
            howl_pause=args.howl_pause,
            observe=args.observe,
        )
        if not results:
            logger.info("No errors found.")
        else:
            for r in results:
                err = r.get("_error", {})
                if r.get("observe"):
                    tag = "ALLOW" if r.get("allow") else "DENY"
                    print(
                        f"[{tag}] {err.get('source', '?')}/{err.get('phase', '?')}: "
                        f"{err.get('error', '?')[:100]}"
                    )
                else:
                    status = "OK" if r.get("success") else ("SKIP" if r.get("skipped") else "FAIL")
                    print(
                        f"[{status}] {err.get('source', '?')}/{err.get('phase', '?')}: "
                        f"{err.get('error', '?')[:100]}"
                    )
            if args.observe:
                allow_count = sum(1 for r in results if r.get("allow"))
                deny_count = len(results) - allow_count
                print(f"\nObserve summary: {allow_count} ALLOW, {deny_count} DENY out of {len(results)} errors")
        return 0

    # Polling loop (Ctrl+C to stop)
    def _handle_sigint(signum, frame):
        logger.info("\nStopping watcher.")
        sys.exit(0)

    signal.signal(signal.SIGINT, _handle_sigint)

    watch_loop(
        output_dir=output_dir,
        poll_interval=args.poll_interval,
        auto_apply=args.auto_apply,
        force=args.force,
        severity=args.severity,
        project_root=project_root,
        howl_pause=args.howl_pause,
        observe=args.observe,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
