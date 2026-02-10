"""
Tests for Coyote investigation actions.

Covers:
- CoyoteInvestigateAction: fire-and-forget investigation, returns run_id
- CoyoteFullPipelineAction: fire-and-forget full pipeline, returns run_id
- CoyoteStatusAction: status for known/unknown runs, missing run_id
- Validation: requires at least one error message field
- Severity mapping: critical→CRITICAL, high→HIGH, warning→MEDIUM, default→MEDIUM
- Graceful ImportError when contextcore-coyote is not installed
"""

import time

import pytest

from contextcore_rabbit.action import ActionResult, ActionStatus, action_registry
from contextcore_rabbit.actions.coyote_investigate import (
    CoyoteInvestigateAction,
    CoyoteFullPipelineAction,
    CoyoteStatusAction,
    _coyote_runs,
    _extract_error_message,
    _map_severity,
)


def _wait_for_threads():
    """Give background threads a moment to finish or fail."""
    import threading
    time.sleep(0.15)
    for t in threading.enumerate():
        if t.name != "MainThread" and t.is_alive():
            t.join(timeout=0.3)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

class TestRegistration:
    def test_coyote_investigate_registered(self):
        action = action_registry.get("coyote_investigate")
        assert action is not None

    def test_coyote_pipeline_registered(self):
        action = action_registry.get("coyote_pipeline")
        assert action is not None

    def test_coyote_status_registered(self):
        action = action_registry.get("coyote_status")
        assert action is not None


# ---------------------------------------------------------------------------
# Error message extraction
# ---------------------------------------------------------------------------

class TestExtractErrorMessage:
    def test_from_message_field(self):
        assert _extract_error_message({"message": "NPE"}) == "NPE"

    def test_from_annotations_description(self):
        payload = {"annotations": {"description": "Disk full"}}
        assert _extract_error_message(payload) == "Disk full"

    def test_from_annotations_summary(self):
        payload = {"annotations": {"summary": "OOM"}}
        assert _extract_error_message(payload) == "OOM"

    def test_from_name_field(self):
        assert _extract_error_message({"name": "HighErrorRate"}) == "HighErrorRate"

    def test_message_takes_priority(self):
        payload = {"message": "msg", "name": "nm", "annotations": {"description": "desc"}}
        assert _extract_error_message(payload) == "msg"

    def test_returns_none_when_empty(self):
        assert _extract_error_message({}) is None
        assert _extract_error_message({"labels": {"foo": "bar"}}) is None


# ---------------------------------------------------------------------------
# Severity mapping
# ---------------------------------------------------------------------------

class TestSeverityMapping:
    def test_critical(self):
        assert _map_severity({"severity": "critical"}) == "CRITICAL"

    def test_high(self):
        assert _map_severity({"severity": "high"}) == "HIGH"

    def test_warning(self):
        assert _map_severity({"severity": "warning"}) == "MEDIUM"

    def test_medium(self):
        assert _map_severity({"severity": "medium"}) == "MEDIUM"

    def test_low(self):
        assert _map_severity({"severity": "low"}) == "LOW"

    def test_info(self):
        assert _map_severity({"severity": "info"}) == "INFO"

    def test_default_is_medium(self):
        assert _map_severity({}) == "MEDIUM"
        assert _map_severity({"severity": "unknown"}) == "MEDIUM"

    def test_case_insensitive(self):
        assert _map_severity({"severity": "CRITICAL"}) == "CRITICAL"
        assert _map_severity({"severity": "High"}) == "HIGH"

    def test_severity_from_labels(self):
        payload = {"labels": {"severity": "critical"}}
        assert _map_severity(payload) == "CRITICAL"


# ---------------------------------------------------------------------------
# CoyoteInvestigateAction
# ---------------------------------------------------------------------------

class TestCoyoteInvestigateAction:
    @pytest.fixture(autouse=True)
    def clear_runs(self):
        _coyote_runs.clear()
        yield
        _wait_for_threads()
        _coyote_runs.clear()

    def test_execute_returns_success_with_run_id(self):
        action = CoyoteInvestigateAction()
        result = action.execute(
            {"message": "NPE in UserService", "severity": "high"},
            {},
        )
        assert result.status == ActionStatus.SUCCESS
        assert "run_id" in result.data
        assert result.data["mode"] == "investigation_only"
        assert result.data["severity"] == "HIGH"

    def test_execute_creates_tracking_entry(self):
        action = CoyoteInvestigateAction()
        result = action.execute({"message": "Error"}, {})
        run_id = result.data["run_id"]

        assert run_id in _coyote_runs
        entry = _coyote_runs[run_id]
        assert entry["mode"] == "investigation_only"
        assert entry["error_message"] == "Error"
        assert entry["status"] in ("starting", "running", "completed", "failed")

    def test_execute_fails_without_error_message(self):
        action = CoyoteInvestigateAction()
        result = action.execute({"labels": {"service": "api"}}, {})
        assert result.status == ActionStatus.FAILED
        assert "message" in result.message.lower() or "error" in result.message.lower()

    def test_execute_with_annotations_description(self):
        action = CoyoteInvestigateAction()
        result = action.execute(
            {"annotations": {"description": "Disk full on /data"}},
            {},
        )
        assert result.status == ActionStatus.SUCCESS

    def test_execute_with_name_only(self):
        action = CoyoteInvestigateAction()
        result = action.execute({"name": "HighErrorRate"}, {})
        assert result.status == ActionStatus.SUCCESS

    def test_status_endpoint_in_response(self):
        action = CoyoteInvestigateAction()
        result = action.execute({"message": "Error"}, {})
        run_id = result.data["run_id"]
        assert result.data["status_endpoint"] == f"/coyote/status/{run_id}"

    def test_validate_returns_none_for_valid_payload(self):
        action = CoyoteInvestigateAction()
        assert action.validate({"message": "Error"}) is None
        assert action.validate({"name": "Alert"}) is None
        assert action.validate({"annotations": {"description": "X"}}) is None

    def test_validate_returns_error_for_empty_payload(self):
        action = CoyoteInvestigateAction()
        error = action.validate({})
        assert error is not None
        assert "message" in error.lower() or "name" in error.lower()


# ---------------------------------------------------------------------------
# CoyoteFullPipelineAction
# ---------------------------------------------------------------------------

class TestCoyoteFullPipelineAction:
    @pytest.fixture(autouse=True)
    def clear_runs(self):
        _coyote_runs.clear()
        yield
        _wait_for_threads()
        _coyote_runs.clear()

    def test_execute_returns_success_with_run_id(self):
        action = CoyoteFullPipelineAction()
        result = action.execute(
            {"message": "Payment service timeout", "severity": "critical"},
            {},
        )
        assert result.status == ActionStatus.SUCCESS
        assert "run_id" in result.data
        assert result.data["mode"] == "full"
        assert result.data["severity"] == "CRITICAL"

    def test_tracking_entry_has_full_mode(self):
        action = CoyoteFullPipelineAction()
        result = action.execute({"message": "Error"}, {})
        run_id = result.data["run_id"]

        assert _coyote_runs[run_id]["mode"] == "full"

    def test_execute_fails_without_error_message(self):
        action = CoyoteFullPipelineAction()
        result = action.execute({}, {})
        assert result.status == ActionStatus.FAILED

    def test_validate_returns_error_for_empty_payload(self):
        action = CoyoteFullPipelineAction()
        error = action.validate({})
        assert error is not None


# ---------------------------------------------------------------------------
# CoyoteStatusAction
# ---------------------------------------------------------------------------

class TestCoyoteStatusAction:
    @pytest.fixture(autouse=True)
    def clear_runs(self):
        _coyote_runs.clear()
        yield
        _coyote_runs.clear()

    def test_returns_status_for_known_run(self):
        _coyote_runs["run-abc"] = {
            "run_id": "run-abc",
            "mode": "investigation_only",
            "error_message": "NPE",
            "severity": "HIGH",
            "status": "running",
            "started_at": "2026-02-09T10:00:00",
            "completed_at": None,
            "incident_id": "INC-123",
            "stages_completed": 1,
            "stage_results": [
                {"stage": "investigate", "status": "completed", "summary": "Root cause found"},
            ],
            "error": None,
        }

        action = CoyoteStatusAction()
        result = action.execute({"run_id": "run-abc"}, {})

        assert result.status == ActionStatus.SUCCESS
        assert result.data["status"] == "running"
        assert result.data["mode"] == "investigation_only"
        assert result.data["stages_completed"] == 1

    def test_returns_failed_for_unknown_run(self):
        action = CoyoteStatusAction()
        result = action.execute({"run_id": "nonexistent"}, {})

        assert result.status == ActionStatus.FAILED
        assert "not found" in result.message.lower()

    def test_returns_failed_when_run_id_missing(self):
        action = CoyoteStatusAction()
        result = action.execute({}, {})

        assert result.status == ActionStatus.FAILED
        assert "missing" in result.message.lower()


# ---------------------------------------------------------------------------
# Graceful ImportError handling
# ---------------------------------------------------------------------------

class TestGracefulImportError:
    @pytest.fixture(autouse=True)
    def clear_runs(self):
        _coyote_runs.clear()
        yield
        _wait_for_threads()
        _coyote_runs.clear()

    def test_investigate_handles_missing_coyote(self, monkeypatch):
        """When contextcore-coyote is not installed, background thread
        sets status to failed with a clear message."""
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if "contextcore_coyote" in name:
                raise ImportError("mocked: contextcore-coyote not installed")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        action = CoyoteInvestigateAction()
        result = action.execute({"message": "Error"}, {})

        # Action itself returns SUCCESS (fire-and-forget)
        assert result.status == ActionStatus.SUCCESS
        run_id = result.data["run_id"]

        # Wait for background thread
        _wait_for_threads()

        # Background thread should have marked it as failed
        entry = _coyote_runs[run_id]
        assert entry["status"] == "failed"
        assert "not available" in entry["error"].lower() or "not installed" in entry["error"].lower()

    def test_full_pipeline_handles_missing_coyote(self, monkeypatch):
        """Same test for full pipeline action."""
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if "contextcore_coyote" in name:
                raise ImportError("mocked: contextcore-coyote not installed")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        action = CoyoteFullPipelineAction()
        result = action.execute({"message": "Error"}, {})

        assert result.status == ActionStatus.SUCCESS
        run_id = result.data["run_id"]

        _wait_for_threads()

        entry = _coyote_runs[run_id]
        assert entry["status"] == "failed"
        assert "not available" in entry["error"].lower() or "not installed" in entry["error"].lower()
