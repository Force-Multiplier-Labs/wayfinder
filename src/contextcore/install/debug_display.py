"""
Debug display module for installation verification.

Provides Rich-formatted output for debug mode, showing checkpoint information,
metric comparisons, and prompts for user interaction.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

import click

if TYPE_CHECKING:
    from contextcore.install.mimir_query import MetricQueryResult
    from contextcore.install.verifier import CategoryResult, RequirementResult


@dataclass
class EmittedMetric:
    """A metric that was emitted locally."""

    name: str
    value: float
    labels: dict[str, str]


@dataclass
class DebugCheckpoint:
    """
    Information about a debug checkpoint.

    Created after each requirement or category verification, depending on mode.
    """

    checkpoint_type: str  # "requirement" or "category"
    checkpoint_number: int
    total_checkpoints: int

    # For requirement checkpoints
    requirement_result: Optional["RequirementResult"] = None

    # For category checkpoints
    category_result: Optional["CategoryResult"] = None
    category_requirements: Optional[list["RequirementResult"]] = None

    # Metrics emitted at this checkpoint
    emitted_metrics: list[EmittedMetric] = None

    def __post_init__(self):
        if self.emitted_metrics is None:
            self.emitted_metrics = []


def _format_duration(duration_ms: float) -> str:
    """Format duration in a human-readable way."""
    if duration_ms < 1:
        return f"{duration_ms * 1000:.0f}μs"
    elif duration_ms < 1000:
        return f"{duration_ms:.0f}ms"
    else:
        return f"{duration_ms / 1000:.2f}s"


def _format_status(status: str) -> str:
    """Format requirement status with color."""
    status_colors = {
        "passed": "green",
        "failed": "red",
        "skipped": "yellow",
        "error": "red",
    }
    color = status_colors.get(status, "white")
    return click.style(f"[{status.upper()}]", fg=color)


def display_separator(char: str = "─", width: int = 70) -> None:
    """Display a separator line."""
    click.echo(char * width)


def display_double_separator(width: int = 70) -> None:
    """Display a double separator line."""
    click.echo("═" * width)


def display_checkpoint_header(checkpoint: DebugCheckpoint) -> None:
    """Display the header for a checkpoint."""
    click.echo()
    display_double_separator()

    if checkpoint.checkpoint_type == "category" and checkpoint.category_result:
        category_name = checkpoint.category_result.category.value.upper()
        click.echo(
            f" CATEGORY CHECKPOINT: {click.style(category_name, fg='cyan', bold=True)} "
            f"({checkpoint.checkpoint_number}/{checkpoint.total_checkpoints})"
        )
    elif checkpoint.checkpoint_type == "requirement" and checkpoint.requirement_result:
        req = checkpoint.requirement_result.requirement
        click.echo(
            f" REQUIREMENT CHECKPOINT: {click.style(req.name, fg='cyan', bold=True)} "
            f"({checkpoint.checkpoint_number}/{checkpoint.total_checkpoints})"
        )

    display_double_separator()


def display_requirement_result(result: "RequirementResult", indent: str = "  ") -> None:
    """Display a single requirement result."""
    req = result.requirement
    status = _format_status(result.status.value)
    duration = _format_duration(result.duration_ms)

    critical_badge = click.style(" [CRITICAL]", fg="red") if req.critical else ""

    click.echo(f"{indent}{status} {req.id:<25} {duration:>8}{critical_badge}")

    if result.error:
        click.echo(f"{indent}     {click.style(result.error, fg='red')}")


def display_category_requirements(
    requirements: list["RequirementResult"],
) -> None:
    """Display all requirement results for a category."""
    click.echo()
    click.echo(click.style("Requirements Checked:", bold=True))

    for result in requirements:
        display_requirement_result(result)


def display_category_summary(category_result: "CategoryResult") -> None:
    """Display summary for a category."""
    click.echo()
    click.echo(click.style("Category Summary:", bold=True))

    total = category_result.total
    passed = category_result.passed
    pct = category_result.completeness

    pct_color = "green" if pct == 100 else "yellow" if pct >= 75 else "red"

    click.echo(f"  Passed: {passed}/{total} ({click.style(f'{pct:.0f}%', fg=pct_color)})")
    if category_result.failed > 0:
        click.echo(f"  Failed: {click.style(str(category_result.failed), fg='red')}")
    if category_result.skipped > 0:
        click.echo(f"  Skipped: {click.style(str(category_result.skipped), fg='yellow')}")
    if category_result.errors > 0:
        click.echo(f"  Errors: {click.style(str(category_result.errors), fg='red')}")


def display_emitted_metrics(metrics: list[EmittedMetric]) -> None:
    """Display metrics that were emitted locally."""
    click.echo()
    display_separator()
    click.echo(click.style(" METRICS EMITTED (Local)", bold=True))
    display_separator()

    if not metrics:
        click.echo("  No metrics emitted")
        return

    for metric in metrics:
        if metric.labels:
            label_str = ",".join(f'{k}="{v}"' for k, v in metric.labels.items())
            full_name = f"{metric.name}{{{label_str}}}"
        else:
            full_name = metric.name

        # Truncate if too long
        if len(full_name) > 60:
            full_name = full_name[:57] + "..."

        click.echo(f"  {full_name:<62} = {metric.value}")


def display_mimir_verification(
    mimir_results: list["MetricQueryResult"],
    mimir_url: str,
) -> None:
    """Display Mimir verification results."""
    click.echo()
    display_separator()
    click.echo(click.style(" MIMIR VERIFICATION", bold=True))
    display_separator()

    click.echo(f"  Querying Mimir at {mimir_url}...")
    click.echo()

    # Header
    click.echo(f"  {'Metric':<50} {'Local':>8} {'Mimir':>8} {'Match':>6}")
    click.echo(f"  {'-' * 50} {'-' * 8} {'-' * 8} {'-' * 6}")

    all_match = True
    for result in mimir_results:
        # Format metric name with labels
        if result.labels:
            label_str = ",".join(f'{k[0]}={v[:6]}' for k, v in list(result.labels.items())[:2])
            metric_display = f"{result.metric_name[:35]}...{{{label_str}}}"
        else:
            metric_display = result.metric_name[:50]

        # Format values
        expected_str = f"{result.expected_value:.1f}"

        if result.found and result.actual_value is not None:
            actual_str = f"{result.actual_value:.1f}"
        elif result.error:
            actual_str = "ERROR"
        else:
            actual_str = "N/A"

        # Match indicator
        if result.matches:
            match_str = click.style("✓", fg="green")
        elif result.found:
            match_str = click.style("✗", fg="red")
            all_match = False
        else:
            match_str = click.style("?", fg="yellow")
            all_match = False

        click.echo(f"  {metric_display:<50} {expected_str:>8} {actual_str:>8} {match_str:>6}")

        if result.error:
            click.echo(f"       {click.style(result.error, fg='red')}")

    click.echo()
    if all_match and mimir_results:
        click.echo(f"  {click.style('All metrics verified!', fg='green')} ✓")
    elif not mimir_results:
        click.echo(f"  {click.style('No metrics to verify', fg='yellow')}")
    else:
        click.echo(f"  {click.style('Some metrics did not match', fg='yellow')}")


def display_checkpoint(
    checkpoint: DebugCheckpoint,
    mimir_results: Optional[list["MetricQueryResult"]] = None,
    mimir_url: str = "http://localhost:9009",
) -> None:
    """
    Display complete checkpoint information.

    Args:
        checkpoint: The debug checkpoint to display
        mimir_results: Optional results from Mimir verification
        mimir_url: Mimir URL for display
    """
    display_checkpoint_header(checkpoint)

    if checkpoint.checkpoint_type == "category":
        if checkpoint.category_requirements:
            display_category_requirements(checkpoint.category_requirements)
        if checkpoint.category_result:
            display_category_summary(checkpoint.category_result)
    elif checkpoint.checkpoint_type == "requirement":
        if checkpoint.requirement_result:
            click.echo()
            click.echo(click.style("Requirement Details:", bold=True))
            display_requirement_result(checkpoint.requirement_result)

    # Display emitted metrics
    if checkpoint.emitted_metrics:
        display_emitted_metrics(checkpoint.emitted_metrics)

    # Display Mimir verification if available
    if mimir_results is not None:
        display_mimir_verification(mimir_results, mimir_url)


def prompt_continue() -> bool:
    """
    Prompt user to continue or abort.

    Returns:
        True to continue, False to abort
    """
    click.echo()
    display_separator()
    response = click.prompt(
        "Press Enter to continue, or 'q' to quit",
        default="",
        show_default=False,
    )
    return response.lower() != "q"


def display_debug_mode_start(total_checkpoints: int, step_all: bool) -> None:
    """Display debug mode introduction."""
    click.echo()
    display_double_separator()
    click.echo(click.style(" DEBUG MODE", fg="cyan", bold=True))
    display_double_separator()
    click.echo()

    mode = "per-requirement" if step_all else "per-category"
    click.echo(f"  Mode: {click.style(mode, bold=True)}")
    click.echo(f"  Checkpoints: {click.style(str(total_checkpoints), bold=True)}")
    click.echo()
    click.echo("  At each checkpoint, you will see:")
    click.echo("    1. Verification results")
    click.echo("    2. Metrics emitted locally")
    click.echo("    3. Mimir verification (confirms metrics received)")
    click.echo()
    click.echo("  Press Enter at each checkpoint to continue, or 'q' to quit.")
    click.echo()


def display_debug_mode_complete(
    passed: int,
    total: int,
    completeness: float,
) -> None:
    """Display debug mode completion summary."""
    click.echo()
    display_double_separator()
    click.echo(click.style(" DEBUG VERIFICATION COMPLETE", fg="cyan", bold=True))
    display_double_separator()
    click.echo()

    pct_color = "green" if completeness == 100 else "yellow" if completeness >= 75 else "red"

    click.echo(f"  Requirements Passed: {passed}/{total}")
    click.echo(f"  Completeness: {click.style(f'{completeness:.1f}%', fg=pct_color)}")
    click.echo()
