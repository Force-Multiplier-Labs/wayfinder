"""Tests for contextcore_coyote.pipeline.stage — Stage abstraction and StageContext."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from contextcore_coyote.models import Incident, IncidentSeverity, StageResult, StageStatus
from contextcore_coyote.pipeline.stage import Stage, StageContext


class MockStage(Stage):
    """Concrete stage for testing that returns a canned result."""

    name = "mock"
    description = "Mock stage for testing"

    def __init__(self, result=None, should_fail=False, should_skip_flag=False):
        # Avoid calling super().__init__() which calls get_config()
        # Instead, set config directly
        from contextcore_coyote.config import CoyoteConfig

        self.config = CoyoteConfig(contextcore_enabled=False, auto_proceed=True)
        self._result = result
        self._should_fail = should_fail
        self._should_skip_flag = should_skip_flag

    def execute(self, ctx: StageContext) -> StageResult:
        if self._should_fail:
            raise RuntimeError("Mock stage failure")

        if self._result:
            return self._result

        return StageResult(
            stage_name=self.name,
            status=StageStatus.COMPLETED,
            started_at=datetime.now(),
            summary="Mock execution complete",
        )

    def should_skip(self, ctx: StageContext) -> bool:
        return self._should_skip_flag


@pytest.fixture
def sample_ctx(sample_incident):
    """StageContext with a sample incident."""
    return StageContext(incident=sample_incident)


# --- StageContext ---


class TestStageContext:
    """Test StageContext."""

    def test_get_result_found(self, sample_ctx, completed_stage_result):
        sample_ctx.previous_results.append(completed_stage_result)
        result = sample_ctx.get_result("investigate")
        assert result is completed_stage_result

    def test_get_result_not_found(self, sample_ctx):
        assert sample_ctx.get_result("nonexistent") is None

    def test_investigation_result_property(self, sample_ctx, completed_stage_result):
        sample_ctx.previous_results.append(completed_stage_result)
        assert sample_ctx.investigation_result is completed_stage_result

    def test_investigation_result_none(self, sample_ctx):
        assert sample_ctx.investigation_result is None

    def test_design_result_property(self, sample_ctx):
        design = StageResult(
            stage_name="design",
            status=StageStatus.COMPLETED,
            started_at=datetime.now(),
        )
        sample_ctx.previous_results.append(design)
        assert sample_ctx.design_result is design

    def test_implementation_result_property(self, sample_ctx):
        impl = StageResult(
            stage_name="implement",
            status=StageStatus.COMPLETED,
            started_at=datetime.now(),
        )
        sample_ctx.previous_results.append(impl)
        assert sample_ctx.implementation_result is impl

    def test_multiple_results(self, sample_ctx):
        inv = StageResult(
            stage_name="investigate",
            status=StageStatus.COMPLETED,
            started_at=datetime.now(),
        )
        design = StageResult(
            stage_name="design",
            status=StageStatus.COMPLETED,
            started_at=datetime.now(),
        )
        sample_ctx.previous_results.extend([inv, design])
        assert sample_ctx.investigation_result is inv
        assert sample_ctx.design_result is design


# --- Stage ---


class TestStage:
    """Test Stage base class behavior via MockStage."""

    def test_run_sets_timing(self, sample_ctx):
        stage = MockStage()
        result = stage.run(sample_ctx)
        assert result.started_at is not None
        assert result.completed_at is not None
        assert result.status == StageStatus.COMPLETED

    def test_run_catches_exception(self, sample_ctx):
        stage = MockStage(should_fail=True)
        result = stage.run(sample_ctx)
        assert result.status == StageStatus.FAILED
        assert "Mock stage failure" in result.error
        assert result.completed_at is not None

    def test_run_skip_logic(self, sample_ctx):
        stage = MockStage(should_skip_flag=True)
        result = stage.run(sample_ctx)
        assert result.status == StageStatus.SKIPPED
        assert "skipped" in result.summary.lower()
        assert result.completed_at is not None

    def test_should_skip_default_false(self, sample_ctx):
        stage = MockStage()
        assert stage.should_skip(sample_ctx) is False

    def test_get_prompt(self, sample_ctx):
        stage = MockStage()
        prompt = stage.get_prompt(sample_ctx)
        assert sample_ctx.incident.title in prompt

    def test_run_duration_positive(self, sample_ctx):
        stage = MockStage()
        result = stage.run(sample_ctx)
        assert result.duration_seconds is not None
        assert result.duration_seconds >= 0

    def test_run_uses_custom_result(self, sample_ctx):
        custom = StageResult(
            stage_name="mock",
            status=StageStatus.COMPLETED,
            started_at=datetime.now(),
            summary="Custom result",
        )
        stage = MockStage(result=custom)
        result = stage.run(sample_ctx)
        assert result.summary == "Custom result"
