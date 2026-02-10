"""Tests for scripts/dev_repair.py — Dev mode auto-repair module."""

from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

# Load dev_repair.py from scripts/ (not a package, so use importlib)
_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "dev_repair", _SCRIPTS_DIR / "dev_repair.py"
)
assert _spec is not None and _spec.loader is not None
dev_repair = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dev_repair)


# ---------------------------------------------------------------------------
# Lightweight stubs for FeatureSpec / CheckpointResult so tests don't
# depend on the full prime_contractor package.
# ---------------------------------------------------------------------------

class CheckpointStatus(Enum):
    PASSED = "passed"
    FAILED = "failed"


@dataclass
class CheckpointResult:
    status: CheckpointStatus
    checkpoint_name: str
    message: str
    errors: List[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.status == CheckpointStatus.PASSED


class FeatureStatus(Enum):
    PENDING = "pending"
    FAILED = "failed"


@dataclass
class FeatureSpec:
    id: str
    name: str
    description: str = ""
    status: FeatureStatus = FeatureStatus.PENDING
    error_message: Optional[str] = None
    target_files: List[str] = field(default_factory=list)
    generated_files: List[str] = field(default_factory=list)
    integration_attempts: int = 0


# ---------------------------------------------------------------------------
# Fake Coyote objects for mocking
# ---------------------------------------------------------------------------

class FakeStageStatus(Enum):
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class FakeStageResult:
    stage_name: str
    status: FakeStageStatus = FakeStageStatus.COMPLETED
    summary: str = "ok"
    code_changes: Dict[str, str] = field(default_factory=dict)
    root_cause: Optional[str] = None
    error: Optional[str] = None


@dataclass
class FakePipelineResult:
    successful: bool = True
    stage_results: List[FakeStageResult] = field(default_factory=list)

    @property
    def failed_stage(self) -> Optional[FakeStageResult]:
        for sr in self.stage_results:
            if sr.status == FakeStageStatus.FAILED:
                return sr
        return None


@dataclass
class FakeIncident:
    id: str = "INC-20260209120000"
    title: str = "Test incident"
    description: str = "test"
    error_message: Optional[str] = None
    severity: str = "HIGH"
    source: str = "dev_repair"
    labels: Dict[str, str] = field(default_factory=dict)
    affected_files: List[str] = field(default_factory=list)

    @classmethod
    def from_error(cls, error_message, severity=None, source="dev_repair", **kw):
        return cls(
            error_message=error_message,
            severity=str(severity) if severity else "HIGH",
            source=source,
        )


class FakeIncidentSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    INFO = "info"


class FakePipeline:
    def __init__(self, result=None):
        self._result = result or FakePipelineResult(
            successful=True,
            stage_results=[
                FakeStageResult(stage_name="investigate", summary="Root cause found", root_cause="null check"),
                FakeStageResult(stage_name="design", summary="Fix designed"),
                FakeStageResult(stage_name="implement", summary="Code generated"),
                FakeStageResult(stage_name="test", summary="Tests pass"),
                FakeStageResult(stage_name="learn", summary="Lesson captured"),
            ],
        )

    @classmethod
    def full(cls):
        return cls()

    def run(self, incident):
        return self._result


# ---------------------------------------------------------------------------
# Tests: repair_from_error
# ---------------------------------------------------------------------------

class TestRepairFromError:
    """Tests for the repair_from_error function."""

    def _mock_coyote_modules(self):
        """Set up fake coyote modules in sys.modules."""
        models_mod = MagicMock()
        models_mod.Incident = FakeIncident
        models_mod.IncidentSeverity = FakeIncidentSeverity

        pipeline_mod = MagicMock()
        pipeline_mod.Pipeline = FakePipeline

        config_mod = MagicMock()
        config_mod.configure = MagicMock()

        return {
            "contextcore_coyote": MagicMock(),
            "contextcore_coyote.models": models_mod,
            "contextcore_coyote.pipeline": pipeline_mod,
            "contextcore_coyote.config": config_mod,
        }

    def test_repair_from_error_returns_result_dict(self):
        """Verify return shape has expected keys."""
        mocks = self._mock_coyote_modules()
        with patch.dict(sys.modules, mocks):
            # Re-execute the module so imports resolve to our mocks
            _spec.loader.exec_module(dev_repair)
            result = dev_repair.repair_from_error("NullPointerException in UserService")

        assert isinstance(result, dict)
        assert "success" in result
        assert "run_id" in result
        assert "incident_id" in result
        assert "stages" in result
        assert "code_changes_count" in result
        assert result["success"] is True
        assert len(result["stages"]) == 5

    def test_repair_from_error_graceful_without_coyote(self):
        """ImportError returns success=False without crashing."""
        # Ensure contextcore_coyote is not importable
        sentinel = object()
        saved = sys.modules.get("contextcore_coyote", sentinel)
        sys.modules["contextcore_coyote"] = None  # type: ignore[assignment]
        try:
            _spec.loader.exec_module(dev_repair)
            result = dev_repair.repair_from_error("Some error")
        finally:
            if saved is sentinel:
                sys.modules.pop("contextcore_coyote", None)
            else:
                sys.modules["contextcore_coyote"] = saved

        assert result["success"] is False
        assert "not available" in result.get("error", "")
        assert result["run_id"] is None

    def test_repair_from_error_auto_apply_writes_files(self, tmp_path):
        """When auto_apply=True and pipeline produces code_changes, files are written."""
        pipeline_result = FakePipelineResult(
            successful=True,
            stage_results=[
                FakeStageResult(
                    stage_name="investigate",
                    summary="Found root cause",
                    root_cause="Missing null check",
                ),
                FakeStageResult(stage_name="design", summary="Fix designed"),
                FakeStageResult(
                    stage_name="implement",
                    summary="Code generated",
                    code_changes={
                        "src/user_service.py": "def get_profile(user_id):\n    if user_id is None:\n        raise ValueError('user_id required')\n",
                    },
                ),
                FakeStageResult(stage_name="test", summary="Tests pass"),
                FakeStageResult(stage_name="learn", summary="Lesson captured"),
            ],
        )

        class CustomPipeline(FakePipeline):
            def __init__(self):
                self._result = pipeline_result

        mocks = self._mock_coyote_modules()
        mocks["contextcore_coyote.pipeline"].Pipeline = CustomPipeline

        with patch.dict(sys.modules, mocks):
            _spec.loader.exec_module(dev_repair)
            result = dev_repair.repair_from_error(
                "NullPointerException",
                auto_apply=True,
                output_dir=tmp_path / "coyote_out",
            )

        assert result["success"] is True
        assert result["code_changes_count"] == 1
        assert result.get("generated_dir") is not None

        generated = Path(result["generated_dir"])
        assert generated.exists()
        # Should have a .py file and a _result.json file
        py_files = list(generated.glob("*.py"))
        json_files = list(generated.glob("*_result.json"))
        assert len(py_files) == 1
        assert len(json_files) == 1

        # Verify metadata
        meta = json.loads(json_files[0].read_text())
        assert meta["source"] == "coyote"
        assert meta["root_cause"] == "Missing null check"

    def test_repair_from_error_no_apply_by_default(self, tmp_path):
        """No files written when auto_apply=False (default)."""
        mocks = self._mock_coyote_modules()
        with patch.dict(sys.modules, mocks):
            _spec.loader.exec_module(dev_repair)
            result = dev_repair.repair_from_error("Some error")

        assert "generated_dir" not in result

    def test_repair_configures_auto_proceed_and_telemetry(self):
        """Verify Coyote is configured with auto_proceed=True and contextcore_enabled=True."""
        mocks = self._mock_coyote_modules()
        configure_mock = mocks["contextcore_coyote.config"].configure

        with patch.dict(sys.modules, mocks):
            _spec.loader.exec_module(dev_repair)
            dev_repair.repair_from_error("Some error")

        configure_mock.assert_called_once_with(auto_proceed=True, contextcore_enabled=True)


# ---------------------------------------------------------------------------
# Tests: coyote_repair_callback
# ---------------------------------------------------------------------------

class TestCoyoteRepairCallback:
    """Tests for the PrimeContractorWorkflow callback."""

    def test_callback_signature(self):
        """Verify it accepts (FeatureSpec, List[CheckpointResult]) and calls repair_from_error."""
        feature = FeatureSpec(id="FEAT-1", name="Test feature")
        results = [
            CheckpointResult(
                status=CheckpointStatus.PASSED,
                checkpoint_name="Syntax Check",
                message="OK",
            ),
        ]

        captured: List[Dict[str, Any]] = []

        def fake_repair(**kwargs):
            captured.append(kwargs)
            return {"success": False, "run_id": None}

        original = dev_repair.repair_from_error
        dev_repair.repair_from_error = fake_repair
        try:
            ret = dev_repair.coyote_repair_callback(feature, results)
        finally:
            dev_repair.repair_from_error = original

        assert len(captured) == 1
        assert ret is None  # run_id is None from our fake

    def test_callback_builds_context_from_feature_and_checkpoints(self):
        """Verify error message is assembled from feature + failed checkpoints."""
        feature = FeatureSpec(
            id="FEAT-2",
            name="Auth feature",
            error_message="Import failed: auth_module",
            target_files=["src/auth.py"],
            generated_files=["generated/auth.py"],
            integration_attempts=2,
        )
        results = [
            CheckpointResult(
                status=CheckpointStatus.PASSED,
                checkpoint_name="Syntax Check",
                message="OK",
            ),
            CheckpointResult(
                status=CheckpointStatus.FAILED,
                checkpoint_name="Import Check",
                message="2 file(s) have import errors",
                errors=["auth.py: ModuleNotFoundError: No module named 'jwt'"],
            ),
        ]

        captured_calls: List[Dict[str, Any]] = []

        def fake_repair(error_message, severity="HIGH", context=None, auto_apply=False):
            captured_calls.append({
                "error_message": error_message,
                "severity": severity,
                "context": context,
                "auto_apply": auto_apply,
            })
            return {"success": False, "run_id": None, "error": "test"}

        original = dev_repair.repair_from_error
        dev_repair.repair_from_error = fake_repair
        try:
            dev_repair.coyote_repair_callback(feature, results)
        finally:
            dev_repair.repair_from_error = original

        assert len(captured_calls) == 1
        call = captured_calls[0]

        # Error message should include feature.error_message and failed checkpoint details
        assert "Import failed: auth_module" in call["error_message"]
        assert "Import Check" in call["error_message"]
        assert "ModuleNotFoundError" in call["error_message"]

        # Context should include feature metadata
        assert call["context"]["feature_id"] == "FEAT-2"
        assert call["context"]["feature_name"] == "Auth feature"
        assert "src/auth.py" in call["context"]["target_files"]
        assert call["context"]["integration_attempts"] == 2


# ---------------------------------------------------------------------------
# Tests: CLI (contextcore dev repair)
# ---------------------------------------------------------------------------

class TestCLIDevRepair:
    """Tests for the CLI dev repair command."""

    def test_dev_repair_with_error_flag(self):
        """CLI invocation with --error produces output."""
        from click.testing import CliRunner
        from contextcore.cli.dev import dev

        runner = CliRunner()

        # Mock repair_from_error at the module level inside the CLI
        with patch("importlib.util.spec_from_file_location") as mock_spec:
            fake_mod = MagicMock()
            fake_mod.repair_from_error.return_value = {
                "success": True,
                "run_id": "INC-TEST",
                "incident_id": "INC-TEST",
                "stages": [
                    {"name": "investigate", "status": "completed", "summary": "Root cause found"},
                ],
                "code_changes_count": 0,
            }

            mock_loader = MagicMock()
            mock_loader.exec_module = MagicMock(side_effect=lambda m: None)
            mock_spec_obj = MagicMock()
            mock_spec_obj.loader = mock_loader
            mock_spec.return_value = mock_spec_obj

            with patch("importlib.util.module_from_spec", return_value=fake_mod):
                result = runner.invoke(dev, [
                    "repair", "--error", "NullPointerException", "--severity", "HIGH",
                ])

        assert result.exit_code == 0
        assert "Coyote Repair" in result.output

    def test_dev_repair_with_log_file(self, tmp_path):
        """CLI invocation with --log-file reads error from file."""
        from click.testing import CliRunner
        from contextcore.cli.dev import dev

        log_file = tmp_path / "error.log"
        log_file.write_text("java.lang.NullPointerException at com.example.Service")

        runner = CliRunner()

        with patch("importlib.util.spec_from_file_location") as mock_spec:
            fake_mod = MagicMock()
            fake_mod.repair_from_error.return_value = {
                "success": True,
                "run_id": "INC-LOG",
                "incident_id": "INC-LOG",
                "stages": [],
                "code_changes_count": 0,
            }
            mock_loader = MagicMock()
            mock_loader.exec_module = MagicMock(side_effect=lambda m: None)
            mock_spec_obj = MagicMock()
            mock_spec_obj.loader = mock_loader
            mock_spec.return_value = mock_spec_obj

            with patch("importlib.util.module_from_spec", return_value=fake_mod):
                result = runner.invoke(dev, [
                    "repair", "--log-file", str(log_file),
                ])

        assert result.exit_code == 0

    def test_dev_repair_missing_error(self):
        """Error when neither --error nor --log-file provided."""
        from click.testing import CliRunner
        from contextcore.cli.dev import dev

        runner = CliRunner()
        result = runner.invoke(dev, ["repair"])

        assert result.exit_code != 0
        assert "provide --error or --log-file" in result.output

    def test_dev_repair_json_output(self):
        """Verify --output json produces valid JSON."""
        from click.testing import CliRunner
        from contextcore.cli.dev import dev

        runner = CliRunner()

        with patch("importlib.util.spec_from_file_location") as mock_spec:
            fake_mod = MagicMock()
            fake_mod.repair_from_error.return_value = {
                "success": True,
                "run_id": "INC-JSON",
                "incident_id": "INC-JSON",
                "stages": [
                    {"name": "investigate", "status": "completed", "summary": "found it"},
                ],
                "code_changes_count": 1,
            }
            mock_loader = MagicMock()
            mock_loader.exec_module = MagicMock(side_effect=lambda m: None)
            mock_spec_obj = MagicMock()
            mock_spec_obj.loader = mock_loader
            mock_spec.return_value = mock_spec_obj

            with patch("importlib.util.module_from_spec", return_value=fake_mod):
                result = runner.invoke(dev, [
                    "repair", "--error", "TestError", "--output", "json",
                ])

        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert parsed["success"] is True
        assert parsed["run_id"] == "INC-JSON"
