"""CLI entry point for contextcore-mole."""

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from . import __version__
from .models import TaskFile
from .parser import parse_task_file, scan_directory

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="mole")
def main() -> None:
    """Mole: Recover tasks from ContextCore task files and Tempo trace exports."""
    pass


@main.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path))
@click.option("--pattern", "-p", default="*-tasks.json", help="Glob pattern for task files")
def scan(path: Path, pattern: str) -> None:
    """Scan for task files and show summary.

    PATH can be a single JSON file or a directory to scan.
    """
    results = scan_directory(path, pattern)

    if not results:
        console.print(f"[yellow]No task files found in {path}[/yellow]")
        return

    table = Table(title="Task Files Found")
    table.add_column("File", style="cyan")
    table.add_column("Project", style="green")
    table.add_column("Tasks", justify="right")
    table.add_column("Status Breakdown", style="dim")

    total_tasks = 0
    for file_path, task_file in results:
        status_counts = task_file.status_counts()
        status_str = ", ".join(f"{s}:{c}" for s, c in sorted(status_counts.items()))
        table.add_row(
            file_path.name,
            task_file.project.id,
            str(task_file.task_count),
            status_str,
        )
        total_tasks += task_file.task_count

    console.print(table)
    console.print(f"\n[bold]Total:[/bold] {len(results)} file(s), {total_tasks} task(s)")


@main.command("list")
@click.argument("path", type=click.Path(exists=True, path_type=Path))
@click.option("--status", "-s", help="Filter by task status (e.g., cancelled, done, pending)")
@click.option("--project", "-p", help="Filter by project ID")
@click.option("--tag", "-t", help="Filter by tag")
@click.option("--type", "task_type", help="Filter by task type (epic, story, task, etc.)")
def list_tasks(
    path: Path,
    status: str | None,
    project: str | None,
    tag: str | None,
    task_type: str | None,
) -> None:
    """List tasks from task files.

    PATH can be a single JSON file or a directory.
    """
    try:
        task_file = parse_task_file(path)
    except Exception as e:
        console.print(f"[red]Error parsing {path}: {e}[/red]")
        return

    # Apply filters
    tasks = task_file.tasks

    if status:
        tasks = [t for t in tasks if t.status == status]
    if tag:
        tasks = [t for t in tasks if tag in t.tags]
    if task_type:
        tasks = [t for t in tasks if t.type == task_type]

    if not tasks:
        console.print("[yellow]No tasks match the filters[/yellow]")
        return

    # Show project header
    console.print(f"[bold]{task_file.project.name}[/bold] ({task_file.project.id})\n")

    # Build table
    table = Table()
    table.add_column("ID", style="cyan")
    table.add_column("Title")
    table.add_column("Type", style="dim")
    table.add_column("Status", style="green")
    table.add_column("Tags", style="dim")

    for task in tasks:
        # Color status
        status_style = {
            "done": "green",
            "cancelled": "red",
            "blocked": "yellow",
            "in_progress": "blue",
            "in_review": "magenta",
        }.get(task.status, "white")

        table.add_row(
            task.id,
            task.title[:50] + "..." if len(task.title) > 50 else task.title,
            task.type,
            f"[{status_style}]{task.status}[/{status_style}]",
            ", ".join(task.tags[:3]),
        )

    console.print(table)
    console.print(f"\n[dim]{len(tasks)} task(s)[/dim]")


@main.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path))
@click.argument("task_id")
def show(path: Path, task_id: str) -> None:
    """Show details for a specific task.

    PATH is the task JSON file.
    TASK_ID is the task identifier (e.g., BLC-001).
    """
    try:
        task_file = parse_task_file(path)
    except Exception as e:
        console.print(f"[red]Error parsing {path}: {e}[/red]")
        return

    # Find the task
    task = next((t for t in task_file.tasks if t.id == task_id), None)

    if not task:
        console.print(f"[red]Task '{task_id}' not found in {path}[/red]")
        console.print("\n[dim]Available tasks:[/dim]")
        for t in task_file.tasks[:10]:
            console.print(f"  {t.id}: {t.title[:40]}...")
        if len(task_file.tasks) > 10:
            console.print(f"  ... and {len(task_file.tasks) - 10} more")
        return

    # Display task details
    status_style = {
        "done": "green",
        "cancelled": "red",
        "blocked": "yellow",
        "in_progress": "blue",
        "in_review": "magenta",
    }.get(task.status, "white")

    console.print(f"[bold cyan]{task.id}[/bold cyan]: {task.title}\n")
    console.print(f"[bold]Project:[/bold] {task_file.project.name} ({task_file.project.id})")
    console.print(f"[bold]Type:[/bold] {task.type}")
    console.print(f"[bold]Status:[/bold] [{status_style}]{task.status}[/{status_style}]")

    if task.parent_id:
        console.print(f"[bold]Parent:[/bold] {task.parent_id}")

    if task.tags:
        console.print(f"[bold]Tags:[/bold] {', '.join(task.tags)}")

    if task.description:
        console.print(f"\n[bold]Description:[/bold]\n{task.description}")


@main.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path))
@click.option("--task-id", "-t", help="Export specific task by ID")
@click.option("--status", "-s", help="Export tasks with this status")
@click.option("--out", "-o", type=click.Path(path_type=Path), help="Output file (default: stdout)")
@click.option("--format", "fmt", type=click.Choice(["json", "jsonl"]), default="json", help="Output format")
def export(
    path: Path,
    task_id: str | None,
    status: str | None,
    out: Path | None,
    fmt: str,
) -> None:
    """Export tasks for re-import to ContextCore.

    PATH is the task JSON file.
    """
    import json

    try:
        task_file = parse_task_file(path)
    except Exception as e:
        console.print(f"[red]Error parsing {path}: {e}[/red]")
        return

    # Filter tasks
    tasks = task_file.tasks

    if task_id:
        tasks = [t for t in tasks if t.id == task_id]
    if status:
        tasks = [t for t in tasks if t.status == status]

    if not tasks:
        console.print("[yellow]No tasks match the filters[/yellow]")
        return

    # Build output
    if fmt == "json":
        output_data = {
            "project": task_file.project.model_dump(),
            "tasks": [t.model_dump() for t in tasks],
        }
        output_str = json.dumps(output_data, indent=2)
    else:  # jsonl
        lines = [json.dumps({"project_id": task_file.project.id, **t.model_dump()}) for t in tasks]
        output_str = "\n".join(lines)

    # Write output
    if out:
        out.write_text(output_str)
        console.print(f"[green]Exported {len(tasks)} task(s) to {out}[/green]")
    else:
        console.print(output_str)


if __name__ == "__main__":
    main()
