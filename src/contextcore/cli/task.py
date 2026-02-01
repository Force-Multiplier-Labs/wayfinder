"""ContextCore CLI - Task tracking commands."""

import os
from typing import Optional

import click


def _get_tracker(project: str):
    """Get or create tracker instance."""
    from contextcore.tracker import TaskTracker
    return TaskTracker(project=project)


@click.group()
def task():
    """Track project tasks as OpenTelemetry spans.

    Tasks are modeled as spans with full lifecycle tracking:
    - start: Creates a span
    - update: Adds span events
    - block/unblock: Sets span status
    - complete: Ends the span

    View tasks in Grafana Tempo as trace hierarchies.
    """
    pass


@task.command("start")
@click.option("--id", "task_id", required=True, help="Task identifier (e.g., PROJ-123)")
@click.option("--title", "-t", required=True, help="Task title")
@click.option("--project", "-p", envvar="CONTEXTCORE_PROJECT", default="default", help="Project ID")
@click.option(
    "--type",
    "task_type",
    type=click.Choice(["epic", "story", "task", "subtask", "bug", "spike", "incident"]),
    default="task",
    help="Task type",
)
@click.option(
    "--status",
    type=click.Choice(["backlog", "todo", "in_progress"]),
    default="todo",
    help="Initial status",
)
@click.option(
    "--priority",
    type=click.Choice(["critical", "high", "medium", "low"]),
    help="Priority level",
)
@click.option("--assignee", "-a", help="Person assigned")
@click.option("--points", type=int, help="Story points")
@click.option("--parent", help="Parent task ID (epic or story)")
@click.option("--depends-on", multiple=True, help="Task IDs this depends on")
@click.option("--label", multiple=True, help="Labels/tags")
@click.option("--url", help="External URL (Jira, GitHub, etc.)")
@click.option("--sprint", help="Sprint ID")
def task_start(
    task_id: str,
    title: str,
    project: str,
    task_type: str,
    status: str,
    priority: Optional[str],
    assignee: Optional[str],
    points: Optional[int],
    parent: Optional[str],
    depends_on: tuple,
    label: tuple,
    url: Optional[str],
    sprint: Optional[str],
):
    """Start a new task (creates a span).

    Example:
        contextcore task start --id PROJ-123 --title "Implement auth" --type story
    """
    tracker = _get_tracker(project)

    ctx = tracker.start_task(
        task_id=task_id,
        title=title,
        task_type=task_type,
        status=status,
        priority=priority,
        assignee=assignee,
        story_points=points,
        labels=list(label) if label else None,
        parent_id=parent,
        depends_on=list(depends_on) if depends_on else None,
        url=url,
        sprint_id=sprint,
    )

    click.echo(f"Started {task_type}: {task_id}")
    click.echo(f"  Title: {title}")
    click.echo(f"  Trace ID: {format(ctx.trace_id, '032x')}")
    if parent:
        click.echo(f"  Parent: {parent}")


@task.command("update")
@click.option("--id", "task_id", required=True, help="Task identifier")
@click.option("--project", "-p", envvar="CONTEXTCORE_PROJECT", default="default", help="Project ID")
@click.option(
    "--status",
    type=click.Choice(["backlog", "todo", "in_progress", "in_review", "blocked", "done"]),
    help="New status",
)
@click.option("--assignee", "-a", help="Reassign to")
@click.option("--points", type=int, help="Update story points")
def task_update(
    task_id: str,
    project: str,
    status: Optional[str],
    assignee: Optional[str],
    points: Optional[int],
):
    """Update a task (adds span events).

    Example:
        contextcore task update --id PROJ-123 --status in_progress
    """
    tracker = _get_tracker(project)

    if status:
        tracker.update_status(task_id, status)
        click.echo(f"Task {task_id}: status -> {status}")

    if assignee:
        tracker.assign_task(task_id, assignee)
        click.echo(f"Task {task_id}: assigned -> {assignee}")


@task.command("block")
@click.option("--id", "task_id", required=True, help="Task identifier")
@click.option("--project", "-p", envvar="CONTEXTCORE_PROJECT", default="default", help="Project ID")
@click.option("--reason", "-r", required=True, help="Why is it blocked?")
@click.option("--by", "blocked_by", help="Blocking task ID")
def task_block(task_id: str, project: str, reason: str, blocked_by: Optional[str]):
    """Mark task as blocked (adds event, sets ERROR status).

    Example:
        contextcore task block --id PROJ-123 --reason "Waiting on API design" --by PROJ-100
    """
    tracker = _get_tracker(project)
    tracker.block_task(task_id, reason=reason, blocked_by=blocked_by)
    click.echo(f"Task {task_id}: BLOCKED - {reason}")
    if blocked_by:
        click.echo(f"  Blocked by: {blocked_by}")


@task.command("unblock")
@click.option("--id", "task_id", required=True, help="Task identifier")
@click.option("--project", "-p", envvar="CONTEXTCORE_PROJECT", default="default", help="Project ID")
@click.option(
    "--status",
    default="in_progress",
    help="Status after unblocking",
)
def task_unblock(task_id: str, project: str, status: str):
    """Remove blocker from task.

    Example:
        contextcore task unblock --id PROJ-123
    """
    tracker = _get_tracker(project)
    tracker.unblock_task(task_id, new_status=status)
    click.echo(f"Task {task_id}: unblocked -> {status}")


@task.command("complete")
@click.option("--id", "task_id", required=True, help="Task identifier")
@click.option("--project", "-p", envvar="CONTEXTCORE_PROJECT", default="default", help="Project ID")
def task_complete(task_id: str, project: str):
    """Complete a task (ends the span).

    Example:
        contextcore task complete --id PROJ-123
    """
    tracker = _get_tracker(project)
    tracker.complete_task(task_id)
    click.echo(f"Task {task_id}: COMPLETED")


@task.command("cancel")
@click.option("--id", "task_id", required=True, help="Task identifier")
@click.option("--project", "-p", envvar="CONTEXTCORE_PROJECT", default="default", help="Project ID")
@click.option("--reason", "-r", help="Cancellation reason")
def task_cancel(task_id: str, project: str, reason: Optional[str]):
    """Cancel a task (ends span with cancelled status).

    Example:
        contextcore task cancel --id PROJ-123 --reason "No longer needed"
    """
    tracker = _get_tracker(project)
    tracker.cancel_task(task_id, reason=reason)
    click.echo(f"Task {task_id}: CANCELLED")
    if reason:
        click.echo(f"  Reason: {reason}")


@task.command("comment")
@click.option("--id", "task_id", required=True, help="Task identifier")
@click.option("--project", "-p", envvar="CONTEXTCORE_PROJECT", default="default", help="Project ID")
@click.option("--author", "-a", default=lambda: os.environ.get("USER", "unknown"), help="Comment author")
@click.option("--text", "-t", required=True, help="Comment text")
def task_comment(task_id: str, project: str, author: str, text: str):
    """Add a comment to task (as span event).

    Example:
        contextcore task comment --id PROJ-123 --text "Updated the API contract"
    """
    tracker = _get_tracker(project)
    tracker.add_comment(task_id, author=author, text=text)
    click.echo(f"Task {task_id}: comment by {author}")


@task.command("list")
@click.option("--project", "-p", envvar="CONTEXTCORE_PROJECT", default="default", help="Project ID")
@click.option("--from-state", is_flag=True, help="List tasks from local state store")
def task_list(project: str, from_state: bool):
    """List active (incomplete) tasks.

    Example:
        contextcore task list --project my-project
    """
    if from_state:
        from contextcore.state import StateManager

        state = StateManager(project)
        active_spans = state.get_active_spans()
        if not active_spans:
            click.echo("No active tasks (state)")
            return

        click.echo(f"Active tasks in {project} (state):")
        for task_id in sorted(active_spans.keys()):
            span_state = active_spans[task_id]
            status = span_state.attributes.get("task.status", "unknown")
            title = span_state.attributes.get("task.title", "")
            click.echo(f"  - {task_id} [{status}] {title}")
        return

    tracker = _get_tracker(project)
    active = tracker.get_active_tasks()

    if not active:
        click.echo("No active tasks")
        return

    click.echo(f"Active tasks in {project}:")
    for task_id in active:
        click.echo(f"  - {task_id}")
