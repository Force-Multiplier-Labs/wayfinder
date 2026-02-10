"""
Coyote Bridge Actions - Connects Coyote pipeline output to Prime Contractor.

Two integration paths:
- coyote_apply: Full pipeline output → save to disk → Prime Contractor integrates
- coyote_spec: Investigation+Design → save work specification → any workflow picks up

Status queries:
- coyote_apply_status: Query status of an apply run
"""

import json
import logging
import re
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from contextcore_rabbit.action import Action, ActionResult, ActionStatus, action_registry
from contextcore_rabbit.actions.coyote_investigate import _coyote_runs

logger = logging.getLogger(__name__)

# Track apply runs separately from pipeline runs
_apply_runs: Dict[str, Dict[str, Any]] = {}

# Default output directory (relative to project root)
DEFAULT_GENERATED_DIR = Path("generated/coyote")


def _slugify(filename: str) -> str:
    """Convert a filename to a safe slug for disk paths."""
    # Strip path separators to prevent directory traversal
    base = Path(filename).name
    # Remove extension, replace non-alphanum with underscore
    stem = Path(base).stem
    return re.sub(r"[^a-zA-Z0-9_-]", "_", stem)


def _write_coyote_output(
    run_id: str,
    output_base: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Write Coyote pipeline output to disk in the format Prime Contractor expects.

    Reads from _coyote_runs[run_id] for code_changes and commit_message.

    Args:
        run_id: The coyote pipeline run ID
        output_base: Base directory for output (default: generated/coyote)

    Returns:
        Dict with generated_dir, files_written, count
    """
    run_data = _coyote_runs[run_id]
    incident_id = run_data.get("incident_id", f"unknown-{run_id}")
    severity = run_data.get("severity", "MEDIUM")

    base_dir = output_base or DEFAULT_GENERATED_DIR
    incident_dir = base_dir / incident_id
    incident_dir.mkdir(parents=True, exist_ok=True)

    # Extract code_changes and commit_message from stage_results
    code_changes: Dict[str, str] = {}
    commit_message: Optional[str] = None
    root_cause: Optional[str] = None

    for sr in run_data.get("stage_results", []):
        if sr.get("stage") == "implement" and sr.get("code_changes"):
            code_changes = sr["code_changes"]
            commit_message = sr.get("commit_message")
        if sr.get("stage") == "investigate" and sr.get("root_cause"):
            root_cause = sr["root_cause"]

    files_written: List[str] = []

    for filename, code_content in code_changes.items():
        slug = _slugify(filename)

        # Write the code file
        code_path = incident_dir / f"{slug}_code.py"
        code_path.write_text(code_content, encoding="utf-8")
        files_written.append(str(code_path))

        # Write the result metadata
        result_meta = {
            "feature": f"{incident_id}-fix-{slug}",
            "success": True,
            "source": "coyote",
            "incident_id": incident_id,
            "root_cause": root_cause,
            "commit_message": commit_message,
            "severity": severity,
            "original_filename": filename,
            "cost": 0.0,
        }
        result_path = incident_dir / f"{slug}_result.json"
        result_path.write_text(
            json.dumps(result_meta, indent=2), encoding="utf-8"
        )
        files_written.append(str(result_path))

    return {
        "generated_dir": str(incident_dir),
        "files_written": files_written,
        "count": len(code_changes),
    }


def _feed_to_prime_contractor(
    generated_dir: Path,
    run_data: Dict[str, Any],
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Feed generated Coyote output to Prime Contractor for integration.

    Args:
        generated_dir: Path to generated files
        run_data: The coyote run data dict
        dry_run: If True, skip actual workflow run

    Returns:
        Workflow result dict
    """
    try:
        from scripts.prime_contractor.workflow import PrimeContractorWorkflow
        from scripts.prime_contractor.feature_queue import FeatureStatus
    except ImportError as e:
        return {
            "success": False,
            "error": f"Prime Contractor not available: {e}",
        }

    incident_id = run_data.get("incident_id", "unknown")

    workflow = PrimeContractorWorkflow(
        allow_dirty=True,
        auto_commit=False,
        dry_run=dry_run,
    )

    # Read result files to create feature specs
    generated_path = Path(generated_dir)
    features_added = []

    for result_file in sorted(generated_path.glob("*_result.json")):
        meta = json.loads(result_file.read_text(encoding="utf-8"))
        feature_id = meta["feature"]
        slug = result_file.stem.replace("_result", "")
        code_file = generated_path / f"{slug}_code.py"

        original_filename = meta.get("original_filename", "")
        target_files = [original_filename] if original_filename else []
        generated_files = [str(code_file)] if code_file.exists() else []

        spec = workflow.queue.add_feature(
            feature_id=feature_id,
            name=f"Coyote fix: {incident_id} - {slug}",
            description=(
                f"Root cause: {meta.get('root_cause', 'N/A')}\n"
                f"Commit: {meta.get('commit_message', 'N/A')}"
            ),
            target_files=target_files,
        )
        # Mark as GENERATED so Prime Contractor skips develop, goes to integrate
        spec.status = FeatureStatus.GENERATED
        spec.generated_files = generated_files
        features_added.append(feature_id)

    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "features_queued": features_added,
            "count": len(features_added),
        }

    result = workflow.run()
    result["features_queued"] = features_added
    return result


def _run_apply_background(
    apply_run_id: str,
    run_id: str,
    dry_run: bool,
    output_base: Optional[Path],
):
    """Background thread for coyote_apply."""
    apply_entry = _apply_runs.get(apply_run_id)
    if apply_entry is None:
        return

    try:
        apply_entry["status"] = "writing"
        apply_entry["started_at"] = datetime.now().isoformat()

        # Step 1: Write output to disk
        write_result = _write_coyote_output(run_id, output_base=output_base)
        apply_entry["write_result"] = write_result
        apply_entry["generated_dir"] = write_result["generated_dir"]

        if write_result["count"] == 0:
            apply_entry["status"] = "completed"
            apply_entry["completed_at"] = datetime.now().isoformat()
            apply_entry["message"] = "No code changes to integrate"
            return

        # Step 2: Feed to Prime Contractor
        apply_entry["status"] = "integrating"
        run_data = _coyote_runs[run_id]
        integration_result = _feed_to_prime_contractor(
            Path(write_result["generated_dir"]),
            run_data,
            dry_run=dry_run,
        )
        apply_entry["integration_result"] = integration_result
        apply_entry["status"] = "completed"
        apply_entry["completed_at"] = datetime.now().isoformat()

        # Update the original coyote run with integration info
        _coyote_runs[run_id]["integration"] = {
            "apply_run_id": apply_run_id,
            "status": "completed",
            "generated_dir": write_result["generated_dir"],
        }

    except Exception as e:
        logger.exception(f"Coyote apply {apply_run_id} failed")
        apply_entry["status"] = "failed"
        apply_entry["error"] = str(e)
        apply_entry["completed_at"] = datetime.now().isoformat()


def _write_coyote_spec(
    run_id: str,
    output_base: Optional[Path] = None,
) -> Path:
    """
    Write Coyote investigation+design as a portable work specification.

    Args:
        run_id: The coyote pipeline run ID
        output_base: Base directory for output (default: generated/coyote)

    Returns:
        Path to the spec JSON file
    """
    run_data = _coyote_runs[run_id]
    incident_id = run_data.get("incident_id", f"unknown-{run_id}")
    severity = run_data.get("severity", "MEDIUM")

    base_dir = output_base or DEFAULT_GENERATED_DIR
    specs_dir = base_dir / "specs"
    specs_dir.mkdir(parents=True, exist_ok=True)

    # Extract investigation and design data from stage_results
    investigation: Dict[str, Any] = {}
    design: Dict[str, Any] = {}

    for sr in run_data.get("stage_results", []):
        if sr.get("stage") == "investigate":
            investigation = {
                "root_cause": sr.get("root_cause"),
                "affected_files": sr.get("affected_files", []),
                "details": sr.get("summary", ""),
            }
        elif sr.get("stage") == "design":
            design = {
                "fix_summary": sr.get("summary", ""),
                "tradeoffs": sr.get("tradeoffs", []),
                "alternatives": sr.get("alternatives", []),
            }

    spec = {
        "schema_version": "1.0.0",
        "type": "incident_fix_specification",
        "incident_id": incident_id,
        "severity": severity,
        "source": "coyote",
        "created_at": datetime.now().isoformat(),
        "investigation": investigation,
        "design": design,
        "conditions": {
            "alert_labels": run_data.get("labels", {}),
            "alert_annotations": run_data.get("annotations", {}),
            "error_message": run_data.get("error_message", ""),
        },
        "observability": {
            "trace_id": run_data.get("trace_id"),
            "log_query": run_data.get("log_query"),
        },
    }

    spec_path = specs_dir / f"{incident_id}_spec.json"
    spec_path.write_text(json.dumps(spec, indent=2), encoding="utf-8")

    return spec_path


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------


@action_registry.register("coyote_apply")
class CoyoteApplyAction(Action):
    """
    Apply Coyote pipeline output via Prime Contractor (fire-and-forget).

    Takes a completed coyote pipeline run, saves its code output to disk,
    then feeds it to Prime Contractor for integration with checkpoints.

    Payload:
        {
            "run_id": "abc12345",
            "dry_run": false
        }
    """

    name = "coyote_apply"
    description = "Apply Coyote pipeline output via Prime Contractor"

    def execute(self, payload: Dict[str, Any], context: Dict[str, Any]) -> ActionResult:
        run_id = payload.get("run_id")
        dry_run = payload.get("dry_run", False)

        if not run_id:
            return ActionResult(
                status=ActionStatus.FAILED,
                action_name=self.name,
                message="Missing run_id",
            )

        if run_id not in _coyote_runs:
            return ActionResult(
                status=ActionStatus.FAILED,
                action_name=self.name,
                message=f"Run not found: {run_id}",
            )

        run_data = _coyote_runs[run_id]

        if run_data.get("status") != "completed":
            return ActionResult(
                status=ActionStatus.FAILED,
                action_name=self.name,
                message=f"Run {run_id} is not completed (status: {run_data.get('status')})",
            )

        # Check for code_changes in stage results
        has_code = any(
            sr.get("code_changes")
            for sr in run_data.get("stage_results", [])
            if sr.get("stage") == "implement"
        )
        if not has_code:
            return ActionResult(
                status=ActionStatus.FAILED,
                action_name=self.name,
                message=f"Run {run_id} has no code changes to apply",
            )

        apply_run_id = str(uuid.uuid4())[:8]

        _apply_runs[apply_run_id] = {
            "apply_run_id": apply_run_id,
            "pipeline_run_id": run_id,
            "dry_run": dry_run,
            "status": "starting",
            "started_at": None,
            "completed_at": None,
            "generated_dir": None,
            "write_result": None,
            "integration_result": None,
            "error": None,
        }

        thread = threading.Thread(
            target=_run_apply_background,
            args=(apply_run_id, run_id, dry_run, None),
            daemon=True,
        )
        thread.start()

        return ActionResult(
            status=ActionStatus.SUCCESS,
            action_name=self.name,
            message=f"Apply started for run {run_id}",
            data={
                "apply_run_id": apply_run_id,
                "pipeline_run_id": run_id,
                "dry_run": dry_run,
                "status_endpoint": f"/coyote/apply/status/{apply_run_id}",
            },
        )

    def validate(self, payload: Dict[str, Any]) -> Optional[str]:
        if not payload.get("run_id"):
            return "Payload must contain 'run_id'"
        return None


@action_registry.register("coyote_apply_status")
class CoyoteApplyStatusAction(Action):
    """
    Get the status of a Coyote apply run.

    Payload:
        {
            "apply_run_id": "abc12345"
        }
    """

    name = "coyote_apply_status"
    description = "Get status of a Coyote apply run"

    def execute(self, payload: Dict[str, Any], context: Dict[str, Any]) -> ActionResult:
        apply_run_id = payload.get("apply_run_id")

        if not apply_run_id:
            return ActionResult(
                status=ActionStatus.FAILED,
                action_name=self.name,
                message="Missing apply_run_id",
            )

        if apply_run_id not in _apply_runs:
            return ActionResult(
                status=ActionStatus.FAILED,
                action_name=self.name,
                message=f"Apply run not found: {apply_run_id}",
            )

        return ActionResult(
            status=ActionStatus.SUCCESS,
            action_name=self.name,
            message=f"Status: {_apply_runs[apply_run_id]['status']}",
            data=_apply_runs[apply_run_id],
        )


@action_registry.register("coyote_spec")
class CoyoteSpecAction(Action):
    """
    Generate a work specification from Coyote investigation+design output.

    Creates a portable spec document that any Beaver workflow can consume.

    Payload:
        {
            "run_id": "abc12345"
        }
    """

    name = "coyote_spec"
    description = "Generate work specification from Coyote investigation+design"

    def execute(self, payload: Dict[str, Any], context: Dict[str, Any]) -> ActionResult:
        run_id = payload.get("run_id")

        if not run_id:
            return ActionResult(
                status=ActionStatus.FAILED,
                action_name=self.name,
                message="Missing run_id",
            )

        if run_id not in _coyote_runs:
            return ActionResult(
                status=ActionStatus.FAILED,
                action_name=self.name,
                message=f"Run not found: {run_id}",
            )

        run_data = _coyote_runs[run_id]

        # Verify investigation stage exists
        has_investigation = any(
            sr.get("stage") == "investigate"
            for sr in run_data.get("stage_results", [])
        )
        if not has_investigation:
            return ActionResult(
                status=ActionStatus.FAILED,
                action_name=self.name,
                message=f"Run {run_id} has no investigation results",
            )

        try:
            spec_path = _write_coyote_spec(run_id)
            return ActionResult(
                status=ActionStatus.SUCCESS,
                action_name=self.name,
                message=f"Spec written to {spec_path}",
                data={
                    "spec_file": str(spec_path),
                    "incident_id": run_data.get("incident_id"),
                    "run_id": run_id,
                },
            )
        except Exception as e:
            return ActionResult(
                status=ActionStatus.FAILED,
                action_name=self.name,
                message=f"Failed to write spec: {e}",
            )

    def validate(self, payload: Dict[str, Any]) -> Optional[str]:
        if not payload.get("run_id"):
            return "Payload must contain 'run_id'"
        return None
