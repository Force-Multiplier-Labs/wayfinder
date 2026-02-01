"""ContextCore CLI - Insight management commands."""

import json
from typing import Optional

import click
import yaml


@click.group()
def insight():
    """Emit and query agent insights (persistent memory)."""
    pass


@insight.command("emit")
@click.option("--project", "-p", envvar="CONTEXTCORE_PROJECT", default="contextcore", help="Project ID")
@click.option("--agent", "-a", envvar="CONTEXTCORE_AGENT", default="claude", help="Agent ID")
@click.option("--type", "insight_type", type=click.Choice(["decision", "recommendation", "lesson", "blocker", "discovery", "analysis", "risk", "progress"]), required=True)
@click.option("--summary", "-s", required=True, help="Brief summary of the insight")
@click.option("--confidence", "-c", type=float, default=0.9, help="Confidence score (0.0-1.0)")
@click.option("--rationale", "-r", help="Reasoning behind the insight")
@click.option("--category", help="Category for lessons")
@click.option("--applies-to", multiple=True, help="File paths this applies to")
@click.option("--local-storage", envvar="CONTEXTCORE_LOCAL_STORAGE", help="Local storage path")
def insight_emit(project: str, agent: str, insight_type: str, summary: str, confidence: float,
                 rationale: Optional[str], category: Optional[str], applies_to: tuple, local_storage: Optional[str]):
    """Emit an insight for future sessions."""
    from contextcore.agent import InsightEmitter

    emitter = InsightEmitter(project_id=project, agent_id=agent, local_storage_path=local_storage)

    emit_methods = {
        "decision": emitter.emit_decision,
        "recommendation": emitter.emit_recommendation,
        "lesson": emitter.emit_lesson,
        "blocker": emitter.emit_blocker,
        "discovery": emitter.emit_discovery,
        "progress": emitter.emit_progress,
    }

    kwargs = {"rationale": rationale} if rationale else {}

    if insight_type == "lesson":
        if not category:
            category = "general"
        insight = emitter.emit_lesson(summary=summary, category=category, confidence=confidence,
                                      applies_to=list(applies_to) if applies_to else None, **kwargs)
    elif insight_type in emit_methods:
        insight = emit_methods[insight_type](summary=summary, confidence=confidence, **kwargs)
    else:
        from contextcore.agent.insights import InsightType
        insight = emitter.emit(InsightType(insight_type), summary=summary, confidence=confidence,
                               applies_to=list(applies_to) if applies_to else None, category=category, **kwargs)

    click.echo(f"Emitted {insight_type}: {insight.id}")
    click.echo(f"  Summary: {summary}")
    click.echo(f"  Confidence: {confidence}")
    click.echo(f"  Trace ID: {insight.trace_id}")
    if applies_to:
        click.echo(f"  Applies to: {', '.join(applies_to)}")
    if local_storage:
        click.echo(f"  Saved locally: {local_storage}/{project}_insights.json")


@insight.command("query")
@click.option("--project", "-p", envvar="CONTEXTCORE_PROJECT", help="Filter by project")
@click.option("--agent", "-a", help="Filter by agent ID")
@click.option("--type", "insight_type", type=click.Choice(["decision", "recommendation", "lesson", "blocker", "discovery", "analysis", "risk", "progress"]))
@click.option("--category", help="Filter by category")
@click.option("--applies-to", help="Filter by file path")
@click.option("--min-confidence", type=float, help="Minimum confidence score")
@click.option("--time-range", "-t", default="30d", help="Time range")
@click.option("--limit", "-l", type=int, default=20, help="Maximum results")
@click.option("--tempo-url", envvar="TEMPO_URL", default="http://localhost:3200", help="Tempo URL")
@click.option("--local-storage", envvar="CONTEXTCORE_LOCAL_STORAGE", help="Local storage path")
@click.option("--format", "output_format", type=click.Choice(["table", "json", "yaml"]), default="table")
def insight_query(project: Optional[str], agent: Optional[str], insight_type: Optional[str], category: Optional[str],
                  applies_to: Optional[str], min_confidence: Optional[float], time_range: str, limit: int,
                  tempo_url: str, local_storage: Optional[str], output_format: str):
    """Query insights from Tempo or local storage."""
    from contextcore.agent import InsightQuerier

    querier = InsightQuerier(tempo_url=tempo_url if not local_storage else None, local_storage_path=local_storage)

    insights = querier.query(project_id=project, insight_type=insight_type, agent_id=agent, min_confidence=min_confidence,
                             time_range=time_range, limit=limit, applies_to=applies_to, category=category)

    if not insights:
        click.echo("No insights found matching criteria.")
        return

    if output_format == "json":
        data = [{"id": i.id, "type": i.type.value, "summary": i.summary, "confidence": i.confidence,
                 "project_id": i.project_id, "agent_id": i.agent_id, "rationale": i.rationale,
                 "applies_to": i.applies_to, "category": i.category, "trace_id": i.trace_id,
                 "timestamp": i.timestamp.isoformat() if i.timestamp else None} for i in insights]
        click.echo(json.dumps(data, indent=2))
    elif output_format == "yaml":
        data = [{"id": i.id, "type": i.type.value, "summary": i.summary, "confidence": i.confidence,
                 "project_id": i.project_id, "agent_id": i.agent_id, "rationale": i.rationale,
                 "applies_to": i.applies_to, "category": i.category} for i in insights]
        click.echo(yaml.dump(data, default_flow_style=False))
    else:
        click.echo(f"Found {len(insights)} insights:")
        click.echo()
        click.echo(f"{'Type':<12} {'Confidence':<10} {'Summary':<50} {'Agent'}")
        click.echo("-" * 90)
        for i in insights:
            summary = i.summary[:47] + "..." if len(i.summary) > 50 else i.summary
            click.echo(f"{i.type.value:<12} {i.confidence:<10.2f} {summary:<50} {i.agent_id}")


@insight.command("lessons")
@click.option("--project", "-p", envvar="CONTEXTCORE_PROJECT", default="contextcore", help="Project ID")
@click.option("--applies-to", help="Filter by file path")
@click.option("--category", help="Filter by category")
@click.option("--time-range", "-t", default="30d", help="Time range")
@click.option("--tempo-url", envvar="TEMPO_URL", default="http://localhost:3200", help="Tempo URL")
@click.option("--local-storage", envvar="CONTEXTCORE_LOCAL_STORAGE", help="Local storage path")
def insight_lessons(project: str, applies_to: Optional[str], category: Optional[str], time_range: str,
                    tempo_url: str, local_storage: Optional[str]):
    """List lessons learned for a project."""
    from contextcore.agent import InsightQuerier

    querier = InsightQuerier(tempo_url=tempo_url if not local_storage else None, local_storage_path=local_storage)

    lessons = querier.get_lessons(project_id=project, applies_to=applies_to, category=category, time_range=time_range)

    if not lessons:
        click.echo("No lessons found.")
        return

    click.echo(f"Lessons Learned ({len(lessons)} total):")
    click.echo()

    for i, lesson in enumerate(lessons, 1):
        click.echo(f"{i}. {lesson.summary}")
        if lesson.category:
            click.echo(f"   Category: {lesson.category}")
        if lesson.applies_to:
            click.echo(f"   Applies to: {', '.join(lesson.applies_to)}")
        click.echo(f"   Confidence: {lesson.confidence:.0%}")
        click.echo()
