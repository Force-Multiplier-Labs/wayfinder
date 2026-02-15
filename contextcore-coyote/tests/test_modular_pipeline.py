"""
Tests for ModularPipeline — gate-validated multi-agent pipeline.

Tests cover:
- LegacyStageAdapter wrapping HOWL stages
- ModularPipeline execution with gates
- Gate failure halting the pipeline
- Override callback to proceed despite gate failure
- Approval checkpoints
- Context fingerprinting
- Diagnostic summary output
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

from contextcore_coyote.models import Incident, IncidentSeverity, StageResult, StageStatus
from contextcore_coyote.pipeline.contracts import (
    InvestigationOutput,
    StageOutput,
    GateResult,
    ContractViolation,
    ViolationSeverity,
)
from contextcore_coyote.pipeline.gates import (
    CompositeGate,
    SchemaGate,
    CompletenessGate,
    standard_gate,
)
from contextcore_coyote.pipeline.modular import (
    LegacyStageAdapter,
    ModularPipeline,
    ModularPipelineResult,
)
from contextcore_coyote.pipeline.stage import Stage, StageContext


# ---------------------------------------------------------------------------
# Helpers: Fake stages for testing
# ---------------------------------------------------------------------------


class FakeSuccessStage(Stage):
    """A fake stage that always succeeds with a meaningful result."""

    name = "investigate"
    description = "Fake investigator"

    def execute(self, ctx: StageContext) -> StageResult:
        return StageResult(
            stage_name=self.name,
            status=StageStatus.COMPLETED,
            started_at=datetime.now(),
            completed_at=datetime.now(),
            summary="Investigation complete: found the root cause of the issue here",
            details="Full investigation report with all the analysis and findings documented thoroughly.",
            root_cause="Missing null check for deleted user accounts in getProfile method",
            affected_code=["UserService.java"],
        )


class FakeFailStage(Stage):
    """A fake stage that always fails."""

    name = "investigate"
    description = "Fake failing investigator"

    def execute(self, ctx: StageContext) -> StageResult:
        return StageResult(
            stage_name=self.name,
            status=StageStatus.FAILED,
            started_at=datetime.now(),
            completed_at=datetime.now(),
            summary="Investigation failed due to LLM timeout error",
            error="Connection timeout after 30s",
        )


class FakeExceptionStage(Stage):
    """A fake stage that raises an exception."""

    name = "investigate"
    description = "Fake exception stage"

    def execute(self, ctx: StageContext) -> StageResult:
        raise RuntimeError("Unexpected error in stage")


class FakeDesignStage(Stage):
    """A fake design stage."""

    name = "design"
    description = "Fake designer"

    def execute(self, ctx: StageContext) -> StageResult:
        return StageResult(
            stage_name=self.name,
            status=StageStatus.COMPLETED,
            started_at=datetime.now(),
            completed_at=datetime.now(),
            summary="Design complete: null guard fix for UserService.getProfile method",
            details="Complete design specification with implementation details and tradeoffs analysis.",
            fix_specification="Add null check before accessing user profile fields in the getProfile method",
            tradeoffs=["Returns empty profile vs throwing"],
        )


# ---------------------------------------------------------------------------
# LegacyStageAdapter
# ---------------------------------------------------------------------------


class TestLegacyStageAdapter:
    """Tests for wrapping HOWL stages."""

    def test_wraps_stage(self):
        """Adapter preserves stage name."""
        stage = FakeSuccessStage()
        adapter = LegacyStageAdapter(stage)
        assert adapter.name == "investigate"

    def test_produces_typed_output(self, sample_incident):
        """Adapter converts StageResult to typed StageOutput."""
        stage = FakeSuccessStage()
        adapter = LegacyStageAdapter(stage)

        ctx = StageContext(incident=sample_incident)
        output = adapter.execute(ctx)

        assert isinstance(output, InvestigationOutput)
        assert output.root_cause.startswith("Missing null")

    def test_sets_fingerprint(self, sample_incident):
        """Adapter sets context fingerprint when provided."""
        stage = FakeSuccessStage()
        adapter = LegacyStageAdapter(stage)

        ctx = StageContext(incident=sample_incident)
        output = adapter.execute(ctx, context_fp="test_fp_12345")

        assert output.context_fingerprint == "test_fp_12345"

    def test_handles_failure(self, sample_incident):
        """Adapter handles failed stage results."""
        stage = FakeFailStage()
        adapter = LegacyStageAdapter(stage)

        ctx = StageContext(incident=sample_incident)
        output = adapter.execute(ctx)

        assert output.status == StageStatus.FAILED
        assert isinstance(output, InvestigationOutput)


# ---------------------------------------------------------------------------
# ModularPipeline: basic execution
# ---------------------------------------------------------------------------


class TestModularPipelineExecution:
    """Tests for pipeline execution flow."""

    def test_single_stage_pipeline(self, sample_incident):
        """Single-stage pipeline runs and validates."""
        pipeline = ModularPipeline()
        pipeline.add_stage(FakeSuccessStage())

        result = pipeline.run(sample_incident)

        assert result.status == "completed"
        assert len(result.stage_outputs) == 1
        assert len(result.gate_results) == 1
        assert result.gate_results[0].passed is True
        assert result.successful is True

    def test_multi_stage_pipeline(self, sample_incident):
        """Multi-stage pipeline runs all stages in sequence."""
        pipeline = ModularPipeline()
        pipeline.add_stage(FakeSuccessStage())
        pipeline.add_stage(FakeDesignStage())

        result = pipeline.run(sample_incident)

        assert result.status == "completed"
        assert len(result.stage_outputs) == 2
        assert result.stage_outputs[0].stage_name == "investigate"
        assert result.stage_outputs[1].stage_name == "design"

    def test_context_fingerprint_set(self, sample_incident):
        """Pipeline sets context fingerprint on result and outputs."""
        pipeline = ModularPipeline()
        pipeline.add_stage(FakeSuccessStage())

        result = pipeline.run(sample_incident)

        assert result.context_fingerprint is not None
        assert len(result.context_fingerprint) == 16
        assert result.stage_outputs[0].context_fingerprint == result.context_fingerprint

    def test_stage_failure_halts_pipeline(self, sample_incident):
        """Failed stage stops the pipeline without running gate."""
        pipeline = ModularPipeline()
        pipeline.add_stage(FakeFailStage())
        pipeline.add_stage(FakeDesignStage())  # Should not run

        result = pipeline.run(sample_incident)

        assert result.status == "failed"
        assert len(result.stage_outputs) == 1
        assert len(result.gate_results) == 0  # Gate not reached

    def test_exception_caught_as_failure(self, sample_incident):
        """Stage exceptions are caught and converted to failure."""
        pipeline = ModularPipeline()
        pipeline.add_stage(FakeExceptionStage())

        result = pipeline.run(sample_incident)

        assert result.status == "failed"
        assert result.stage_outputs[0].status == StageStatus.FAILED
        assert "Unexpected error" in result.stage_outputs[0].error

    def test_auto_wraps_legacy_stages(self, sample_incident):
        """add_stage() auto-wraps HOWL Stage instances."""
        pipeline = ModularPipeline()
        stage = FakeSuccessStage()
        pipeline.add_stage(stage)  # Should auto-wrap

        assert isinstance(pipeline.stages[0], LegacyStageAdapter)
        result = pipeline.run(sample_incident)
        assert result.status == "completed"


# ---------------------------------------------------------------------------
# ModularPipeline: gate behavior
# ---------------------------------------------------------------------------


class TestModularPipelineGates:
    """Tests for gate validation between stages."""

    def test_gate_failure_halts_pipeline(self, sample_incident):
        """Gate failure stops the pipeline."""

        # Create a gate that always fails
        class AlwaysFailGate:
            name = "always_fail"

            def validate(self, output):
                return GateResult(
                    passed=False,
                    gate_name=self.name,
                    violations=[
                        ContractViolation(
                            gate_name=self.name,
                            stage_name=output.stage_name,
                            field="test",
                            message="Always fails for testing",
                        )
                    ],
                )

        pipeline = ModularPipeline(
            gate=CompositeGate(gates=[AlwaysFailGate()], label="fail-test"),
        )
        pipeline.add_stage(FakeSuccessStage())
        pipeline.add_stage(FakeDesignStage())

        result = pipeline.run(sample_incident)

        assert result.status == "gate_failed"
        assert len(result.stage_outputs) == 1  # Only first stage ran
        assert len(result.gate_results) == 1
        assert not result.gate_results[0].passed

    def test_gate_override_allows_proceed(self, sample_incident):
        """on_gate_failed callback returning True allows proceeding."""

        class AlwaysFailGate:
            name = "always_fail"

            def validate(self, output):
                return GateResult(
                    passed=False,
                    gate_name=self.name,
                    violations=[
                        ContractViolation(
                            gate_name=self.name,
                            stage_name=output.stage_name,
                            field="test",
                            message="Fails but should be overridden",
                        )
                    ],
                )

        pipeline = ModularPipeline(
            gate=CompositeGate(gates=[AlwaysFailGate()], label="override-test"),
            on_gate_failed=lambda gate_result: True,  # Override
        )
        pipeline.add_stage(FakeSuccessStage())
        pipeline.add_stage(FakeDesignStage())

        result = pipeline.run(sample_incident)

        assert result.status == "completed"
        assert len(result.stage_outputs) == 2

    def test_custom_gate_per_boundary(self, sample_incident):
        """Different gates for different boundaries."""
        call_log = []

        class TrackingGate:
            def __init__(self, label):
                self.name = label

            def validate(self, output):
                call_log.append(self.name)
                return GateResult(passed=True, gate_name=self.name)

        pipeline = ModularPipeline(
            gate=CompositeGate(gates=[TrackingGate("default")], label="default"),
        )
        pipeline.add_stage(FakeSuccessStage())
        pipeline.add_stage(FakeDesignStage())

        # Override gate after stage 0
        pipeline.set_gate_after(
            0, CompositeGate(gates=[TrackingGate("custom")], label="custom")
        )

        result = pipeline.run(sample_incident)

        assert result.status == "completed"
        assert "custom" in call_log  # Custom gate was used after stage 0
        assert "default" in call_log  # Default gate was used after stage 1


# ---------------------------------------------------------------------------
# ModularPipeline: approval checkpoints
# ---------------------------------------------------------------------------


class TestModularPipelineApproval:
    """Tests for human approval checkpoints."""

    def test_approval_pauses_pipeline(self, sample_incident):
        """Pipeline pauses when approval is denied."""
        pipeline = ModularPipeline(
            auto_proceed=False,
            on_approval_needed=lambda name, output: False,  # Deny
        )
        pipeline.add_stage(FakeSuccessStage())
        pipeline.add_stage(FakeDesignStage())

        result = pipeline.run(sample_incident)

        assert result.status == "awaiting_approval"
        assert len(result.stage_outputs) == 1

    def test_approval_continues_pipeline(self, sample_incident):
        """Pipeline continues when approval is granted."""
        pipeline = ModularPipeline(
            auto_proceed=False,
            on_approval_needed=lambda name, output: True,  # Approve
        )
        pipeline.add_stage(FakeSuccessStage())
        pipeline.add_stage(FakeDesignStage())

        result = pipeline.run(sample_incident)

        assert result.status == "completed"
        assert len(result.stage_outputs) == 2


# ---------------------------------------------------------------------------
# ModularPipelineResult: diagnostics
# ---------------------------------------------------------------------------


class TestModularPipelineResult:
    """Tests for pipeline result diagnostics."""

    def test_diagnostic_summary(self, sample_incident):
        """Diagnostic summary answers the three questions."""
        pipeline = ModularPipeline()
        pipeline.add_stage(FakeSuccessStage())

        result = pipeline.run(sample_incident)
        summary = result.diagnostic_summary()

        assert "Question 1" in summary
        assert "Question 2" in summary
        assert "Question 3" in summary
        assert sample_incident.id in summary
        assert "investigate" in summary

    def test_all_violations_collected(self, sample_incident):
        """all_violations aggregates across gates."""
        result = ModularPipelineResult(incident=sample_incident)
        result.gate_results = [
            GateResult(
                passed=False,
                gate_name="gate1",
                violations=[
                    ContractViolation(
                        gate_name="gate1",
                        stage_name="s1",
                        field="f1",
                        message="v1",
                    )
                ],
            ),
            GateResult(
                passed=False,
                gate_name="gate2",
                violations=[
                    ContractViolation(
                        gate_name="gate2",
                        stage_name="s2",
                        field="f2",
                        message="v2",
                    )
                ],
            ),
        ]

        assert len(result.all_violations) == 2
        assert result.all_violations[0].message == "v1"
        assert result.all_violations[1].message == "v2"

    def test_successful_requires_all_gates_passed(self, sample_incident):
        """successful is False if any gate failed."""
        result = ModularPipelineResult(incident=sample_incident)
        result.stage_outputs = [
            StageOutput(
                stage_name="test",
                status=StageStatus.COMPLETED,
                summary="OK stage output",
            )
        ]
        result.gate_results = [
            GateResult(passed=False, gate_name="schema", violations=[
                ContractViolation(
                    gate_name="schema",
                    stage_name="test",
                    field="type",
                    message="wrong type",
                )
            ])
        ]

        assert result.successful is False

    def test_on_stage_complete_callback(self, sample_incident):
        """on_stage_complete is called after each stage."""
        calls = []
        pipeline = ModularPipeline(
            on_stage_complete=lambda output: calls.append(output.stage_name),
        )
        pipeline.add_stage(FakeSuccessStage())
        pipeline.add_stage(FakeDesignStage())

        pipeline.run(sample_incident)

        assert calls == ["investigate", "design"]
