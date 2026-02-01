"""ContextCore CLI - Project metrics commands."""

import json
import signal
import sys
import time

import click


def _get_tracker(project: str):
    """Get or create tracker instance."""
    from contextcore.tracker import TaskTracker
    return TaskTracker(project=project)


@click.group()
def metrics():
    """View derived project metrics from task spans.

    Metrics include:
    - Lead time (creation to completion)
    - Cycle time (in_progress to completion)
    - Throughput (tasks completed per period)
    - WIP (work in progress count)
    - Velocity (story points per sprint)
    """
    pass


@metrics.command("summary")
@click.option("--project", "-p", envvar="CONTEXTCORE_PROJECT", default="default", help="Project ID")
@click.option("--days", "-d", type=int, default=30, help="Days to analyze")
@click.option("--format", "output_format", type=click.Choice(["text", "json"]), default="text")
def metrics_summary(project: str, days: int, output_format: str):
    """Show summary metrics for a project.

    Example:
        contextcore metrics summary --project my-project --days 14
    """
    from contextcore.metrics import TaskMetrics

    metrics_collector = TaskMetrics(project=project)
    summary = metrics_collector.get_summary(days=days)

    if output_format == "json":
        click.echo(json.dumps(summary, indent=2))
    else:
        click.echo(f"Project Metrics: {project}")
        click.echo(f"  Period: last {days} days")
        click.echo()
        click.echo("Throughput:")
        click.echo(f"  Tasks completed: {summary['tasks_completed']}")
        click.echo(f"  Story points: {summary['story_points_completed']}")
        click.echo()
        click.echo("Current State:")
        click.echo(f"  Active tasks: {summary['tasks_active']}")
        click.echo(f"  Work in progress: {summary['wip']}")
        click.echo(f"  Blocked: {summary['blocked']}")
        click.echo()
        if summary['avg_lead_time_hours']:
            click.echo(f"Lead Time (avg): {summary['avg_lead_time_hours']:.1f} hours")
        if summary['avg_cycle_time_hours']:
            click.echo(f"Cycle Time (avg): {summary['avg_cycle_time_hours']:.1f} hours")

        if summary['status_breakdown']:
            click.echo()
            click.echo("Status Breakdown:")
            for status, count in summary['status_breakdown'].items():
                click.echo(f"  {status}: {count}")


@metrics.command("wip")
@click.option("--project", "-p", envvar="CONTEXTCORE_PROJECT", default="default", help="Project ID")
def metrics_wip(project: str):
    """Show current work in progress.

    Example:
        contextcore metrics wip --project my-project
    """
    from contextcore.state import StateManager

    state = StateManager(project)
    active = state.get_active_spans()

    wip = []
    for task_id, span_state in active.items():
        if span_state.attributes.get("task.status") == "in_progress":
            wip.append({
                "id": task_id,
                "title": span_state.attributes.get("task.title", ""),
                "type": span_state.attributes.get("task.type", "task"),
                "assignee": span_state.attributes.get("task.assignee", "unassigned"),
            })

    if not wip:
        click.echo("No tasks in progress")
        return

    click.echo(f"Work in Progress ({len(wip)} tasks):")
    for task in wip:
        click.echo(f"  [{task['type']}] {task['id']}: {task['title']}")
        click.echo(f"           Assignee: {task['assignee']}")


@metrics.command("blocked")
@click.option("--project", "-p", envvar="CONTEXTCORE_PROJECT", default="default", help="Project ID")
def metrics_blocked(project: str):
    """Show currently blocked tasks.

    Example:
        contextcore metrics blocked --project my-project
    """
    from contextcore.state import StateManager

    state = StateManager(project)
    active = state.get_active_spans()

    blocked = []
    for task_id, span_state in active.items():
        if span_state.attributes.get("task.status") == "blocked":
            # Find blocking reason from events
            reason = "Unknown reason"
            for event in reversed(span_state.events):
                if event.get("name") == "task.blocked":
                    reason = event.get("attributes", {}).get("reason", reason)
                    break

            blocked.append({
                "id": task_id,
                "title": span_state.attributes.get("task.title", ""),
                "reason": reason,
                "blocked_by": span_state.attributes.get("task.blocked_by"),
            })

    if not blocked:
        click.echo("No blocked tasks")
        return

    click.echo(f"Blocked Tasks ({len(blocked)}):")
    for task in blocked:
        click.echo(f"  {task['id']}: {task['title']}")
        click.echo(f"    Reason: {task['reason']}")
        if task['blocked_by']:
            click.echo(f"    Blocked by: {task['blocked_by']}")


@metrics.command("export")
@click.option("--project", "-p", envvar="CONTEXTCORE_PROJECT", default="default", help="Project ID")
@click.option("--endpoint", envvar="OTEL_EXPORTER_OTLP_ENDPOINT", default="localhost:4317", help="OTLP endpoint")
@click.option("--interval", type=int, default=60, help="Export interval in seconds")
def metrics_export(project: str, endpoint: str, interval: int):
    """Start exporting metrics to OTLP endpoint.

    Runs continuously, exporting metrics at the specified interval.

    Example:
        contextcore metrics export --project my-project --endpoint localhost:4317
    """
    from contextcore.metrics import TaskMetrics

    click.echo(f"Starting metrics export for {project}")
    click.echo(f"  Endpoint: {endpoint}")
    click.echo(f"  Interval: {interval}s")
    click.echo("Press Ctrl+C to stop")

    metrics_collector = TaskMetrics(
        project=project,
        export_interval_ms=interval * 1000,
    )

    def shutdown(signum, frame):
        click.echo("\nShutting down...")
        metrics_collector.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Keep running until interrupted
    while True:
        time.sleep(interval)
