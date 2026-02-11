"""
CLI entry point for contextcore-squirrel.

Provides commands for parsing and emitting knowledge items and lessons learned.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import click

logger = logging.getLogger(__name__)


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def main(verbose: bool) -> None:
    """ContextCore Squirrel (Ajidamoo) - Skills library for token-efficient agent discovery."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s", stream=sys.stdout)


@main.command("parse")
@click.argument("index_path", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), help="Output JSON file")
@click.option("--stats", is_flag=True, help="Print statistics only")
def parse_command(index_path: str, output: str | None, stats: bool) -> None:
    """Parse a Squirrel knowledge index directory."""
    from contextcore_squirrel.knowledge_parser import parse_capability_index

    index = parse_capability_index(Path(index_path))
    index_stats = index.get_stats()

    if stats:
        click.echo(f"Tier: {index.tier}")
        click.echo(f"Total items: {index.total_items()}")
        for category, count in index_stats.items():
            click.echo(f"  {category}: {count}")
        return

    output_dict = index.model_dump()
    output_dict["total_items"] = index.total_items()
    json_str = json.dumps(output_dict, indent=2, default=str)

    if output:
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        Path(output).write_text(json_str)
        click.echo(f"Wrote {index.total_items()} items to {output}")
    else:
        click.echo(json_str)


@main.command("emit-knowledge")
@click.argument("index_path", type=click.Path(exists=True))
@click.option(
    "--endpoint",
    default="http://localhost:4317",
    help="OTLP gRPC endpoint",
)
@click.option("--dry-run", is_flag=True, help="Print spans to console instead of sending")
def emit_knowledge_command(index_path: str, endpoint: str, dry_run: bool) -> None:
    """Emit knowledge items to Tempo as OTel spans."""
    from contextcore_squirrel.knowledge_emitter import KnowledgeEmitter
    from contextcore_squirrel.knowledge_parser import parse_capability_index

    index = parse_capability_index(Path(index_path))

    if index.total_items() == 0:
        click.echo("No items found in index. Nothing to emit.")
        return

    emitter = KnowledgeEmitter(endpoint=endpoint, dry_run=dry_run)

    try:
        click.echo(f"Emitting {index.total_items()} items to {endpoint}")
        emitter.emit_index(index)

        stats = emitter.get_stats()
        click.echo(f"Emission complete: {stats['total_spans']} spans emitted")
        for key, value in stats.items():
            if key != "total_spans":
                click.echo(f"  {key}: {value}")
    finally:
        emitter.shutdown()


@main.command("emit-lessons")
@click.argument("path", type=click.Path(exists=True))
@click.option("--domain", "-d", help="Emit only specific domain")
@click.option(
    "--endpoint",
    "-e",
    default="http://localhost:4317",
    help="OTLP endpoint",
)
@click.option("--dry-run", is_flag=True, help="Parse only, don't emit")
@click.option("--json-output", "-o", type=click.Path(), help="Save parsed data to JSON")
def emit_lessons_command(
    path: str, domain: str | None, endpoint: str, dry_run: bool, json_output: str | None
) -> None:
    """Emit lessons learned to Tempo via OTLP."""
    from contextcore_squirrel.lessons_emitter import LessonsEmitter
    from contextcore_squirrel.lessons_parser import parse_all_domains, parse_domain, to_dict

    base_path = Path(path)

    if (base_path / "lessons").exists():
        domain_obj = parse_domain(base_path)
        domains = [domain_obj] if domain_obj else []
    elif domain:
        domain_path = base_path / domain
        if not domain_path.exists():
            click.echo(f"Error: Domain {domain} not found", err=True)
            sys.exit(1)
        domain_obj = parse_domain(domain_path)
        domains = [domain_obj] if domain_obj else []
    else:
        domains = parse_all_domains(base_path)

    if not domains:
        click.echo("No lessons found to emit")
        return

    domains_data = [to_dict(d) for d in domains]

    if json_output:
        import datetime

        output = {
            "schema_version": "1.0.0",
            "emission_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "endpoint": endpoint,
            "domains": domains_data,
        }
        Path(json_output).write_text(json.dumps(output, indent=2))
        click.echo(f"Parsed data saved to: {json_output}")

    emitter = LessonsEmitter(endpoint=endpoint, dry_run=dry_run)
    stats = emitter.emit_all(domains_data)
    emitter.shutdown()

    total_lessons = sum(d.lesson_count for d in domains)
    click.echo(f"Domains: {len(domains)}, Lessons: {total_lessons}")
    click.echo(f"Emitted: {stats['lessons_emitted']}, Tokens: {stats['total_tokens']:,}")


@main.command("emit-all")
@click.option("--lessons", type=click.Path(), help="Path to lessons directory")
@click.option("--knowledge", type=click.Path(), help="Path to knowledge index directory")
@click.option(
    "--endpoint",
    default="http://localhost:4317",
    help="OTLP endpoint",
)
@click.option("--dry-run", is_flag=True, help="Perform dry run")
def emit_all_command(
    lessons: str | None, knowledge: str | None, endpoint: str, dry_run: bool
) -> None:
    """Emit both lessons learned and knowledge items to Tempo."""
    from contextcore_squirrel.emit_all import emit_all

    if not lessons and not knowledge:
        click.echo("Error: At least one of --lessons or --knowledge must be provided.", err=True)
        sys.exit(1)

    stats = emit_all(
        lessons_path=lessons,
        knowledge_path=knowledge,
        endpoint=endpoint,
        dry_run=dry_run,
    )

    click.echo("\nCombined Statistics:")
    click.echo(f"  Lessons emitted:   {stats['lessons']['emitted']}")
    click.echo(f"  Lessons failed:    {stats['lessons']['failed']}")
    click.echo(f"  Knowledge emitted: {stats['knowledge']['emitted']}")
    click.echo(f"  Knowledge failed:  {stats['knowledge']['failed']}")


if __name__ == "__main__":
    main()
