"""Discovery CLI commands."""

from __future__ import annotations

import click


@click.group("discovery")
def discovery_group() -> None:
    """Agent discovery commands."""


@discovery_group.command("info")
def discovery_info() -> None:
    """Show discovery command status."""
    click.echo("Discovery CLI is available.")
    click.echo("Additional discovery commands will be added in a future release.")


__all__ = ["discovery_group"]
