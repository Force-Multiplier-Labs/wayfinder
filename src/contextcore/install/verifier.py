"""
Installation verification with telemetry emission.

Verifies ContextCore installation completeness and emits metrics, logs,
and traces representing the installation state.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Optional

from opentelemetry import metrics, trace
from opentelemetry.trace import Status, StatusCode

from contextcore.install.requirements import (
    INSTALLATION_REQUIREMENTS,
    InstallationRequirement,
    RequirementCategory,
    RequirementStatus,
    get_requirements_by_category,
)

logger = logging.getLogger(__name__)

# Initialize OTel instruments
tracer = trace.get_tracer("contextcore.install")
meter = metrics.get_meter("contextcore.install")

# =============================================================================
# Metrics
# =============================================================================
# NOTE: OTel to Prometheus metric name conversion:
# - Dots (.) become underscores (_)
# - Unit suffixes are appended: % -> _percent, 1 -> _ratio, ms -> _milliseconds
#
# OTel Name                              -> Prometheus Name
# contextcore.install.completeness (%)   -> contextcore_install_completeness_percent
# contextcore.install.requirement.status -> contextcore_install_requirement_status_ratio
# contextcore.install.category.completeness -> contextcore_install_category_completeness_percent
# contextcore.install.verification.duration -> contextcore_install_verification_duration_milliseconds
# contextcore.install.critical.met       -> contextcore_install_critical_met_ratio
# contextcore.install.critical.total     -> contextcore_install_critical_total_ratio
# =============================================================================

installation_completeness = meter.create_gauge(
    name="contextcore.install.completeness",
    description="Installation completeness percentage (0-100)",
    unit="%",
)

requirement_status = meter.create_gauge(
    name="contextcore.install.requirement.status",
    description="Individual requirement status (1=passed, 0=failed)",
    unit="1",
)

category_completeness = meter.create_gauge(
    name="contextcore.install.category.completeness",
    description="Category completeness percentage",
    unit="%",
)

verification_duration = meter.create_histogram(
    name="contextcore.install.verification.duration",
    description="Time to run verification",
    unit="ms",
)

critical_requirements_met = meter.create_gauge(
    name="contextcore.install.critical.met",
    description="Number of critical requirements met",
    unit="1",
)

critical_requirements_total = meter.create_gauge(
    name="contextcore.install.critical.total",
    description="Total number of critical requirements",
    unit="1",
)


@dataclass
class RequirementResult:
    """Result of checking a single requirement."""

    requirement: InstallationRequirement
    status: RequirementStatus
    duration_ms: float
    error: Optional[str] = None
    checked_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def passed(self) -> bool:
        return self.status == RequirementStatus.PASSED


@dataclass
class CategoryResult:
    """Aggregated results for a category."""

    category: RequirementCategory
    total: int
    passed: int
    failed: int
    skipped: int
    errors: int

    @property
    def completeness(self) -> float:
        if self.total == 0:
            return 100.0
        return (self.passed / self.total) * 100


@dataclass
class VerificationResult:
    """Complete verification result."""

    results: list[RequirementResult]
    categories: dict[RequirementCategory, CategoryResult]
    total_requirements: int
    passed_requirements: int
    failed_requirements: int
    critical_met: int
    critical_total: int
    completeness: float
    duration_ms: float
    verified_at: str
    is_complete: bool

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "verified_at": self.verified_at,
            "is_complete": self.is_complete,
            "completeness": self.completeness,
            "duration_ms": self.duration_ms,
            "total_requirements": self.total_requirements,
            "passed_requirements": self.passed_requirements,
            "failed_requirements": self.failed_requirements,
            "critical_met": self.critical_met,
            "critical_total": self.critical_total,
            "categories": {
                cat.value: {
                    "total": result.total,
                    "passed": result.passed,
                    "completeness": result.completeness,
                }
                for cat, result in self.categories.items()
            },
            "requirements": [
                {
                    "id": r.requirement.id,
                    "name": r.requirement.name,
                    "category": r.requirement.category.value,
                    "status": r.status.value,
                    "critical": r.requirement.critical,
                    "duration_ms": r.duration_ms,
                    "error": r.error,
                }
                for r in self.results
            ],
        }


class InstallationVerifier:
    """
    Verifies ContextCore installation and emits telemetry.

    Usage:
        verifier = InstallationVerifier()
        result = verifier.verify()

        # Or with specific categories
        result = verifier.verify(categories=[RequirementCategory.INFRASTRUCTURE])
    """

    def __init__(
        self,
        requirements: Optional[list[InstallationRequirement]] = None,
        emit_telemetry: bool = True,
    ):
        """
        Initialize verifier.

        Args:
            requirements: Custom requirements list (defaults to all)
            emit_telemetry: Whether to emit OTel metrics/traces
        """
        self.requirements = requirements or INSTALLATION_REQUIREMENTS
        self.emit_telemetry = emit_telemetry
        self._results_cache: dict[str, RequirementResult] = {}

    def _check_requirement(
        self, req: InstallationRequirement
    ) -> RequirementResult:
        """Check a single requirement."""
        start = time.perf_counter()
        status = RequirementStatus.FAILED
        error = None

        # Check dependencies first
        for dep_id in req.depends_on:
            if dep_id in self._results_cache:
                dep_result = self._results_cache[dep_id]
                if not dep_result.passed:
                    duration_ms = (time.perf_counter() - start) * 1000
                    return RequirementResult(
                        requirement=req,
                        status=RequirementStatus.SKIPPED,
                        duration_ms=duration_ms,
                        error=f"Dependency '{dep_id}' not met",
                    )

        try:
            if req.check():
                status = RequirementStatus.PASSED
            else:
                status = RequirementStatus.FAILED
        except Exception as e:
            status = RequirementStatus.ERROR
            error = str(e)

        duration_ms = (time.perf_counter() - start) * 1000

        result = RequirementResult(
            requirement=req,
            status=status,
            duration_ms=duration_ms,
            error=error,
        )

        self._results_cache[req.id] = result
        return result

    def _emit_requirement_telemetry(
        self, result: RequirementResult, parent_span: trace.Span
    ) -> None:
        """Emit telemetry for a single requirement check."""
        if not self.emit_telemetry:
            return

        req = result.requirement

        # Create span for this requirement check
        with tracer.start_as_current_span(
            req.span_name,
            attributes={
                "contextcore.install.requirement.id": req.id,
                "contextcore.install.requirement.name": req.name,
                "contextcore.install.requirement.category": req.category.value,
                "contextcore.install.requirement.critical": req.critical,
                "contextcore.install.requirement.status": result.status.value,
                "contextcore.install.requirement.duration_ms": result.duration_ms,
            },
        ) as span:
            if result.status == RequirementStatus.PASSED:
                span.set_status(Status(StatusCode.OK))
            elif result.status == RequirementStatus.SKIPPED:
                span.set_status(Status(StatusCode.OK, "Skipped due to dependency"))
            else:
                span.set_status(
                    Status(StatusCode.ERROR, result.error or "Requirement not met")
                )

            # Log the result
            if result.status == RequirementStatus.PASSED:
                logger.info(
                    f"Requirement passed: {req.name}",
                    extra={
                        "requirement_id": req.id,
                        "category": req.category.value,
                        "duration_ms": result.duration_ms,
                    },
                )
            elif result.status == RequirementStatus.FAILED:
                logger.warning(
                    f"Requirement failed: {req.name}",
                    extra={
                        "requirement_id": req.id,
                        "category": req.category.value,
                        "critical": req.critical,
                        "duration_ms": result.duration_ms,
                    },
                )
            elif result.status == RequirementStatus.ERROR:
                logger.error(
                    f"Requirement error: {req.name} - {result.error}",
                    extra={
                        "requirement_id": req.id,
                        "category": req.category.value,
                        "error": result.error,
                    },
                )

        # Emit metric
        requirement_status.set(
            1 if result.passed else 0,
            attributes={
                "requirement_id": req.id,
                "requirement_name": req.name,
                "category": req.category.value,
                "critical": str(req.critical).lower(),
            },
        )

    def _emit_summary_telemetry(self, result: VerificationResult) -> None:
        """Emit summary telemetry."""
        if not self.emit_telemetry:
            return

        # Overall completeness
        installation_completeness.set(
            result.completeness,
            attributes={"installation_id": "contextcore"},
        )

        # Critical requirements
        critical_requirements_met.set(
            result.critical_met,
            attributes={"installation_id": "contextcore"},
        )
        critical_requirements_total.set(
            result.critical_total,
            attributes={"installation_id": "contextcore"},
        )

        # Category completeness
        for cat, cat_result in result.categories.items():
            category_completeness.set(
                cat_result.completeness,
                attributes={
                    "installation_id": "contextcore",
                    "category": cat.value,
                },
            )

        # Verification duration
        verification_duration.record(
            result.duration_ms,
            attributes={"installation_id": "contextcore"},
        )

        # Summary log
        if result.is_complete:
            logger.info(
                f"Installation complete: {result.completeness:.1f}% "
                f"({result.passed_requirements}/{result.total_requirements} requirements)",
                extra={
                    "completeness": result.completeness,
                    "passed": result.passed_requirements,
                    "total": result.total_requirements,
                    "critical_met": result.critical_met,
                },
            )
        else:
            logger.warning(
                f"Installation incomplete: {result.completeness:.1f}% "
                f"({result.critical_met}/{result.critical_total} critical requirements met)",
                extra={
                    "completeness": result.completeness,
                    "passed": result.passed_requirements,
                    "total": result.total_requirements,
                    "critical_met": result.critical_met,
                    "critical_total": result.critical_total,
                },
            )

    def verify(
        self,
        categories: Optional[list[RequirementCategory]] = None,
    ) -> VerificationResult:
        """
        Run verification and emit telemetry.

        Args:
            categories: Specific categories to check (defaults to all)

        Returns:
            VerificationResult with all check results and metrics
        """
        start = time.perf_counter()
        self._results_cache.clear()

        # Filter requirements by category if specified
        requirements = self.requirements
        if categories:
            requirements = [r for r in requirements if r.category in categories]

        results: list[RequirementResult] = []

        # Create parent span for entire verification
        with tracer.start_as_current_span(
            "contextcore.install.verify",
            attributes={
                "contextcore.install.total_requirements": len(requirements),
                "contextcore.install.categories": (
                    [c.value for c in categories] if categories else "all"
                ),
                "gen_ai.operation.name": "install.verify",
            },
        ) as parent_span:
            # Check each requirement
            for req in requirements:
                result = self._check_requirement(req)
                results.append(result)
                self._emit_requirement_telemetry(result, parent_span)

            # Calculate category results
            category_results: dict[RequirementCategory, CategoryResult] = {}
            for cat in RequirementCategory:
                cat_reqs = [r for r in results if r.requirement.category == cat]
                if cat_reqs:
                    category_results[cat] = CategoryResult(
                        category=cat,
                        total=len(cat_reqs),
                        passed=sum(1 for r in cat_reqs if r.passed),
                        failed=sum(
                            1
                            for r in cat_reqs
                            if r.status == RequirementStatus.FAILED
                        ),
                        skipped=sum(
                            1
                            for r in cat_reqs
                            if r.status == RequirementStatus.SKIPPED
                        ),
                        errors=sum(
                            1
                            for r in cat_reqs
                            if r.status == RequirementStatus.ERROR
                        ),
                    )

            # Calculate totals
            total = len(results)
            passed = sum(1 for r in results if r.passed)
            failed = total - passed

            critical_results = [r for r in results if r.requirement.critical]
            critical_met = sum(1 for r in critical_results if r.passed)
            critical_total = len(critical_results)

            completeness = (passed / total * 100) if total > 0 else 100.0
            is_complete = critical_met == critical_total

            duration_ms = (time.perf_counter() - start) * 1000

            verification_result = VerificationResult(
                results=results,
                categories=category_results,
                total_requirements=total,
                passed_requirements=passed,
                failed_requirements=failed,
                critical_met=critical_met,
                critical_total=critical_total,
                completeness=completeness,
                duration_ms=duration_ms,
                verified_at=datetime.now(timezone.utc).isoformat(),
                is_complete=is_complete,
            )

            # Set final span status
            if is_complete:
                parent_span.set_status(Status(StatusCode.OK))
            else:
                parent_span.set_status(
                    Status(
                        StatusCode.ERROR,
                        f"Installation incomplete: {critical_met}/{critical_total} critical",
                    )
                )

            parent_span.set_attribute(
                "contextcore.install.completeness", completeness
            )
            parent_span.set_attribute("contextcore.install.is_complete", is_complete)
            parent_span.set_attribute(
                "contextcore.install.critical_met", critical_met
            )

            self._emit_summary_telemetry(verification_result)

            return verification_result

    def verify_debug(
        self,
        categories: Optional[list[RequirementCategory]] = None,
        step_all: bool = False,
        on_checkpoint: Optional[
            Callable[
                ["DebugCheckpointData", list["RequirementResult"], "CategoryResult"],
                bool,
            ]
        ] = None,
    ) -> VerificationResult:
        """
        Run verification in debug mode with checkpoints for step-by-step validation.

        Args:
            categories: Specific categories to check (defaults to all)
            step_all: If True, checkpoint after each requirement; otherwise after each category
            on_checkpoint: Callback function called at each checkpoint.
                          Receives (checkpoint_data, requirement_results, category_result).
                          Returns True to continue, False to abort.

        Returns:
            VerificationResult with all check results and metrics
        """
        from contextcore.install.debug_display import DebugCheckpoint, EmittedMetric

        start = time.perf_counter()
        self._results_cache.clear()

        # Filter requirements by category if specified
        requirements = self.requirements
        if categories:
            requirements = [r for r in requirements if r.category in categories]

        # Group requirements by category for category-level checkpoints
        requirements_by_category: dict[RequirementCategory, list[InstallationRequirement]] = {}
        for req in requirements:
            if req.category not in requirements_by_category:
                requirements_by_category[req.category] = []
            requirements_by_category[req.category].append(req)

        # Calculate total checkpoints
        if step_all:
            total_checkpoints = len(requirements)
        else:
            total_checkpoints = len(requirements_by_category)

        results: list[RequirementResult] = []
        checkpoint_number = 0
        aborted = False

        # Create parent span for entire verification
        with tracer.start_as_current_span(
            "contextcore.install.verify.debug",
            attributes={
                "contextcore.install.total_requirements": len(requirements),
                "contextcore.install.debug_mode": True,
                "contextcore.install.step_all": step_all,
                "gen_ai.operation.name": "install.verify.debug",
            },
        ) as parent_span:
            if step_all:
                # Checkpoint after each requirement
                for req in requirements:
                    result = self._check_requirement(req)
                    results.append(result)
                    self._emit_requirement_telemetry(result, parent_span)

                    checkpoint_number += 1

                    # Build emitted metrics for this requirement
                    emitted_metrics = [
                        EmittedMetric(
                            name="contextcore_install_requirement_status_ratio",
                            value=1.0 if result.passed else 0.0,
                            labels={
                                "requirement_id": req.id,
                                "requirement_name": req.name,
                                "category": req.category.value,
                                "critical": str(req.critical).lower(),
                            },
                        )
                    ]

                    if on_checkpoint:
                        checkpoint = DebugCheckpoint(
                            checkpoint_type="requirement",
                            checkpoint_number=checkpoint_number,
                            total_checkpoints=total_checkpoints,
                            requirement_result=result,
                            emitted_metrics=emitted_metrics,
                        )
                        if not on_checkpoint(checkpoint):
                            aborted = True
                            break
            else:
                # Checkpoint after each category
                for cat, cat_requirements in requirements_by_category.items():
                    cat_results: list[RequirementResult] = []

                    for req in cat_requirements:
                        result = self._check_requirement(req)
                        results.append(result)
                        cat_results.append(result)
                        self._emit_requirement_telemetry(result, parent_span)

                    checkpoint_number += 1

                    # Calculate category result
                    category_result = CategoryResult(
                        category=cat,
                        total=len(cat_results),
                        passed=sum(1 for r in cat_results if r.passed),
                        failed=sum(
                            1 for r in cat_results if r.status == RequirementStatus.FAILED
                        ),
                        skipped=sum(
                            1 for r in cat_results if r.status == RequirementStatus.SKIPPED
                        ),
                        errors=sum(
                            1 for r in cat_results if r.status == RequirementStatus.ERROR
                        ),
                    )

                    # Build emitted metrics for this category
                    emitted_metrics = []
                    for r in cat_results:
                        emitted_metrics.append(
                            EmittedMetric(
                                name="contextcore_install_requirement_status_ratio",
                                value=1.0 if r.passed else 0.0,
                                labels={
                                    "requirement_id": r.requirement.id,
                                    "requirement_name": r.requirement.name,
                                    "category": r.requirement.category.value,
                                    "critical": str(r.requirement.critical).lower(),
                                },
                            )
                        )

                    # Add category completeness metric
                    emitted_metrics.append(
                        EmittedMetric(
                            name="contextcore_install_category_completeness_percent",
                            value=category_result.completeness,
                            labels={
                                "installation_id": "contextcore",
                                "category": cat.value,
                            },
                        )
                    )

                    if on_checkpoint:
                        checkpoint = DebugCheckpoint(
                            checkpoint_type="category",
                            checkpoint_number=checkpoint_number,
                            total_checkpoints=total_checkpoints,
                            category_result=category_result,
                            category_requirements=cat_results,
                            emitted_metrics=emitted_metrics,
                        )
                        if not on_checkpoint(checkpoint):
                            aborted = True
                            break

            # Calculate final results (even if aborted, return what we have)
            category_results: dict[RequirementCategory, CategoryResult] = {}
            for cat in RequirementCategory:
                cat_reqs = [r for r in results if r.requirement.category == cat]
                if cat_reqs:
                    category_results[cat] = CategoryResult(
                        category=cat,
                        total=len(cat_reqs),
                        passed=sum(1 for r in cat_reqs if r.passed),
                        failed=sum(
                            1
                            for r in cat_reqs
                            if r.status == RequirementStatus.FAILED
                        ),
                        skipped=sum(
                            1
                            for r in cat_reqs
                            if r.status == RequirementStatus.SKIPPED
                        ),
                        errors=sum(
                            1
                            for r in cat_reqs
                            if r.status == RequirementStatus.ERROR
                        ),
                    )

            # Calculate totals
            total = len(results)
            passed = sum(1 for r in results if r.passed)
            failed = total - passed

            critical_results = [r for r in results if r.requirement.critical]
            critical_met = sum(1 for r in critical_results if r.passed)
            critical_total = len(critical_results)

            completeness = (passed / total * 100) if total > 0 else 100.0
            is_complete = critical_met == critical_total and not aborted

            duration_ms = (time.perf_counter() - start) * 1000

            verification_result = VerificationResult(
                results=results,
                categories=category_results,
                total_requirements=total,
                passed_requirements=passed,
                failed_requirements=failed,
                critical_met=critical_met,
                critical_total=critical_total,
                completeness=completeness,
                duration_ms=duration_ms,
                verified_at=datetime.now(timezone.utc).isoformat(),
                is_complete=is_complete,
            )

            # Set final span status
            if is_complete:
                parent_span.set_status(Status(StatusCode.OK))
            elif aborted:
                parent_span.set_status(
                    Status(StatusCode.ERROR, "Verification aborted by user")
                )
            else:
                parent_span.set_status(
                    Status(
                        StatusCode.ERROR,
                        f"Installation incomplete: {critical_met}/{critical_total} critical",
                    )
                )

            parent_span.set_attribute("contextcore.install.aborted", aborted)
            parent_span.set_attribute(
                "contextcore.install.completeness", completeness
            )
            parent_span.set_attribute("contextcore.install.is_complete", is_complete)
            parent_span.set_attribute(
                "contextcore.install.critical_met", critical_met
            )

            if not aborted:
                self._emit_summary_telemetry(verification_result)

            return verification_result


def verify_installation(
    categories: Optional[list[RequirementCategory]] = None,
    emit_telemetry: bool = True,
) -> VerificationResult:
    """
    Convenience function to verify installation.

    Args:
        categories: Specific categories to check (defaults to all)
        emit_telemetry: Whether to emit OTel telemetry

    Returns:
        VerificationResult with all check results
    """
    verifier = InstallationVerifier(emit_telemetry=emit_telemetry)
    return verifier.verify(categories=categories)


def get_installation_status() -> dict:
    """
    Get a quick installation status summary.

    Returns:
        Dictionary with installation status
    """
    result = verify_installation(emit_telemetry=False)
    return {
        "complete": result.is_complete,
        "completeness": f"{result.completeness:.1f}%",
        "critical": f"{result.critical_met}/{result.critical_total}",
        "total": f"{result.passed_requirements}/{result.total_requirements}",
    }
