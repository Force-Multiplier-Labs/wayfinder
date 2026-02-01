"""ContextCore CLI - Git integration commands."""

import os
import re
import sys
from typing import List, Optional

import click


# Patterns for detecting task references in commit messages
TASK_PATTERNS = [
    r"(?:implements?|closes?|fixes?|refs?|resolves?|relates?\s+to)\s+([A-Z]+-\d+)",
    r"\b([A-Z]{2,10}-\d+)\b",
    r"#(\d+)",
]

COMPLETION_PATTERNS = [
    r"(?:closes?|fixes?|resolves?)\s+([A-Z]+-\d+)",
]


def parse_task_refs(message: str) -> List[str]:
    """Extract task IDs from a commit message."""
    task_ids = []
    for pattern in TASK_PATTERNS:
        matches = re.findall(pattern, message, re.IGNORECASE)
        task_ids.extend(matches)
    return list(set(task_ids))


def parse_completion_refs(message: str) -> List[str]:
    """Extract task IDs that should be marked complete."""
    task_ids = []
    for pattern in COMPLETION_PATTERNS:
        matches = re.findall(pattern, message, re.IGNORECASE)
        task_ids.extend(matches)
    return list(set(task_ids))


def _get_tracker(project: str):
    """Get or create tracker instance."""
    from contextcore.tracker import TaskTracker
    return TaskTracker(project=project)


@click.group()
def git():
    """Git integration for automatic task linking."""
    pass


@git.command("link")
@click.option("--commit", "-c", "commit_sha", required=True, help="Commit SHA")
@click.option("--message", "-m", "commit_message", required=True, help="Commit message")
@click.option("--author", "-a", help="Commit author")
@click.option("--repo", "-r", help="Repository name")
@click.option("--project", "-p", envvar="CONTEXTCORE_PROJECT", default="default", help="Project ID")
@click.option("--auto-status/--no-auto-status", default=True, help="Auto-update task status")
def git_link(commit_sha: str, commit_message: str, author: Optional[str], repo: Optional[str], project: str, auto_status: bool):
    """Link a commit to tasks found in its message."""
    from contextcore.state import StateManager

    task_ids = parse_task_refs(commit_message)
    completion_ids = parse_completion_refs(commit_message)

    if not task_ids:
        click.echo("No task references found in commit message")
        return

    click.echo(f"Commit: {commit_sha[:8]}")
    click.echo(f"Tasks found: {', '.join(task_ids)}")

    tracker = _get_tracker(project)
    state_mgr = StateManager(project)
    active_tasks = state_mgr.get_active_spans()

    linked = []
    status_updated = []

    for task_id in task_ids:
        if task_id not in active_tasks:
            click.echo(f"  {task_id}: not found (skipping)")
            continue

        span_state = active_tasks[task_id]
        current_status = span_state.attributes.get("task.status", "unknown")

        state_mgr.add_event(task_id, "commit.linked", {
            "commit_sha": commit_sha,
            "commit_message": commit_message[:200],
            "author": author or "unknown",
            "repo": repo or "unknown",
        })
        linked.append(task_id)

        if auto_status:
            if current_status in ("todo", "backlog"):
                tracker.update_status(task_id, "in_progress")
                status_updated.append((task_id, "in_progress"))

            if task_id in completion_ids and current_status == "in_progress":
                tracker.update_status(task_id, "in_review")
                status_updated.append((task_id, "in_review"))

    if linked:
        click.echo(f"\nLinked commit to {len(linked)} task(s)")

    if status_updated:
        click.echo("Status updates:")
        for task_id, new_status in status_updated:
            click.echo(f"  {task_id} -> {new_status}")


@git.command("hook")
@click.option("--type", "hook_type", type=click.Choice(["post-commit"]), default="post-commit")
@click.option("--project", "-p", envvar="CONTEXTCORE_PROJECT", default="default", help="Project ID")
@click.option("--output", "-o", help="Output path (defaults to .git/hooks/<type>)")
def git_hook(hook_type: str, project: str, output: Optional[str]):
    """Generate a git hook script for automatic commit linking."""
    import stat

    hook_content = f'''#!/bin/bash
# ContextCore git hook - auto-link commits to tasks
COMMIT_SHA=$(git rev-parse HEAD)
COMMIT_MSG=$(git log -1 --format=%B)
AUTHOR=$(git log -1 --format=%an)
REPO=$(basename "$(git remote get-url origin 2>/dev/null || echo 'unknown')" .git)

contextcore git link \\
    --commit "$COMMIT_SHA" \\
    --message "$COMMIT_MSG" \\
    --author "$AUTHOR" \\
    --repo "$REPO" \\
    --project "{project}"
'''

    if output == "-":
        click.echo(hook_content)
        return

    if output:
        hook_path = output
    else:
        import subprocess
        result = subprocess.run(["git", "rev-parse", "--git-dir"], capture_output=True, text=True)
        if result.returncode != 0:
            click.echo("Error: Not in a git repository", err=True)
            sys.exit(1)

        git_dir = result.stdout.strip()
        hooks_dir = os.path.join(git_dir, "hooks")
        os.makedirs(hooks_dir, exist_ok=True)
        hook_path = os.path.join(hooks_dir, hook_type)

    with open(hook_path, "w") as f:
        f.write(hook_content)

    os.chmod(hook_path, os.stat(hook_path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    click.echo(f"Git hook installed: {hook_path}")


@git.command("test")
@click.option("--message", "-m", required=True, help="Commit message to test")
def git_test(message: str):
    """Test task pattern matching on a commit message."""
    task_ids = parse_task_refs(message)
    completion_ids = parse_completion_refs(message)

    click.echo(f"Message: {message}")
    click.echo()

    if task_ids:
        click.echo(f"Task references found: {', '.join(task_ids)}")
    else:
        click.echo("No task references found")

    if completion_ids:
        click.echo(f"Completion triggers: {', '.join(completion_ids)}")
