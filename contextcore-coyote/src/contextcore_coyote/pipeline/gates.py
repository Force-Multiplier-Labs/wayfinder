"""
Gate Implementations — Validation at Every Boundary.

Concrete implementations of the Gate protocol from contracts.py.
Each gate checks a specific concern at the handoff between pipeline stages.

Defense in Depth Principle 1: Validate at the boundary, not just at the end.
Defense in Depth Principle 2: Treat each piece as potentially adversarial.
Defense in Depth Principle 3: Use checksums as circuit breakers.
Defense in Depth Principle 4: Fail loud, fail early, fail specific.

ContextCore A2A Alignment (D16, D17):
    Each gate populates `blocking`, `severity`, `evidence`, and `next_action`
    on the returned GateResult. The pipeline runner enriches with `phase`,
    `trace_id`, and `task_id` after the gate returns.

Gates are composable — a pipeline can stack multiple gates at each boundary.
Use `CompositeGate` to combine several gates into a single checkpoint.

Usage:
    from contextcore_coyote.pipeline.gates import SchemaGate, CompletenessGate, CompositeGate

    gate = CompositeGate(gates=[
        SchemaGate(),
        CompletenessGate(min_summary_length=20),
        IntegrityGate(expected_fingerprint="abc123"),
    ])
    result = gate.validate(stage_output)
    if not result.passed:
        for v in result.violations:
            print(v)
"""

from __future__ import annotations

import logging
from typing import Optional

from pydantic import ValidationError

from contextcore_coyote.models import StageStatus
from contextcore_coyote.pipeline.contracts import (
    ContractViolation,
    Evidence,
    GateResult,
    StageOutput,
    ViolationSeverity,
    STAGE_OUTPUT_REGISTRY,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# SchemaGate — Does the output match the expected Pydantic model?
# ---------------------------------------------------------------------------


class SchemaGate:
    """Validates that a stage output is the correct type and passes Pydantic validation.

    Defense in Depth Principle 2: Treat each piece as potentially adversarial.
    A stage claiming to be 'investigate' must produce an InvestigationOutput,
    not a raw StageOutput with investigation fields stuffed in.

    This gate catches:
    - Wrong output type for the stage name
    - Missing required fields
    - Invalid field values (type errors, constraint violations)

    Gate properties (D16, D17):
    - blocking: True (schema mismatch = cannot proceed)
    - severity: ERROR
    - evidence: expected type reference on failure
    - next_action: "Ensure stage produces the correct output type"
    """

    name: str = "schema"

    def validate(self, output: StageOutput) -> GateResult:
        """Validate that the output matches the expected schema for its stage_name."""
        violations: list[ContractViolation] = []
        warnings: list[ContractViolation] = []
        evidence: list[Evidence] = []

        expected_type = STAGE_OUTPUT_REGISTRY.get(output.stage_name)

        if expected_type is None:
            # Unknown stage — warn but don't fail (extensibility)
            warnings.append(
                ContractViolation(
                    gate_name=self.name,
                    stage_name=output.stage_name,
                    field="stage_name",
                    message=f"Unknown stage '{output.stage_name}' — not in STAGE_OUTPUT_REGISTRY",
                    severity=ViolationSeverity.WARNING,
                    suggestion="Register the stage output type in STAGE_OUTPUT_REGISTRY",
                )
            )
        elif not isinstance(output, expected_type):
            violations.append(
                ContractViolation(
                    gate_name=self.name,
                    stage_name=output.stage_name,
                    field="__type__",
                    message=(
                        f"Expected {expected_type.__name__} for stage '{output.stage_name}', "
                        f"got {type(output).__name__}"
                    ),
                    severity=ViolationSeverity.ERROR,
                    suggestion=f"Return {expected_type.__name__} from stage '{output.stage_name}'",
                )
            )
            evidence.append(
                Evidence(
                    type="schema",
                    ref=expected_type.__name__,
                    description=f"Expected output type for stage '{output.stage_name}'",
                )
            )

        # Verify status is not PENDING or RUNNING (shouldn't pass through a gate)
        if output.status in (StageStatus.PENDING, StageStatus.RUNNING):
            violations.append(
                ContractViolation(
                    gate_name=self.name,
                    stage_name=output.stage_name,
                    field="status",
                    message=f"Stage output has non-terminal status '{output.status.value}'",
                    severity=ViolationSeverity.ERROR,
                    suggestion="Stage must complete (COMPLETED, FAILED, SKIPPED) before passing through a gate",
                )
            )

        passed = len(violations) == 0
        return GateResult(
            passed=passed,
            gate_name=self.name,
            blocking=True,
            severity=ViolationSeverity.ERROR if not passed else ViolationSeverity.INFO,
            violations=violations,
            warnings=warnings,
            evidence=evidence,
            next_action="Ensure stage produces the correct output type" if not passed else None,
        )


# ---------------------------------------------------------------------------
# CompletenessGate — Are required fields populated with meaningful content?
# ---------------------------------------------------------------------------


class CompletenessGate:
    """Validates that stage output fields contain meaningful content.

    Defense in Depth Principle 1: Validate at the boundary.
    Pydantic catches missing fields, but can't catch empty strings or
    placeholder values. This gate ensures fields have real content.

    This gate catches:
    - Empty summary (stage didn't describe what it did)
    - Failed status without error message (silent failure)
    - Completed status without details (stage produced nothing)

    Gate properties (D16, D17):
    - blocking: True (incomplete output = cannot proceed reliably)
    - severity: ERROR
    - next_action: "Complete all required fields before proceeding"
    """

    name: str = "completeness"

    def __init__(
        self,
        min_summary_length: int = 10,
        require_details_on_success: bool = True,
    ) -> None:
        """Configure completeness thresholds.

        Args:
            min_summary_length: Minimum summary character count.
            require_details_on_success: Whether COMPLETED stages must have details.
        """
        self.min_summary_length = min_summary_length
        self.require_details_on_success = require_details_on_success

    def validate(self, output: StageOutput) -> GateResult:
        """Validate completeness of stage output fields."""
        violations: list[ContractViolation] = []
        warnings: list[ContractViolation] = []

        # Summary must be meaningful
        if len(output.summary.strip()) < self.min_summary_length:
            violations.append(
                ContractViolation(
                    gate_name=self.name,
                    stage_name=output.stage_name,
                    field="summary",
                    message=(
                        f"Summary is too short ({len(output.summary.strip())} chars, "
                        f"min {self.min_summary_length})"
                    ),
                    severity=ViolationSeverity.ERROR,
                    suggestion="Provide a meaningful summary of what the stage accomplished",
                )
            )

        # Failed stages must explain why
        if output.status == StageStatus.FAILED and not output.error:
            violations.append(
                ContractViolation(
                    gate_name=self.name,
                    stage_name=output.stage_name,
                    field="error",
                    message="Stage failed but no error message provided",
                    severity=ViolationSeverity.ERROR,
                    suggestion="Set the 'error' field when status is FAILED",
                )
            )

        # Completed stages should have details
        if (
            self.require_details_on_success
            and output.status == StageStatus.COMPLETED
            and not output.details.strip()
        ):
            warnings.append(
                ContractViolation(
                    gate_name=self.name,
                    stage_name=output.stage_name,
                    field="details",
                    message="Stage completed but has empty details",
                    severity=ViolationSeverity.WARNING,
                    suggestion="Include the full output or report in the 'details' field",
                )
            )

        # Completed stages should have timing
        if output.status == StageStatus.COMPLETED and output.completed_at is None:
            warnings.append(
                ContractViolation(
                    gate_name=self.name,
                    stage_name=output.stage_name,
                    field="completed_at",
                    message="Stage completed but completed_at is not set",
                    severity=ViolationSeverity.WARNING,
                    suggestion="Set completed_at when the stage finishes",
                )
            )

        passed = not any(v.severity == ViolationSeverity.ERROR for v in violations)
        return GateResult(
            passed=passed,
            gate_name=self.name,
            blocking=True,
            severity=ViolationSeverity.ERROR if not passed else ViolationSeverity.INFO,
            violations=violations,
            warnings=warnings,
            next_action="Complete all required fields before proceeding" if not passed else None,
        )


# ---------------------------------------------------------------------------
# IntegrityGate — Does the context fingerprint match? (Principle 3)
# ---------------------------------------------------------------------------


class IntegrityGate:
    """Validates context integrity via fingerprint chain.

    Defense in Depth Principle 3: Use checksums as circuit breakers.
    If a stage's context_fingerprint doesn't match the expected value,
    it means the stage operated on different data than expected.

    This is the "circuit breaker" — any mismatch is a hard stop.

    Gate properties (D16, D17):
    - blocking: True always (integrity = circuit breaker)
    - severity: CRITICAL (integrity failure is the most severe)
    - evidence: fingerprint comparison on failure
    - next_action: "Re-run pipeline from source — context integrity broken"
    """

    name: str = "integrity"

    def __init__(self, expected_fingerprint: Optional[str] = None) -> None:
        """Configure expected fingerprint.

        Args:
            expected_fingerprint: The fingerprint to check against.
                If None, only checks that the fingerprint exists.
        """
        self.expected_fingerprint = expected_fingerprint

    def validate(self, output: StageOutput) -> GateResult:
        """Validate context fingerprint integrity."""
        violations: list[ContractViolation] = []
        warnings: list[ContractViolation] = []
        evidence: list[Evidence] = []

        if output.context_fingerprint is None:
            if self.expected_fingerprint is not None:
                # We expect a fingerprint but stage didn't set one
                violations.append(
                    ContractViolation(
                        gate_name=self.name,
                        stage_name=output.stage_name,
                        field="context_fingerprint",
                        message="Stage did not set context_fingerprint but one is expected",
                        severity=ViolationSeverity.CRITICAL,
                        suggestion="Set context_fingerprint = fingerprint(input_data) in stage output",
                    )
                )
                evidence.append(
                    Evidence(
                        type="fingerprint",
                        ref=self.expected_fingerprint,
                        description="Expected fingerprint — stage provided none",
                    )
                )
            else:
                # No fingerprint expected or provided — just warn
                warnings.append(
                    ContractViolation(
                        gate_name=self.name,
                        stage_name=output.stage_name,
                        field="context_fingerprint",
                        message="No context fingerprint set — integrity cannot be verified",
                        severity=ViolationSeverity.WARNING,
                        suggestion="Consider setting context_fingerprint for integrity tracking",
                    )
                )
        elif self.expected_fingerprint is not None:
            if output.context_fingerprint != self.expected_fingerprint:
                violations.append(
                    ContractViolation(
                        gate_name=self.name,
                        stage_name=output.stage_name,
                        field="context_fingerprint",
                        message=(
                            f"Context fingerprint mismatch: "
                            f"expected '{self.expected_fingerprint}', "
                            f"got '{output.context_fingerprint}'"
                        ),
                        severity=ViolationSeverity.CRITICAL,
                        suggestion=(
                            "Stage is operating on stale/modified data. "
                            "Re-run the pipeline from the source."
                        ),
                    )
                )
                evidence.append(
                    Evidence(
                        type="fingerprint",
                        ref=f"expected={self.expected_fingerprint}, actual={output.context_fingerprint}",
                        description="Fingerprint mismatch — data integrity broken",
                    )
                )

        passed = not any(
            v.severity in (ViolationSeverity.ERROR, ViolationSeverity.CRITICAL)
            for v in violations
        )
        return GateResult(
            passed=passed,
            gate_name=self.name,
            blocking=True,
            severity=ViolationSeverity.CRITICAL if not passed else ViolationSeverity.INFO,
            violations=violations,
            warnings=warnings,
            evidence=evidence,
            next_action="Re-run pipeline from source — context integrity broken" if not passed else None,
        )


# ---------------------------------------------------------------------------
# QualityGate — Is the output quality above a threshold?
# ---------------------------------------------------------------------------


class QualityGate:
    """Validates output quality heuristics.

    Defense in Depth Principle 5: Design calibration guards.
    Catches outputs that technically pass schema validation but are
    low quality — too short, too generic, or missing expected content.

    This is a soft gate — violations are warnings by default, upgradable
    to errors via `strict` mode.

    Gate properties (D16, D17):
    - blocking: only in strict mode
    - severity: WARNING (or ERROR in strict mode)
    - next_action: "Improve output quality — content is below threshold"
    """

    name: str = "quality"

    def __init__(
        self,
        min_details_length: int = 50,
        strict: bool = False,
    ) -> None:
        """Configure quality thresholds.

        Args:
            min_details_length: Minimum length for the details field.
            strict: If True, quality issues are errors (hard stop).
                    If False, they're warnings (proceed with caution).
        """
        self.min_details_length = min_details_length
        self.strict = strict

    def validate(self, output: StageOutput) -> GateResult:
        """Validate output quality heuristics."""
        violations: list[ContractViolation] = []
        warnings: list[ContractViolation] = []
        severity = ViolationSeverity.ERROR if self.strict else ViolationSeverity.WARNING
        target = violations if self.strict else warnings

        # Check details length for successful stages
        if (
            output.status == StageStatus.COMPLETED
            and len(output.details.strip()) < self.min_details_length
        ):
            target.append(
                ContractViolation(
                    gate_name=self.name,
                    stage_name=output.stage_name,
                    field="details",
                    message=(
                        f"Details too short ({len(output.details.strip())} chars, "
                        f"min {self.min_details_length})"
                    ),
                    severity=severity,
                    suggestion="LLM output may be truncated or too brief for this stage",
                )
            )

        # Check for placeholder/generic content
        generic_phrases = [
            "todo",
            "placeholder",
            "not implemented",
            "lorem ipsum",
            "example text",
        ]
        details_lower = output.details.lower()
        for phrase in generic_phrases:
            if phrase in details_lower:
                target.append(
                    ContractViolation(
                        gate_name=self.name,
                        stage_name=output.stage_name,
                        field="details",
                        message=f"Details contain placeholder content: '{phrase}'",
                        severity=severity,
                        suggestion="Replace placeholder content with actual analysis",
                    )
                )

        passed = not any(v.severity == ViolationSeverity.ERROR for v in violations)
        return GateResult(
            passed=passed,
            gate_name=self.name,
            blocking=self.strict,
            severity=ViolationSeverity.ERROR if self.strict and not passed else ViolationSeverity.WARNING,
            violations=violations,
            warnings=warnings,
            next_action="Improve output quality — content is below threshold" if not passed else None,
        )


# ---------------------------------------------------------------------------
# CompositeGate — Combine multiple gates into a single checkpoint
# ---------------------------------------------------------------------------


class CompositeGate:
    """Combines multiple gates into a single validation checkpoint.

    Gates run in order. All gates run even if an earlier one fails,
    so you get the full picture of all violations at once.

    This follows Principle 4: Fail specific — give the operator all
    diagnostic information in one pass rather than requiring re-runs
    to discover each issue.

    Composite gate derives its properties from sub-gates:
    - blocking: True if any sub-gate with blocking=True failed
    - severity: worst severity from sub-gate results
    - evidence: aggregated from all sub-gates
    - next_action: from first failed blocking sub-gate
    """

    name: str = "composite"

    def __init__(self, gates: list, label: str = "composite") -> None:
        """Create a composite gate from multiple gates.

        Args:
            gates: List of Gate implementations to run in order.
            label: Human-readable label for this checkpoint.
        """
        self.gates = gates
        self.name = label

    def validate(self, output: StageOutput) -> GateResult:
        """Run all gates and aggregate results."""
        all_violations: list[ContractViolation] = []
        all_warnings: list[ContractViolation] = []
        all_evidence: list[Evidence] = []
        worst_severity = ViolationSeverity.INFO
        any_blocking_failed = False
        first_next_action: str | None = None

        _severity_rank = {
            ViolationSeverity.INFO: 0,
            ViolationSeverity.WARNING: 1,
            ViolationSeverity.ERROR: 2,
            ViolationSeverity.CRITICAL: 3,
        }

        for gate in self.gates:
            result = gate.validate(output)
            all_violations.extend(result.violations)
            all_warnings.extend(result.warnings)
            all_evidence.extend(result.evidence)

            # Track worst severity
            if _severity_rank.get(result.severity, 0) > _severity_rank.get(worst_severity, 0):
                worst_severity = result.severity

            if not result.passed:
                logger.warning(
                    "Gate '%s' failed for stage '%s': %s",
                    gate.name,
                    output.stage_name,
                    result.summary(),
                )
                if result.blocking:
                    any_blocking_failed = True
                    if first_next_action is None and result.next_action:
                        first_next_action = result.next_action

        has_errors = any(
            v.severity in (ViolationSeverity.ERROR, ViolationSeverity.CRITICAL)
            for v in all_violations
        )
        return GateResult(
            passed=not has_errors,
            gate_name=self.name,
            blocking=any_blocking_failed,
            severity=worst_severity,
            violations=all_violations,
            warnings=all_warnings,
            evidence=all_evidence,
            next_action=first_next_action,
        )


# ---------------------------------------------------------------------------
# Pre-built gate configurations
# ---------------------------------------------------------------------------


def standard_gate(strict: bool = False) -> CompositeGate:
    """Create a standard gate with schema + completeness + quality checks.

    This is the recommended default for most pipeline boundaries.

    Args:
        strict: If True, quality issues are errors. Default: False.

    Returns:
        CompositeGate combining schema, completeness, and quality validation.
    """
    return CompositeGate(
        gates=[
            SchemaGate(),
            CompletenessGate(),
            QualityGate(strict=strict),
        ],
        label="standard",
    )


def strict_gate(expected_fingerprint: Optional[str] = None) -> CompositeGate:
    """Create a strict gate with all checks including integrity.

    Use this for high-stakes boundaries (e.g., before implementation).

    Args:
        expected_fingerprint: Expected context fingerprint, or None.

    Returns:
        CompositeGate combining all validation gates in strict mode.
    """
    return CompositeGate(
        gates=[
            SchemaGate(),
            CompletenessGate(),
            QualityGate(strict=True),
            IntegrityGate(expected_fingerprint=expected_fingerprint),
        ],
        label="strict",
    )
