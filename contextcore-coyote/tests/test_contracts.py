"""
Tests for typed stage contracts, gates, and legacy adapters.

Validates Defense in Depth Principle 1 (boundary validation) and
Principle 2 (typed outputs prevent arbitrary field access).
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from contextcore_coyote.models import StageResult, StageStatus
from contextcore_coyote.pipeline.contracts import (
    ContractViolation,
    DesignOutput,
    GateResult,
    ImplementationOutput,
    InvestigationOutput,
    LessonOutput,
    StageOutput,
    ValidationOutput,
    ViolationSeverity,
    adapt_legacy_result,
    fingerprint,
    STAGE_OUTPUT_REGISTRY,
)


# ---------------------------------------------------------------------------
# fingerprint()
# ---------------------------------------------------------------------------


class TestFingerprint:
    """Tests for context fingerprinting (Principle 3)."""

    def test_deterministic(self):
        """Same input always produces same fingerprint."""
        assert fingerprint("hello") == fingerprint("hello")

    def test_different_inputs_differ(self):
        """Different inputs produce different fingerprints."""
        assert fingerprint("hello") != fingerprint("world")

    def test_returns_16_chars(self):
        """Fingerprint is truncated to 16 hex chars."""
        fp = fingerprint("test data")
        assert len(fp) == 16
        assert all(c in "0123456789abcdef" for c in fp)


# ---------------------------------------------------------------------------
# StageOutput (base model)
# ---------------------------------------------------------------------------


class TestStageOutput:
    """Tests for the base StageOutput model."""

    def test_create_minimal(self):
        """Can create with required fields only."""
        output = StageOutput(
            stage_name="test",
            status=StageStatus.COMPLETED,
            summary="Done",
        )
        assert output.stage_name == "test"
        assert output.succeeded is True
        assert output.context_fingerprint is None

    def test_succeeded_property(self):
        """succeeded is True only for COMPLETED status."""
        completed = StageOutput(
            stage_name="test", status=StageStatus.COMPLETED, summary="Done"
        )
        failed = StageOutput(
            stage_name="test", status=StageStatus.FAILED, summary="Oops"
        )
        assert completed.succeeded is True
        assert failed.succeeded is False

    def test_duration_seconds(self):
        """Duration calculated from started_at and completed_at."""
        start = datetime(2026, 2, 9, 12, 0, 0)
        output = StageOutput(
            stage_name="test",
            status=StageStatus.COMPLETED,
            summary="Done",
            started_at=start,
            completed_at=start + timedelta(seconds=42),
        )
        assert output.duration_seconds == 42.0

    def test_duration_none_when_incomplete(self):
        """Duration is None when completed_at is not set."""
        output = StageOutput(
            stage_name="test", status=StageStatus.RUNNING, summary="Working"
        )
        assert output.duration_seconds is None

    def test_to_legacy(self):
        """to_legacy() returns a dict with non-None fields."""
        output = StageOutput(
            stage_name="test",
            status=StageStatus.COMPLETED,
            summary="Done",
            context_fingerprint="abc123",
        )
        legacy = output.to_legacy()
        assert legacy["stage_name"] == "test"
        assert legacy["context_fingerprint"] == "abc123"
        assert "error" not in legacy  # None fields excluded


# ---------------------------------------------------------------------------
# InvestigationOutput
# ---------------------------------------------------------------------------


class TestInvestigationOutput:
    """Tests for typed investigation output."""

    def test_valid_investigation(self):
        """Can create with all required fields."""
        output = InvestigationOutput(
            status=StageStatus.COMPLETED,
            summary="Found the bug",
            root_cause="Missing null check in UserService.getProfile()",
            affected_files=["UserService.java"],
        )
        assert output.stage_name == "investigate"
        assert output.root_cause.startswith("Missing null")

    def test_root_cause_required(self):
        """root_cause is required — cannot be omitted."""
        with pytest.raises(ValidationError):
            InvestigationOutput(
                status=StageStatus.COMPLETED,
                summary="Found something",
                # root_cause omitted
            )

    def test_root_cause_min_length(self):
        """root_cause must be at least 10 characters (not just 'unknown')."""
        with pytest.raises(ValidationError):
            InvestigationOutput(
                status=StageStatus.COMPLETED,
                summary="Found something",
                root_cause="short",  # < 10 chars
            )

    def test_empty_affected_files_allowed(self):
        """affected_files can be empty (not always known)."""
        output = InvestigationOutput(
            status=StageStatus.COMPLETED,
            summary="Found the bug",
            root_cause="Config error in application.yaml at line 42",
        )
        assert output.affected_files == []


# ---------------------------------------------------------------------------
# DesignOutput
# ---------------------------------------------------------------------------


class TestDesignOutput:
    """Tests for typed design output."""

    def test_valid_design(self):
        """Can create with all required fields."""
        output = DesignOutput(
            status=StageStatus.COMPLETED,
            summary="Fix designed",
            fix_summary="Add null guard in UserService.getProfile()",
            proposed_solution="Add an early return with empty UserProfile when user is null or deleted",
            risk_level="low",
        )
        assert output.stage_name == "design"
        assert output.risk_level == "low"

    def test_fix_summary_required(self):
        """fix_summary is required."""
        with pytest.raises(ValidationError):
            DesignOutput(
                status=StageStatus.COMPLETED,
                summary="Fix designed",
                proposed_solution="Do the thing that fixes it by adding the null check",
                # fix_summary omitted
            )

    def test_proposed_solution_required(self):
        """proposed_solution is required."""
        with pytest.raises(ValidationError):
            DesignOutput(
                status=StageStatus.COMPLETED,
                summary="Fix designed",
                fix_summary="Add null guard in UserService.getProfile()",
                # proposed_solution omitted
            )

    def test_invalid_risk_level(self):
        """risk_level must be low/medium/high."""
        with pytest.raises(ValidationError):
            DesignOutput(
                status=StageStatus.COMPLETED,
                summary="Fix designed",
                fix_summary="Add null guard in UserService.getProfile()",
                proposed_solution="Add an early return with empty UserProfile when user is null",
                risk_level="extreme",  # Invalid
            )

    def test_risk_level_case_insensitive(self):
        """risk_level validation is case-insensitive."""
        output = DesignOutput(
            status=StageStatus.COMPLETED,
            summary="Fix designed",
            fix_summary="Add null guard in UserService.getProfile()",
            proposed_solution="Add an early return with empty UserProfile when user is null",
            risk_level="High",  # Capitalized
        )
        assert output.risk_level == "High"


# ---------------------------------------------------------------------------
# ImplementationOutput
# ---------------------------------------------------------------------------


class TestImplementationOutput:
    """Tests for typed implementation output."""

    def test_valid_implementation(self):
        """Can create with code changes."""
        output = ImplementationOutput(
            status=StageStatus.COMPLETED,
            summary="Code changes applied",
            code_changes={"UserService.java": "- old line\n+ new line"},
            modified_files=["UserService.java"],
        )
        assert output.stage_name == "implement"
        assert "UserService.java" in output.code_changes

    def test_empty_changes_allowed(self):
        """Implementation can complete with no changes (e.g., config-only)."""
        output = ImplementationOutput(
            status=StageStatus.COMPLETED,
            summary="Config updated, no code changes",
        )
        assert output.code_changes == {}


# ---------------------------------------------------------------------------
# TestOutput
# ---------------------------------------------------------------------------


class TestValidationOutput:
    """Tests for typed validation/test output."""

    def test_valid_test_result(self):
        """Can create with test results."""
        output = ValidationOutput(
            status=StageStatus.COMPLETED,
            summary="All tests pass",
            tests_passed=True,
            test_results=["test_null_user: PASS", "test_active_user: PASS"],
        )
        assert output.stage_name == "test"
        assert output.tests_passed is True

    def test_coverage_delta_optional(self):
        """Coverage delta is optional."""
        output = ValidationOutput(
            status=StageStatus.COMPLETED,
            summary="Tests pass",
            tests_passed=True,
        )
        assert output.coverage_delta is None


# ---------------------------------------------------------------------------
# LessonOutput
# ---------------------------------------------------------------------------


class TestLessonOutput:
    """Tests for typed lesson output."""

    def test_valid_lesson(self):
        """Can create with lessons and prevention steps."""
        output = LessonOutput(
            status=StageStatus.COMPLETED,
            summary="Lessons captured",
            lessons=["Always check for null before accessing properties"],
            prevention_steps=["Add null checks at service boundaries"],
            confidence=0.9,
        )
        assert output.stage_name == "learn"
        assert output.confidence == 0.9

    def test_confidence_bounds(self):
        """Confidence must be between 0 and 1."""
        with pytest.raises(ValidationError):
            LessonOutput(
                status=StageStatus.COMPLETED,
                summary="Lessons captured",
                confidence=1.5,  # > 1.0
            )


# ---------------------------------------------------------------------------
# ContractViolation and GateResult
# ---------------------------------------------------------------------------


class TestContractViolation:
    """Tests for contract violation model."""

    def test_str_representation(self):
        """String representation includes severity and field info."""
        violation = ContractViolation(
            gate_name="schema",
            stage_name="investigate",
            field="root_cause",
            message="root_cause is too short",
            severity=ViolationSeverity.ERROR,
            suggestion="Provide at least 10 characters",
        )
        s = str(violation)
        assert "[ERROR]" in s
        assert "schema/investigate.root_cause" in s
        assert "suggestion:" in s

    def test_warning_severity(self):
        """Warnings use WARN prefix."""
        violation = ContractViolation(
            gate_name="quality",
            stage_name="design",
            field="tradeoffs",
            message="No tradeoffs listed",
            severity=ViolationSeverity.WARNING,
        )
        assert "[WARN]" in str(violation)


class TestGateResult:
    """Tests for gate result model."""

    def test_passed_result(self):
        """Passed result with no violations."""
        result = GateResult(passed=True, gate_name="schema")
        assert result.passed is True
        assert not result.has_errors
        assert not result.has_warnings
        assert "PASSED" in result.summary()

    def test_failed_result(self):
        """Failed result with violations."""
        result = GateResult(
            passed=False,
            gate_name="schema",
            violations=[
                ContractViolation(
                    gate_name="schema",
                    stage_name="investigate",
                    field="root_cause",
                    message="missing",
                )
            ],
        )
        assert result.passed is False
        assert result.has_errors
        assert "FAILED" in result.summary()
        assert "1 error" in result.summary()

    def test_passed_with_warnings(self):
        """Passed result can have warnings."""
        result = GateResult(
            passed=True,
            gate_name="quality",
            warnings=[
                ContractViolation(
                    gate_name="quality",
                    stage_name="design",
                    field="tradeoffs",
                    message="empty",
                    severity=ViolationSeverity.WARNING,
                )
            ],
        )
        assert result.passed is True
        assert result.has_warnings
        assert "1 warning" in result.summary()


# ---------------------------------------------------------------------------
# adapt_legacy_result()
# ---------------------------------------------------------------------------


class TestAdaptLegacyResult:
    """Tests for the legacy StageResult → typed StageOutput adapter."""

    def test_adapt_investigation(self, completed_stage_result):
        """Adapts investigation StageResult to InvestigationOutput."""
        output = adapt_legacy_result(completed_stage_result)
        assert isinstance(output, InvestigationOutput)
        assert output.root_cause == "Missing null check for deleted user accounts"
        assert "UserService.java" in output.affected_files[0]
        assert output.originating_pr == "#42"

    def test_adapt_design(self):
        """Adapts design StageResult to DesignOutput."""
        result = StageResult(
            stage_name="design",
            status=StageStatus.COMPLETED,
            started_at=datetime.now(),
            summary="Fix designed: add null guard",
            details="Detailed fix plan for the null pointer issue",
            fix_specification="Add null check before accessing user profile fields in getProfile method",
            tradeoffs=["Returns empty profile vs throwing exception"],
            alternatives=["Use Optional return type — rejected: too many changes"],
        )
        output = adapt_legacy_result(result)
        assert isinstance(output, DesignOutput)
        assert output.fix_summary == "Fix designed: add null guard"
        assert len(output.tradeoffs) == 1

    def test_adapt_implementation(self):
        """Adapts implementation StageResult to ImplementationOutput."""
        result = StageResult(
            stage_name="implement",
            status=StageStatus.COMPLETED,
            started_at=datetime.now(),
            summary="Code changes applied",
            code_changes={"UserService.java": "added null check"},
            pr_url="https://github.com/example/repo/pull/43",
        )
        output = adapt_legacy_result(result)
        assert isinstance(output, ImplementationOutput)
        assert "UserService.java" in output.code_changes
        assert output.pr_url is not None

    def test_adapt_test(self):
        """Adapts test StageResult to TestOutput."""
        result = StageResult(
            stage_name="test",
            status=StageStatus.COMPLETED,
            started_at=datetime.now(),
            summary="All tests pass",
            tests_passed=True,
            regression_risk="Low",
        )
        output = adapt_legacy_result(result)
        assert isinstance(output, ValidationOutput)
        assert output.tests_passed is True
        assert output.regression_risk == "Low"

    def test_adapt_learn(self):
        """Adapts learn StageResult to LessonOutput."""
        result = StageResult(
            stage_name="learn",
            status=StageStatus.COMPLETED,
            started_at=datetime.now(),
            summary="Lessons captured",
            lessons=["Always check for null"],
            prevention_steps=["Add null checks at boundaries"],
        )
        output = adapt_legacy_result(result)
        assert isinstance(output, LessonOutput)
        assert len(output.lessons) == 1
        assert len(output.prevention_steps) == 1

    def test_adapt_unknown_stage(self):
        """Unknown stage names get base StageOutput."""
        result = StageResult(
            stage_name="custom_stage",
            status=StageStatus.COMPLETED,
            started_at=datetime.now(),
            summary="Custom work done",
        )
        output = adapt_legacy_result(result)
        assert isinstance(output, StageOutput)
        assert not isinstance(output, InvestigationOutput)
        assert output.stage_name == "custom_stage"

    def test_adapt_failed_investigation(self):
        """Failed investigation gets placeholder root_cause."""
        result = StageResult(
            stage_name="investigate",
            status=StageStatus.FAILED,
            started_at=datetime.now(),
            summary="Investigation failed",
            error="LLM timeout",
        )
        output = adapt_legacy_result(result)
        assert isinstance(output, InvestigationOutput)
        assert "legacy result" in output.root_cause.lower() or "unknown" in output.root_cause.lower()


# ---------------------------------------------------------------------------
# STAGE_OUTPUT_REGISTRY
# ---------------------------------------------------------------------------


class TestStageOutputRegistry:
    """Tests for the stage output type registry."""

    def test_all_stages_registered(self):
        """All known stage names are in the registry."""
        expected = {"investigate", "design", "implement", "test", "learn"}
        assert set(STAGE_OUTPUT_REGISTRY.keys()) == expected

    def test_types_match(self):
        """Registry maps to correct types."""
        assert STAGE_OUTPUT_REGISTRY["investigate"] is InvestigationOutput
        assert STAGE_OUTPUT_REGISTRY["design"] is DesignOutput
        assert STAGE_OUTPUT_REGISTRY["implement"] is ImplementationOutput
        assert STAGE_OUTPUT_REGISTRY["test"] is ValidationOutput
        assert STAGE_OUTPUT_REGISTRY["learn"] is LessonOutput
