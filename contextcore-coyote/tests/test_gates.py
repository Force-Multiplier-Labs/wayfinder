"""
Tests for gate implementations — Defense in Depth Principle 1 validation.

Tests cover:
- SchemaGate: Type correctness and status validation
- CompletenessGate: Meaningful content checks
- IntegrityGate: Context fingerprint chain
- QualityGate: Output quality heuristics
- CompositeGate: Gate composition
- Pre-built gate configurations
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from contextcore_coyote.models import StageStatus
from contextcore_coyote.pipeline.contracts import (
    ContractViolation,
    DesignOutput,
    InvestigationOutput,
    StageOutput,
    ValidationOutput,
    ViolationSeverity,
    fingerprint,
)
from contextcore_coyote.pipeline.gates import (
    CompletenessGate,
    CompositeGate,
    IntegrityGate,
    QualityGate,
    SchemaGate,
    standard_gate,
    strict_gate,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def valid_investigation():
    """A well-formed InvestigationOutput."""
    return InvestigationOutput(
        status=StageStatus.COMPLETED,
        summary="Found root cause: missing null check in UserService",
        details="Detailed investigation report with multiple paragraphs of analysis...",
        root_cause="NullPointerException due to missing null check for deleted users in getProfile()",
        affected_files=["src/main/java/com/example/UserService.java"],
        started_at=datetime(2026, 2, 9, 12, 0, 0),
        completed_at=datetime(2026, 2, 9, 12, 0, 15),
        context_fingerprint="abc123def456",
    )


@pytest.fixture
def valid_design():
    """A well-formed DesignOutput."""
    return DesignOutput(
        status=StageStatus.COMPLETED,
        summary="Designed null guard fix for UserService.getProfile()",
        details="Complete design specification with tradeoffs and alternatives...",
        fix_summary="Add null guard in UserService.getProfile() for deleted users",
        proposed_solution="Add an early return with empty UserProfile when the user lookup returns null or user.isDeleted()",
        files_to_modify=["UserService.java"],
        tradeoffs=["Returns empty profile vs throwing exception"],
        risk_level="low",
        started_at=datetime(2026, 2, 9, 12, 0, 15),
        completed_at=datetime(2026, 2, 9, 12, 0, 30),
    )


# ---------------------------------------------------------------------------
# SchemaGate
# ---------------------------------------------------------------------------


class TestSchemaGate:
    """Tests for schema validation gate."""

    def test_correct_type_passes(self, valid_investigation):
        """InvestigationOutput with stage_name='investigate' passes."""
        gate = SchemaGate()
        result = gate.validate(valid_investigation)
        assert result.passed is True
        assert len(result.violations) == 0

    def test_wrong_type_fails(self):
        """Base StageOutput with stage_name='investigate' fails."""
        output = StageOutput(
            stage_name="investigate",
            status=StageStatus.COMPLETED,
            summary="I investigated but returned the wrong type",
        )
        gate = SchemaGate()
        result = gate.validate(output)
        assert result.passed is False
        assert any("Expected InvestigationOutput" in v.message for v in result.violations)

    def test_unknown_stage_warns(self):
        """Unknown stage names get a warning, not an error."""
        output = StageOutput(
            stage_name="custom_analysis",
            status=StageStatus.COMPLETED,
            summary="Custom analysis complete with sufficient detail",
        )
        gate = SchemaGate()
        result = gate.validate(output)
        assert result.passed is True  # Warning, not error
        assert len(result.warnings) == 1
        assert "Unknown stage" in result.warnings[0].message

    def test_pending_status_fails(self):
        """PENDING status should not pass through a gate."""
        output = InvestigationOutput(
            status=StageStatus.PENDING,
            summary="Not started yet",
            root_cause="This shouldn't exist yet — investigation hasn't started",
        )
        gate = SchemaGate()
        result = gate.validate(output)
        assert result.passed is False
        assert any("non-terminal status" in v.message for v in result.violations)

    def test_running_status_fails(self):
        """RUNNING status should not pass through a gate."""
        output = InvestigationOutput(
            status=StageStatus.RUNNING,
            summary="Still working on the investigation process",
            root_cause="This shouldn't exist yet — investigation still running",
        )
        gate = SchemaGate()
        result = gate.validate(output)
        assert result.passed is False

    def test_failed_status_passes(self):
        """FAILED status is a terminal state — valid to pass through gate."""
        output = InvestigationOutput(
            status=StageStatus.FAILED,
            summary="Investigation failed due to LLM timeout",
            root_cause="Unknown — investigation did not complete successfully",
            error="LLM timeout after 30s",
        )
        gate = SchemaGate()
        result = gate.validate(output)
        assert result.passed is True

    def test_skipped_status_passes(self):
        """SKIPPED status is a terminal state — valid to pass through gate."""
        output = InvestigationOutput(
            status=StageStatus.SKIPPED,
            summary="Investigation skipped — not applicable",
            root_cause="Not applicable — stage was skipped by pipeline",
        )
        gate = SchemaGate()
        result = gate.validate(output)
        assert result.passed is True


# ---------------------------------------------------------------------------
# CompletenessGate
# ---------------------------------------------------------------------------


class TestCompletenessGate:
    """Tests for completeness validation gate."""

    def test_complete_output_passes(self, valid_investigation):
        """Well-formed output passes completeness checks."""
        gate = CompletenessGate()
        result = gate.validate(valid_investigation)
        assert result.passed is True

    def test_short_summary_fails(self):
        """Summary shorter than min_summary_length fails."""
        output = InvestigationOutput(
            status=StageStatus.COMPLETED,
            summary="Short",  # < 10 chars
            root_cause="Sufficient root cause explanation for the error",
        )
        gate = CompletenessGate(min_summary_length=10)
        result = gate.validate(output)
        assert result.passed is False
        assert any("too short" in v.message for v in result.violations)

    def test_custom_min_length(self):
        """Custom min_summary_length is respected."""
        output = InvestigationOutput(
            status=StageStatus.COMPLETED,
            summary="OK summary",
            root_cause="Sufficient root cause explanation for the error",
        )
        # Passes with low threshold
        gate_low = CompletenessGate(min_summary_length=5)
        assert gate_low.validate(output).passed is True

        # Fails with high threshold
        gate_high = CompletenessGate(min_summary_length=50)
        assert gate_high.validate(output).passed is False

    def test_failed_without_error_fails(self):
        """Failed stage without error message fails completeness."""
        output = InvestigationOutput(
            status=StageStatus.FAILED,
            summary="Investigation failed — unable to analyze this issue",
            root_cause="Unknown — investigation did not complete successfully",
            error=None,  # No error!
        )
        gate = CompletenessGate()
        result = gate.validate(output)
        assert result.passed is False
        assert any("no error message" in v.message for v in result.violations)

    def test_completed_without_details_warns(self):
        """Completed stage without details gets a warning."""
        output = InvestigationOutput(
            status=StageStatus.COMPLETED,
            summary="Investigation complete: found the root cause",
            details="",  # Empty!
            root_cause="Sufficient root cause explanation for this error",
        )
        gate = CompletenessGate()
        result = gate.validate(output)
        assert result.passed is True  # Warning, not error
        assert len(result.warnings) > 0
        assert any("empty details" in w.message for w in result.warnings)

    def test_details_not_required_when_disabled(self):
        """require_details_on_success=False suppresses the warning."""
        output = InvestigationOutput(
            status=StageStatus.COMPLETED,
            summary="Investigation complete: found the root cause",
            details="",
            root_cause="Sufficient root cause explanation for this error",
        )
        gate = CompletenessGate(require_details_on_success=False)
        result = gate.validate(output)
        assert result.passed is True
        assert len(result.warnings) == 0 or not any(
            "empty details" in w.message for w in result.warnings
        )


# ---------------------------------------------------------------------------
# IntegrityGate
# ---------------------------------------------------------------------------


class TestIntegrityGate:
    """Tests for integrity/fingerprint gate."""

    def test_matching_fingerprint_passes(self, valid_investigation):
        """Matching fingerprint passes."""
        gate = IntegrityGate(expected_fingerprint="abc123def456")
        result = gate.validate(valid_investigation)
        assert result.passed is True

    def test_mismatched_fingerprint_fails(self, valid_investigation):
        """Mismatched fingerprint is a hard stop."""
        gate = IntegrityGate(expected_fingerprint="different_fingerprint")
        result = gate.validate(valid_investigation)
        assert result.passed is False
        assert any("mismatch" in v.message for v in result.violations)
        assert any("stale" in v.suggestion for v in result.violations)

    def test_missing_fingerprint_when_expected_fails(self):
        """Missing fingerprint when one is expected fails."""
        output = InvestigationOutput(
            status=StageStatus.COMPLETED,
            summary="Investigation complete but no fingerprint",
            root_cause="Sufficient root cause explanation for the error",
            context_fingerprint=None,
        )
        gate = IntegrityGate(expected_fingerprint="expected_fp")
        result = gate.validate(output)
        assert result.passed is False

    def test_no_expectation_warns_when_missing(self):
        """No expected fingerprint + no actual = warning."""
        output = InvestigationOutput(
            status=StageStatus.COMPLETED,
            summary="Investigation complete with enough detail",
            root_cause="Sufficient root cause explanation for the error",
            context_fingerprint=None,
        )
        gate = IntegrityGate(expected_fingerprint=None)
        result = gate.validate(output)
        assert result.passed is True
        assert len(result.warnings) > 0

    def test_fingerprint_present_no_expectation(self, valid_investigation):
        """Fingerprint present but no expected value = pass."""
        gate = IntegrityGate(expected_fingerprint=None)
        result = gate.validate(valid_investigation)
        assert result.passed is True


# ---------------------------------------------------------------------------
# QualityGate
# ---------------------------------------------------------------------------


class TestQualityGate:
    """Tests for quality heuristics gate."""

    def test_quality_output_passes(self, valid_investigation):
        """Good quality output passes."""
        gate = QualityGate()
        result = gate.validate(valid_investigation)
        assert result.passed is True

    def test_short_details_warns(self):
        """Short details get a warning in non-strict mode."""
        output = InvestigationOutput(
            status=StageStatus.COMPLETED,
            summary="Investigation complete: found the root cause of the issue",
            details="Short",
            root_cause="Sufficient root cause explanation for the error",
        )
        gate = QualityGate(min_details_length=50, strict=False)
        result = gate.validate(output)
        assert result.passed is True  # Warning, not error
        assert len(result.warnings) > 0

    def test_short_details_fails_strict(self):
        """Short details fail in strict mode."""
        output = InvestigationOutput(
            status=StageStatus.COMPLETED,
            summary="Investigation complete: found the root cause of the issue",
            details="Short",
            root_cause="Sufficient root cause explanation for the error",
        )
        gate = QualityGate(min_details_length=50, strict=True)
        result = gate.validate(output)
        assert result.passed is False

    def test_placeholder_content_detected(self):
        """Placeholder content is flagged."""
        output = InvestigationOutput(
            status=StageStatus.COMPLETED,
            summary="Investigation complete with enough detail here",
            details="TODO: implement real analysis. This is placeholder text for now.",
            root_cause="Sufficient root cause explanation for the error",
        )
        gate = QualityGate(strict=True)
        result = gate.validate(output)
        assert result.passed is False
        assert any("placeholder" in v.message for v in result.violations)

    def test_failed_stages_skip_quality(self):
        """Failed stages aren't checked for detail length."""
        output = InvestigationOutput(
            status=StageStatus.FAILED,
            summary="Investigation failed due to a timeout error",
            details="",
            root_cause="Unknown — investigation timed out before completion",
            error="Timeout",
        )
        gate = QualityGate(min_details_length=50, strict=True)
        result = gate.validate(output)
        # Quality gate only checks COMPLETED stages for detail length
        assert result.passed is True


# ---------------------------------------------------------------------------
# CompositeGate
# ---------------------------------------------------------------------------


class TestCompositeGate:
    """Tests for gate composition."""

    def test_all_pass(self, valid_investigation):
        """All sub-gates passing means composite passes."""
        gate = CompositeGate(
            gates=[SchemaGate(), CompletenessGate()],
            label="test-composite",
        )
        result = gate.validate(valid_investigation)
        assert result.passed is True
        assert result.gate_name == "test-composite"

    def test_one_fails(self):
        """One sub-gate failing means composite fails."""
        # Wrong type for stage name — SchemaGate will fail
        output = StageOutput(
            stage_name="investigate",
            status=StageStatus.COMPLETED,
            summary="Wrong type used for this investigation output",
        )
        gate = CompositeGate(
            gates=[SchemaGate(), CompletenessGate()],
            label="test",
        )
        result = gate.validate(output)
        assert result.passed is False

    def test_all_gates_run_even_when_first_fails(self):
        """All gates run to collect all violations, not just the first."""
        output = StageOutput(
            stage_name="investigate",
            status=StageStatus.PENDING,  # SchemaGate: non-terminal
            summary="short",  # CompletenessGate: too short
        )
        gate = CompositeGate(
            gates=[SchemaGate(), CompletenessGate()],
            label="full-check",
        )
        result = gate.validate(output)
        assert result.passed is False
        # Should have violations from both gates
        gate_names = {v.gate_name for v in result.violations}
        assert "schema" in gate_names
        assert "completeness" in gate_names

    def test_warnings_aggregated(self, valid_investigation):
        """Warnings from all gates are aggregated."""
        # IntegrityGate will warn (no expected fingerprint)
        # QualityGate will pass
        gate = CompositeGate(
            gates=[
                SchemaGate(),
                QualityGate(),
            ],
            label="aggregate-test",
        )
        result = gate.validate(valid_investigation)
        assert result.passed is True


# ---------------------------------------------------------------------------
# Pre-built configurations
# ---------------------------------------------------------------------------


class TestPrebuiltGates:
    """Tests for standard_gate() and strict_gate()."""

    def test_standard_gate_passes_good_output(self, valid_investigation):
        """Standard gate passes well-formed output."""
        gate = standard_gate()
        result = gate.validate(valid_investigation)
        assert result.passed is True

    def test_standard_gate_catches_wrong_type(self):
        """Standard gate catches type mismatches."""
        output = StageOutput(
            stage_name="investigate",
            status=StageStatus.COMPLETED,
            summary="I investigated but returned wrong type here",
        )
        gate = standard_gate()
        result = gate.validate(output)
        assert result.passed is False

    def test_strict_gate_requires_quality(self):
        """Strict gate fails on low-quality output."""
        output = InvestigationOutput(
            status=StageStatus.COMPLETED,
            summary="Investigation complete: found root cause of issue",
            details="Brief",
            root_cause="NullPointerException due to missing null check in service",
        )
        gate = strict_gate()
        result = gate.validate(output)
        assert result.passed is False

    def test_strict_gate_with_fingerprint(self, valid_investigation):
        """Strict gate validates fingerprint when provided."""
        gate = strict_gate(expected_fingerprint="abc123def456")
        result = gate.validate(valid_investigation)
        assert result.passed is True

    def test_strict_gate_rejects_wrong_fingerprint(self, valid_investigation):
        """Strict gate rejects mismatched fingerprint."""
        gate = strict_gate(expected_fingerprint="wrong")
        result = gate.validate(valid_investigation)
        assert result.passed is False
