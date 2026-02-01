"""ContextCore CLI - Skill management commands."""

import json
import sys
from typing import Optional

import click
import yaml


@click.group()
def skill():
    """Manage skill capabilities as OTel spans."""
    pass


@skill.command("emit")
@click.option("--path", "-p", required=True, help="Path to skill directory")
@click.option("--endpoint", envvar="OTEL_EXPORTER_OTLP_ENDPOINT", default="localhost:4317", help="OTLP endpoint")
def skill_emit(path: str, endpoint: str):
    """Emit a skill's capabilities to Tempo."""
    from contextcore.skill import SkillParser, SkillCapabilityEmitter
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource

    resource = Resource.create({"service.name": "contextcore-skills", "service.version": "1.0.0"})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    try:
        parser = SkillParser()
        manifest, capabilities = parser.parse_skill_directory(path)

        click.echo(f"Parsed skill: {manifest.skill_id}")
        click.echo(f"  Type: {manifest.skill_type}")
        click.echo(f"  Capabilities: {len(capabilities)}")
        click.echo(f"  Total tokens: {manifest.total_tokens}")
        click.echo(f"  Compressed tokens: {manifest.compressed_tokens}")
        click.echo()

        emitter = SkillCapabilityEmitter()
        trace_id, span_ids = emitter.emit_skill_with_capabilities(manifest, capabilities)

        click.echo(f"Emitted to Tempo:")
        click.echo(f"  Trace ID: {trace_id}")
        click.echo(f"  Span count: {len(span_ids) + 1}")
        click.echo()

        provider.force_flush()

        click.echo("Capabilities emitted:")
        for cap in capabilities:
            compression = ((cap.token_budget - cap.summary_tokens) / cap.token_budget * 100) if cap.token_budget > 0 else 0
            click.echo(f"  - {cap.capability_id}: {cap.token_budget} -> {cap.summary_tokens} tokens ({compression:.0f}% reduction)")

    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error emitting skill: {e}", err=True)
        sys.exit(1)


@skill.command("query")
@click.option("--trigger", "-t", help="Find by trigger keyword")
@click.option("--category", "-c", type=click.Choice(["transform", "generate", "validate", "audit", "query", "action", "analyze"]), help="Filter by category")
@click.option("--budget", "-b", type=int, help="Max token budget")
@click.option("--skill-id", "-s", help="Filter by skill ID")
@click.option("--tempo-url", envvar="TEMPO_URL", default="http://localhost:3200", help="Tempo URL")
@click.option("--format", "output_format", type=click.Choice(["table", "json", "yaml"]), default="table")
@click.option("--time-range", default="24h", help="Time range")
def skill_query(trigger: Optional[str], category: Optional[str], budget: Optional[int], skill_id: Optional[str],
                tempo_url: str, output_format: str, time_range: str):
    """Query capabilities from Tempo."""
    from contextcore.skill import SkillCapabilityQuerier, CapabilityCategory

    querier = SkillCapabilityQuerier(tempo_url=tempo_url)
    cat = CapabilityCategory(category) if category else None
    capabilities = querier.query(skill_id=skill_id, category=cat, trigger=trigger, max_tokens=budget, time_range=time_range)

    if not capabilities:
        click.echo("No capabilities found matching criteria.")
        return

    if output_format == "json":
        data = [{"skill_id": c.skill_id, "capability_id": c.capability_id, "category": c.category,
                 "summary": c.summary, "token_budget": c.token_budget, "triggers": c.triggers} for c in capabilities]
        click.echo(json.dumps(data, indent=2))
    elif output_format == "yaml":
        data = [{"skill_id": c.skill_id, "capability_id": c.capability_id, "category": c.category,
                 "summary": c.summary, "token_budget": c.token_budget, "triggers": c.triggers} for c in capabilities]
        click.echo(yaml.dump(data, default_flow_style=False))
    else:
        click.echo(f"Found {len(capabilities)} capabilities:")
        click.echo()
        click.echo(f"{'Skill':<20} {'Capability':<25} {'Category':<12} {'Tokens':<8} {'Summary'}")
        click.echo("-" * 100)
        for c in capabilities:
            summary = c.summary[:40] + "..." if len(c.summary) > 40 else c.summary
            click.echo(f"{c.skill_id:<20} {c.capability_id:<25} {c.category:<12} {c.token_budget:<8} {summary}")


@skill.command("list")
@click.option("--tempo-url", envvar="TEMPO_URL", default="http://localhost:3200", help="Tempo URL")
@click.option("--time-range", default="24h", help="Time range")
def skill_list(tempo_url: str, time_range: str):
    """List all skills in Tempo."""
    from contextcore.skill import SkillManifestQuerier

    querier = SkillManifestQuerier(tempo_url=tempo_url)
    skills = querier.list_skills(time_range=time_range)

    if not skills:
        click.echo("No skills found in Tempo.")
        click.echo("Use 'contextcore skill emit' to emit skills first.")
        return

    click.echo(f"Found {len(skills)} skills:")
    click.echo()
    click.echo(f"{'Skill ID':<25} {'Type':<15} {'Capabilities':<12} {'Total Tokens':<12} {'Compressed'}")
    click.echo("-" * 80)
    for s in skills:
        click.echo(f"{s.skill_id:<25} {s.skill_type:<15} {len(s.capability_refs):<12} {s.total_tokens:<12} {s.compressed_tokens}")


@skill.command("routing")
@click.option("--skill-id", "-s", required=True, help="Skill ID")
@click.option("--tempo-url", envvar="TEMPO_URL", default="http://localhost:3200", help="Tempo URL")
@click.option("--format", "output_format", type=click.Choice(["table", "yaml"]), default="table")
def skill_routing(skill_id: str, tempo_url: str, output_format: str):
    """Get routing table for a skill."""
    from contextcore.skill import SkillCapabilityQuerier

    querier = SkillCapabilityQuerier(tempo_url=tempo_url)
    routing = querier.get_routing_table(skill_id)

    if not routing:
        click.echo(f"No routing table found for skill: {skill_id}")
        return

    if output_format == "yaml":
        click.echo(yaml.dump(routing, default_flow_style=False))
    else:
        click.echo(f"Routing table for {skill_id}:")
        click.echo()
        click.echo(f"{'Trigger':<25} {'Capability'}")
        click.echo("-" * 50)
        for trigger, cap_id in sorted(routing.items()):
            click.echo(f"{trigger:<25} {cap_id}")


@skill.command("compress")
@click.option("--path", "-p", required=True, help="Path to skill directory")
@click.option("--target-tokens", "-t", type=int, default=25000, help="Target token budget")
@click.option("--output", "-o", help="Output directory")
@click.option("--dry-run", is_flag=True, help="Show what would be done without writing")
def skill_compress(path: str, target_tokens: int, output: Optional[str], dry_run: bool):
    """Analyze and suggest compression for a skill."""
    from contextcore.skill import SkillParser

    parser = SkillParser(compress=True)

    try:
        manifest, capabilities = parser.parse_skill_directory(path)
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    total_full = manifest.total_tokens
    total_compressed = manifest.compressed_tokens

    click.echo(f"Skill: {manifest.skill_id}")
    click.echo(f"Source: {path}")
    click.echo()
    click.echo("Token Analysis:")
    click.echo(f"  Current total: {total_full:,} tokens")
    click.echo(f"  After summary compression: {total_compressed:,} tokens")
    click.echo(f"  Potential reduction: {total_full - total_compressed:,} tokens ({(total_full - total_compressed) / total_full * 100:.1f}%)")
    click.echo(f"  Target: {target_tokens:,} tokens")
    click.echo()

    if total_compressed <= target_tokens:
        click.echo(f"SUCCESS: Compressed size ({total_compressed:,}) meets target ({target_tokens:,})")
    else:
        click.echo(f"WARNING: Compressed size ({total_compressed:,}) still exceeds target ({target_tokens:,})")

    click.echo()
    click.echo("Per-Capability Analysis:")
    click.echo(f"{'Capability':<30} {'Full':<10} {'Summary':<10} {'Reduction'}")
    click.echo("-" * 65)

    for cap in sorted(capabilities, key=lambda c: c.token_budget, reverse=True):
        reduction = (cap.token_budget - cap.summary_tokens) / cap.token_budget * 100 if cap.token_budget > 0 else 0
        click.echo(f"{cap.capability_id:<30} {cap.token_budget:<10} {cap.summary_tokens:<10} {reduction:.0f}%")

    if dry_run:
        click.echo()
        click.echo("(Dry run - no files written)")
