"""Shared utilities for CLI commands."""

from typing import Any, Optional

import click
import json
import yaml


def output_data(data: Any, format: str = "yaml"):
    """Output data in specified format."""
    if format == "json":
        click.echo(json.dumps(data, indent=2))
    else:
        click.echo(yaml.dump(data, default_flow_style=False))


def echo_error(message: str):
    """Echo error message to stderr."""
    click.echo(click.style(f"Error: {message}", fg="red"), err=True)


def echo_success(message: str):
    """Echo success message."""
    click.echo(click.style(message, fg="green"))


def echo_warning(message: str):
    """Echo warning message."""
    click.echo(click.style(f"Warning: {message}", fg="yellow"))


def echo_info(message: str):
    """Echo info message."""
    click.echo(click.style(message, fg="blue"))


# Common option decorators
def project_option(default: str = "default"):
    """Common --project option."""
    return click.option(
        "--project", "-p",
        envvar="CONTEXTCORE_PROJECT",
        default=default,
        help="Project identifier"
    )


def namespace_option(default: str = "default"):
    """Common --namespace option."""
    return click.option(
        "--namespace", "-ns",
        default=default,
        help="Kubernetes namespace"
    )


def tempo_url_option():
    """Common --tempo-url option."""
    return click.option(
        "--tempo-url",
        envvar="TEMPO_URL",
        default="http://localhost:3200",
        help="Tempo URL"
    )


def output_format_option(choices=("yaml", "json"), default="yaml"):
    """Common --output format option."""
    return click.option(
        "--output", "-o",
        type=click.Choice(choices),
        default=default,
        help="Output format"
    )


def _get_tracker(project: str):
    """Get a TaskTracker instance for the given project."""
    from contextcore.tracker import TaskTracker
    return TaskTracker(project=project)


def parse_task_refs(message: str) -> list:
    """Parse task references from a message (e.g., commit message)."""
    import re
    # Match patterns like PROJ-123, #123, etc.
    patterns = [
        r'[A-Z]{2,}-\d+',  # Jira-style: PROJ-123
        r'#(\d+)',         # GitHub-style: #123
    ]

    refs = []
    for pattern in patterns:
        refs.extend(re.findall(pattern, message))

    return refs


def parse_completion_refs(message: str) -> list:
    """Parse completion indicators from a message."""
    import re
    # Match patterns like "fixes #123", "closes PROJ-456"
    pattern = r'(?:fix(?:es)?|close[sd]?|resolve[sd]?)\s+([A-Z]{2,}-\d+|#\d+)'
    return re.findall(pattern, message, re.IGNORECASE)
