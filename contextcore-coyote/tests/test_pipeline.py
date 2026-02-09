"""Tests for contextcore_coyote.pipeline.core — Pipeline orchestration."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from contextcore_coyote.config import CoyoteConfig
from contextcore_coyote.models import Incident, IncidentSeverity, StageResult, StageStatus
from contextcore_coyote.pipeline.core import Pipeline, PipelineResult
from contextcore_coyote.pipeline.stage import Stage, StageContext
import contextcore_coyote.config as config_module


class PassStage(Stage):
    """Stage that always succeeds."""

    def __init__(self, name="pass"):
        from contextcore_coyote.config import CoyoteConfig

        self.config = CoyoteConfig(contextcore_enabled=False, auto_proceed=True)
        self.name = name
        self.description = f"Pass stage: {name}"

    def execute(self, ctx: StageContext) -> StageResult:
        return StageResult(
            stage_name=self.name,
            status=StageStatus.COMPLETED,
            started_at=datetime.now(),
            summary=f"{self.name} completed",
        )


class FailStage(Stage):
    """Stage that always fails."""

    def __init__(self, name="fail"):
        from contextcore_coyote.config import CoyoteConfig

        self.config = CoyoteConfig(contextcore_enabled=False, auto_proceed=True)
        self.name = name
        self.description = f"Fail stage: {name}"

    def execute(self, ctx: StageContext) -> StageResult:
        raise RuntimeError(f"{self.name} deliberately failed")


class SkipStage(Stage):
    """Stage that always skips."""

    def __init__(self, name="skip"):
        from contextcore_coyote.config import CoyoteConfig

        self.config = CoyoteConfig(contextcore_enabled=False, auto_proceed=True)
        self.name = name
        self.description = f"Skip stage: {name}"

    def should_skip(self, ctx: StageContext) -> bool:
        return True

    def execute(self, ctx: StageContext) -> StageResult:
        return StageResult(
            stage_name=self.name,
            status=StageStatus.COMPLETED,
            started_at=datetime.now(),
        )


@pytest.fixture
def auto_config():
    """Set global config with auto_proceed=True for tests."""
    config = CoyoteConfig(auto_proceed=True, contextcore_enabled=False)
    config_module._config = config
    return config


# --- Pipeline construction ---


class TestPipelineConstruction:
    """Test Pipeline construction and stage management."""

    def test_empty_pipeline(self, auto_config):
        pipe = Pipeline()
        assert pipe.stages == []

    def test_with_stages(self, auto_config):
        stages = [PassStage("a"), PassStage("b")]
        pipe = Pipeline(stages=stages)
        assert len(pipe.stages) == 2

    def test_add_stage(self, auto_config):
        pipe = Pipeline()
        pipe.add_stage(PassStage("a"))
        assert len(pipe.stages) == 1
        assert pipe.stages[0].name == "a"

    def test_add_stage_chaining(self, auto_config):
        pipe = Pipeline()
        result = pipe.add_stage(PassStage("a")).add_stage(PassStage("b"))
        assert result is pipe
        assert len(pipe.stages) == 2

    def test_insert_stage(self, auto_config):
        pipe = Pipeline(stages=[PassStage("a"), PassStage("c")])
        pipe.insert_stage(1, PassStage("b"))
        assert [s.name for s in pipe.stages] == ["a", "b", "c"]

    def test_insert_stage_chaining(self, auto_config):
        pipe = Pipeline(stages=[PassStage("a")])
        result = pipe.insert_stage(0, PassStage("b"))
        assert result is pipe


# --- Pipeline.run() ---


class TestPipelineRun:
    """Test Pipeline execution."""

    def test_run_all_stages(self, auto_config, sample_incident):
        pipe = Pipeline(stages=[PassStage("a"), PassStage("b"), PassStage("c")])
        result = pipe.run(sample_incident)
        assert result.status == "completed"
        assert len(result.stage_results) == 3
        assert result.completed_at is not None

    def test_run_empty_pipeline(self, auto_config, sample_incident):
        pipe = Pipeline()
        result = pipe.run(sample_incident)
        assert result.status == "completed"
        assert len(result.stage_results) == 0

    def test_run_stops_on_failure(self, auto_config, sample_incident):
        pipe = Pipeline(
            stages=[PassStage("a"), FailStage("b"), PassStage("c")]
        )
        result = pipe.run(sample_incident)
        assert result.status == "failed"
        assert len(result.stage_results) == 2  # a completed, b failed, c never ran

    def test_run_skipped_stages(self, auto_config, sample_incident):
        pipe = Pipeline(
            stages=[PassStage("a"), SkipStage("b"), PassStage("c")]
        )
        result = pipe.run(sample_incident)
        assert result.status == "completed"
        assert len(result.stage_results) == 3
        assert result.stage_results[1].status == StageStatus.SKIPPED

    def test_run_on_stage_complete_callback(self, auto_config, sample_incident):
        callback = MagicMock()
        pipe = Pipeline(stages=[PassStage("a")], on_stage_complete=callback)
        pipe.run(sample_incident)
        callback.assert_called_once()

    def test_run_collects_results_in_context(self, auto_config, sample_incident):
        """Verify results are passed to subsequent stages via context."""
        received_previous = []

        class InspectStage(Stage):
            def __init__(self, name):
                self.config = CoyoteConfig(contextcore_enabled=False, auto_proceed=True)
                self.name = name
                self.description = name

            def execute(self, ctx: StageContext) -> StageResult:
                received_previous.append(len(ctx.previous_results))
                return StageResult(
                    stage_name=self.name,
                    status=StageStatus.COMPLETED,
                    started_at=datetime.now(),
                )

        pipe = Pipeline(stages=[InspectStage("a"), InspectStage("b"), InspectStage("c")])
        pipe.run(sample_incident)
        assert received_previous == [0, 1, 2]


# --- PipelineResult ---


class TestPipelineResult:
    """Test PipelineResult properties."""

    def test_successful_all_completed(self, sample_incident):
        result = PipelineResult(
            incident=sample_incident,
            stage_results=[
                StageResult(stage_name="a", status=StageStatus.COMPLETED, started_at=datetime.now()),
                StageResult(stage_name="b", status=StageStatus.COMPLETED, started_at=datetime.now()),
            ],
        )
        assert result.successful is True

    def test_successful_with_skipped(self, sample_incident):
        result = PipelineResult(
            incident=sample_incident,
            stage_results=[
                StageResult(stage_name="a", status=StageStatus.COMPLETED, started_at=datetime.now()),
                StageResult(stage_name="b", status=StageStatus.SKIPPED, started_at=datetime.now()),
            ],
        )
        assert result.successful is True

    def test_not_successful_with_failure(self, sample_incident):
        result = PipelineResult(
            incident=sample_incident,
            stage_results=[
                StageResult(stage_name="a", status=StageStatus.COMPLETED, started_at=datetime.now()),
                StageResult(stage_name="b", status=StageStatus.FAILED, started_at=datetime.now()),
            ],
        )
        assert result.successful is False

    def test_successful_empty(self, sample_incident):
        result = PipelineResult(incident=sample_incident)
        assert result.successful is True

    def test_failed_stage_returns_first_failure(self, sample_incident):
        fail1 = StageResult(stage_name="b", status=StageStatus.FAILED, started_at=datetime.now())
        result = PipelineResult(
            incident=sample_incident,
            stage_results=[
                StageResult(stage_name="a", status=StageStatus.COMPLETED, started_at=datetime.now()),
                fail1,
            ],
        )
        assert result.failed_stage is fail1

    def test_failed_stage_none_when_all_pass(self, sample_incident):
        result = PipelineResult(
            incident=sample_incident,
            stage_results=[
                StageResult(stage_name="a", status=StageStatus.COMPLETED, started_at=datetime.now()),
            ],
        )
        assert result.failed_stage is None

    def test_duration_seconds(self, sample_incident):
        now = datetime.now()
        result = PipelineResult(
            incident=sample_incident,
            started_at=now,
            completed_at=now + __import__("datetime").timedelta(seconds=30),
        )
        assert result.duration_seconds == pytest.approx(30.0)

    def test_duration_seconds_none_when_running(self, sample_incident):
        result = PipelineResult(incident=sample_incident)
        assert result.duration_seconds is None

    def test_summary_format(self, sample_incident):
        result = PipelineResult(
            incident=sample_incident,
            stage_results=[
                StageResult(
                    stage_name="investigate",
                    status=StageStatus.COMPLETED,
                    started_at=datetime.now(),
                    summary="Found root cause",
                ),
                StageResult(
                    stage_name="design",
                    status=StageStatus.FAILED,
                    started_at=datetime.now(),
                    summary="Design failed",
                ),
            ],
            status="failed",
        )
        s = result.summary()
        assert sample_incident.id in s
        assert "investigate" in s
        assert "design" in s
        assert "failed" in s.lower()

    def test_summary_status_icons(self, sample_incident):
        result = PipelineResult(
            incident=sample_incident,
            stage_results=[
                StageResult(stage_name="a", status=StageStatus.COMPLETED, started_at=datetime.now()),
                StageResult(stage_name="b", status=StageStatus.FAILED, started_at=datetime.now()),
                StageResult(stage_name="c", status=StageStatus.SKIPPED, started_at=datetime.now()),
            ],
        )
        s = result.summary()
        assert "\u2713" in s  # checkmark for completed
        assert "\u2717" in s  # x for failed
        assert "\u25CB" in s  # circle for skipped
