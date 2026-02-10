"""
Coyote Investigation Actions - Triggers incident resolution pipelines.

Three actions:
- coyote_investigate: Fire-and-forget investigation (background thread)
- coyote_pipeline: Fire-and-forget full 5-stage pipeline (background thread)
- coyote_status: Synchronous status query for a running/completed pipeline
"""

import logging
import threading
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from contextcore_rabbit.action import Action, ActionResult, ActionStatus, action_registry

logger = logging.getLogger(__name__)

# Track running coyote pipelines for status queries
_coyote_runs: Dict[str, Dict[str, Any]] = {}

# Map alert severity labels to IncidentSeverity enum values
_SEVERITY_MAP = {
    "critical": "CRITICAL",
    "high": "HIGH",
    "warning": "MEDIUM",
    "medium": "MEDIUM",
    "low": "LOW",
    "info": "INFO",
}


def _extract_error_message(payload: Dict[str, Any]) -> Optional[str]:
    """Extract error message from alert payload, trying multiple fields."""
    # Direct message field
    if payload.get("message"):
        return payload["message"]

    # Grafana-style annotations
    annotations = payload.get("annotations", {})
    if annotations.get("description"):
        return annotations["description"]
    if annotations.get("summary"):
        return annotations["summary"]

    # Alert name as fallback
    if payload.get("name"):
        return payload["name"]

    return None


def _map_severity(payload: Dict[str, Any]) -> str:
    """Map alert severity label to IncidentSeverity enum name."""
    severity_str = payload.get("severity", "").lower()
    # Also check labels dict
    if not severity_str:
        labels = payload.get("labels", {})
        severity_str = labels.get("severity", "").lower()
    return _SEVERITY_MAP.get(severity_str, "MEDIUM")


def _run_coyote_background(run_id: str, error_message: str, severity_name: str,
                           payload: Dict[str, Any], mode: str):
    """Run coyote pipeline in a background thread."""
    # Grab a reference to avoid KeyError if dict is cleared during test cleanup
    run_entry = _coyote_runs.get(run_id)
    if run_entry is None:
        return

    try:
        run_entry["status"] = "running"
        run_entry["started_at"] = datetime.now().isoformat()

        # Lazy import — graceful if coyote not installed
        try:
            from contextcore_coyote.models import Incident, IncidentSeverity
            from contextcore_coyote.pipeline import Pipeline
            from contextcore_coyote.config import configure
        except ImportError as e:
            logger.error(f"contextcore-coyote not installed: {e}")
            run_entry["status"] = "failed"
            run_entry["error"] = (
                f"contextcore-coyote package not available: {e}"
            )
            run_entry["completed_at"] = datetime.now().isoformat()
            return

        # Configure for unattended execution
        configure(auto_proceed=True)

        # Map severity string to enum
        severity = IncidentSeverity[severity_name]

        # Create incident from alert data
        incident = Incident.from_error(
            error_message=error_message,
            severity=severity,
            source="alert",
        )

        # Enrich incident with alert context
        labels = payload.get("labels", {})
        annotations = payload.get("annotations", {})
        if labels or annotations:
            incident.description += (
                f"\n\nAlert labels: {labels}"
                f"\nAlert annotations: {annotations}"
            )

        run_entry["incident_id"] = incident.id

        # Select pipeline mode
        if mode == "investigation_only":
            pipeline = Pipeline.investigation_only()
        else:
            pipeline = Pipeline.full()

        # Run pipeline
        result = pipeline.run(incident)

        # Update tracking
        run_entry["status"] = "completed" if result.successful else "failed"
        run_entry["completed_at"] = datetime.now().isoformat()
        run_entry["pipeline_status"] = result.status
        run_entry["stages_completed"] = len(result.stage_results)
        run_entry["duration_seconds"] = result.duration_seconds
        run_entry["summary"] = result.summary()

        # Preserve O11y cross-references for Grafana drill-down
        run_entry["trace_id"] = incident.trace_id
        run_entry["span_id"] = incident.span_id
        run_entry["log_query"] = incident.log_query

        # Capture stage summaries and implementation artifacts
        run_entry["stage_results"] = []
        for sr in result.stage_results:
            stage_data = {
                "stage": sr.stage_name,
                "status": sr.status.value,
                "summary": sr.summary,
                "root_cause": sr.root_cause,
                "duration_seconds": sr.duration_seconds,
            }
            # Preserve code draft from Implementer stage
            if sr.stage_name == "implement" and hasattr(sr, "code_changes"):
                stage_data["code_changes"] = sr.code_changes
                stage_data["commit_message"] = sr.output.get("commit_message")
            run_entry["stage_results"].append(stage_data)

        if result.failed_stage:
            run_entry["error"] = (
                f"Stage '{result.failed_stage.stage_name}' failed: "
                f"{result.failed_stage.summary}"
            )

    except Exception as e:
        logger.exception(f"Coyote run {run_id} failed")
        run_entry["status"] = "failed"
        run_entry["error"] = str(e)
        run_entry["completed_at"] = datetime.now().isoformat()


@action_registry.register("coyote_investigate")
class CoyoteInvestigateAction(Action):
    """
    Trigger Coyote investigation pipeline (fire-and-forget).

    Runs investigation only — root cause analysis without remediation.

    Payload:
        {
            "message": "NullPointerException in UserService",
            "severity": "high",
            "labels": {"service": "user-service"},
            "annotations": {"description": "..."}
        }
    """

    name = "coyote_investigate"
    description = "Trigger Coyote investigation pipeline (fire-and-forget)"

    def execute(self, payload: Dict[str, Any], context: Dict[str, Any]) -> ActionResult:
        error_message = _extract_error_message(payload)
        if not error_message:
            return ActionResult(
                status=ActionStatus.FAILED,
                action_name=self.name,
                message="No error message found in payload (need 'message', 'annotations.description', or 'name')",
            )

        severity_name = _map_severity(payload)
        run_id = str(uuid.uuid4())[:8]

        _coyote_runs[run_id] = {
            "run_id": run_id,
            "mode": "investigation_only",
            "error_message": error_message,
            "severity": severity_name,
            "status": "starting",
            "started_at": None,
            "completed_at": None,
            "incident_id": None,
            "stages_completed": 0,
            "stage_results": [],
            "error": None,
        }

        thread = threading.Thread(
            target=_run_coyote_background,
            args=(run_id, error_message, severity_name, payload, "investigation_only"),
            daemon=True,
        )
        thread.start()

        return ActionResult(
            status=ActionStatus.SUCCESS,
            action_name=self.name,
            message=f"Investigation started (severity={severity_name})",
            data={
                "run_id": run_id,
                "mode": "investigation_only",
                "severity": severity_name,
                "status_endpoint": f"/coyote/status/{run_id}",
            },
        )

    def validate(self, payload: Dict[str, Any]) -> Optional[str]:
        if not _extract_error_message(payload):
            return "Payload must contain 'message', 'annotations.description', or 'name'"
        return None


@action_registry.register("coyote_pipeline")
class CoyoteFullPipelineAction(Action):
    """
    Trigger full Coyote 5-stage pipeline (fire-and-forget).

    Runs all stages: investigate, design, implement, test, learn.

    Payload: same as coyote_investigate.
    """

    name = "coyote_pipeline"
    description = "Trigger full Coyote incident resolution pipeline (fire-and-forget)"

    def execute(self, payload: Dict[str, Any], context: Dict[str, Any]) -> ActionResult:
        error_message = _extract_error_message(payload)
        if not error_message:
            return ActionResult(
                status=ActionStatus.FAILED,
                action_name=self.name,
                message="No error message found in payload (need 'message', 'annotations.description', or 'name')",
            )

        severity_name = _map_severity(payload)
        run_id = str(uuid.uuid4())[:8]

        _coyote_runs[run_id] = {
            "run_id": run_id,
            "mode": "full",
            "error_message": error_message,
            "severity": severity_name,
            "status": "starting",
            "started_at": None,
            "completed_at": None,
            "incident_id": None,
            "stages_completed": 0,
            "stage_results": [],
            "error": None,
        }

        thread = threading.Thread(
            target=_run_coyote_background,
            args=(run_id, error_message, severity_name, payload, "full"),
            daemon=True,
        )
        thread.start()

        return ActionResult(
            status=ActionStatus.SUCCESS,
            action_name=self.name,
            message=f"Full pipeline started (severity={severity_name})",
            data={
                "run_id": run_id,
                "mode": "full",
                "severity": severity_name,
                "status_endpoint": f"/coyote/status/{run_id}",
            },
        )

    def validate(self, payload: Dict[str, Any]) -> Optional[str]:
        if not _extract_error_message(payload):
            return "Payload must contain 'message', 'annotations.description', or 'name'"
        return None


@action_registry.register("coyote_status")
class CoyoteStatusAction(Action):
    """
    Get the status of a Coyote pipeline run.

    Payload:
        {
            "run_id": "abc12345"
        }
    """

    name = "coyote_status"
    description = "Get status of a Coyote pipeline run"

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

        return ActionResult(
            status=ActionStatus.SUCCESS,
            action_name=self.name,
            message=f"Status: {run_data['status']}",
            data=run_data,
        )
