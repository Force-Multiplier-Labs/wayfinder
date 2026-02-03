"""ContextCore CLI - Knowledge management commands."""

import json
import sys
from typing import Optional

import click
import yaml


@click.group()
def knowledge():
    """Convert markdown knowledge documents to queryable telemetry."""
    pass


@knowledge.command("emit")
@click.option("--path", "-p", required=True, help="Path to skill directory or SKILL.md file")
@click.option("--skill-id", help="Override skill ID")
@click.option("--endpoint", envvar="OTEL_EXPORTER_OTLP_ENDPOINT", default="localhost:4317", help="OTLP endpoint")
@click.option("--dry-run", is_flag=True, help="Preview without emitting")
@click.option("--format", "output_format", type=click.Choice(["table", "json", "yaml"]), default="table")
def knowledge_emit(path: str, skill_id: Optional[str], endpoint: str, dry_run: bool, output_format: str):
    """Parse markdown SKILL.md and emit as queryable capabilities."""
    from pathlib import Path
    from contextcore.knowledge import MarkdownCapabilityParser, KnowledgeEmitter

    try:
        parser = MarkdownCapabilityParser(Path(path).expanduser())
        manifest, capabilities = parser.parse()
        if skill_id:
            manifest.skill_id = skill_id
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    click.echo(f"Parsed: {manifest.skill_id}")
    click.echo(f"  Source: {manifest.source_file}")
    click.echo(f"  Lines: {manifest.total_lines}")
    click.echo(f"  H2 Sections: {manifest.section_count}")
    click.echo(f"  Total Capabilities: {len(capabilities)}")
    click.echo()
    click.echo(f"Token Analysis:")
    click.echo(f"  Full content: {manifest.total_tokens:,} tokens")
    click.echo(f"  After compression: {manifest.compressed_tokens:,} tokens")
    compression = (manifest.total_tokens - manifest.compressed_tokens) / manifest.total_tokens * 100 if manifest.total_tokens > 0 else 0
    click.echo(f"  Compression: {compression:.1f}%")
    click.echo()

    if output_format == "json":
        data = [{"capability_id": c.capability_id, "name": c.capability_name, "knowledge_category": c.knowledge_category,
                 "source_section": c.source_section, "line_range": c.line_range, "summary": c.summary,
                 "triggers": c.triggers[:10], "token_budget": c.token_budget, "has_code": c.has_code,
                 "has_tables": c.has_tables, "tools": c.tools, "ports": c.ports, "env_vars": c.env_vars[:5]} for c in capabilities]
        click.echo(json.dumps(data, indent=2))
        return

    elif output_format == "yaml":
        data = [{"capability_id": c.capability_id, "name": c.capability_name, "knowledge_category": c.knowledge_category,
                 "source_section": c.source_section, "line_range": c.line_range, "summary": c.summary,
                 "triggers": c.triggers[:10], "token_budget": c.token_budget} for c in capabilities]
        click.echo(yaml.dump(data, default_flow_style=False))
        return

    click.echo("Capabilities extracted:")
    click.echo()
    click.echo(f"{'ID':<35} {'Category':<15} {'Lines':<12} {'Tokens':<8} {'Code':<5} {'Tables'}")
    click.echo("-" * 90)

    for c in capabilities:
        has_code = "Yes" if c.has_code else ""
        has_tables = "Yes" if c.has_tables else ""
        click.echo(f"{c.capability_id:<35} {c.knowledge_category:<15} {c.line_range:<12} {c.token_budget:<8} {has_code:<5} {has_tables}")

    if dry_run:
        click.echo()
        click.echo("(Dry run - no spans emitted)")
        return

    click.echo()
    click.echo(f"Emitting to {endpoint}...")

    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from contextcore.exporter_factory import create_span_exporter
    from opentelemetry.sdk.resources import Resource

    resource = Resource.create({"service.name": "contextcore-knowledge", "service.version": "1.0.0"})
    provider = TracerProvider(resource=resource)
    exporter = create_span_exporter(endpoint=endpoint)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    try:
        emitter = KnowledgeEmitter(agent_id=manifest.skill_id)
        trace_id, span_ids = emitter.emit_knowledge_with_capabilities(manifest, capabilities)
        provider.force_flush()

        click.echo()
        click.echo(f"Emitted {len(capabilities)} capabilities")
        click.echo(f"  Trace ID: {trace_id}")

    except Exception as e:
        click.echo(f"Error emitting: {e}", err=True)
        sys.exit(1)


@knowledge.command("query")
@click.option("--skill-id", "-s", help="Filter by skill ID")
@click.option("--category", "-c", type=click.Choice(["infrastructure", "workflow", "sdk", "reference", "security", "configuration"]))
@click.option("--trigger", "-t", help="Find by trigger keyword")
@click.option("--has-code", is_flag=True, help="Only capabilities with code examples")
@click.option("--port", help="Find capabilities mentioning a specific port")
@click.option("--tool", help="Find capabilities mentioning a CLI tool")
@click.option("--tempo-url", envvar="TEMPO_URL", default="http://localhost:3200", help="Tempo URL")
@click.option("--time-range", default="24h", help="Time range")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.option("--skip-rbac", is_flag=True, help="Skip RBAC filtering")
def knowledge_query(skill_id: Optional[str], category: Optional[str], trigger: Optional[str], has_code: bool,
                    port: Optional[str], tool: Optional[str], tempo_url: str, time_range: str,
                    output_format: str, skip_rbac: bool):
    """Query knowledge capabilities from Tempo with RBAC filtering."""
    import requests
    from contextcore.rbac import get_enforcer, PrincipalResolver, Resource, ResourceType, Action, PolicyDecision
    from contextcore.knowledge.models import SENSITIVE_CATEGORIES, KnowledgeCategory

    principal = PrincipalResolver.from_cli_context()
    enforcer = get_enforcer()

    if category and not skip_rbac:
        try:
            cat_enum = KnowledgeCategory(category)
            is_sensitive = cat_enum in SENSITIVE_CATEGORIES
        except ValueError:
            is_sensitive = False

        if is_sensitive:
            resource = Resource(resource_type=ResourceType.KNOWLEDGE_CATEGORY, resource_id=category, sensitive=True)
            decision = enforcer.check_access(principal.id, principal.principal_type, resource, Action.QUERY)
            if decision.decision != PolicyDecision.ALLOW:
                click.echo(click.style(f"Access denied: You don't have permission to query '{category}' knowledge.", fg="red"))
                sys.exit(1)

    conditions = ['name =~ "capability:.*"']
    if skill_id:
        conditions.append(f'skill.id = "{skill_id}"')
    if category:
        conditions.append(f'knowledge.category = "{category}"')
    if trigger:
        conditions.append(f'capability.triggers =~ ".*{trigger}.*"')
    if has_code:
        conditions.append('capability.has_code = true')
    if port:
        conditions.append(f'capability.ports =~ ".*{port}.*"')
    if tool:
        conditions.append(f'capability.tools =~ ".*{tool}.*"')

    query = "{ " + " && ".join(conditions) + " }"

    click.echo(f"TraceQL: {query}")
    click.echo()

    try:
        response = requests.get(f"{tempo_url}/api/search", params={"q": query, "limit": 50}, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        click.echo(f"Error querying Tempo: {e}", err=True)
        sys.exit(1)

    traces = data.get("traces", [])
    if not traces:
        click.echo("No capabilities found matching criteria.")
        return

    if output_format == "json":
        click.echo(json.dumps({"traces": traces}, indent=2))
        return

    click.echo(f"Found {len(traces)} matching capabilities:")
    click.echo()
    click.echo(f"{'Trace ID':<35} {'Service'}")
    click.echo("-" * 50)

    for t in traces:
        trace_id = t.get("traceID", "")
        root_service = t.get("rootServiceName", "")
        click.echo(f"{trace_id:<35} {root_service}")
