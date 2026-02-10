"""
Tests for Coyote Bridge actions.

Covers:
- CoyoteApplyAction: validates run_id, status, code_changes; fire-and-forget apply
- CoyoteApplyStatusAction: status for known/unknown apply runs
- CoyoteSpecAction: validates run_id, investigation stage; writes spec JSON
- _write_coyote_output(): file structure correctness
- _write_coyote_spec(): JSON schema correctness
"""

import json
import time
import threading

import pytest

from contextcore_rabbit.action import ActionResult, ActionStatus, action_registry
from contextcore_rabbit.actions.coyote_investigate import _coyote_runs
from contextcore_rabbit.actions.coyote_bridge import (
    CoyoteApplyAction,
    CoyoteApplyStatusAction,
    CoyoteSpecAction,
    _apply_runs,
    _write_coyote_output,
    _write_coyote_spec,
    _slugify,
)


def _wait_for_threads():
    """Give background threads a moment to finish or fail."""
    time.sleep(0.15)
    for t in threading.enumerate():
        if t.name != "MainThread" and t.is_alive():
            t.join(timeout=0.3)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

class TestRegistration:
    def test_coyote_apply_registered(self):
        action = action_registry.get("coyote_apply")
        assert action is not None

    def test_coyote_apply_status_registered(self):
        action = action_registry.get("coyote_apply_status")
        assert action is not None

    def test_coyote_spec_registered(self):
        action = action_registry.get("coyote_spec")
        assert action is not None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class TestSlugify:
    def test_simple_filename(self):
        assert _slugify("auth.py") == "auth"

    def test_path_with_directories(self):
        assert _slugify("src/auth/handler.py") == "handler"

    def test_special_characters(self):
        assert _slugify("my file (2).py") == "my_file__2_"


# ---------------------------------------------------------------------------
# _write_coyote_output
# ---------------------------------------------------------------------------

class TestWriteCoyoteOutput:
    @pytest.fixture(autouse=True)
    def clear_runs(self):
        _coyote_runs.clear()
        yield
        _coyote_runs.clear()

    def test_writes_code_and_result_files(self, tmp_path):
        _coyote_runs["run-1"] = {
            "run_id": "run-1",
            "incident_id": "INC-20260209-001",
            "severity": "HIGH",
            "stage_results": [
                {
                    "stage": "investigate",
                    "status": "completed",
                    "summary": "Null ref in handler",
                    "root_cause": "Missing null check in UserService.get()",
                },
                {
                    "stage": "implement",
                    "status": "completed",
                    "summary": "Fixed null check",
                    "code_changes": {
                        "src/user_service.py": "def get(self):\n    if self.user is None:\n        return None\n    return self.user",
                    },
                    "commit_message": "fix: add null check in UserService.get()",
                },
            ],
        }

        result = _write_coyote_output("run-1", output_base=tmp_path)

        assert result["count"] == 1
        assert len(result["files_written"]) == 2

        # Check code file
        incident_dir = tmp_path / "INC-20260209-001"
        code_file = incident_dir / "user_service_code.py"
        assert code_file.exists()
        assert "if self.user is None" in code_file.read_text()

        # Check result file
        result_file = incident_dir / "user_service_result.json"
        assert result_file.exists()
        meta = json.loads(result_file.read_text())
        assert meta["source"] == "coyote"
        assert meta["incident_id"] == "INC-20260209-001"
        assert meta["root_cause"] == "Missing null check in UserService.get()"
        assert meta["commit_message"] == "fix: add null check in UserService.get()"
        assert meta["severity"] == "HIGH"

    def test_writes_multiple_files(self, tmp_path):
        _coyote_runs["run-2"] = {
            "run_id": "run-2",
            "incident_id": "INC-002",
            "severity": "CRITICAL",
            "stage_results": [
                {
                    "stage": "implement",
                    "status": "completed",
                    "summary": "Two files",
                    "code_changes": {
                        "handler.py": "# fixed handler",
                        "model.py": "# fixed model",
                    },
                    "commit_message": "fix: handler and model",
                },
            ],
        }

        result = _write_coyote_output("run-2", output_base=tmp_path)
        assert result["count"] == 2
        assert len(result["files_written"]) == 4  # 2 code + 2 result

    def test_empty_code_changes(self, tmp_path):
        _coyote_runs["run-3"] = {
            "run_id": "run-3",
            "incident_id": "INC-003",
            "severity": "LOW",
            "stage_results": [
                {
                    "stage": "implement",
                    "status": "completed",
                    "summary": "No changes needed",
                    "code_changes": {},
                },
            ],
        }

        result = _write_coyote_output("run-3", output_base=tmp_path)
        assert result["count"] == 0
        assert result["files_written"] == []


# ---------------------------------------------------------------------------
# _write_coyote_spec
# ---------------------------------------------------------------------------

class TestWriteCoyoteSpec:
    @pytest.fixture(autouse=True)
    def clear_runs(self):
        _coyote_runs.clear()
        yield
        _coyote_runs.clear()

    def test_writes_valid_spec_json(self, tmp_path):
        _coyote_runs["run-spec"] = {
            "run_id": "run-spec",
            "incident_id": "INC-SPEC-001",
            "severity": "HIGH",
            "error_message": "NullPointerException",
            "trace_id": "abc123",
            "log_query": '{job="app"} |= "NPE"',
            "stage_results": [
                {
                    "stage": "investigate",
                    "status": "completed",
                    "summary": "NPE in UserService",
                    "root_cause": "Missing null check",
                    "affected_files": ["src/user.py"],
                },
                {
                    "stage": "design",
                    "status": "completed",
                    "summary": "Add guard clause before access",
                    "tradeoffs": ["Slightly more verbose"],
                    "alternatives": ["Optional chaining"],
                },
            ],
        }

        spec_path = _write_coyote_spec("run-spec", output_base=tmp_path)

        assert spec_path.exists()
        assert spec_path.name == "INC-SPEC-001_spec.json"

        spec = json.loads(spec_path.read_text())
        assert spec["schema_version"] == "1.0.0"
        assert spec["type"] == "incident_fix_specification"
        assert spec["incident_id"] == "INC-SPEC-001"
        assert spec["severity"] == "HIGH"
        assert spec["source"] == "coyote"
        assert spec["investigation"]["root_cause"] == "Missing null check"
        assert spec["investigation"]["affected_files"] == ["src/user.py"]
        assert spec["design"]["fix_summary"] == "Add guard clause before access"
        assert spec["design"]["tradeoffs"] == ["Slightly more verbose"]
        assert spec["observability"]["trace_id"] == "abc123"
        assert spec["conditions"]["error_message"] == "NullPointerException"

    def test_spec_with_minimal_data(self, tmp_path):
        _coyote_runs["run-min"] = {
            "run_id": "run-min",
            "incident_id": "INC-MIN",
            "severity": "LOW",
            "stage_results": [
                {
                    "stage": "investigate",
                    "status": "completed",
                    "summary": "Minor issue",
                },
            ],
        }

        spec_path = _write_coyote_spec("run-min", output_base=tmp_path)
        spec = json.loads(spec_path.read_text())

        assert spec["investigation"]["root_cause"] is None
        assert spec["investigation"]["details"] == "Minor issue"
        assert spec["design"] == {}  # No design stage


# ---------------------------------------------------------------------------
# CoyoteApplyAction
# ---------------------------------------------------------------------------

class TestCoyoteApplyAction:
    @pytest.fixture(autouse=True)
    def clear_runs(self):
        _coyote_runs.clear()
        _apply_runs.clear()
        yield
        _wait_for_threads()
        _coyote_runs.clear()
        _apply_runs.clear()

    def _make_completed_run(self, run_id="run-ok"):
        _coyote_runs[run_id] = {
            "run_id": run_id,
            "incident_id": "INC-TEST",
            "severity": "HIGH",
            "status": "completed",
            "error_message": "NPE",
            "stage_results": [
                {
                    "stage": "investigate",
                    "status": "completed",
                    "summary": "Root cause found",
                    "root_cause": "Missing null check",
                },
                {
                    "stage": "implement",
                    "status": "completed",
                    "summary": "Fixed",
                    "code_changes": {"handler.py": "# fixed code"},
                    "commit_message": "fix: null check",
                },
            ],
        }

    def test_returns_failed_if_run_id_missing(self):
        action = CoyoteApplyAction()
        result = action.execute({}, {})
        assert result.status == ActionStatus.FAILED
        assert "missing" in result.message.lower()

    def test_returns_failed_if_run_not_found(self):
        action = CoyoteApplyAction()
        result = action.execute({"run_id": "nonexistent"}, {})
        assert result.status == ActionStatus.FAILED
        assert "not found" in result.message.lower()

    def test_returns_failed_if_run_not_completed(self):
        _coyote_runs["run-running"] = {
            "run_id": "run-running",
            "status": "running",
            "stage_results": [],
        }
        action = CoyoteApplyAction()
        result = action.execute({"run_id": "run-running"}, {})
        assert result.status == ActionStatus.FAILED
        assert "not completed" in result.message.lower()

    def test_returns_failed_if_no_code_changes(self):
        _coyote_runs["run-nocode"] = {
            "run_id": "run-nocode",
            "status": "completed",
            "stage_results": [
                {"stage": "investigate", "status": "completed", "summary": "OK"},
            ],
        }
        action = CoyoteApplyAction()
        result = action.execute({"run_id": "run-nocode"}, {})
        assert result.status == ActionStatus.FAILED
        assert "no code" in result.message.lower()

    def test_returns_success_with_apply_run_id(self):
        self._make_completed_run()
        action = CoyoteApplyAction()
        result = action.execute({"run_id": "run-ok"}, {})
        assert result.status == ActionStatus.SUCCESS
        assert "apply_run_id" in result.data
        assert result.data["pipeline_run_id"] == "run-ok"

    def test_creates_apply_tracking_entry(self):
        self._make_completed_run()
        action = CoyoteApplyAction()
        result = action.execute({"run_id": "run-ok"}, {})
        apply_id = result.data["apply_run_id"]
        assert apply_id in _apply_runs
        entry = _apply_runs[apply_id]
        assert entry["pipeline_run_id"] == "run-ok"
        assert entry["status"] in ("starting", "writing", "integrating", "completed", "failed")

    def test_validate_requires_run_id(self):
        action = CoyoteApplyAction()
        assert action.validate({}) is not None
        assert action.validate({"run_id": "abc"}) is None

    def test_dry_run_flag_passed(self):
        self._make_completed_run()
        action = CoyoteApplyAction()
        result = action.execute({"run_id": "run-ok", "dry_run": True}, {})
        assert result.data["dry_run"] is True


# ---------------------------------------------------------------------------
# CoyoteApplyStatusAction
# ---------------------------------------------------------------------------

class TestCoyoteApplyStatusAction:
    @pytest.fixture(autouse=True)
    def clear_runs(self):
        _apply_runs.clear()
        yield
        _apply_runs.clear()

    def test_returns_status_for_known_apply(self):
        _apply_runs["apply-1"] = {
            "apply_run_id": "apply-1",
            "pipeline_run_id": "run-1",
            "status": "completed",
            "generated_dir": "/tmp/gen",
        }
        action = CoyoteApplyStatusAction()
        result = action.execute({"apply_run_id": "apply-1"}, {})
        assert result.status == ActionStatus.SUCCESS
        assert result.data["status"] == "completed"

    def test_returns_failed_for_unknown_apply(self):
        action = CoyoteApplyStatusAction()
        result = action.execute({"apply_run_id": "nonexistent"}, {})
        assert result.status == ActionStatus.FAILED
        assert "not found" in result.message.lower()

    def test_returns_failed_when_apply_run_id_missing(self):
        action = CoyoteApplyStatusAction()
        result = action.execute({}, {})
        assert result.status == ActionStatus.FAILED
        assert "missing" in result.message.lower()


# ---------------------------------------------------------------------------
# CoyoteSpecAction
# ---------------------------------------------------------------------------

class TestCoyoteSpecAction:
    @pytest.fixture(autouse=True)
    def clear_runs(self):
        _coyote_runs.clear()
        yield
        _coyote_runs.clear()

    def test_returns_failed_if_run_id_missing(self):
        action = CoyoteSpecAction()
        result = action.execute({}, {})
        assert result.status == ActionStatus.FAILED

    def test_returns_failed_if_run_not_found(self):
        action = CoyoteSpecAction()
        result = action.execute({"run_id": "nope"}, {})
        assert result.status == ActionStatus.FAILED
        assert "not found" in result.message.lower()

    def test_returns_failed_if_no_investigation(self):
        _coyote_runs["run-noinv"] = {
            "run_id": "run-noinv",
            "incident_id": "INC-NOINV",
            "severity": "LOW",
            "stage_results": [
                {"stage": "design", "status": "completed", "summary": "design only"},
            ],
        }
        action = CoyoteSpecAction()
        result = action.execute({"run_id": "run-noinv"}, {})
        assert result.status == ActionStatus.FAILED
        assert "investigation" in result.message.lower()

    def test_returns_success_with_spec_path(self, tmp_path, monkeypatch):
        _coyote_runs["run-spec"] = {
            "run_id": "run-spec",
            "incident_id": "INC-SPEC",
            "severity": "HIGH",
            "error_message": "NPE",
            "stage_results": [
                {
                    "stage": "investigate",
                    "status": "completed",
                    "summary": "Found root cause",
                    "root_cause": "Missing null check",
                },
            ],
        }

        # Monkeypatch the default dir so we write to tmp_path
        import contextcore_rabbit.actions.coyote_bridge as bridge_mod
        monkeypatch.setattr(bridge_mod, "DEFAULT_GENERATED_DIR", tmp_path)

        action = CoyoteSpecAction()
        result = action.execute({"run_id": "run-spec"}, {})
        assert result.status == ActionStatus.SUCCESS
        assert "spec_file" in result.data
        assert result.data["incident_id"] == "INC-SPEC"

        # Verify the file was actually written
        spec_path = result.data["spec_file"]
        spec = json.loads(open(spec_path).read())
        assert spec["incident_id"] == "INC-SPEC"

    def test_validate_requires_run_id(self):
        action = CoyoteSpecAction()
        assert action.validate({}) is not None
        assert action.validate({"run_id": "abc"}) is None
