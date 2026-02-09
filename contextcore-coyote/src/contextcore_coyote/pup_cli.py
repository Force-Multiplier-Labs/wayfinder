"""
Pup CLI - Simple entry point for ContextCore setup.

Pup wraps the existing ContextCore TUI and provides quick CLI shortcuts
for common operations. No Docker required - uses whatever observability
stack is already configured.

Commands:
    pup           - Launch the ContextCore TUI
    pup check     - Quick health check (CLI output)
    pup hello     - Smoke test the stack
"""

from __future__ import annotations

import sys
import time

import click

from contextcore_coyote import __version__


# 2-frame running pup - side profile, facing right
PUP_RUN = [
    [
        r"                            .              ",
        r"                           _|\__           ",
        r"                          /  o  \____        ",
        r"                         /          ∞       ",
        r"~~~\                    /    _______|       ",
        r"    \__________________/    /              ",
        r"    |                      /               ",
        r"    |                     /                ",
        r"    |                    /                 ",
        r"    |_______________\___/                  ",
        r"    |    |      |    |                     ",
        r"    |    |      |    |                     ",
        r"   /|    |\    /|    |\                    ",
    ],
    [
        r"                            .              ",
        r"                           _|\__           ",
        r"                          /  o  \____        ",
        r"                         /          ∞       ",
        r"~~~\                    /    _______|       ",
        r"    \__________________/    /              ",
        r"    |                      /               ",
        r"    |                     /                ",
        r"    |                    /                 ",
        r"    |_______________\___/                  ",
        r"    |    |      |    |                     ",
        r"    |    |      |    |                     ",
        r"  _/    /_    _/    /_                     ",
    ],
]


def animate_pup(delay: float = 0.05):
    """Play pup running left-to-right across terminal."""
    import shutil

    if not sys.stdout.isatty():
        return

    try:
        cols = shutil.get_terminal_size().columns
        pup_width = 38
        run_distance = cols - pup_width

        # Hide cursor
        click.echo("\033[?25l", nl=False)

        for pos in range(run_distance):
            frame = PUP_RUN[pos % 2]
            # Move cursor to top-left
            click.echo("\033[H", nl=False)
            # Draw each line with padding
            for line in frame:
                click.echo(" " * pos + line + " " * (cols - pos - len(line)))
            time.sleep(delay)

        # Show final message briefly
        click.echo("\033[H", nl=False)
        padding = " " * (run_distance - 1)
        click.echo(padding + r"                            .              ")
        click.echo(padding + r"                           _|\__ *pup!      ")
        click.echo(padding + r"                          /  ^  \___        ")
        click.echo(padding + r"                         /          ∞       ")
        click.echo(padding + r"~~~\                    /    _______|       ")
        click.echo(padding + r"    \__________________/    /              ")
        click.echo(padding + r"    |                      /               ")
        click.echo(padding + r"    |                     /                ")
        click.echo(padding + r"    |                    /                 ")
        click.echo(padding + r"    |_______________\___/                  ")
        click.echo(padding + r"    |    |      |    |                     ")
        click.echo(padding + r"    |    |      |    |                     ")
        click.echo(padding + r"   /|    |\    /|    |\                    ")
        time.sleep(0.4)

        # Clear and show cursor
        click.echo("\033[2J\033[H\033[?25h", nl=False)

    except Exception:
        # Restore cursor if anything fails
        click.echo("\033[?25h", nl=False)
        pass


@click.group(invoke_without_command=True)
@click.version_option(version=__version__, prog_name="pup")
@click.pass_context
def main(ctx):
    """Pup - Quick start for ContextCore observability.

    Run without arguments to launch the interactive TUI.

    \b
    Quick start:
      pup         # Launch TUI
      pup check   # Quick health check
      pup hello   # Smoke test
    """
    if ctx.invoked_subcommand is None:
        # Default: launch TUI
        ctx.invoke(launch)


@main.command()
@click.option(
    "--screen", "-s",
    type=click.Choice(["welcome", "install", "status", "configure"]),
    default="welcome",
    help="Initial screen to display"
)
def launch(screen: str):
    """Launch the ContextCore TUI."""
    try:
        from contextcore.tui import ContextCoreTUI
    except ImportError:
        click.echo("ContextCore TUI not available.", err=True)
        click.echo("Install with: pip install contextcore[tui]", err=True)
        click.echo()
        click.echo("Or run 'pup check' for CLI-only health check.")
        sys.exit(1)

    try:
        app = ContextCoreTUI(initial_screen=screen)
        app.run()
    except KeyboardInterrupt:
        click.echo("\nExited.")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.option("--no-animation", is_flag=True, help="Skip the pup animation")
def check(output_json: bool, no_animation: bool):
    """Quick health check of observability services."""
    import os

    import httpx

    if not output_json and not no_animation:
        animate_pup()

    services = {
        "Grafana": os.getenv("GRAFANA_URL", "http://localhost:3000"),
        "Prometheus": os.getenv("PROMETHEUS_URL", "http://localhost:9090"),
        "Loki": os.getenv("LOKI_URL", "http://localhost:3100"),
        "Tempo": os.getenv("TEMPO_URL", "http://localhost:3200"),
    }

    health_paths = {
        "Grafana": "/api/health",
        "Prometheus": "/-/healthy",
        "Loki": "/ready",
        "Tempo": "/ready",
    }

    results = {}

    for name, base_url in services.items():
        url = f"{base_url.rstrip('/')}{health_paths[name]}"
        try:
            with httpx.Client(timeout=3.0) as client:
                resp = client.get(url)
                results[name] = resp.status_code == 200
        except Exception:
            results[name] = False

    if output_json:
        import json
        click.echo(json.dumps({
            name: {"healthy": healthy, "url": services[name]}
            for name, healthy in results.items()
        }, indent=2))
    else:
        click.echo("ContextCore Health Check")
        click.echo("=" * 30)
        for name, healthy in results.items():
            status = click.style("✓", fg="green") if healthy else click.style("✗", fg="red")
            click.echo(f"  {status} {name:12} {services[name]}")

        healthy_count = sum(results.values())
        click.echo()
        if healthy_count == len(results):
            click.echo(click.style("All services healthy!", fg="green"))
        elif healthy_count > 0:
            click.echo(click.style(f"{healthy_count}/{len(results)} services healthy", fg="yellow"))
        else:
            click.echo(click.style("No services reachable", fg="red"))
            click.echo("Run 'pup' to launch the setup wizard.")


@main.command()
@click.option("--no-animation", is_flag=True, help="Skip the pup animation")
def hello(no_animation: bool):
    """Smoke test - send test data to verify the stack."""
    import json
    import os
    import time as time_module

    import httpx

    if not no_animation:
        animate_pup()

    click.echo("Pup Hello - Smoke Test")
    click.echo("=" * 30)

    loki_url = os.getenv("LOKI_URL", "http://localhost:3100")
    grafana_url = os.getenv("GRAFANA_URL", "http://localhost:3000")

    # Check Loki is up
    click.echo("\nChecking Loki...")
    try:
        with httpx.Client(timeout=3.0) as client:
            resp = client.get(f"{loki_url}/ready")
            if resp.status_code != 200:
                click.echo(click.style(f"  ✗ Loki not ready at {loki_url}", fg="red"))
                sys.exit(1)
            click.echo(click.style("  ✓ Loki is ready", fg="green"))
    except Exception as e:
        click.echo(click.style(f"  ✗ Cannot reach Loki: {e}", fg="red"))
        sys.exit(1)

    # Send test log
    click.echo("\nSending test log...")
    timestamp_ns = int(time_module.time() * 1e9)
    payload = {
        "streams": [{
            "stream": {"job": "pup-hello", "source": "pup"},
            "values": [[str(timestamp_ns), "Hello from pup! Your stack is working."]],
        }]
    }

    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.post(
                f"{loki_url}/loki/api/v1/push",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            if resp.status_code in (200, 204):
                click.echo(click.style("  ✓ Test log sent to Loki", fg="green"))
            else:
                click.echo(click.style(f"  ✗ Loki returned {resp.status_code}", fg="red"))
                sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"  ✗ Failed to send log: {e}", fg="red"))
        sys.exit(1)

    # Success message
    click.echo()
    click.echo(click.style("Stack is working!", fg="green", bold=True))
    click.echo()
    click.echo("View your test log:")
    click.echo(f"  {grafana_url}/explore")
    click.echo('  Query: {job="pup-hello"}')
    click.echo()
    click.echo("Next: Run 'coyote investigate' to debug your first issue.")


if __name__ == "__main__":
    main()
