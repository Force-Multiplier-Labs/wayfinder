"""ContextCore CLI - Operational commands."""

import sys
from typing import Optional

import click


@click.group()
def ops():
    """Operational commands for health, validation, and backup.

    \b
    Commands:
        doctor      Preflight system checks
        health      Component health status
        smoke-test  Full stack validation
        backup      Export state to backup
        restore     Restore from backup
        backups     List available backups
    """
    pass


@ops.command("doctor")
@click.option("--no-ports", is_flag=True, help="Skip port availability checks")
@click.option("--no-docker", is_flag=True, help="Skip Docker daemon check")
def ops_doctor(no_ports: bool, no_docker: bool):
    """Run preflight system checks.

    Validates system readiness before deployment:
    - Required tools (docker, python)
    - Docker daemon running
    - Port availability
    - Disk space
    - Data directories

    \b
    Examples:
        contextcore ops doctor
        contextcore ops doctor --no-ports
    """
    from contextcore.ops import doctor
    from contextcore.ops.doctor import CheckStatus

    click.echo(click.style("=== Preflight Check ===", fg="cyan", bold=True))
    click.echo()

    result = doctor(
        check_ports=not no_ports,
        check_docker=not no_docker,
    )

    for check in result.checks:
        if check.status == CheckStatus.PASS:
            icon = click.style("[PASS]", fg="green")
        elif check.status == CheckStatus.WARN:
            icon = click.style("[WARN]", fg="yellow")
        else:
            icon = click.style("[FAIL]", fg="red")

        click.echo(f"  {icon} {check.message}")
        if check.details:
            click.echo(f"      {check.details}")

    click.echo()
    if result.ready:
        click.echo(click.style("=== System Ready ===", fg="green", bold=True))
    else:
        click.echo(click.style(f"=== {result.failed} issue(s) found ===", fg="red", bold=True))
        sys.exit(1)


@ops.command("health")
def ops_health():
    """Show one-line health status per component.

    Checks health of:
    - Grafana
    - Tempo
    - Mimir
    - Loki
    - OTLP endpoints

    \b
    Examples:
        contextcore ops health
    """
    from contextcore.ops import health_check, HealthStatus

    click.echo(click.style("=== Component Health ===", fg="cyan", bold=True))

    result = health_check()

    for component in result.components:
        if component.status == HealthStatus.HEALTHY:
            icon = click.style("[OK]", fg="green")
            status = "Ready"
        elif component.status == HealthStatus.UNHEALTHY:
            icon = click.style("[ERR]", fg="red")
            status = component.message
        else:
            icon = click.style("[???]", fg="yellow")
            status = component.message

        name = f"{component.name}:".ljust(14)
        click.echo(f"  {icon} {name} {status}")

    click.echo()
    if result.all_healthy:
        click.echo(click.style(f"All {len(result.components)} components healthy", fg="green"))
    else:
        click.echo(click.style(f"{result.unhealthy_count}/{len(result.components)} components unhealthy", fg="red"))


@ops.command("smoke-test")
def ops_smoke_test():
    """Validate entire stack is working after deployment.

    Runs comprehensive tests:
    1. Component health (Grafana, Tempo, Mimir, Loki)
    2. Grafana datasources configured
    3. Grafana dashboards provisioned
    4. ContextCore CLI available
    5. OTLP endpoint accessible

    \b
    Examples:
        contextcore ops smoke-test
    """
    from contextcore.ops import smoke_test
    from contextcore.ops.smoke_test import TestStatus

    click.echo(click.style("=== Smoke Test ===", fg="cyan", bold=True))
    click.echo()

    suite = smoke_test()

    for result in suite.results:
        if result.status == TestStatus.PASS:
            icon = click.style("[PASS]", fg="green")
        elif result.status == TestStatus.FAIL:
            icon = click.style("[FAIL]", fg="red")
        else:
            icon = click.style("[SKIP]", fg="yellow")

        click.echo(f"  {icon} {result.name}: {result.message}")
        if result.details:
            click.echo(f"      {result.details}")

    click.echo()
    click.echo(click.style(
        f"=== Smoke Test Complete: {suite.passed}/{len(suite.results)} passed ===",
        fg="green" if suite.all_passed else "red",
        bold=True,
    ))

    if not suite.all_passed:
        sys.exit(1)


@ops.command("backup")
@click.option("--output-dir", "-o", type=click.Path(), help="Output directory for backup")
@click.option("--grafana-url", default="http://localhost:3000", help="Grafana URL")
@click.option("--grafana-user", default="admin", help="Grafana username")
@click.option("--grafana-password", default="admin", help="Grafana password")
def ops_backup(
    output_dir: Optional[str],
    grafana_url: str,
    grafana_user: str,
    grafana_password: str,
):
    """Export state to timestamped backup directory.

    Exports:
    - Grafana dashboards
    - Grafana datasources
    - Backup manifest

    \b
    Examples:
        contextcore ops backup
        contextcore ops backup --output-dir ./my-backups
    """
    from contextcore.ops import backup
    from pathlib import Path

    click.echo(click.style("=== Creating Backup ===", fg="cyan", bold=True))
    click.echo()

    result = backup(
        output_dir=Path(output_dir) if output_dir else None,
        grafana_url=grafana_url,
        grafana_auth=(grafana_user, grafana_password),
    )

    click.echo(f"Backup directory: {result.path}")
    click.echo(f"Dashboards: {result.manifest.dashboards_count}")
    click.echo(f"Datasources: {result.manifest.datasources_count}")

    if result.errors:
        click.echo()
        click.echo(click.style("Warnings:", fg="yellow"))
        for error in result.errors:
            click.echo(f"  - {error}")

    click.echo()
    if result.success:
        click.echo(click.style(f"Backup complete: {result.path}", fg="green", bold=True))
    else:
        click.echo(click.style("Backup completed with errors", fg="yellow", bold=True))


@ops.command("restore")
@click.argument("backup_path", type=click.Path(exists=True))
@click.option("--grafana-url", default="http://localhost:3000", help="Grafana URL")
@click.option("--grafana-user", default="admin", help="Grafana username")
@click.option("--grafana-password", default="admin", help="Grafana password")
def ops_restore(
    backup_path: str,
    grafana_url: str,
    grafana_user: str,
    grafana_password: str,
):
    """Restore from a backup directory.

    \b
    Examples:
        contextcore ops restore ./backups/20260117-143000
    """
    from contextcore.ops import restore
    from pathlib import Path

    click.echo(click.style("=== Restoring from Backup ===", fg="cyan", bold=True))
    click.echo()
    click.echo(f"Backup path: {backup_path}")
    click.echo()

    success, messages = restore(
        backup_path=Path(backup_path),
        grafana_url=grafana_url,
        grafana_auth=(grafana_user, grafana_password),
    )

    for msg in messages:
        if msg.startswith("Imported"):
            click.echo(click.style(f"  [OK] {msg}", fg="green"))
        else:
            click.echo(click.style(f"  [ERR] {msg}", fg="red"))

    click.echo()
    if success:
        click.echo(click.style("Restore complete", fg="green", bold=True))
        click.echo("Run 'contextcore ops smoke-test' to verify")
    else:
        click.echo(click.style("Restore completed with errors", fg="yellow", bold=True))


@ops.command("backups")
@click.option("--dir", "-d", "base_dir", type=click.Path(), help="Backups directory")
def ops_list_backups(base_dir: Optional[str]):
    """List available backups.

    \b
    Examples:
        contextcore ops backups
        contextcore ops backups --dir ./my-backups
    """
    from contextcore.ops import list_backups
    from pathlib import Path

    backups = list_backups(Path(base_dir) if base_dir else None)

    if not backups:
        click.echo("No backups found")
        click.echo()
        click.echo("Create a backup with: contextcore ops backup")
        return

    click.echo(click.style("Available Backups:", fg="cyan", bold=True))
    click.echo()

    for path, manifest in backups:
        click.echo(f"  {click.style(str(path), bold=True)}")
        click.echo(f"    Created: {manifest.created_at}")
        click.echo(f"    Dashboards: {manifest.dashboards_count}")
        click.echo(f"    Datasources: {manifest.datasources_count}")
        click.echo()
