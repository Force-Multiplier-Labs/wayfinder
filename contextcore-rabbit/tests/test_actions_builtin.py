"""
Tests for the built-in Rabbit actions: LogAction, BeaverWorkflow actions.

Covers:
- LogAction: execute returns success, data includes payload keys
- BeaverWorkflowAction: execute starts background thread, returns run_id
- BeaverWorkflowStatusAction: returns status for known/unknown run_ids
- BeaverWorkflowHistoryAction: list, filter by project, limit
- BeaverWorkflowDryRunAction: handles missing Prime Contractor import gracefully
"""

import time

import pytest

from contextcore_rabbit.action import ActionResult, ActionStatus, action_registry
from contextcore_rabbit.actions.log import LogAction
from contextcore_rabbit.actions.beaver_workflow import (
    BeaverWorkflowAction,
    BeaverWorkflowStatusAction,
    BeaverWorkflowHistoryAction,
    BeaverWorkflowDryRunAction,
    _workflow_runs,
)


def _wait_for_threads():
    """Give background workflow threads a moment to finish or fail."""
    import threading
    time.sleep(0.15)
    # Wait for any daemon threads that are running _run_workflow_background
    for t in threading.enumerate():
        if t.name != "MainThread" and t.is_alive():
            t.join(timeout=0.3)


# ---------------------------------------------------------------------------
# LogAction
# ---------------------------------------------------------------------------

class TestLogAction:
    def test_is_registered(self):
        action = action_registry.get("log")
        assert action is not None

    def test_execute_returns_success(self):
        action = LogAction()
        result = action.execute(
            {"alert_name": "Test", "value": 42},
            {"source": "test"},
        )
        assert result.status == ActionStatus.SUCCESS
        assert result.action_name == "log"
        assert "logged" in result.message.lower()

    def test_execute_includes_payload_keys_in_data(self):
        action = LogAction()
        result = action.execute({"a": 1, "b": 2, "c": 3}, {})
        assert set(result.data["payload_keys"]) == {"a", "b", "c"}

    def test_execute_with_empty_payload(self):
        action = LogAction()
        result = action.execute({}, {})
        assert result.status == ActionStatus.SUCCESS
        assert result.data["payload_keys"] == []

    def test_validate_always_returns_none(self):
        action = LogAction()
        assert action.validate({"anything": True}) is None
        assert action.validate({}) is None


# ---------------------------------------------------------------------------
# BeaverWorkflowAction
# ---------------------------------------------------------------------------

class TestBeaverWorkflowAction:
    @pytest.fixture(autouse=True)
    def clear_workflow_runs(self):
        """Clear the global _workflow_runs dict before each test."""
        _workflow_runs.clear()
        yield
        _wait_for_threads()
        _workflow_runs.clear()

    def test_is_registered(self):
        action = action_registry.get("beaver_workflow")
        assert action is not None

    def test_execute_returns_success_with_run_id(self):
        action = BeaverWorkflowAction()
        result = action.execute(
            {"project_id": "my-project", "dry_run": True},
            {},
        )
        assert result.status == ActionStatus.SUCCESS
        assert "run_id" in result.data
        assert result.data["project_id"] == "my-project"
        assert result.data["mode"] == "dry_run"

    def test_execute_defaults_project_to_default(self):
        action = BeaverWorkflowAction()
        result = action.execute({}, {})
        assert result.data["project_id"] == "default"
        assert result.data["mode"] == "execute"

    def test_execute_creates_tracking_entry(self):
        action = BeaverWorkflowAction()
        result = action.execute({"project_id": "proj-a"}, {})
        run_id = result.data["run_id"]

        assert run_id in _workflow_runs
        entry = _workflow_runs[run_id]
        assert entry["project_id"] == "proj-a"
        # The background thread may have already transitioned past "starting"
        assert entry["status"] in ("starting", "running", "completed", "failed")
        assert entry["dry_run"] is False

    def test_execute_dry_run_flag(self):
        action = BeaverWorkflowAction()
        result = action.execute({"dry_run": True}, {})
        run_id = result.data["run_id"]

        assert _workflow_runs[run_id]["dry_run"] is True
        assert result.data["mode"] == "dry_run"

    def test_status_endpoint_in_response(self):
        action = BeaverWorkflowAction()
        result = action.execute({"project_id": "p"}, {})
        run_id = result.data["run_id"]

        assert result.data["status_endpoint"] == f"/workflow/status/{run_id}"

    def test_validate_returns_none(self):
        action = BeaverWorkflowAction()
        assert action.validate({}) is None
        assert action.validate({"project_id": "x"}) is None


# ---------------------------------------------------------------------------
# BeaverWorkflowStatusAction
# ---------------------------------------------------------------------------

class TestBeaverWorkflowStatusAction:
    @pytest.fixture(autouse=True)
    def clear_workflow_runs(self):
        _workflow_runs.clear()
        yield
        _workflow_runs.clear()

    def test_is_registered(self):
        action = action_registry.get("beaver_workflow_status")
        assert action is not None

    def test_returns_status_for_known_run(self):
        _workflow_runs["run-abc"] = {
            "run_id": "run-abc",
            "project_id": "proj-x",
            "status": "running",
            "dry_run": False,
            "started_at": "2026-01-15T10:00:00",
            "completed_at": None,
            "steps_total": 5,
            "steps_completed": 2,
            "error": None,
        }

        action = BeaverWorkflowStatusAction()
        result = action.execute({"run_id": "run-abc"}, {})

        assert result.status == ActionStatus.SUCCESS
        assert result.data["status"] == "running"
        assert result.data["project_id"] == "proj-x"
        assert result.data["steps_total"] == 5
        assert result.data["steps_completed"] == 2

    def test_returns_failed_for_unknown_run(self):
        action = BeaverWorkflowStatusAction()
        result = action.execute({"run_id": "nonexistent"}, {})

        assert result.status == ActionStatus.FAILED
        assert "not found" in result.message.lower()

    def test_returns_failed_when_run_id_missing(self):
        action = BeaverWorkflowStatusAction()
        result = action.execute({}, {})

        assert result.status == ActionStatus.FAILED
        assert "missing" in result.message.lower()


# ---------------------------------------------------------------------------
# BeaverWorkflowHistoryAction
# ---------------------------------------------------------------------------

class TestBeaverWorkflowHistoryAction:
    @pytest.fixture(autouse=True)
    def clear_workflow_runs(self):
        _workflow_runs.clear()
        yield
        _workflow_runs.clear()

    def test_is_registered(self):
        action = action_registry.get("beaver_workflow_history")
        assert action is not None

    def test_returns_empty_when_no_runs(self):
        action = BeaverWorkflowHistoryAction()
        result = action.execute({}, {})

        assert result.status == ActionStatus.SUCCESS
        assert result.data["runs"] == []
        assert result.data["total"] == 0

    def test_returns_all_runs(self):
        _workflow_runs["r1"] = {
            "run_id": "r1", "project_id": "p1",
            "started_at": "2026-01-15T10:00:00",
        }
        _workflow_runs["r2"] = {
            "run_id": "r2", "project_id": "p2",
            "started_at": "2026-01-15T11:00:00",
        }

        action = BeaverWorkflowHistoryAction()
        result = action.execute({}, {})

        assert result.status == ActionStatus.SUCCESS
        assert len(result.data["runs"]) == 2
        assert result.data["total"] == 2

    def test_filters_by_project_id(self):
        _workflow_runs["r1"] = {
            "run_id": "r1", "project_id": "alpha",
            "started_at": "2026-01-15T10:00:00",
        }
        _workflow_runs["r2"] = {
            "run_id": "r2", "project_id": "beta",
            "started_at": "2026-01-15T11:00:00",
        }
        _workflow_runs["r3"] = {
            "run_id": "r3", "project_id": "alpha",
            "started_at": "2026-01-15T12:00:00",
        }

        action = BeaverWorkflowHistoryAction()
        result = action.execute({"project_id": "alpha"}, {})

        assert len(result.data["runs"]) == 2
        for run in result.data["runs"]:
            assert run["project_id"] == "alpha"

    def test_respects_limit(self):
        for i in range(10):
            _workflow_runs[f"r{i}"] = {
                "run_id": f"r{i}", "project_id": "p",
                "started_at": f"2026-01-15T{10 + i}:00:00",
            }

        action = BeaverWorkflowHistoryAction()
        result = action.execute({"limit": 3}, {})

        assert len(result.data["runs"]) == 3
        assert result.data["total"] == 10

    def test_sorts_by_started_at_descending(self):
        _workflow_runs["r_early"] = {
            "run_id": "r_early", "project_id": "p",
            "started_at": "2026-01-15T08:00:00",
        }
        _workflow_runs["r_late"] = {
            "run_id": "r_late", "project_id": "p",
            "started_at": "2026-01-15T20:00:00",
        }
        _workflow_runs["r_mid"] = {
            "run_id": "r_mid", "project_id": "p",
            "started_at": "2026-01-15T14:00:00",
        }

        action = BeaverWorkflowHistoryAction()
        result = action.execute({}, {})

        run_ids = [r["run_id"] for r in result.data["runs"]]
        assert run_ids == ["r_late", "r_mid", "r_early"]


# ---------------------------------------------------------------------------
# BeaverWorkflowDryRunAction
# ---------------------------------------------------------------------------

class TestBeaverWorkflowDryRunAction:
    def test_is_registered(self):
        action = action_registry.get("beaver_workflow_dry_run")
        assert action is not None

    def test_execute_returns_valid_result(self):
        """Dry run returns a well-formed ActionResult regardless of environment.

        In CI or isolated environments PrimeContractorWorkflow is not
        importable, so the action returns FAILED gracefully.  When run from
        the Wayfinder monorepo root, the import succeeds and the action
        returns SUCCESS with step data.  Both outcomes are valid.
        """
        action = BeaverWorkflowDryRunAction()
        result = action.execute({"project_id": "test-proj"}, {})

        assert result.action_name == "beaver_workflow_dry_run"
        assert isinstance(result, ActionResult)
        assert result.status in (ActionStatus.SUCCESS, ActionStatus.FAILED)

        if result.status == ActionStatus.SUCCESS:
            # If it succeeded the data should have expected structure
            assert "steps" in result.data
            assert "total" in result.data
            assert "would_execute" in result.data
            assert "would_skip" in result.data
        else:
            # If it failed, the message should explain why
            assert result.message  # non-empty error message

    def test_execute_with_missing_import(self, monkeypatch):
        """Force an ImportError to verify graceful handling."""
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if "prime_contractor" in name:
                raise ImportError("mocked: Prime Contractor not available")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        action = BeaverWorkflowDryRunAction()
        result = action.execute({"project_id": "test-proj"}, {})

        assert result.status == ActionStatus.FAILED
        assert "not available" in result.message.lower()
