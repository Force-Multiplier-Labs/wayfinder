"""
Command-line interface for ContextCore Coyote.
"""

from __future__ import annotations

import json
import logging
import sys

import click

from contextcore_coyote import configure, __version__
from contextcore_coyote.config import get_config


@click.group()
@click.version_option(version=__version__)
def main():
    """ContextCore Coyote (Wiisagi-ma'iingan) - Multi-agent incident resolution."""
    pass


@main.command()
@click.option("--log-file", "-f", help="Path to log file containing errors")
@click.option("--error", "-e", help="Error message to investigate")
@click.option("--issue", "-i", type=int, help="GitHub issue number")
@click.option("--output", "-o", default="text", type=click.Choice(["text", "json"]))
@click.option("--debug", is_flag=True, help="Enable debug logging")
def investigate(log_file, error, issue, output, debug):
    """Investigate an incident to find the root cause."""
    from contextcore_coyote import Pipeline, Incident
    from contextcore_coyote.agents import Investigator

    if debug:
        logging.basicConfig(level=logging.DEBUG)

    # Get the incident
    if log_file:
        with open(log_file) as f:
            error_content = f.read()
        incident = Incident.from_error(error_content, source="log-file")
    elif error:
        incident = Incident.from_error(error, source="cli")
    elif issue:
        # TODO: Fetch from GitHub
        click.echo(f"GitHub issue #{issue} - not yet implemented")
        return
    else:
        click.echo("Provide --log-file, --error, or --issue")
        sys.exit(1)

    # Run investigation
    pipeline = Pipeline(stages=[Investigator()])
    result = pipeline.run(incident)

    # Output results
    if output == "json":
        click.echo(json.dumps({
            "incident_id": incident.id,
            "successful": result.successful,
            "stages": [r.to_dict() for r in result.stage_results],
        }, indent=2))
    else:
        click.echo(result.summary())


@main.command()
@click.option("--incident", "-i", required=True, help="Incident ID or error message")
@click.option("--stages", "-s", default="full", help="Stages to run (full, investigate, design-implement)")
@click.option("--auto", is_flag=True, help="Run without approval checkpoints")
@click.option("--output", "-o", default="text", type=click.Choice(["text", "json"]))
def run(incident, stages, auto, output):
    """Run the full incident resolution pipeline."""
    from contextcore_coyote import Pipeline, Incident

    configure(auto_proceed=auto)

    # Create incident
    inc = Incident.from_error(incident, source="cli")

    # Select pipeline
    if stages == "full":
        pipeline = Pipeline.full()
    elif stages == "investigate":
        pipeline = Pipeline.investigation_only()
    elif stages == "design-implement":
        pipeline = Pipeline.design_and_implement()
    else:
        click.echo(f"Unknown stages: {stages}")
        sys.exit(1)

    # Run
    click.echo(f"Running pipeline for incident {inc.id}...")
    result = pipeline.run(inc)

    # Output
    if output == "json":
        click.echo(json.dumps({
            "incident_id": inc.id,
            "status": result.status,
            "successful": result.successful,
            "stages": [r.to_dict() for r in result.stage_results],
        }, indent=2))
    else:
        click.echo(result.summary())


@main.group()
def lessons():
    """Manage lessons learned knowledge base."""
    pass


@lessons.command("list")
@click.option("--category", "-c", help="Filter by category")
@click.option("--file", "-f", help="Filter by related file")
@click.option("--search", "-s", help="Full-text search")
@click.option("--limit", "-n", default=10, help="Maximum results")
@click.option("--output", "-o", default="text", type=click.Choice(["text", "json"]))
def list_lessons(category, file, search, limit, output):
    """List lessons from the knowledge base."""
    from contextcore_coyote.knowledge import LessonsLearned

    kb = LessonsLearned()

    categories = [category] if category else None
    files = [file] if file else None

    results = kb.query(
        categories=categories,
        files=files,
        text=search,
        limit=limit,
    )

    if output == "json":
        click.echo(json.dumps([l.to_dict() for l in results], indent=2))
    else:
        if not results:
            click.echo("No lessons found")
            return

        for lesson in results:
            click.echo(f"\n[{lesson.category}] {lesson.incident_id}")
            click.echo(f"  Lesson: {lesson.lesson}")
            click.echo(f"  Prevention: {lesson.prevention}")
            if lesson.tags:
                click.echo(f"  Tags: {', '.join(lesson.tags)}")


@lessons.command("add")
@click.option("--incident", "-i", required=True, help="Incident ID")
@click.option("--category", "-c", required=True, help="Category")
@click.option("--lesson", "-l", required=True, help="Lesson text")
@click.option("--prevention", "-p", required=True, help="Prevention steps")
@click.option("--files", "-f", multiple=True, help="Related files")
@click.option("--tags", "-t", multiple=True, help="Tags")
def add_lesson(incident, category, lesson, prevention, files, tags):
    """Add a lesson to the knowledge base."""
    from contextcore_coyote.knowledge import LessonsLearned

    kb = LessonsLearned()
    result = kb.add(
        incident_id=incident,
        category=category,
        lesson=lesson,
        prevention=prevention,
        related_files=list(files),
        tags=list(tags),
    )

    click.echo(f"Added lesson {result.id}")


@lessons.command("categories")
def list_categories():
    """List all lesson categories."""
    from contextcore_coyote.knowledge import LessonsLearned

    kb = LessonsLearned()
    categories = kb.get_categories()

    if not categories:
        click.echo("No categories found")
        return

    for cat in sorted(categories):
        click.echo(f"  - {cat}")


@main.command()
def config():
    """Show current configuration."""
    cfg = get_config()

    click.echo("ContextCore Coyote Configuration")
    click.echo("=" * 40)
    click.echo(f"LLM Provider: {cfg.llm_provider}")
    click.echo(f"LLM Model: {cfg.llm_model}")
    click.echo(f"Auto Proceed: {cfg.auto_proceed}")
    click.echo(f"ContextCore Enabled: {cfg.contextcore_enabled}")
    click.echo(f"OTEL Endpoint: {cfg.otel_endpoint}")
    click.echo(f"Prometheus URL: {cfg.prometheus_url or 'Not configured'}")
    click.echo(f"Loki URL: {cfg.loki_url or 'Not configured'}")
    click.echo(f"Tempo URL: {cfg.tempo_url or 'Not configured'}")
    click.echo(f"Lessons File: {cfg.lessons_file}")


@main.command()
def status():
    """Check pipeline status and dependencies."""
    click.echo("ContextCore Coyote Status")
    click.echo("=" * 40)

    # Check LLM availability
    cfg = get_config()

    click.echo("\nLLM Configuration:")
    if cfg.llm_provider == "anthropic":
        if cfg.anthropic_api_key:
            click.echo("  ✓ Anthropic API key configured")
        else:
            click.echo("  ✗ Anthropic API key not set (ANTHROPIC_API_KEY)")
    elif cfg.llm_provider == "openai":
        if cfg.openai_api_key:
            click.echo("  ✓ OpenAI API key configured")
        else:
            click.echo("  ✗ OpenAI API key not set (OPENAI_API_KEY)")

    click.echo("\nObservability:")
    click.echo(f"  Prometheus: {'✓ ' + cfg.prometheus_url if cfg.prometheus_url else '○ Not configured'}")
    click.echo(f"  Loki: {'✓ ' + cfg.loki_url if cfg.loki_url else '○ Not configured'}")
    click.echo(f"  Tempo: {'✓ ' + cfg.tempo_url if cfg.tempo_url else '○ Not configured'}")

    click.echo("\nIntegrations:")
    click.echo(f"  ContextCore: {'✓ Enabled' if cfg.contextcore_enabled else '○ Disabled'}")
    click.echo(f"  GitHub: {'✓ Token configured' if cfg.github_token else '○ Not configured'}")

    # Check lessons file
    from pathlib import Path
    lessons_path = Path(cfg.lessons_file)
    click.echo(f"\nKnowledge Base:")
    if lessons_path.exists():
        from contextcore_coyote.knowledge import LessonsLearned
        kb = LessonsLearned()
        click.echo(f"  ✓ {cfg.lessons_file} ({kb.count()} lessons)")
    else:
        click.echo(f"  ○ {cfg.lessons_file} (not created yet)")


if __name__ == "__main__":
    main()
