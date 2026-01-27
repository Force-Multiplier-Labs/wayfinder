#!/usr/bin/env python3
"""
Lessons Learned Emitter for ContextCore Squirrel

Emits parsed lessons learned to Tempo via OTLP.
Uses the lesson-learned-schema.yaml specification.

Usage:
    # Emit all lessons from a directory
    python lessons_learned_emitter.py /path/to/Lessons_Learned/

    # Emit specific domain
    python lessons_learned_emitter.py /path/to/Lessons_Learned/ --domain observability

    # Dry run (parse only, don't emit)
    python lessons_learned_emitter.py /path/to/Lessons_Learned/ --dry-run

    # Use specific OTLP endpoint
    python lessons_learned_emitter.py /path/to/Lessons_Learned/ --endpoint http://localhost:4317

Environment:
    OTEL_EXPORTER_OTLP_ENDPOINT: OTLP endpoint (default: http://localhost:4317)
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Import the parser
from lessons_learned_parser import parse_all_domains, parse_domain, to_dict

# OpenTelemetry imports
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.trace import Status, StatusCode
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    print("Warning: OpenTelemetry not installed. Use --dry-run or install with:")
    print("  pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp-proto-grpc")


class LessonsEmitter:
    """Emits lessons learned to Tempo via OTLP."""

    def __init__(self, endpoint: str = "http://localhost:4317", dry_run: bool = False):
        self.endpoint = endpoint
        self.dry_run = dry_run
        self.tracer = None
        self.stats = {
            "domains_emitted": 0,
            "legs_emitted": 0,
            "lessons_emitted": 0,
            "total_tokens": 0
        }

        if not dry_run and OTEL_AVAILABLE:
            self._setup_tracer()

    def _setup_tracer(self):
        """Initialize OpenTelemetry tracer."""
        resource = Resource.create({
            "service.name": "contextcore-squirrel-lessons",
            "service.version": "1.0.0",
            "deployment.environment": os.getenv("DEPLOYMENT_ENV", "development")
        })

        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=self.endpoint, insecure=True)
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)

        self.tracer = trace.get_tracer("contextcore-lessons-emitter", "1.0.0")

    def emit_lesson(self, lesson: dict, parent_context=None) -> None:
        """Emit a single lesson as a span."""
        span_name = f"lesson:{lesson['id']}"

        if self.dry_run:
            print(f"      [DRY RUN] Would emit: {span_name}")
            print(f"                Title: {lesson['title'][:60]}...")
            print(f"                Tokens: {lesson['token_budget']}")
            self.stats["lessons_emitted"] += 1
            self.stats["total_tokens"] += lesson['token_budget']
            return

        if not self.tracer:
            return

        with self.tracer.start_as_current_span(
            span_name,
            context=parent_context
        ) as span:
            # Identity attributes
            span.set_attribute("lesson.id", lesson['id'])
            span.set_attribute("lesson.number", lesson['number'])
            span.set_attribute("lesson.title", lesson['title'])

            # Metadata attributes
            span.set_attribute("lesson.domain", lesson['domain'])
            span.set_attribute("lesson.leg", lesson['leg'])
            span.set_attribute("lesson.leg_number", lesson['leg_number'])

            if lesson.get('version'):
                span.set_attribute("lesson.version", lesson['version'])
            if lesson.get('date'):
                span.set_attribute("lesson.date", lesson['date'])
            span.set_attribute("lesson.actor", lesson.get('actor', 'agent:claude-code'))

            # Content summaries
            span.set_attribute("lesson.context_summary", lesson.get('context_summary', ''))
            span.set_attribute("lesson.problem_summary", lesson.get('problem_summary', ''))
            span.set_attribute("lesson.solution_summary", lesson.get('solution_summary', ''))

            # Reusable knowledge
            if lesson.get('heuristic'):
                span.set_attribute("lesson.heuristic", lesson['heuristic'])
            if lesson.get('pattern_name'):
                span.set_attribute("lesson.pattern_name", lesson['pattern_name'])
            if lesson.get('anti_pattern'):
                span.set_attribute("lesson.anti_pattern", lesson['anti_pattern'])

            span.set_attribute("lesson.has_checklist", lesson.get('has_checklist', False))
            span.set_attribute("lesson.has_code_example", lesson.get('has_code_example', False))

            # Categorization
            span.set_attribute("lesson.tags", lesson.get('tags', ''))
            if lesson.get('scope'):
                span.set_attribute("lesson.scope", lesson['scope'])
            if lesson.get('root_cause'):
                span.set_attribute("lesson.root_cause", lesson['root_cause'])

            # Progressive disclosure
            span.set_attribute("lesson.token_budget", lesson.get('token_budget', 0))
            span.set_attribute("lesson.summary_tokens", lesson.get('summary_tokens', 0))
            span.set_attribute("lesson.source_file", lesson.get('source_file', ''))
            span.set_attribute("lesson.source_line", lesson.get('source_line', 0))

            span.set_status(Status(StatusCode.OK))

        self.stats["lessons_emitted"] += 1
        self.stats["total_tokens"] += lesson.get('token_budget', 0)

    def emit_leg(self, leg: dict, parent_context=None) -> None:
        """Emit a leg/topic and its lessons."""
        span_name = f"lesson_leg:{leg['domain']}-{leg['id']}"

        if self.dry_run:
            print(f"    [DRY RUN] Would emit leg: {span_name}")
            print(f"              Name: {leg['name']}")
            print(f"              Lessons: {leg['lesson_count']}")
            self.stats["legs_emitted"] += 1

            for lesson in leg.get('lessons', []):
                self.emit_lesson(lesson)
            return

        if not self.tracer:
            return

        with self.tracer.start_as_current_span(
            span_name,
            context=parent_context
        ) as span:
            span.set_attribute("leg.id", leg['id'])
            span.set_attribute("leg.number", leg['number'])
            span.set_attribute("leg.name", leg['name'])
            span.set_attribute("leg.description", leg.get('description', ''))
            span.set_attribute("leg.domain", leg['domain'])
            span.set_attribute("leg.lesson_count", leg['lesson_count'])
            span.set_attribute("leg.key_patterns", leg.get('key_patterns', ''))
            span.set_attribute("leg.source_file", leg.get('source_file', ''))

            span.set_status(Status(StatusCode.OK))

            # Get current context for child spans
            current_context = trace.get_current_span().get_span_context()

            # Emit lessons as child spans
            for lesson in leg.get('lessons', []):
                self.emit_lesson(lesson)

        self.stats["legs_emitted"] += 1

    def emit_domain(self, domain: dict) -> None:
        """Emit a domain and all its legs/lessons."""
        span_name = f"lesson_domain:{domain['id']}"

        if self.dry_run:
            print(f"  [DRY RUN] Would emit domain: {span_name}")
            print(f"            Name: {domain['name']}")
            print(f"            Legs: {domain['leg_count']}, Lessons: {domain['lesson_count']}")
            self.stats["domains_emitted"] += 1

            for leg in domain.get('legs', []):
                self.emit_leg(leg)
            return

        if not self.tracer:
            return

        with self.tracer.start_as_current_span(span_name) as span:
            span.set_attribute("domain.id", domain['id'])
            span.set_attribute("domain.name", domain['name'])
            span.set_attribute("domain.description", domain.get('description', ''))
            span.set_attribute("domain.leg_count", domain['leg_count'])
            span.set_attribute("domain.lesson_count", domain['lesson_count'])
            span.set_attribute("domain.source_path", domain.get('source_path', ''))

            span.set_status(Status(StatusCode.OK))

            # Emit legs as child spans
            for leg in domain.get('legs', []):
                self.emit_leg(leg)

        self.stats["domains_emitted"] += 1

    def emit_all(self, domains: list) -> dict:
        """Emit all domains."""
        print(f"\n{'='*60}")
        print(f"EMITTING TO TEMPO")
        print(f"{'='*60}")
        print(f"Endpoint: {self.endpoint}")
        print(f"Dry run: {self.dry_run}")
        print()

        for domain in domains:
            print(f"Emitting domain: {domain['name']}")
            self.emit_domain(domain)

        return self.stats

    def shutdown(self):
        """Flush and shutdown the tracer."""
        if not self.dry_run and OTEL_AVAILABLE:
            provider = trace.get_tracer_provider()
            if hasattr(provider, 'force_flush'):
                provider.force_flush()
            if hasattr(provider, 'shutdown'):
                provider.shutdown()


def main():
    parser = argparse.ArgumentParser(
        description="Emit Lessons Learned to Tempo via OTLP"
    )
    parser.add_argument(
        "path",
        type=Path,
        help="Path to Lessons_Learned directory"
    )
    parser.add_argument(
        "--domain", "-d",
        type=str,
        default=None,
        help="Emit only specific domain"
    )
    parser.add_argument(
        "--endpoint", "-e",
        type=str,
        default=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"),
        help="OTLP endpoint (default: $OTEL_EXPORTER_OTLP_ENDPOINT or http://localhost:4317)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and show what would be emitted, but don't send to Tempo"
    )
    parser.add_argument(
        "--json-output", "-o",
        type=Path,
        default=None,
        help="Also save parsed data to JSON file"
    )

    args = parser.parse_args()

    if not args.path.exists():
        print(f"Error: Path {args.path} does not exist", file=sys.stderr)
        sys.exit(1)

    if not args.dry_run and not OTEL_AVAILABLE:
        print("Error: OpenTelemetry not installed. Use --dry-run or install dependencies.")
        sys.exit(1)

    # Parse lessons
    print(f"Parsing lessons from: {args.path}")

    if (args.path / "lessons").exists():
        # Single domain
        domain = parse_domain(args.path)
        domains_data = [to_dict(domain)] if domain else []
    else:
        # Multiple domains
        if args.domain:
            domain_path = args.path / args.domain
            if not domain_path.exists():
                print(f"Error: Domain {args.domain} not found", file=sys.stderr)
                sys.exit(1)
            domain = parse_domain(domain_path)
            domains_data = [to_dict(domain)] if domain else []
        else:
            domains = parse_all_domains(args.path)
            domains_data = [to_dict(d) for d in domains]

    if not domains_data:
        print("No lessons found to emit")
        sys.exit(0)

    # Save JSON if requested
    if args.json_output:
        output = {
            "schema_version": "1.0.0",
            "emission_timestamp": datetime.now(timezone.utc).isoformat(),
            "endpoint": args.endpoint,
            "domains": domains_data
        }
        args.json_output.write_text(json.dumps(output, indent=2))
        print(f"Parsed data saved to: {args.json_output}")

    # Emit to Tempo
    emitter = LessonsEmitter(endpoint=args.endpoint, dry_run=args.dry_run)
    stats = emitter.emit_all(domains_data)
    emitter.shutdown()

    # Print summary
    print(f"\n{'='*60}")
    print(f"EMISSION COMPLETE")
    print(f"{'='*60}")
    print(f"Domains emitted:  {stats['domains_emitted']}")
    print(f"Legs emitted:     {stats['legs_emitted']}")
    print(f"Lessons emitted:  {stats['lessons_emitted']}")
    print(f"Total tokens:     {stats['total_tokens']:,}")

    if not args.dry_run:
        print(f"\nVerify in Tempo:")
        print(f"  curl -s 'http://localhost:3200/api/search?q={{name=~\"lesson:.*\"}}&limit=10'")
        print(f"\nOr in Grafana Explore:")
        print(f"  {{ name =~ \"lesson:.*\" }} | select(span.lesson.id, span.lesson.title, span.lesson.tags)")


if __name__ == "__main__":
    main()
