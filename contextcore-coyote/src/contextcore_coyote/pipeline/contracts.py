"""
Typed Stage Contracts — Defense in Depth for Multi-Agent Pipelines.

This module establishes typed input/output contracts for pipeline stages,
validation gates between stages, and structured error types. It implements
the foundational abstractions for the modular pipeline design:

    Defense in Depth Principles Applied:
    - P1 (Validate at Boundary): Gate protocol validates outputs at every handoff
    - P2 (Treat as Adversarial): Typed outputs prevent stages from setting arbitrary fields
    - P3 (Checksums as Circuit Breakers): Context fingerprinting for integrity chain
    - P4 (Fail Loud, Early, Specific): ContractViolation with rich diagnostics

Design Philosophy:
    The existing HOWL pipeline uses a single `StageResult` dataclass with 15+ optional
    fields covering every stage type (god object anti-pattern). This module replaces that
    with stage-specific Pydantic models that enforce structure at the boundary.

    Each stage declares what it produces (output_type) and what it requires from
    previous stages (required_inputs). Gates validate at every handoff.

Usage:
    These contracts are used by the new ModularPipeline (Step 3) alongside HOWL.
    HOWL is NOT modified. Legacy StageResult can be adapted via `adapt_legacy_result()`.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import Enum
from typing import Any, ClassVar, Optional, Protocol, runtime_checkable

from pydantic import BaseModel, Field, model_validator

from contextcore_coyote.models import StageResult, StageStatus


# ---------------------------------------------------------------------------
# Context fingerprinting (Defense in Depth Principle 3)
# ---------------------------------------------------------------------------


def fingerprint(data: str) -> str:
    """Create a sha256 fingerprint of the given data.

    Used to chain integrity from the original incident through every stage.
    Any break in the chain means a stage is operating on stale/modified data.
    """
    return hashlib.sha256(data.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Typed Stage Outputs (Defense in Depth Principle 2)
# ---------------------------------------------------------------------------


class StageOutput(BaseModel):
    """Base model for all typed stage outputs.

    Every stage produces a concrete subclass of this. The Pydantic schema
    enforces that only declared fields are set — preventing the god-object
    problem where any stage can write any field.

    Attributes:
        stage_name: Identifier matching the stage that produced this output.
        status: Final status of the stage execution.
        summary: Human-readable one-line summary of what happened.
        details: Full output text (LLM response, report, etc.).
        started_at: When the stage began execution.
        completed_at: When the stage finished execution.
        error: Error message if status is FAILED.
        context_fingerprint: Integrity chain — hash of the input this stage received.
            Downstream stages can verify they're operating on the expected data.
    """

    stage_name: str
    status: StageStatus
    summary: str
    details: str = ""
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    context_fingerprint: Optional[str] = None

    model_config = {"arbitrary_types_allowed": True}

    @property
    def succeeded(self) -> bool:
        """Whether this stage completed successfully."""
        return self.status == StageStatus.COMPLETED

    @property
    def duration_seconds(self) -> Optional[float]:
        """Stage duration in seconds, if completed."""
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def to_legacy(self) -> dict[str, Any]:
        """Convert to a dict compatible with legacy StageResult fields.

        This enables gradual migration: new contracted stages can produce
        typed outputs that the old pipeline can still consume.
        """
        return self.model_dump(exclude_none=True)


class InvestigationOutput(StageOutput):
    """Typed output from the investigation stage.

    Required fields enforce that investigation must identify a root cause
    and affected files — not just return free-form text.
    """

    stage_name: str = "investigate"
    root_cause: str = Field(
        ..., min_length=10, description="Clear explanation of what caused the error"
    )
    affected_files: list[str] = Field(
        default_factory=list, description="File paths affected by the issue"
    )
    originating_pr: Optional[str] = Field(
        default=None, description="PR reference that introduced the issue"
    )
    severity_assessment: str = Field(
        default="", description="Severity level with justification"
    )
    recommended_steps: list[str] = Field(
        default_factory=list, description="Ordered list of recommended next steps"
    )


class DesignOutput(StageOutput):
    """Typed output from the design stage.

    Required fields enforce that design must provide a concrete fix summary
    and proposed solution — not just restate the problem.
    """

    stage_name: str = "design"
    fix_summary: str = Field(
        ..., min_length=10, description="One-sentence description of the fix"
    )
    proposed_solution: str = Field(
        ..., min_length=20, description="Detailed description of the fix approach"
    )
    files_to_modify: list[str] = Field(
        default_factory=list, description="Files that need changes"
    )
    tradeoffs: list[str] = Field(default_factory=list, description="Known tradeoffs")
    alternatives: list[str] = Field(
        default_factory=list, description="Alternatives considered and why rejected"
    )
    risk_level: str = Field(default="medium", description="Low, Medium, or High")
    acceptance_criteria: list[str] = Field(
        default_factory=list, description="Criteria for accepting the fix"
    )

    @model_validator(mode="after")
    def validate_risk_level(self) -> "DesignOutput":
        """Ensure risk_level is one of the allowed values."""
        allowed = {"low", "medium", "high"}
        if self.risk_level.lower() not in allowed:
            raise ValueError(f"risk_level must be one of {allowed}, got '{self.risk_level}'")
        return self


class ImplementationOutput(StageOutput):
    """Typed output from the implementation stage."""

    stage_name: str = "implement"
    code_changes: dict[str, str] = Field(
        default_factory=dict, description="file path -> diff or new content"
    )
    new_files: list[str] = Field(
        default_factory=list, description="Newly created file paths"
    )
    modified_files: list[str] = Field(
        default_factory=list, description="Modified file paths"
    )
    pr_url: Optional[str] = Field(default=None, description="PR URL if created")


class ValidationOutput(StageOutput):
    """Typed output from the test/validation stage."""

    stage_name: str = "test"
    tests_passed: bool = Field(default=False, description="Whether all tests passed")
    test_results: list[str] = Field(
        default_factory=list, description="Individual test results"
    )
    coverage_delta: Optional[float] = Field(
        default=None, description="Change in code coverage percentage"
    )
    regression_risk: str = Field(
        default="", description="Assessment of regression risk"
    )


class LessonOutput(StageOutput):
    """Typed output from the learning/knowledge stage."""

    stage_name: str = "learn"
    lessons: list[str] = Field(
        default_factory=list, description="Lessons learned from this incident"
    )
    prevention_steps: list[str] = Field(
        default_factory=list, description="Steps to prevent recurrence"
    )
    tags: list[str] = Field(
        default_factory=list, description="Categorization tags"
    )
    confidence: float = Field(
        default=0.8, ge=0.0, le=1.0, description="Confidence in the lessons"
    )


# ---------------------------------------------------------------------------
# Validation Gates (Defense in Depth Principle 1)
# ---------------------------------------------------------------------------


class ViolationSeverity(str, Enum):
    """How severe a contract violation is."""

    ERROR = "error"  # Hard stop — cannot proceed
    WARNING = "warning"  # Proceed with caution


class Evidence(BaseModel):
    """Supporting evidence attached to a gate result.

    Provides diagnostic proof (e.g. expected type, fingerprint value)
    so failures are actionable without re-running the pipeline.
    """

    type: str = Field(description="Category of evidence (e.g. 'schema', 'fingerprint', 'quality')")
    ref: str = Field(description="Reference value (e.g. class name, hash, field path)")
    description: str = Field(default="", description="Human-readable explanation")


class ContractViolation(BaseModel):
    """A specific contract violation found by a gate.

    Rich diagnostic info so failures are loud, early, and specific (Principle 4).
    """

    gate_name: str = Field(description="Which gate caught this")
    stage_name: str = Field(description="Which stage produced the invalid output")
    field: str = Field(description="Which field failed validation")
    message: str = Field(description="Human-readable explanation of the violation")
    severity: ViolationSeverity = ViolationSeverity.ERROR
    suggestion: str = Field(
        default="", description="Suggested remediation"
    )

    def __str__(self) -> str:
        prefix = "ERROR" if self.severity == ViolationSeverity.ERROR else "WARN"
        suggestion = f" (suggestion: {self.suggestion})" if self.suggestion else ""
        return f"[{prefix}] {self.gate_name}/{self.stage_name}.{self.field}: {self.message}{suggestion}"


class GateResult(BaseModel):
    """Result of running a validation gate between stages."""

    passed: bool
    gate_name: str
    violations: list[ContractViolation] = Field(default_factory=list)
    warnings: list[ContractViolation] = Field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        """Whether there are any ERROR-severity violations."""
        return any(v.severity == ViolationSeverity.ERROR for v in self.violations)

    @property
    def has_warnings(self) -> bool:
        """Whether there are any WARNING-severity violations."""
        return bool(self.warnings)

    def summary(self) -> str:
        """Human-readable summary of gate result."""
        if self.passed:
            warning_count = len(self.warnings)
            if warning_count:
                return f"Gate '{self.gate_name}' PASSED with {warning_count} warning(s)"
            return f"Gate '{self.gate_name}' PASSED"
        error_count = len([v for v in self.violations if v.severity == ViolationSeverity.ERROR])
        return f"Gate '{self.gate_name}' FAILED with {error_count} error(s)"


@runtime_checkable
class Gate(Protocol):
    """Protocol for validation gates between pipeline stages.

    Gates implement Defense in Depth Principle 1: validate at the boundary,
    not just at the end. Each gate checks a specific concern:

    - SchemaGate: Does the output match the expected Pydantic model?
    - CompletenessGate: Are required fields populated with meaningful content?
    - QualityGate: Is the output quality above a threshold?
    - IntegrityGate: Does the context fingerprint match? (Principle 3)

    Gates are composable — a pipeline can have multiple gates at each boundary.
    """

    name: str

    def validate(self, output: StageOutput) -> GateResult:
        """Validate a stage output.

        Args:
            output: The stage output to validate.

        Returns:
            GateResult indicating pass/fail with any violations.
        """
        ...


# ---------------------------------------------------------------------------
# Stage Contract Declaration
# ---------------------------------------------------------------------------


@runtime_checkable
class TypedStage(Protocol):
    """Protocol for stages that declare typed input/output contracts.

    This is the replacement for the untyped `Stage.execute(ctx) -> StageResult`
    pattern. A TypedStage explicitly declares:

    - output_type: What Pydantic model this stage produces
    - required_inputs: What typed outputs from previous stages this stage needs

    Name reflects the functional difference from HOWL: typed Pydantic outputs
    and structured extraction vs god-object StageResult and regex parsing.

    This enables the ModularPipeline (Step 3) to:
    1. Validate that required inputs exist before running a stage
    2. Validate outputs against the declared schema after running
    3. Type-check the wiring at pipeline construction time

    Example:
        class TypedDesigner:
            name = "design"
            output_type = DesignOutput
            required_inputs = {"investigate": InvestigationOutput}

            def execute_typed(self, context, inputs):
                investigation = inputs["investigate"]  # Typed!
                # ... produce DesignOutput
    """

    name: str
    output_type: type[StageOutput]
    required_inputs: dict[str, type[StageOutput]]

    def execute_typed(
        self,
        context: Any,  # StageContext — uses Any to avoid circular import
        inputs: dict[str, StageOutput],
    ) -> StageOutput:
        """Execute the stage with typed inputs and produce typed output.

        Args:
            context: The pipeline context (incident, codebase info, etc.)
            inputs: Dict of stage_name -> typed output from required stages.
                    Keys match `required_inputs`.

        Returns:
            Typed StageOutput matching `output_type`.
        """
        ...


# ---------------------------------------------------------------------------
# Legacy Adapter (Defense in Depth Principle 6: start from the source)
# ---------------------------------------------------------------------------


def adapt_legacy_result(result: StageResult) -> StageOutput:
    """Convert a legacy StageResult into the appropriate typed StageOutput.

    This bridge function enables gradual migration. Old HOWL stages produce
    StageResult (god object). New code can convert these to typed outputs
    for use with gates and typed stages.

    The conversion is lossy — only fields relevant to the stage type are
    preserved. This is intentional: it forces explicit handling of each
    stage's contract.

    Args:
        result: Legacy StageResult from HOWL pipeline.

    Returns:
        Appropriate StageOutput subclass based on stage_name.
    """
    common = {
        "status": result.status,
        "summary": result.summary or "",
        "details": result.details or "",
        "started_at": result.started_at,
        "completed_at": result.completed_at,
        "error": result.error,
    }

    if result.stage_name == "investigate":
        return InvestigationOutput(
            root_cause=result.root_cause or "Unknown — legacy result without root_cause",
            affected_files=result.affected_code or [],
            originating_pr=result.originating_pr,
            **common,
        )

    if result.stage_name == "design":
        return DesignOutput(
            fix_summary=result.summary or "No summary — legacy result",
            proposed_solution=result.fix_specification or result.details or "No specification — legacy result",
            tradeoffs=result.tradeoffs or [],
            alternatives=result.alternatives or [],
            **common,
        )

    if result.stage_name == "implement":
        return ImplementationOutput(
            code_changes=result.code_changes or {},
            pr_url=result.pr_url,
            **common,
        )

    if result.stage_name == "test":
        return ValidationOutput(
            tests_passed=result.tests_passed or False,
            regression_risk=result.regression_risk or "",
            **common,
        )

    if result.stage_name == "learn":
        return LessonOutput(
            lessons=result.lessons or [],
            prevention_steps=result.prevention_steps or [],
            **common,
        )

    # Unknown stage — return base StageOutput
    return StageOutput(
        stage_name=result.stage_name,
        **common,
    )


# ---------------------------------------------------------------------------
# Registry of known output types
# ---------------------------------------------------------------------------

# Maps stage name → expected output type. Used by gates and pipeline
# to validate that stages produce the right type.
STAGE_OUTPUT_REGISTRY: dict[str, type[StageOutput]] = {
    "investigate": InvestigationOutput,
    "design": DesignOutput,
    "implement": ImplementationOutput,
    "test": ValidationOutput,
    "learn": LessonOutput,
}
