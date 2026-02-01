"""ContextCore CLI - Value tracking commands."""

import json
import time as time_module
from typing import Optional

import click
import yaml


@click.group()
def value():
    """Convert value-focused skill documents to queryable telemetry."""
    pass


@value.command("emit")
@click.option("--path", "-p", required=True, help="Path to skill directory or SKILL.md file")
@click.option("--skill-id", help="Override skill ID")
@click.option("--endpoint", envvar="OTEL_EXPORTER_OTLP_ENDPOINT", default="localhost:4317", help="OTLP endpoint")
@click.option("--dry-run", is_flag=True, help="Preview without emitting")
@click.option("--format", "output_format", type=click.Choice(["table", "json", "yaml"]), default="table")
def value_emit(path: str, skill_id: Optional[str], endpoint: str, dry_run: bool, output_format: str):
    """Parse and emit a value-focused skill as OTel spans."""
    from pathlib import Path as PathLib
    from contextcore.value import ValueCapabilityParser, ValueEmitter

    skill_path = PathLib(path).expanduser()

    try:
        parser = ValueCapabilityParser(skill_path)
        manifest, capabilities = parser.parse()
        if skill_id:
            manifest.skill_id = skill_id
    except FileNotFoundError as e:
        raise click.ClickException(str(e))
    except Exception as e:
        raise click.ClickException(f"Parse error: {e}")

    if output_format == "json":
        output = {"manifest": manifest.model_dump(mode="json"), "capabilities": [c.model_dump(mode="json") for c in capabilities]}
        click.echo(json.dumps(output, indent=2))
        return

    if output_format == "yaml":
        output = {"manifest": manifest.model_dump(mode="json"), "capabilities": [c.model_dump(mode="json") for c in capabilities]}
        click.echo(yaml.dump(output, default_flow_style=False))
        return

    click.echo(click.style(f"\n=== Value Manifest: {manifest.skill_id} ===", fg="cyan", bold=True))
    click.echo(f"Source: {manifest.source_file}")
    click.echo(f"Total capabilities: {len(capabilities)}")
    click.echo(f"Personas covered: {', '.join(manifest.personas_covered)}")
    click.echo(f"Channels supported: {', '.join(manifest.channels_supported)}")

    click.echo(click.style(f"\n=== Value Capabilities ({len(capabilities)}) ===", fg="cyan", bold=True))
    for cap in capabilities:
        click.echo(f"\n  {click.style(cap.capability_id, fg='green')}")
        click.echo(f"    Name: {cap.capability_name}")
        click.echo(f"    Value type: {click.style(cap.value.value_type, fg='yellow')}")
        click.echo(f"    Personas: {', '.join(cap.value.personas)}")

    if dry_run:
        click.echo(click.style("\n[DRY RUN] No spans emitted", fg="yellow"))
        return

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

        provider = TracerProvider()
        exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        emitter = ValueEmitter(agent_id=f"cli:{manifest.skill_id}")
        trace_id, span_ids = emitter.emit_value_with_capabilities(manifest, capabilities)

        click.echo(click.style(f"\nEmitted to {endpoint}", fg="green", bold=True))
        click.echo(f"  Trace ID: {trace_id}")
        click.echo(f"  Span count: {len(span_ids)}")

    except Exception as e:
        raise click.ClickException(f"Emit error: {e}")


@value.command("query")
@click.option("--skill-id", "-s", help="Filter by skill ID")
@click.option("--persona", "-p", help="Filter by persona")
@click.option("--value-type", "-v", type=click.Choice(["direct", "indirect", "ripple"]), help="Filter by value type")
@click.option("--channel", "-c", help="Filter by channel")
@click.option("--pain-point", help="Search pain point text")
@click.option("--benefit", help="Search benefit text")
@click.option("--related-skill", help="Find capabilities related to a technical skill")
@click.option("--tempo-url", envvar="TEMPO_URL", default="http://localhost:3200", help="Tempo URL")
@click.option("--time-range", default="24h", help="Time range")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
def value_query(skill_id: Optional[str], persona: Optional[str], value_type: Optional[str], channel: Optional[str],
                pain_point: Optional[str], benefit: Optional[str], related_skill: Optional[str],
                tempo_url: str, time_range: str, output_format: str):
    """Query value capabilities from Tempo."""
    import requests

    conditions = ['name =~ "value_capability:.*"']
    if skill_id:
        conditions.append(f'skill.id = "{skill_id}"')
    if persona:
        conditions.append(f'value.persona = "{persona}"')
    if value_type:
        conditions.append(f'value.type = "{value_type}"')
    if channel:
        conditions.append(f'value.channels =~ ".*{channel}.*"')
    if pain_point:
        conditions.append(f'value.pain_point =~ ".*{pain_point}.*"')
    if benefit:
        conditions.append(f'value.benefit =~ ".*{benefit}.*"')
    if related_skill:
        conditions.append(f'value.related_skills =~ ".*{related_skill}.*"')

    traceql = "{ " + " && ".join(conditions) + " }"
    click.echo(click.style(f"TraceQL: {traceql}", fg="cyan"))

    time_map = {"h": 3600, "d": 86400, "w": 604800, "m": 2592000}
    time_unit = time_range[-1]
    time_value = int(time_range[:-1])
    seconds = time_value * time_map.get(time_unit, 3600)

    end_ns = int(time_module.time() * 1e9)
    start_ns = end_ns - (seconds * int(1e9))

    url = f"{tempo_url}/api/search"
    params = {"q": traceql, "start": start_ns, "end": end_ns, "limit": 100}

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        raise click.ClickException(f"Query failed: {e}")

    traces = data.get("traces", [])

    if output_format == "json":
        click.echo(json.dumps(data, indent=2))
        return

    if not traces:
        click.echo(click.style("No matching value capabilities found", fg="yellow"))
        return

    click.echo(click.style(f"\nFound {len(traces)} trace(s)", fg="green", bold=True))


@value.command("list-personas")
def value_list_personas():
    """List available personas for value capability queries."""
    from contextcore.value.models import Persona

    click.echo(click.style("Available Personas:", fg="cyan", bold=True))
    for p in Persona:
        click.echo(f"  {click.style(p.value, fg='green')}")


@value.command("list-channels")
def value_list_channels():
    """List available channels for value capability queries."""
    from contextcore.value.models import Channel

    click.echo(click.style("Available Channels:", fg="cyan", bold=True))
    for c in Channel:
        click.echo(f"  {click.style(c.value, fg='green')}")
