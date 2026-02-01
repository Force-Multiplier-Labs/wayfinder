"""ContextCore CLI - Dashboard provisioning commands."""

from typing import Optional

import click


# Common options for Grafana connection
def grafana_options(f):
    """Decorator to add common Grafana connection options."""
    f = click.option(
        "--grafana-url",
        envvar="GRAFANA_URL",
        default="http://localhost:3000",
        help="Grafana base URL",
    )(f)
    f = click.option(
        "--api-key", envvar="GRAFANA_API_KEY", help="Grafana API key"
    )(f)
    f = click.option(
        "--username",
        envvar="GRAFANA_USERNAME",
        default="admin",
        help="Grafana username",
    )(f)
    f = click.option(
        "--password",
        envvar="GRAFANA_PASSWORD",
        default="admin",
        help="Grafana password",
    )(f)
    return f


@click.group()
def dashboards():
    """Provision and manage Grafana dashboards.

    ContextCore organizes dashboards by extension pack:

    \b
      core      - Core project management dashboards
      squirrel  - Skills library dashboards
      rabbit    - Alert automation dashboards
      beaver    - LLM abstraction dashboards
      fox       - Context enrichment dashboards
      coyote    - Multi-agent pipeline dashboards
      owl       - Grafana plugin dashboards
      external  - Third-party dashboards

    Use --extension/-e to filter operations by extension.

    \b
    Examples:
      contextcore dashboards provision              # Provision all
      contextcore dashboards provision -e core      # Provision core only
      contextcore dashboards list --source local    # Show local dashboards
      contextcore dashboards extensions             # List all extensions
    """
    pass


@dashboards.command("provision")
@grafana_options
@click.option(
    "--extension",
    "-e",
    help="Filter by extension (core, squirrel, rabbit, beaver, fox, coyote, owl, external)",
)
@click.option("--dry-run", is_flag=True, help="Preview without applying")
def dashboards_provision(
    grafana_url: str,
    api_key: Optional[str],
    username: str,
    password: str,
    extension: Optional[str],
    dry_run: bool,
):
    """Provision ContextCore dashboards to Grafana.

    Discovers dashboards from extension folders and provisions them
    to the appropriate Grafana folders.

    \b
    Examples:
      contextcore dashboards provision              # Provision all 11 dashboards
      contextcore dashboards provision -e core      # Provision 5 core dashboards
      contextcore dashboards provision -e squirrel  # Provision 2 squirrel dashboards
      contextcore dashboards provision --dry-run    # Preview what would be provisioned
    """
    from contextcore.dashboards import DashboardProvisioner
    from contextcore.dashboards.discovery import EXTENSION_REGISTRY

    # Validate extension if provided
    if extension and extension not in EXTENSION_REGISTRY:
        valid = ", ".join(EXTENSION_REGISTRY.keys())
        raise click.BadParameter(f"Unknown extension '{extension}'. Valid: {valid}")

    click.echo(click.style("ContextCore Dashboard Provisioning", fg="cyan", bold=True))
    click.echo()

    if dry_run:
        click.echo(click.style("DRY RUN MODE - No changes will be made", fg="yellow"))
        click.echo()

    click.echo(f"Grafana URL: {grafana_url}")
    click.echo(f"Auth: {'API Key' if api_key else 'Basic Auth'}")
    if extension:
        ext_info = EXTENSION_REGISTRY[extension]
        click.echo(f"Extension: {extension} ({ext_info['name']})")
    click.echo()

    provisioner = DashboardProvisioner(
        grafana_url=grafana_url,
        api_key=api_key,
        username=username,
        password=password,
    )

    results = provisioner.provision_all(dry_run=dry_run, extension=extension)

    if not results:
        click.echo(click.style("No dashboards found to provision", fg="yellow"))
        return

    # Group results by extension (extract from folder name)
    click.echo(click.style("Results:", bold=True))
    success_count = 0
    for name, success, message in results:
        if success:
            click.echo(f"  {click.style('[OK]', fg='green')} {name}")
            click.echo(f"       {message}")
            success_count += 1
        else:
            click.echo(f"  {click.style('[ERR]', fg='red')} {name}")
            click.echo(f"       {message}")

    click.echo()
    total = len(results)
    if success_count == total:
        click.echo(
            click.style(f"Successfully provisioned {success_count}/{total} dashboards", fg="green")
        )
    else:
        click.echo(f"Provisioned {success_count}/{total} dashboards")


@dashboards.command("list")
@grafana_options
@click.option(
    "--extension",
    "-e",
    help="Filter by extension (core, squirrel, rabbit, beaver, fox, coyote, owl, external)",
)
@click.option(
    "--source",
    "-s",
    type=click.Choice(["local", "grafana", "both"]),
    default="both",
    help="Source to list from: local files, Grafana, or both",
)
def dashboards_list(
    grafana_url: str,
    api_key: Optional[str],
    username: str,
    password: str,
    extension: Optional[str],
    source: str,
):
    """List ContextCore dashboards.

    Shows dashboards from local filesystem, Grafana, or both.
    Groups dashboards by extension for easy navigation.

    \b
    Examples:
      contextcore dashboards list                   # Show all from both sources
      contextcore dashboards list --source local    # Show local files only
      contextcore dashboards list --source grafana  # Show Grafana dashboards only
      contextcore dashboards list -e core           # Show only core dashboards
    """
    from contextcore.dashboards import DashboardProvisioner
    from contextcore.dashboards.discovery import (
        EXTENSION_REGISTRY,
        discover_all_dashboards,
    )

    # Validate extension if provided
    if extension and extension not in EXTENSION_REGISTRY:
        valid = ", ".join(EXTENSION_REGISTRY.keys())
        raise click.BadParameter(f"Unknown extension '{extension}'. Valid: {valid}")

    show_local = source in ("local", "both")
    show_grafana = source in ("grafana", "both")

    # Collect local dashboards
    local_dashboards = []
    if show_local:
        local_dashboards = discover_all_dashboards(extension=extension)

    # Collect Grafana dashboards
    grafana_dashboards = []
    if show_grafana:
        provisioner = DashboardProvisioner(
            grafana_url=grafana_url,
            api_key=api_key,
            username=username,
            password=password,
        )
        grafana_dashboards = provisioner.list_provisioned(extension=extension)

    # Display local dashboards grouped by extension
    if show_local:
        click.echo(click.style("Local Dashboards:", fg="cyan", bold=True))
        click.echo()

        if not local_dashboards:
            click.echo("  No local dashboards found")
            click.echo()
        else:
            # Group by extension
            by_extension: dict = {}
            for db in local_dashboards:
                ext = db.extension
                if ext not in by_extension:
                    by_extension[ext] = []
                by_extension[ext].append(db)

            for ext in EXTENSION_REGISTRY.keys():
                if ext not in by_extension:
                    continue
                ext_info = EXTENSION_REGISTRY[ext]
                click.echo(f"  {click.style(ext_info['name'], bold=True)} ({ext}/)")
                for db in by_extension[ext]:
                    click.echo(f"    - {db.title or db.uid}")
                    click.echo(f"      UID: {db.uid}")
                    if db.file_name:
                        click.echo(f"      File: {db.file_name}")
                click.echo()

    # Display Grafana dashboards
    if show_grafana:
        click.echo(click.style("Grafana Dashboards:", fg="cyan", bold=True))
        click.echo()

        if not grafana_dashboards:
            click.echo("  No ContextCore dashboards found in Grafana")
            click.echo()
            if show_local and local_dashboards:
                click.echo("  Run 'contextcore dashboards provision' to create them")
                click.echo()
        else:
            # Group by folder
            by_folder: dict = {}
            for db in grafana_dashboards:
                folder = db.get("folderTitle", "Unknown")
                if folder not in by_folder:
                    by_folder[folder] = []
                by_folder[folder].append(db)

            for folder, dbs in sorted(by_folder.items()):
                click.echo(f"  {click.style(folder, bold=True)}")
                for db in dbs:
                    click.echo(f"    - {db.get('title', 'Unknown')}")
                    click.echo(f"      UID: {db.get('uid', 'N/A')}")
                    click.echo(f"      URL: {grafana_url}{db.get('url', '')}")
                click.echo()

    # Summary
    click.echo(click.style("Summary:", bold=True))
    if show_local:
        click.echo(f"  Local: {len(local_dashboards)} dashboards")
    if show_grafana:
        click.echo(f"  Grafana: {len(grafana_dashboards)} dashboards")


@dashboards.command("delete")
@grafana_options
@click.option(
    "--extension",
    "-e",
    help="Filter by extension (core, squirrel, rabbit, beaver, fox, coyote, owl, external)",
)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
def dashboards_delete(
    grafana_url: str,
    api_key: Optional[str],
    username: str,
    password: str,
    extension: Optional[str],
    yes: bool,
):
    """Delete ContextCore dashboards from Grafana.

    \b
    Examples:
      contextcore dashboards delete                 # Delete all (with confirmation)
      contextcore dashboards delete -e core         # Delete only core dashboards
      contextcore dashboards delete -y              # Delete all without confirmation
    """
    from contextcore.dashboards import DashboardProvisioner
    from contextcore.dashboards.discovery import EXTENSION_REGISTRY, discover_all_dashboards

    # Validate extension if provided
    if extension and extension not in EXTENSION_REGISTRY:
        valid = ", ".join(EXTENSION_REGISTRY.keys())
        raise click.BadParameter(f"Unknown extension '{extension}'. Valid: {valid}")

    # Get dashboards that would be deleted
    dashboards_to_delete = discover_all_dashboards(extension=extension)

    if not dashboards_to_delete:
        click.echo("No dashboards found to delete")
        return

    # Show what will be deleted
    click.echo(click.style("Dashboards to delete:", fg="yellow", bold=True))
    for db in dashboards_to_delete:
        click.echo(f"  - {db.title or db.uid} ({db.extension})")
    click.echo()

    if not yes:
        msg = f"Delete {len(dashboards_to_delete)} dashboard(s)?"
        if extension:
            msg = f"Delete {len(dashboards_to_delete)} {extension} dashboard(s)?"
        if not click.confirm(msg):
            click.echo("Cancelled")
            return

    provisioner = DashboardProvisioner(
        grafana_url=grafana_url,
        api_key=api_key,
        username=username,
        password=password,
    )

    results = provisioner.delete_all(extension=extension)

    click.echo(click.style("Deletion Results:", bold=True))
    success_count = 0
    for uid, success, message in results:
        if success:
            click.echo(f"  {click.style('[OK]', fg='green')} {uid}: {message}")
            success_count += 1
        else:
            click.echo(f"  {click.style('[ERR]', fg='red')} {uid}: {message}")

    click.echo()
    click.echo(f"Deleted {success_count}/{len(results)} dashboards")


@dashboards.command("extensions")
def dashboards_extensions():
    """List all available dashboard extensions.

    Shows each extension pack with its dashboard count and folder location.

    \b
    Extension packs follow the ContextCore animal naming convention:
      core      - Spider (Asabikeshiinh) - Core framework
      squirrel  - Squirrel (Ajidamoo) - Skills library
      rabbit    - Rabbit (Waabooz) - Alert automation
      beaver    - Beaver (Amik) - LLM abstraction
      fox       - Fox (Waagosh) - Context enrichment
      coyote    - Coyote (Wiisagi-ma'iingan) - Multi-agent pipeline
      owl       - Owl (Gookooko'oo) - Grafana plugins
      external  - Third-party/community dashboards
    """
    from contextcore.dashboards.discovery import EXTENSION_REGISTRY, list_extensions

    click.echo(click.style("ContextCore Dashboard Extensions", fg="cyan", bold=True))
    click.echo()

    extensions = list_extensions()

    # Calculate column widths
    max_name = max(len(ext["name"]) for ext in extensions)
    max_ext = max(len(ext["extension"]) for ext in extensions)

    # Header
    click.echo(
        f"  {'Extension':<{max_ext}}  {'Name':<{max_name}}  {'Count':>5}  Folder"
    )
    click.echo(f"  {'-' * max_ext}  {'-' * max_name}  {'-' * 5}  {'-' * 25}")

    # Rows
    total = 0
    for ext in extensions:
        count = ext["count"]
        total += count
        count_str = str(count) if count > 0 else click.style("-", dim=True)
        name = ext["name"]
        folder = ext["folder"]
        extension = ext["extension"]

        if count > 0:
            click.echo(f"  {extension:<{max_ext}}  {name:<{max_name}}  {count_str:>5}  {folder}")
        else:
            # Dim extensions with no dashboards
            click.echo(
                click.style(
                    f"  {extension:<{max_ext}}  {name:<{max_name}}  {count_str:>5}  {folder}",
                    dim=True,
                )
            )

    click.echo()
    click.echo(f"  Total: {total} dashboards across {len(extensions)} extensions")
    click.echo()
    click.echo("Use 'contextcore dashboards provision -e <extension>' to provision specific extensions")
