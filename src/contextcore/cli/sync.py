"""ContextCore CLI - External sync commands."""

import sys
from typing import Optional

import click


@click.group()
def sync():
    """Sync ProjectContext from external tools."""
    pass


@sync.command()
@click.option("--project", "-p", required=True, help="Jira project key")
@click.option("--namespace", "-n", default="default", help="Target K8s namespace")
@click.option("--url", envvar="JIRA_URL", help="Jira URL")
@click.option("--token", envvar="JIRA_TOKEN", help="Jira API token")
def jira(project: str, namespace: str, url: Optional[str], token: Optional[str]):
    """Sync ProjectContext from Jira project."""
    if not url or not token:
        click.echo("JIRA_URL and JIRA_TOKEN environment variables required", err=True)
        sys.exit(1)

    click.echo(f"Syncing from Jira project {project} to namespace {namespace}")
    click.echo("(Jira sync not yet implemented)")


@sync.command()
@click.option("--repo", "-r", required=True, help="GitHub repo (owner/name)")
@click.option("--namespace", "-n", default="default", help="Target K8s namespace")
@click.option("--token", envvar="GITHUB_TOKEN", help="GitHub token")
def github(repo: str, namespace: str, token: Optional[str]):
    """Sync ProjectContext from GitHub issues."""
    if not token:
        click.echo("GITHUB_TOKEN environment variable required", err=True)
        sys.exit(1)

    click.echo(f"Syncing from GitHub repo {repo} to namespace {namespace}")
    click.echo("(GitHub sync not yet implemented)")
