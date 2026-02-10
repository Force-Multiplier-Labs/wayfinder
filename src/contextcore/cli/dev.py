"""ContextCore CLI - Dev mode commands (local auto-repair)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import click


@click.group()
def dev():
    """Developer mode utilities (local, no infrastructure required)."""
    pass


@dev.command("repair")
@click.option(
    "--error", "-e",
    type=str,
    default=None,
    help="Error message to investigate and fix.",
)
@click.option(
    "--log-file", "-f",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to file containing error output.",
)
@click.option(
    "--severity", "-s",
    type=click.Choice(["LOW", "MEDIUM", "HIGH", "CRITICAL"], case_sensitive=False),
    default="HIGH",
    help="Incident severity (default: HIGH).",
)
@click.option(
    "--auto-apply",
    is_flag=True,
    default=False,
    help="Save generated code to generated/coyote/.",
)
@click.option(
    "--output", "-o",
    "output_format",
    type=click.Choice(["text", "json"], case_sensitive=False),
    default="text",
    help="Output format (default: text).",
)
def dev_repair(
    error: Optional[str],
    log_file: Optional[str],
    severity: str,
    auto_apply: bool,
    output_format: str,
):
    """Run Coyote incident pipeline on an error (no Rabbit/HTTP required).

    Provide an error message directly or point to a log file:

      contextcore dev repair --error "NullPointerException in UserService"

      contextcore dev repair --log-file /tmp/error.log --severity critical --auto-apply
    """
    # Resolve error message from --error or --log-file
    if error and log_file:
        click.echo("Error: provide --error or --log-file, not both.", err=True)
        sys.exit(1)
    elif log_file:
        error_message = Path(log_file).read_text().strip()
    elif error:
        error_message = error
    else:
        click.echo("Error: provide --error or --log-file.", err=True)
        sys.exit(1)

    if not error_message:
        click.echo("Error: empty error message.", err=True)
        sys.exit(1)

    # Lazy import — scripts/ is not in the package, so add to path
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "dev_repair",
        Path(__file__).resolve().parents[3] / "scripts" / "dev_repair.py",
    )
    if spec is None or spec.loader is None:
        click.echo("Error: scripts/dev_repair.py not found.", err=True)
        sys.exit(1)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    if output_format == "text":
        click.echo(f"Coyote Repair: severity={severity}")
        click.echo(f"Error: {error_message[:200]}{'...' if len(error_message) > 200 else ''}")
        click.echo()

    result = mod.repair_from_error(
        error_message=error_message,
        severity=severity,
        auto_apply=auto_apply,
    )

    if output_format == "json":
        click.echo(json.dumps(result, indent=2, default=str))
        return

    # Text output
    if result["success"]:
        click.echo(f"Pipeline completed successfully (run_id: {result['run_id']})")
    else:
        click.echo(f"Pipeline failed: {result.get('error', 'unknown')}")

    click.echo()
    for stage in result.get("stages", []):
        status_icon = "+" if stage["status"] == "completed" else "-"
        click.echo(f"  [{status_icon}] {stage['name']}: {stage['summary'][:80]}")

    if result.get("code_changes_count", 0) > 0:
        click.echo()
        click.echo(f"Code changes: {result['code_changes_count']} file(s)")
        if result.get("generated_dir"):
            click.echo(f"Generated at: {result['generated_dir']}")
        elif not auto_apply:
            click.echo("Tip: use --auto-apply to save generated code to disk.")


@dev.command("callback-demo")
def dev_callback_demo():
    """Show how to use coyote_repair_callback with PrimeContractorWorkflow."""
    click.echo(
        "To enable auto-repair during Beaver/Prime Contractor workflows:\n"
        "\n"
        "  from scripts.dev_repair import coyote_repair_callback\n"
        "  from scripts.prime_contractor.workflow import PrimeContractorWorkflow\n"
        "\n"
        "  workflow = PrimeContractorWorkflow(\n"
        '      on_checkpoint_failed=coyote_repair_callback,\n'
        "  )\n"
        "  workflow.run()\n"
        "\n"
        "When a checkpoint fails, Coyote will automatically investigate\n"
        "the error and attempt to generate a fix.\n"
    )
