"""
Squirrel Knowledge Emitter - OpenTelemetry Integration

Emits parsed knowledge items from SquirrelIndex files to Tempo as OTel spans via OTLP.
Part of the ContextCore system for structured knowledge management.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

from contextcore_squirrel.knowledge_parser import (
    Endpoint,
    Process,
    Project,
    Skill,
    SquirrelIndex,
    Tool,
    Workflow,
)

logger = logging.getLogger(__name__)

SERVICE_NAME = "contextcore-squirrel"
DEFAULT_OTLP_ENDPOINT = "http://localhost:4317"
MAX_ATTRIBUTE_LENGTH = 4096


class KnowledgeEmitter:
    """
    OpenTelemetry emitter for SquirrelIndex knowledge items.

    Parses SquirrelIndex files and sends structured knowledge items
    to Tempo as OpenTelemetry spans via OTLP protocol.

    Features:
    - Hierarchical span structure (tier -> items)
    - Rich attribute mapping for all knowledge item types
    - Guaranteed span flushing via shutdown()
    - Dry-run mode for testing
    """

    def __init__(self, endpoint: str = DEFAULT_OTLP_ENDPOINT, dry_run: bool = False) -> None:
        self.dry_run = dry_run
        self.endpoint = endpoint
        self.tracer_provider: Optional[TracerProvider] = None
        self.tracer: Optional[trace.Tracer] = None
        self.exporter = None
        self.shutdown_called = False

        self.stats: Dict[str, int] = {
            "endpoints_emitted": 0,
            "skills_emitted": 0,
            "tools_emitted": 0,
            "workflows_emitted": 0,
            "processes_emitted": 0,
            "projects_emitted": 0,
            "total_spans": 0,
            "total_tokens": 0,
        }

        self._initialize_otel()

    def _initialize_otel(self) -> None:
        """Initialize the OpenTelemetry SDK with proper configuration."""
        try:
            resource = Resource.create({
                "service.name": SERVICE_NAME,
                "service.version": "1.0.0",
                "service.namespace": "contextcore",
            })

            self.tracer_provider = TracerProvider(resource=resource)

            if self.dry_run:
                logger.info("Dry run mode: spans will be printed to console")
                console_exporter = ConsoleSpanExporter()
                self.tracer_provider.add_span_processor(SimpleSpanProcessor(console_exporter))
            else:
                endpoint = self._normalize_endpoint(self.endpoint)
                logger.info(f"Initializing OTLP exporter for: {endpoint}")

                self.exporter = OTLPSpanExporter(
                    endpoint=endpoint,
                    insecure=True,
                    timeout=30,
                )

                batch_processor = BatchSpanProcessor(
                    self.exporter,
                    max_queue_size=2048,
                    max_export_batch_size=50,
                    export_timeout_millis=30000,
                )
                self.tracer_provider.add_span_processor(batch_processor)

            # Use provider directly instead of global to avoid conflicts
            self.tracer = self.tracer_provider.get_tracer(__name__)

            logger.info("OpenTelemetry SDK initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize OpenTelemetry SDK: {e}")
            self.shutdown()
            raise

    def _normalize_endpoint(self, endpoint: str) -> str:
        """Normalize endpoint URL for OTLP exporter."""
        if not endpoint:
            return DEFAULT_OTLP_ENDPOINT

        endpoint = endpoint.replace("http://", "").replace("https://", "")

        if ":" not in endpoint:
            endpoint += ":4317"

        return endpoint

    def _truncate_attribute(self, value: str) -> str:
        """Truncate attribute value to stay within OTel limits."""
        if len(value) > MAX_ATTRIBUTE_LENGTH:
            return value[: MAX_ATTRIBUTE_LENGTH - 3] + "..."
        return value

    def _set_common_attributes(self, span: trace.Span, item_type: str, item: Any) -> None:
        """Set common attributes for all knowledge item spans."""
        span.set_attribute("item.type", item_type)
        span.set_attribute("item.id", getattr(item, "id", ""))
        span.set_attribute("item.name", getattr(item, "name", ""))
        span.set_attribute("item.tier", getattr(item, "tier", ""))

        if hasattr(item, "category"):
            span.set_attribute("item.category", getattr(item, "category", ""))
        if hasattr(item, "tags"):
            span.set_attribute("item.tags", getattr(item, "tags", ""))
        if hasattr(item, "description"):
            description = self._truncate_attribute(getattr(item, "description", ""))
            span.set_attribute("item.description", description)
        if hasattr(item, "source_file"):
            span.set_attribute("item.source_file", getattr(item, "source_file", ""))

    def emit_endpoint(self, endpoint: Endpoint, parent_context: Optional[Context] = None) -> None:
        """Emit endpoint knowledge item as OTel span."""
        span_name = f"endpoint:{endpoint.id}"

        with self.tracer.start_as_current_span(span_name, context=parent_context) as span:
            self._set_common_attributes(span, "endpoint", endpoint)
            span.set_attribute("endpoint.url", endpoint.url)
            span.set_attribute("endpoint.port", endpoint.port)

            self.stats["endpoints_emitted"] += 1
            self.stats["total_spans"] += 1

    def emit_skill(self, skill: Skill, parent_context: Optional[Context] = None) -> None:
        """Emit skill knowledge item as OTel span."""
        span_name = f"skill:{skill.id}"

        with self.tracer.start_as_current_span(span_name, context=parent_context) as span:
            self._set_common_attributes(span, "skill", skill)

            if skill.token_budget is not None:
                try:
                    budget = int(skill.token_budget)
                    span.set_attribute("skill.token_budget", budget)
                    self.stats["total_tokens"] += budget
                except (ValueError, TypeError):
                    span.set_attribute("skill.token_budget", -1)

            self.stats["skills_emitted"] += 1
            self.stats["total_spans"] += 1

    def emit_tool(self, tool: Tool, parent_context: Optional[Context] = None) -> None:
        """Emit tool knowledge item as OTel span."""
        span_name = f"tool:{tool.id}"

        with self.tracer.start_as_current_span(span_name, context=parent_context) as span:
            self._set_common_attributes(span, "tool", tool)

            self.stats["tools_emitted"] += 1
            self.stats["total_spans"] += 1

    def emit_workflow(self, workflow: Workflow, parent_context: Optional[Context] = None) -> None:
        """Emit workflow knowledge item as OTel span."""
        span_name = f"workflow:{workflow.id}"

        with self.tracer.start_as_current_span(span_name, context=parent_context) as span:
            self._set_common_attributes(span, "workflow", workflow)

            self.stats["workflows_emitted"] += 1
            self.stats["total_spans"] += 1

    def emit_process(self, process: Process, parent_context: Optional[Context] = None) -> None:
        """Emit process knowledge item as OTel span."""
        span_name = f"process:{process.id}"

        with self.tracer.start_as_current_span(span_name, context=parent_context) as span:
            self._set_common_attributes(span, "process", process)
            span.set_attribute("process.is_anti_pattern", bool(process.is_anti_pattern))

            self.stats["processes_emitted"] += 1
            self.stats["total_spans"] += 1

    def emit_project(self, project: Project, parent_context: Optional[Context] = None) -> None:
        """Emit project knowledge item as OTel span."""
        span_name = f"project:{project.id}"

        with self.tracer.start_as_current_span(span_name, context=parent_context) as span:
            self._set_common_attributes(span, "project", project)

            self.stats["projects_emitted"] += 1
            self.stats["total_spans"] += 1

    def emit_index(self, index: SquirrelIndex) -> None:
        """Emit all items from a SquirrelIndex as child spans under a parent."""
        span_name = f"squirrel_index:{index.tier}"

        with self.tracer.start_as_current_span(span_name) as parent_span:
            parent_span.set_attribute("index.tier", index.tier)
            parent_span.set_attribute("index.source_path", index.source_path)
            parent_span.set_attribute("index.total_items", index.total_items())

            parent_context = trace.set_span_in_context(parent_span)

            for endpoint in index.endpoints:
                self.emit_endpoint(endpoint, parent_context)

            for skill in index.skills:
                self.emit_skill(skill, parent_context)

            for tool in index.tools:
                self.emit_tool(tool, parent_context)

            for workflow in index.workflows:
                self.emit_workflow(workflow, parent_context)

            for process in index.processes:
                self.emit_process(process, parent_context)

            for project in index.projects:
                self.emit_project(project, parent_context)

            self.stats["total_spans"] += 1  # Count the parent span

    def shutdown(self) -> None:
        """Shutdown the tracer provider and flush all spans."""
        if self.shutdown_called:
            return

        self.shutdown_called = True

        if self.tracer_provider:
            try:
                self.tracer_provider.shutdown()
                logger.info("Tracer provider shut down successfully")
            except Exception as e:
                logger.error(f"Error shutting down tracer provider: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Return emission statistics."""
        return dict(self.stats)
