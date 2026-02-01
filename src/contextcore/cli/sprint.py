"""ContextCore CLI - Sprint tracking commands."""

from typing import Optional

import click


def _get_tracker(project: str):
    """Get or create tracker instance."""
    from contextcore.tracker import TaskTracker
    return TaskTracker(project=project)


@click.group()
def sprint():
    """Track sprints as parent spans."""
    pass


@sprint.command("start")
@click.option("--id", "sprint_id", required=True, help="Sprint identifier")
@click.option("--name", "-n", required=True, help="Sprint name")
@click.option("--project", "-p", envvar="CONTEXTCORE_PROJECT", default="default", help="Project ID")
@click.option("--goal", "-g", help="Sprint goal")
@click.option("--start-date", help="Start date (ISO format)")
@click.option("--end-date", help="End date (ISO format)")
@click.option("--points", type=int, help="Planned story points")
def sprint_start(
    sprint_id: str,
    name: str,
    project: str,
    goal: Optional[str],
    start_date: Optional[str],
    end_date: Optional[str],
    points: Optional[int],
):
    """Start a new sprint.

    Example:
        contextcore sprint start --id sprint-3 --name "Sprint 3" --goal "Complete auth"
    """
    from contextcore.tracker import SprintTracker

    tracker = _get_tracker(project)
    sprint_tracker = SprintTracker(tracker)

    ctx = sprint_tracker.start_sprint(
        sprint_id=sprint_id,
        name=name,
        goal=goal,
        start_date=start_date,
        end_date=end_date,
        planned_points=points,
    )

    click.echo(f"Started sprint: {sprint_id}")
    click.echo(f"  Name: {name}")
    if goal:
        click.echo(f"  Goal: {goal}")


@sprint.command("end")
@click.option("--id", "sprint_id", required=True, help="Sprint identifier")
@click.option("--project", "-p", envvar="CONTEXTCORE_PROJECT", default="default", help="Project ID")
@click.option("--points", type=int, help="Completed story points")
@click.option("--notes", help="Retrospective notes")
def sprint_end(
    sprint_id: str,
    project: str,
    points: Optional[int],
    notes: Optional[str],
):
    """End a sprint.

    Example:
        contextcore sprint end --id sprint-3 --points 21
    """
    from contextcore.tracker import SprintTracker

    tracker = _get_tracker(project)
    sprint_tracker = SprintTracker(tracker)
    sprint_tracker.end_sprint(sprint_id, completed_points=points, notes=notes)

    click.echo(f"Ended sprint: {sprint_id}")
    if points:
        click.echo(f"  Completed points: {points}")
