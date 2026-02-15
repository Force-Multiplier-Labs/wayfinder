"""
ModularPipeline — Gate-Validated Multi-Agent Pipeline.

A new pipeline runner that uses typed contracts and validation gates
between every stage. This runs ALONGSIDE the HOWL Pipeline — it does
NOT replace it.

Key differences from HOWL Pipeline (core.py):
    1. Gates between stages: Every stage output is validated before
       the next stage runs (Defense in Depth Principle 1).
    2. Typed outputs: Stages produce typed Pydantic models, not the
       god-object StageResult (Principle 2).
    3. Context fingerprinting: Integrity chain from incident through
       all stages (Principle 3).
    4. Rich diagnostics: Violations are collected and reported, not
       silently swallowed (Principle 4).
    5. Configurable gates per boundary: Different validation levels
       for different handoffs (Principle 5).

Architecture:
    ModularPipeline wraps TypedStage instances (from contracts.py)
    and inserts Gate validation at every boundary:

    [Stage 1] ──[Gate]──▶ [Stage 2] ──[Gate]──▶ [Stage 3] ──[Gate]──▶ [Output]

    Gates are configured per boundary. Use standard_gate() for most,
    strict_gate() before implementation.

Migration Strategy:
    ModularPipeline can wrap legacy HOWL stages via LegacyStageAdapter,
    converting their StageResult outputs to typed StageOutput using
    adapt_legacy_result(). This enables gradual migration one stage at a time.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from contextcore_coyote.models import Incident, StageStatus
from contextcore_coyote.pipeline.contracts import (
    ContractViolation,
    GateResult,
    StageOutput,
    adapt_legacy_result,
    fingerprint,
)
from contextcore_coyote.pipeline.gates import CompositeGate, standard_gate
from contextcore_coyote.pipeline.stage import Stage, StageContext

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pipeline Result (richer than HOWL's PipelineResult)
# ---------------------------------------------------------------------------


@dataclass
class ModularPipelineResult:
    """Result of a modular pipeline execution with full diagnostics.

    Includes gate results at every boundary for post-mortem analysis
    (Defense in Depth Principle 6: The Three Questions).
    """

    incident: Incident
    stage_outputs: List[StageOutput] = field(default_factory=list)
    gate_results: List[GateResult] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    status: str = "running"
    context_fingerprint: Optional[str] = None

    @property
    def successful(self) -> bool:
        """Whether all stages completed and all gates passed."""
        stages_ok = all(
            o.status in (StageStatus.COMPLETED, StageStatus.SKIPPED)
            for o in self.stage_outputs
        )
        gates_ok = all(g.passed for g in self.gate_results)
        return stages_ok and gates_ok

    @property
    def failed_stage(self) -> Optional[StageOutput]:
        """Get the first failed stage output, if any."""
        for output in self.stage_outputs:
            if output.status == StageStatus.FAILED:
                return output
        return None

    @property
    def failed_gate(self) -> Optional[GateResult]:
        """Get the first failed gate result, if any."""
        for result in self.gate_results:
            if not result.passed:
                return result
        return None

    @property
    def all_violations(self) -> List[ContractViolation]:
        """Collect all violations across all gates."""
        violations = []
        for result in self.gate_results:
            violations.extend(result.violations)
        return violations

    @property
    def all_warnings(self) -> List[ContractViolation]:
        """Collect all warnings across all gates."""
        warnings = []
        for result in self.gate_results:
            warnings.extend(result.warnings)
        return warnings

    @property
    def duration_seconds(self) -> Optional[float]:
        """Total pipeline duration."""
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def diagnostic_summary(self) -> str:
        """Generate a diagnostic summary answering the Three Questions (Principle 6).

        1. Was the input complete? (context fingerprint + incident)
        2. Was the contract faithfully translated? (gate results)
        3. Was the plan faithfully executed? (stage results)
        """
        lines = [
            f"═══ ModularPipeline Diagnostic for {self.incident.id} ═══",
            f"Status: {self.status}",
            f"Duration: {self.duration_seconds:.1f}s" if self.duration_seconds else "",
            f"Context Fingerprint: {self.context_fingerprint or 'not set'}",
            "",
            "── Question 1: Was the input complete? ──",
            f"  Incident: {self.incident.title}",
            f"  Fingerprint: {'✓' if self.context_fingerprint else '✗ (not set)'}",
            "",
            "── Question 2: Was the contract faithfully translated? ──",
        ]

        for gate_result in self.gate_results:
            icon = "✓" if gate_result.passed else "✗"
            lines.append(f"  {icon} {gate_result.summary()}")
            for v in gate_result.violations:
                lines.append(f"    ✗ {v}")
            for w in gate_result.warnings:
                lines.append(f"    ⚠ {w}")

        lines.append("")
        lines.append("── Question 3: Was the plan faithfully executed? ──")

        for output in self.stage_outputs:
            icon = {
                StageStatus.COMPLETED: "✓",
                StageStatus.FAILED: "✗",
                StageStatus.SKIPPED: "○",
            }.get(output.status, "?")
            duration = f"({output.duration_seconds:.1f}s)" if output.duration_seconds else ""
            lines.append(f"  {icon} {output.stage_name} {duration}")
            lines.append(f"    {output.summary}")
            if output.error:
                lines.append(f"    ERROR: {output.error}")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Legacy Stage Adapter
# ---------------------------------------------------------------------------


class LegacyStageAdapter:
    """Wraps a HOWL Stage to work with the ModularPipeline.

    This adapter lets you use existing HOWL agents (Investigator, Designer, etc.)
    in the ModularPipeline without rewriting them. It:
    1. Calls the legacy stage's run() method
    2. Converts the StageResult to a typed StageOutput via adapt_legacy_result()
    3. Sets the context fingerprint for integrity tracking

    This enables gradual migration: swap one stage at a time from legacy
    to typed, while the rest continue working via this adapter.
    """

    def __init__(self, legacy_stage: Stage) -> None:
        self.legacy_stage = legacy_stage
        self.name = legacy_stage.name

    def execute(
        self, ctx: StageContext, context_fp: Optional[str] = None
    ) -> StageOutput:
        """Execute the legacy stage and adapt the result.

        Args:
            ctx: The pipeline context.
            context_fp: Context fingerprint to set on the output.

        Returns:
            Typed StageOutput adapted from the legacy StageResult.
        """
        # Run the legacy stage
        legacy_result = self.legacy_stage.run(ctx)

        # Convert to typed output
        typed_output = adapt_legacy_result(legacy_result)

        # Set fingerprint for integrity chain
        if context_fp is not None:
            typed_output.context_fingerprint = context_fp

        return typed_output


# ---------------------------------------------------------------------------
# ModularPipeline
# ---------------------------------------------------------------------------


class ModularPipeline:
    """Gate-validated multi-agent pipeline.

    Runs stages in sequence with validation gates at every boundary.
    Supports both new TypedStage implementations and legacy HOWL
    stages via LegacyStageAdapter.

    Unlike HOWL's Pipeline, this pipeline:
    - Validates every stage output before proceeding
    - Produces typed outputs (not god-object StageResult)
    - Tracks context integrity via fingerprints
    - Collects full diagnostics for post-mortem analysis
    """

    def __init__(
        self,
        stages: Optional[List] = None,
        gate: Optional[CompositeGate] = None,
        on_stage_complete: Optional[Callable[[StageOutput], None]] = None,
        on_gate_failed: Optional[Callable[[GateResult], bool]] = None,
        on_approval_needed: Optional[Callable[[str, StageOutput], bool]] = None,
        auto_proceed: bool = True,
    ) -> None:
        """Initialize the modular pipeline.

        Args:
            stages: List of stages (LegacyStageAdapter or TypedStage-like objects).
            gate: Default gate to use between stages. If None, uses standard_gate().
            on_stage_complete: Callback after each stage completes.
            on_gate_failed: Callback when a gate fails. Return True to proceed anyway.
            on_approval_needed: Callback for human approval (returns True to proceed).
            auto_proceed: If False, requires approval between stages.
        """
        self.stages = stages or []
        self.default_gate = gate or standard_gate()
        self.on_stage_complete = on_stage_complete
        self.on_gate_failed = on_gate_failed
        self.on_approval_needed = on_approval_needed
        self.auto_proceed = auto_proceed

        # Per-boundary gate overrides: {boundary_index: gate}
        # boundary_index 0 = gate after stage 0, etc.
        self._boundary_gates: Dict[int, CompositeGate] = {}

    def set_gate_after(self, stage_index: int, gate: CompositeGate) -> "ModularPipeline":
        """Set a specific gate after a stage (overrides default).

        Args:
            stage_index: Index of the stage after which to apply this gate.
            gate: The gate to use at this boundary.

        Returns:
            Self for chaining.
        """
        self._boundary_gates[stage_index] = gate
        return self

    def add_stage(self, stage) -> "ModularPipeline":
        """Add a stage to the pipeline.

        Accepts either:
        - A LegacyStageAdapter wrapping a HOWL stage
        - A TypedStage implementation
        - A raw HOWL Stage (auto-wrapped in LegacyStageAdapter)

        Args:
            stage: Stage to add.

        Returns:
            Self for chaining.
        """
        if isinstance(stage, Stage):
            stage = LegacyStageAdapter(stage)
        self.stages.append(stage)
        return self

    def run(
        self,
        incident: Incident,
        project_root: Optional[str] = None,
        project_name: Optional[str] = None,
        project_language: Optional[str] = None,
        file_tree: Optional[str] = None,
        key_files: Optional[Dict[str, str]] = None,
        capability_index: Optional[str] = None,
    ) -> ModularPipelineResult:
        """Run the pipeline with gate validation at every boundary.

        Args:
            incident: The incident to process.
            project_root: Root directory of the codebase.
            project_name: Name of the project.
            project_language: Primary language.
            file_tree: Abbreviated directory structure.
            key_files: Dict of path -> content snippet.
            capability_index: System capability summary.

        Returns:
            ModularPipelineResult with outputs, gate results, and diagnostics.
        """
        # Create context fingerprint from incident (Principle 3)
        incident_data = f"{incident.id}:{incident.title}:{incident.description}"
        context_fp = fingerprint(incident_data)

        result = ModularPipelineResult(
            incident=incident,
            context_fingerprint=context_fp,
        )

        # Build stage context (compatible with legacy stages)
        ctx = StageContext(
            incident=incident,
            project_root=project_root,
            project_name=project_name,
            project_language=project_language,
            file_tree=file_tree,
            key_files=key_files or {},
            capability_index=capability_index,
        )

        logger.info(
            "ModularPipeline starting for %s (fingerprint: %s, stages: %d)",
            incident.id,
            context_fp,
            len(self.stages),
        )

        # Execute stages with gate validation
        for i, stage in enumerate(self.stages):
            stage_name = getattr(stage, "name", f"stage_{i}")
            logger.info("Running stage %d/%d: %s", i + 1, len(self.stages), stage_name)

            # Execute stage
            try:
                if isinstance(stage, LegacyStageAdapter):
                    output = stage.execute(ctx, context_fp=context_fp)
                elif hasattr(stage, "execute_typed"):
                    # TypedStage — build typed inputs from previous outputs
                    inputs = {o.stage_name: o for o in result.stage_outputs}
                    output = stage.execute_typed(ctx, inputs)
                    if output.context_fingerprint is None:
                        output.context_fingerprint = context_fp
                else:
                    raise TypeError(
                        f"Stage {stage_name} is not a LegacyStageAdapter or TypedStage"
                    )
            except Exception as e:
                logger.error("Stage %s raised exception: %s", stage_name, e)
                output = StageOutput(
                    stage_name=stage_name,
                    status=StageStatus.FAILED,
                    summary=f"Stage {stage_name} raised exception",
                    error=str(e),
                    context_fingerprint=context_fp,
                )

            result.stage_outputs.append(output)

            # Accumulate in legacy context for adapter compatibility
            # (so subsequent legacy stages can see previous_results)
            from contextcore_coyote.models import StageResult

            legacy_result = StageResult(
                stage_name=output.stage_name,
                status=output.status,
                started_at=output.started_at,
                completed_at=output.completed_at,
                summary=output.summary,
                details=output.details,
                error=output.error,
                **{
                    k: v
                    for k, v in output.to_legacy().items()
                    if k
                    in {
                        "root_cause",
                        "affected_code",
                        "originating_pr",
                        "fix_specification",
                        "tradeoffs",
                        "alternatives",
                        "code_changes",
                        "pr_url",
                        "tests_passed",
                        "test_output",
                        "regression_risk",
                        "lessons",
                        "prevention_steps",
                    }
                    and v is not None
                },
            )
            ctx.previous_results.append(legacy_result)

            # Notify completion
            if self.on_stage_complete:
                self.on_stage_complete(output)

            # Check for stage failure
            if output.status == StageStatus.FAILED:
                logger.error("Stage %s failed: %s", stage_name, output.error)
                result.status = "failed"
                result.completed_at = datetime.now()
                return result

            # Run validation gate (Principle 1: validate at the boundary)
            gate = self._boundary_gates.get(i, self.default_gate)
            gate_result = gate.validate(output)
            result.gate_results.append(gate_result)

            if not gate_result.passed:
                logger.error(
                    "Gate failed after stage %s: %s",
                    stage_name,
                    gate_result.summary(),
                )
                for v in gate_result.violations:
                    logger.error("  Violation: %s", v)

                # Check if we should proceed anyway
                if self.on_gate_failed:
                    if self.on_gate_failed(gate_result):
                        logger.warning("Proceeding despite gate failure (override)")
                        continue

                result.status = "gate_failed"
                result.completed_at = datetime.now()
                return result
            else:
                if gate_result.has_warnings:
                    for w in gate_result.warnings:
                        logger.warning("  Gate warning: %s", w)

            # Human approval checkpoint
            if not self.auto_proceed and output.status == StageStatus.COMPLETED:
                if self.on_approval_needed:
                    approved = self.on_approval_needed(stage_name, output)
                    if not approved:
                        logger.info("Pipeline paused after %s — awaiting approval", stage_name)
                        result.status = "awaiting_approval"
                        return result

        result.status = "completed"
        result.completed_at = datetime.now()
        logger.info(
            "ModularPipeline completed for %s (duration: %.1fs)",
            incident.id,
            result.duration_seconds or 0,
        )

        return result

    @classmethod
    def from_howl(cls, **kwargs) -> "ModularPipeline":
        """Create a ModularPipeline wrapping all HOWL stages.

        This is the migration bridge: same stages as Pipeline.full(),
        but with gate validation between each one.

        Args:
            **kwargs: Passed to ModularPipeline.__init__.

        Returns:
            ModularPipeline with all 5 HOWL stages wrapped.
        """
        from contextcore_coyote.agents import (
            Investigator,
            Designer,
            Implementer,
            Tester,
            KnowledgeAgent,
        )
        from contextcore_coyote.pipeline.gates import strict_gate

        pipeline = cls(**kwargs)
        pipeline.add_stage(Investigator())
        pipeline.add_stage(Designer())
        pipeline.add_stage(Implementer())
        pipeline.add_stage(Tester())
        pipeline.add_stage(KnowledgeAgent())

        # Use strict gate before implementation (high stakes)
        pipeline.set_gate_after(1, strict_gate())  # After design, before implement

        return pipeline
