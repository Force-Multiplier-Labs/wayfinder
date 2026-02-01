#!/usr/bin/env python3
"""
Example 2: Agent Insight Telemetry

This example demonstrates the AI agent communication pattern.
Agent decisions, lessons, and questions are stored as spans for persistence.

Prerequisites:
    pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp

Run with local Tempo:
    export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
    python 02_agent_insights.py
"""

import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource


# =============================================================================
# Setup: Configure OpenTelemetry
# =============================================================================

def setup_tracing(service_name: str = "agent-insights") -> trace.Tracer:
    """Configure OTel tracing with OTLP export."""
    resource = Resource.create({
        "service.name": service_name,
        "service.version": "1.0.0",
    })

    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter()
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    return trace.get_tracer(__name__)


# =============================================================================
# Data Models
# =============================================================================

class InsightType(str, Enum):
    DECISION = "decision"
    LESSON = "lesson"
    QUESTION = "question"
    HANDOFF = "handoff"


class Urgency(str, Enum):
    BLOCKING = "blocking"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Decision:
    summary: str
    confidence: float
    rationale: str
    alternatives: Optional[List[str]] = None
    applies_to: Optional[List[str]] = None


@dataclass
class Lesson:
    summary: str
    category: str
    applies_to: Optional[List[str]] = None
    severity: str = "recommended"


@dataclass
class Question:
    summary: str
    urgency: Urgency
    options: Optional[List[str]] = None


@dataclass
class Handoff:
    to_agent: str
    context_summary: str
    open_items: List[str]
    decisions_made: Optional[List[str]] = None


# =============================================================================
# Core Pattern: InsightEmitter
# =============================================================================

class InsightEmitter:
    """
    Emit agent insights as OpenTelemetry spans.

    Each insight becomes a span with:
    - Span name: "agent.insight"
    - Attributes: agent.id, agent.insight.type, agent.insight.summary, etc.
    - These persist in trace storage for future queries
    """

    def __init__(
        self,
        project_id: str,
        agent_id: str,
        session_id: Optional[str] = None,
        tracer: Optional[trace.Tracer] = None,
    ):
        self.project_id = project_id
        self.agent_id = agent_id
        self.session_id = session_id or str(uuid.uuid4())
        self.tracer = tracer or trace.get_tracer(__name__)
        self._decision_refs: List[str] = []

    def _emit_insight(self, insight_type: InsightType, attributes: Dict) -> str:
        """Base method to emit an insight span."""
        span = self.tracer.start_span(
            name="agent.insight",
            attributes={
                "agent.id": self.agent_id,
                "agent.session.id": self.session_id,
                "project.id": self.project_id,
                "agent.insight.type": insight_type.value,
                "agent.insight.timestamp": int(datetime.now().timestamp()),
                **attributes,
            }
        )
        span.end()

        # Return span ID for reference
        span_id = format(span.get_span_context().span_id, '016x')
        return span_id

    def emit_decision(self, decision: Decision) -> str:
        """
        Emit a decision insight.

        Decisions represent architectural or implementation choices made by the agent.
        They include confidence scores and rationale for future reference.
        """
        attributes = {
            "agent.insight.summary": decision.summary,
            "agent.insight.confidence": decision.confidence,
            "agent.insight.rationale": decision.rationale,
        }

        if decision.alternatives:
            attributes["agent.insight.alternatives"] = decision.alternatives
        if decision.applies_to:
            attributes["agent.insight.applies_to"] = decision.applies_to

        span_id = self._emit_insight(InsightType.DECISION, attributes)
        self._decision_refs.append(span_id)

        print(f"✓ Emitted decision: {decision.summary[:50]}... (confidence: {decision.confidence})")
        return span_id

    def emit_lesson(self, lesson: Lesson) -> str:
        """
        Emit a lesson learned.

        Lessons are patterns discovered during work that should apply to future tasks.
        """
        attributes = {
            "agent.insight.summary": lesson.summary,
            "agent.insight.category": lesson.category,
            "agent.insight.severity": lesson.severity,
        }

        if lesson.applies_to:
            attributes["agent.insight.applies_to"] = lesson.applies_to

        span_id = self._emit_insight(InsightType.LESSON, attributes)
        print(f"✓ Emitted lesson: {lesson.summary[:50]}... (category: {lesson.category})")
        return span_id

    def emit_question(self, question: Question) -> str:
        """
        Emit an unresolved question.

        Questions are items requiring human input before the agent can proceed.
        """
        attributes = {
            "agent.insight.summary": question.summary,
            "agent.insight.urgency": question.urgency.value,
            "agent.insight.resolved": False,
        }

        if question.options:
            attributes["agent.insight.options"] = question.options

        span_id = self._emit_insight(InsightType.QUESTION, attributes)
        print(f"✓ Emitted question: {question.summary[:50]}... (urgency: {question.urgency.value})")
        return span_id

    def emit_handoff(self, handoff: Handoff) -> str:
        """
        Emit a handoff to another agent or human.

        Handoffs capture context for smooth transitions between agents or agent-to-human.
        """
        attributes = {
            "agent.insight.from_agent": self.agent_id,
            "agent.insight.to_agent": handoff.to_agent,
            "agent.insight.context_summary": handoff.context_summary,
            "agent.insight.open_items": handoff.open_items,
        }

        if handoff.decisions_made or self._decision_refs:
            attributes["agent.insight.decisions_made"] = handoff.decisions_made or self._decision_refs

        span_id = self._emit_insight(InsightType.HANDOFF, attributes)
        print(f"✓ Emitted handoff: {self.agent_id} → {handoff.to_agent}")
        return span_id


# =============================================================================
# Core Pattern: InsightQuerier (Conceptual)
# =============================================================================

class InsightQuerier:
    """
    Query prior insights from trace storage.

    Note: This is a conceptual implementation. In production, you'd use
    the Tempo API or a TraceQL query library.
    """

    def __init__(self, tempo_endpoint: str = "http://localhost:3200"):
        self.tempo_endpoint = tempo_endpoint

    def query_decisions(
        self,
        project_id: str,
        applies_to: Optional[List[str]] = None,
        min_confidence: float = 0.0,
        time_range: str = "30d",
    ) -> str:
        """
        Generate TraceQL query for prior decisions.

        Returns the query string to execute against Tempo.
        """
        query = f'{{ agent.insight.type = "decision" && project.id = "{project_id}"'

        if min_confidence > 0:
            query += f" && agent.insight.confidence >= {min_confidence}"

        query += " }"

        if applies_to:
            # Note: contains operator for array attributes
            for path in applies_to:
                query = query[:-1] + f' && agent.insight.applies_to contains "{path}" }}'

        return query

    def query_lessons(
        self,
        project_id: str,
        category: Optional[str] = None,
        time_range: str = "90d",
    ) -> str:
        """Generate TraceQL query for lessons learned."""
        query = f'{{ agent.insight.type = "lesson" && project.id = "{project_id}"'

        if category:
            query += f' && agent.insight.category = "{category}"'

        query += " }"
        return query

    def query_open_questions(self, project_id: str) -> str:
        """Generate TraceQL query for unresolved questions."""
        return f'{{ agent.insight.type = "question" && project.id = "{project_id}" && agent.insight.resolved = false }}'


# =============================================================================
# Example Usage
# =============================================================================

def main():
    """Demonstrate agent insight telemetry."""

    # Setup tracing
    tracer = setup_tracing("example-agent")

    print("\n" + "="*60)
    print("Example 2: Agent Insight Telemetry")
    print("="*60 + "\n")

    # Create insight emitter for this agent session
    emitter = InsightEmitter(
        project_id="my-project",
        agent_id="claude-code",
        tracer=tracer,
    )

    # Simulate an agent making decisions during a coding session
    print("--- Agent Session: Implementing API Framework ---\n")

    # Decision 1: Framework selection
    emitter.emit_decision(Decision(
        summary="Selected FastAPI over Flask for the API framework",
        confidence=0.88,
        rationale="FastAPI provides better async support, automatic OpenAPI documentation, "
                  "and built-in request validation via Pydantic",
        alternatives=["Flask", "Django REST Framework", "Starlette"],
        applies_to=["src/api/", "src/api/main.py"],
    ))

    time.sleep(0.2)

    # Decision 2: Database choice
    emitter.emit_decision(Decision(
        summary="Use PostgreSQL with SQLAlchemy ORM",
        confidence=0.92,
        rationale="Team has PostgreSQL expertise, ACID compliance needed for financial data, "
                  "SQLAlchemy provides good async support",
        alternatives=["MongoDB", "MySQL"],
        applies_to=["src/db/", "src/models/"],
    ))

    time.sleep(0.2)

    # Lesson learned during implementation
    emitter.emit_lesson(Lesson(
        summary="Always use dependency injection for database sessions in FastAPI",
        category="architecture",
        applies_to=["src/api/routes/", "src/db/session.py"],
        severity="must_follow",
    ))

    time.sleep(0.2)

    # Question requiring human input
    emitter.emit_question(Question(
        summary="Should user passwords be hashed with bcrypt or argon2?",
        urgency=Urgency.HIGH,
        options=["bcrypt (widely used, battle-tested)", "argon2 (newer, memory-hard)"],
    ))

    time.sleep(0.2)

    # Another lesson
    emitter.emit_lesson(Lesson(
        summary="Mock external APIs in integration tests to avoid flaky tests",
        category="testing",
        applies_to=["tests/integration/"],
    ))

    time.sleep(0.2)

    # Handoff to human for code review
    emitter.emit_handoff(Handoff(
        to_agent="human",
        context_summary="Implemented basic API structure with FastAPI, PostgreSQL models, "
                        "and authentication endpoints. Ready for code review.",
        open_items=[
            "Decide on password hashing algorithm (see question above)",
            "Add rate limiting to auth endpoints",
            "Write integration tests for OAuth flow",
        ],
    ))

    print("\n" + "="*60)
    print("Agent session complete!")
    print("="*60)

    # Show how to query these insights
    querier = InsightQuerier()

    print("\nQuery these insights with TraceQL:")
    print("\n1. All high-confidence decisions:")
    print(f"   {querier.query_decisions('my-project', min_confidence=0.8)}")

    print("\n2. Lessons about architecture:")
    print(f"   {querier.query_lessons('my-project', category='architecture')}")

    print("\n3. Unresolved questions:")
    print(f"   {querier.query_open_questions('my-project')}")

    print("\n4. Decisions affecting src/api/:")
    print(f"   {querier.query_decisions('my-project', applies_to=['src/api/'])}")

    print()

    # Give time for spans to export
    time.sleep(2)


if __name__ == "__main__":
    main()
