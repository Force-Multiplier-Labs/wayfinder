"""
Base stage definition for pipeline execution.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from contextcore_coyote.models import Incident, StageResult, StageStatus
from contextcore_coyote.config import get_config

if TYPE_CHECKING:
    from contextcore_coyote.pipeline.core import Pipeline


@dataclass
class StageContext:
    """Context passed to stages during execution."""

    incident: Incident
    previous_results: List[StageResult] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_result(self, stage_name: str) -> Optional[StageResult]:
        """Get result from a previous stage."""
        for result in self.previous_results:
            if result.stage_name == stage_name:
                return result
        return None

    @property
    def investigation_result(self) -> Optional[StageResult]:
        """Get the investigation stage result."""
        return self.get_result("investigate")

    @property
    def design_result(self) -> Optional[StageResult]:
        """Get the design stage result."""
        return self.get_result("design")

    @property
    def implementation_result(self) -> Optional[StageResult]:
        """Get the implementation stage result."""
        return self.get_result("implement")


class Stage(ABC):
    """
    Base class for pipeline stages.

    Each stage handles one step in the incident resolution pipeline.
    Subclasses implement the `execute` method with stage-specific logic.
    """

    name: str = "base"
    description: str = "Base stage"

    def __init__(self) -> None:
        self.config = get_config()

    @abstractmethod
    def execute(self, ctx: StageContext) -> StageResult:
        """
        Execute the stage.

        Args:
            ctx: Stage context with incident and previous results

        Returns:
            StageResult with execution outcome
        """
        ...

    def should_skip(self, ctx: StageContext) -> bool:
        """
        Check if this stage should be skipped.

        Override to implement skip logic based on context.

        Args:
            ctx: Stage context

        Returns:
            True if stage should be skipped
        """
        return False

    def run(self, ctx: StageContext) -> StageResult:
        """
        Run the stage with timing and error handling.

        Args:
            ctx: Stage context

        Returns:
            StageResult with execution outcome
        """
        started_at = datetime.now()

        # Check if should skip
        if self.should_skip(ctx):
            return StageResult(
                stage_name=self.name,
                status=StageStatus.SKIPPED,
                started_at=started_at,
                completed_at=datetime.now(),
                summary=f"Stage {self.name} skipped",
            )

        try:
            # Execute with telemetry if enabled
            if self.config.contextcore_enabled:
                result = self._execute_with_telemetry(ctx, started_at)
            else:
                result = self.execute(ctx)
                result.started_at = started_at
                result.completed_at = datetime.now()

            return result

        except Exception as e:
            return StageResult(
                stage_name=self.name,
                status=StageStatus.FAILED,
                started_at=started_at,
                completed_at=datetime.now(),
                summary=f"Stage {self.name} failed",
                error=str(e),
            )

    def _execute_with_telemetry(self, ctx: StageContext, started_at: datetime) -> StageResult:
        """Execute stage with OpenTelemetry tracing."""
        try:
            from opentelemetry import trace

            tracer = trace.get_tracer("contextcore-coyote")

            with tracer.start_as_current_span(
                f"coyote.stage.{self.name}",
                attributes={
                    "coyote.stage.name": self.name,
                    "coyote.incident.id": ctx.incident.id,
                    "coyote.incident.severity": ctx.incident.severity.value,
                },
            ) as span:
                result = self.execute(ctx)
                result.started_at = started_at
                result.completed_at = datetime.now()

                span.set_attribute("coyote.stage.status", result.status.value)
                if result.error:
                    span.set_attribute("coyote.stage.error", result.error)

                return result

        except ImportError:
            # OTel not available, execute without tracing
            result = self.execute(ctx)
            result.started_at = started_at
            result.completed_at = datetime.now()
            return result

    def get_prompt(self, ctx: StageContext) -> str:
        """
        Get the LLM prompt for this stage.

        Override to customize the prompt.

        Args:
            ctx: Stage context

        Returns:
            Prompt string
        """
        return f"Process incident: {ctx.incident.title}"

    def call_llm(self, prompt: str) -> str:
        """
        Call the configured LLM.

        Args:
            prompt: Prompt to send

        Returns:
            LLM response
        """
        if self.config.llm_provider == "anthropic":
            return self._call_anthropic(prompt)
        elif self.config.llm_provider == "openai":
            return self._call_openai(prompt)
        else:
            raise ValueError(f"Unknown LLM provider: {self.config.llm_provider}")

    def _call_anthropic(self, prompt: str) -> str:
        """Call Anthropic API."""
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=self.config.anthropic_api_key)
            message = client.messages.create(
                model=self.config.llm_model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            return message.content[0].text

        except ImportError:
            raise RuntimeError("anthropic package not installed. Run: pip install anthropic")

    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API."""
        try:
            import openai

            client = openai.OpenAI(api_key=self.config.openai_api_key)
            response = client.chat.completions.create(
                model=self.config.llm_model,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content

        except ImportError:
            raise RuntimeError("openai package not installed. Run: pip install openai")
