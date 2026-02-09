"""
Core pipeline orchestration.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, List, Optional, TYPE_CHECKING

from contextcore_coyote.models import Incident, StageResult, StageStatus
from contextcore_coyote.config import get_config
from contextcore_coyote.pipeline.stage import Stage, StageContext

if TYPE_CHECKING:
    from contextcore_coyote.agents import (
        Investigator,
        Designer,
        Implementer,
        Tester,
        KnowledgeAgent,
    )

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Result of a complete pipeline execution."""

    incident: Incident
    stage_results: List[StageResult] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    status: str = "running"

    @property
    def successful(self) -> bool:
        """Check if all stages completed successfully."""
        return all(
            r.status in (StageStatus.COMPLETED, StageStatus.SKIPPED) for r in self.stage_results
        )

    @property
    def failed_stage(self) -> Optional[StageResult]:
        """Get the first failed stage, if any."""
        for result in self.stage_results:
            if result.status == StageStatus.FAILED:
                return result
        return None

    @property
    def duration_seconds(self) -> Optional[float]:
        """Get total pipeline duration."""
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def summary(self) -> str:
        """Generate a summary of the pipeline execution."""
        lines = [
            f"Pipeline Result for {self.incident.id}",
            f"Status: {self.status}",
            f"Duration: {self.duration_seconds:.1f}s" if self.duration_seconds else "",
            "",
            "Stages:",
        ]

        for result in self.stage_results:
            status_icon = {
                StageStatus.COMPLETED: "✓",
                StageStatus.FAILED: "✗",
                StageStatus.SKIPPED: "○",
                StageStatus.PENDING: "·",
            }.get(result.status, "?")

            duration = f"({result.duration_seconds:.1f}s)" if result.duration_seconds else ""
            lines.append(f"  {status_icon} {result.stage_name} {duration}")
            if result.summary:
                lines.append(f"    {result.summary}")

        return "\n".join(lines)


class Pipeline:
    """
    Multi-stage incident resolution pipeline.

    Orchestrates the execution of stages in sequence, with optional
    human approval checkpoints between stages.
    """

    def __init__(
        self,
        stages: Optional[List[Stage]] = None,
        on_stage_complete: Optional[Callable[[StageResult], None]] = None,
        on_approval_needed: Optional[Callable[[str, StageResult], bool]] = None,
    ) -> None:
        """
        Initialize the pipeline.

        Args:
            stages: List of stages to execute (default: full pipeline)
            on_stage_complete: Callback when a stage completes
            on_approval_needed: Callback for approval checkpoints (returns True to proceed)
        """
        self.config = get_config()
        self.stages = stages or []
        self.on_stage_complete = on_stage_complete
        self.on_approval_needed = on_approval_needed

    @classmethod
    def full(cls) -> "Pipeline":
        """
        Create a full pipeline with all stages.

        Returns:
            Pipeline with investigate, design, implement, test, and learn stages
        """
        from contextcore_coyote.agents import (
            Investigator,
            Designer,
            Implementer,
            Tester,
            KnowledgeAgent,
        )

        return cls(
            stages=[
                Investigator(),
                Designer(),
                Implementer(),
                Tester(),
                KnowledgeAgent(),
            ]
        )

    @classmethod
    def investigation_only(cls) -> "Pipeline":
        """Create a pipeline that only investigates."""
        from contextcore_coyote.agents import Investigator

        return cls(stages=[Investigator()])

    @classmethod
    def design_and_implement(cls) -> "Pipeline":
        """Create a pipeline for design and implementation."""
        from contextcore_coyote.agents import Investigator, Designer, Implementer

        return cls(stages=[Investigator(), Designer(), Implementer()])

    def run(self, incident: Incident) -> PipelineResult:
        """
        Run the pipeline on an incident.

        Args:
            incident: The incident to process

        Returns:
            PipelineResult with all stage outcomes
        """
        result = PipelineResult(incident=incident)
        ctx = StageContext(incident=incident)

        logger.info(f"Starting pipeline for incident {incident.id}")

        # Execute with telemetry if enabled
        if self.config.contextcore_enabled:
            return self._run_with_telemetry(incident, result, ctx)

        return self._run_stages(result, ctx)

    def _run_stages(self, result: PipelineResult, ctx: StageContext) -> PipelineResult:
        """Execute all stages in sequence."""
        for stage in self.stages:
            logger.info(f"Running stage: {stage.name}")

            # Execute stage
            stage_result = stage.run(ctx)
            result.stage_results.append(stage_result)
            ctx.previous_results.append(stage_result)

            # Notify completion
            if self.on_stage_complete:
                self.on_stage_complete(stage_result)

            # Check for failure
            if stage_result.status == StageStatus.FAILED:
                logger.error(f"Stage {stage.name} failed: {stage_result.error}")
                result.status = "failed"
                result.completed_at = datetime.now()
                return result

            # Check for approval if not auto-proceeding
            if not self.config.auto_proceed and stage_result.status == StageStatus.COMPLETED:
                if self.on_approval_needed:
                    approved = self.on_approval_needed(stage.name, stage_result)
                    if not approved:
                        logger.info(f"Pipeline halted after {stage.name} - awaiting approval")
                        result.status = "awaiting_approval"
                        return result

        result.status = "completed"
        result.completed_at = datetime.now()
        logger.info(f"Pipeline completed for incident {ctx.incident.id}")

        return result

    def _run_with_telemetry(
        self,
        incident: Incident,
        result: PipelineResult,
        ctx: StageContext,
    ) -> PipelineResult:
        """Run pipeline with OpenTelemetry tracing."""
        try:
            from opentelemetry import trace

            tracer = trace.get_tracer("contextcore-coyote")

            with tracer.start_as_current_span(
                "coyote.pipeline",
                attributes={
                    "coyote.incident.id": incident.id,
                    "coyote.incident.title": incident.title,
                    "coyote.incident.severity": incident.severity.value,
                    "coyote.pipeline.stages": len(self.stages),
                },
            ) as span:
                result = self._run_stages(result, ctx)

                span.set_attribute("coyote.pipeline.status", result.status)
                span.set_attribute("coyote.pipeline.successful", result.successful)

                return result

        except ImportError:
            return self._run_stages(result, ctx)

    def add_stage(self, stage: Stage) -> "Pipeline":
        """
        Add a stage to the pipeline.

        Args:
            stage: Stage to add

        Returns:
            Self for chaining
        """
        self.stages.append(stage)
        return self

    def insert_stage(self, index: int, stage: Stage) -> "Pipeline":
        """
        Insert a stage at a specific position.

        Args:
            index: Position to insert at
            stage: Stage to insert

        Returns:
            Self for chaining
        """
        self.stages.insert(index, stage)
        return self
