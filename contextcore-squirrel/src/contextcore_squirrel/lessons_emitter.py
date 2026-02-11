"""
Lessons Learned Emitter for ContextCore Squirrel

Emits parsed lessons learned to Tempo via OTLP.
Uses the lesson-learned-schema.yaml specification.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from contextcore_squirrel.lessons_parser import (
    LessonDomain,
    parse_all_domains,
    parse_domain,
    to_dict,
)

logger = logging.getLogger(__name__)

# OTel imports are optional - emitter works in dry-run mode without them
try:
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.trace import Status, StatusCode

    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False


class LessonsEmitter:
    """Emits lessons learned to Tempo via OTLP."""

    def __init__(self, endpoint: str = "http://localhost:4317", dry_run: bool = False) -> None:
        self.endpoint = endpoint
        self.dry_run = dry_run
        self.tracer: Any = None
        self.stats: Dict[str, int] = {
            "domains_emitted": 0,
            "legs_emitted": 0,
            "lessons_emitted": 0,
            "total_tokens": 0,
        }

        if not dry_run and OTEL_AVAILABLE:
            self._setup_tracer()

    def _setup_tracer(self) -> None:
        """Initialize OpenTelemetry tracer."""
        resource = Resource.create({
            "service.name": "contextcore-squirrel-lessons",
            "service.version": "1.0.0",
            "deployment.environment": os.getenv("DEPLOYMENT_ENV", "development"),
        })

        self._provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=self.endpoint, insecure=True)
        processor = SimpleSpanProcessor(exporter)
        self._provider.add_span_processor(processor)

        # Use provider directly instead of global to avoid conflicts
        self.tracer = self._provider.get_tracer("contextcore-lessons-emitter", "1.0.0")

    def emit_lesson(self, lesson: dict, parent_context: Any = None) -> None:
        """Emit a single lesson as a span."""
        span_name = f"lesson:{lesson['id']}"

        if self.dry_run:
            logger.info(f"[DRY RUN] Would emit: {span_name} - {lesson['title'][:60]}")
            self.stats["lessons_emitted"] += 1
            self.stats["total_tokens"] += lesson.get("token_budget", 0)
            return

        if not self.tracer:
            return

        with self.tracer.start_as_current_span(span_name, context=parent_context) as span:
            # Identity attributes
            span.set_attribute("lesson.id", lesson["id"])
            span.set_attribute("lesson.number", lesson["number"])
            span.set_attribute("lesson.title", lesson["title"])

            # Metadata attributes
            span.set_attribute("lesson.domain", lesson["domain"])
            span.set_attribute("lesson.leg", lesson["leg"])
            span.set_attribute("lesson.leg_number", lesson["leg_number"])

            if lesson.get("version"):
                span.set_attribute("lesson.version", lesson["version"])
            if lesson.get("date"):
                span.set_attribute("lesson.date", lesson["date"])
            span.set_attribute("lesson.actor", lesson.get("actor", "agent:claude-code"))

            # Content summaries
            span.set_attribute("lesson.context_summary", lesson.get("context_summary", ""))
            span.set_attribute("lesson.problem_summary", lesson.get("problem_summary", ""))
            span.set_attribute("lesson.solution_summary", lesson.get("solution_summary", ""))

            # Reusable knowledge
            if lesson.get("heuristic"):
                span.set_attribute("lesson.heuristic", lesson["heuristic"])
            if lesson.get("pattern_name"):
                span.set_attribute("lesson.pattern_name", lesson["pattern_name"])
            if lesson.get("anti_pattern"):
                span.set_attribute("lesson.anti_pattern", lesson["anti_pattern"])

            span.set_attribute("lesson.has_checklist", lesson.get("has_checklist", False))
            span.set_attribute("lesson.has_code_example", lesson.get("has_code_example", False))

            # Categorization
            span.set_attribute("lesson.tags", lesson.get("tags", ""))
            if lesson.get("scope"):
                span.set_attribute("lesson.scope", lesson["scope"])
            if lesson.get("root_cause"):
                span.set_attribute("lesson.root_cause", lesson["root_cause"])

            # Progressive disclosure
            span.set_attribute("lesson.token_budget", lesson.get("token_budget", 0))
            span.set_attribute("lesson.summary_tokens", lesson.get("summary_tokens", 0))
            span.set_attribute("lesson.source_file", lesson.get("source_file", ""))
            span.set_attribute("lesson.source_line", lesson.get("source_line", 0))

            span.set_status(Status(StatusCode.OK))

        self.stats["lessons_emitted"] += 1
        self.stats["total_tokens"] += lesson.get("token_budget", 0)

    def emit_leg(self, leg: dict, parent_context: Any = None) -> None:
        """Emit a leg/topic and its lessons."""
        span_name = f"lesson_leg:{leg['domain']}-{leg['id']}"

        if self.dry_run:
            logger.info(f"[DRY RUN] Would emit leg: {span_name} ({leg['lesson_count']} lessons)")
            self.stats["legs_emitted"] += 1
            for lesson in leg.get("lessons", []):
                self.emit_lesson(lesson)
            return

        if not self.tracer:
            return

        with self.tracer.start_as_current_span(span_name, context=parent_context) as span:
            span.set_attribute("leg.id", leg["id"])
            span.set_attribute("leg.number", leg["number"])
            span.set_attribute("leg.name", leg["name"])
            span.set_attribute("leg.description", leg.get("description", ""))
            span.set_attribute("leg.domain", leg["domain"])
            span.set_attribute("leg.lesson_count", leg["lesson_count"])
            span.set_attribute("leg.key_patterns", leg.get("key_patterns", ""))
            span.set_attribute("leg.source_file", leg.get("source_file", ""))

            span.set_status(Status(StatusCode.OK))

            leg_context = trace.set_span_in_context(span)
            for lesson in leg.get("lessons", []):
                self.emit_lesson(lesson, parent_context=leg_context)

        self.stats["legs_emitted"] += 1

    def emit_domain(self, domain: dict) -> None:
        """Emit a domain and all its legs/lessons."""
        span_name = f"lesson_domain:{domain['id']}"

        if self.dry_run:
            logger.info(
                f"[DRY RUN] Would emit domain: {span_name} "
                f"({domain['leg_count']} legs, {domain['lesson_count']} lessons)"
            )
            self.stats["domains_emitted"] += 1
            for leg in domain.get("legs", []):
                self.emit_leg(leg)
            return

        if not self.tracer:
            return

        with self.tracer.start_as_current_span(span_name) as span:
            span.set_attribute("domain.id", domain["id"])
            span.set_attribute("domain.name", domain["name"])
            span.set_attribute("domain.description", domain.get("description", ""))
            span.set_attribute("domain.leg_count", domain["leg_count"])
            span.set_attribute("domain.lesson_count", domain["lesson_count"])
            span.set_attribute("domain.source_path", domain.get("source_path", ""))

            span.set_status(Status(StatusCode.OK))

            domain_context = trace.set_span_in_context(span)
            for leg in domain.get("legs", []):
                self.emit_leg(leg, parent_context=domain_context)

        self.stats["domains_emitted"] += 1

    def emit_all(self, domains: list) -> Dict[str, int]:
        """Emit all domains."""
        for domain in domains:
            logger.info(f"Emitting domain: {domain.get('name', domain.get('id', 'unknown'))}")
            self.emit_domain(domain)

        return self.stats

    def shutdown(self) -> None:
        """Flush and shutdown the tracer."""
        if not self.dry_run and OTEL_AVAILABLE and hasattr(self, "_provider"):
            self._provider.force_flush()
            self._provider.shutdown()
