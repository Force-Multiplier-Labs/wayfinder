Looking at this implementation, it's very well structured and comprehensive. I'll make some minor polish adjustments to ensure it's production-ready:

```python
#!/usr/bin/env python3
"""
Squirrel Knowledge Emitter - OpenTelemetry Integration

Emits parsed knowledge items from SquirrelIndex files to Tempo as OTel spans via OTLP.
Part of the ContextCore system for structured knowledge management.

Usage:
    python squirrel_knowledge_emitter.py ./skills/dev-tour-guide/index/ --endpoint localhost:4317
    python squirrel_knowledge_emitter.py ./skills/dev-tour-guide/index/ --dry-run
    python squirrel_knowledge_emitter.py ./skills/dev-tour-guide/index/ --tier public
"""

import os
import argparse
import json
import logging
from typing import List, Dict, Optional, Any
from pathlib import Path
import sys

# CRITICAL: Set environment variables before any OTel imports
# This allows the OTel SDK to pick up configuration like the endpoint.
os.environ.setdefault("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor
from opentelemetry.trace.propagation.tracecontext import TraceContextPropagator
from opentelemetry.context import Context

# Import squirrel_index_parser with fallback to mock for testing
try:
    from squirrel_index_parser import (
        SquirrelIndex, Endpoint, Skill, Tool, Workflow, Process, Project,
        parse_squirrel_indexes
    )
except ImportError:
    print("Warning: 'squirrel_index_parser' not found. Using mock classes for demonstration.", file=sys.stderr)

    class MockBase:
        """Base mock class for testing when squirrel_index_parser is unavailable."""
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    class Endpoint(MockBase):
        def __init__(self, id: str, name: str, tier: str, url: str, port: int, **kwargs):
            super().__init__(id=id, name=name, tier=tier, url=url, port=port, **kwargs)

    class Skill(MockBase):
        def __init__(self, id: str, name: str, tier: str, description: str, token_budget: Optional[int] = None, **kwargs):
            super().__init__(id=id, name=name, tier=tier, description=description, token_budget=token_budget, **kwargs)

    class Tool(MockBase):
        def __init__(self, id: str, name: str, tier: str, description: str, **kwargs):
            super().__init__(id=id, name=name, tier=tier, description=description, **kwargs)

    class Workflow(MockBase):
        def __init__(self, id: str, name: str, tier: str, description: str, steps: List[str], **kwargs):
            super().__init__(id=id, name=name, tier=tier, description=description, steps=steps, **kwargs)

    class Process(MockBase):
        def __init__(self, id: str, name: str, tier: str, description: str, steps: List[str], **kwargs):
            super().__init__(id=id, name=name, tier=tier, description=description, steps=steps, **kwargs)

    class Project(MockBase):
        def __init__(self, id: str, name: str, tier: str, description: str, **kwargs):
            super().__init__(id=id, name=name, tier=tier, description=description, **kwargs)

    class SquirrelIndex:
        def __init__(self, tier: str, endpoints: List[Endpoint] = None, skills: List[Skill] = None,
                     tools: List[Tool] = None, workflows: List[Workflow] = None,
                     processes: List[Process] = None, projects: List[Project] = None):
            self.tier = tier
            self.endpoints = endpoints or []
            self.skills = skills or []
            self.tools = tools or []
            self.workflows = workflows or []
            self.processes = processes or []
            self.projects = projects or []

    def parse_squirrel_indexes(directory: Path) -> List[SquirrelIndex]:
        """Mock parser for testing when real parser is unavailable."""
        print(f"Mock: Parsing SquirrelIndex from directory: {directory}", file=sys.stderr)
        
        if not directory.exists():
            print(f"Mock: Directory '{directory}' not found. Returning empty list.", file=sys.stderr)
            return []

        # Generate realistic mock data for testing
        mock_endpoints = [
            Endpoint(id="grafana_local", name="Grafana Dashboard", tier="public", url="localhost", port=3000, 
                    description="Local Grafana instance for monitoring", category="monitoring", 
                    tags="grafana,monitoring,dashboard", source_file="endpoints.yaml"),
            Endpoint(id="tempo_local", name="Tempo Tracing", tier="private", url="localhost", port=3200, 
                    description="Tempo distributed tracing backend", category="tracing", 
                    tags="tempo,tracing,jaeger", source_file="endpoints.yaml"),
        ]
        
        mock_skills = [
            Skill(id="o11y", name="Observability Analysis", tier="public", 
                 description="Analyze system observability metrics and traces", token_budget=2000,
                 category="analysis", tags="monitoring,metrics,traces", source_file="skills.yaml"),
            Skill(id="debug_trace", name="Distributed Trace Debugging", tier="private", 
                 description="Debug issues using distributed tracing data", token_budget=1500,
                 category="debugging", tags="tracing,debug,analysis", source_file="skills.yaml"),
        ]
        
        mock_tools = [
            Tool(id="curl_wrapper", name="Enhanced cURL Tool", tier="private", 
                description="Wrapper around cURL with retry and error handling",
                category="network", tags="http,api,testing", source_file="tools.yaml"),
        ]
        
        mock_workflows = [
            Workflow(id="deploy_service", name="Service Deployment", tier="public", 
                    description="Standard workflow for deploying microservices", 
                    steps=["validate", "build", "test", "deploy", "verify"],
                    category="deployment", tags="deploy,ci/cd", source_file="workflows.yaml"),
        ]
        
        mock_processes = [
            Process(id="incident_response", name="Incident Response Process", tier="private", 
                   description="Process for handling production incidents", 
                   steps=["detect", "assess", "mitigate", "resolve", "post-mortem"],
                   category="operations", tags="incident,sre,ops", source_file="processes.yaml"),
        ]
        
        mock_projects = [
            Project(id="contextcore", name="ContextCore Platform", tier="public", 
                   description="AI-powered context management system",
                   category="platform", tags="ai,context,knowledge", source_file="projects.yaml"),
        ]

        return [
            SquirrelIndex(tier="public", 
                         endpoints=mock_endpoints[:1], 
                         skills=mock_skills[:1],
                         workflows=mock_workflows, 
                         projects=mock_projects),
            SquirrelIndex(tier="private", 
                         endpoints=mock_endpoints[1:], 
                         skills=mock_skills[1:],
                         tools=mock_tools, 
                         processes=mock_processes),
        ]

# Constants
SERVICE_NAME = "contextcore-squirrel"
DEFAULT_OTLP_ENDPOINT = "http://localhost:4317"
MAX_ATTRIBUTE_LENGTH = 4096  # OTel attribute value length limit

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SquirrelEmitter:
    """
    OpenTelemetry emitter for SquirrelIndex knowledge items.
    
    Parses SquirrelIndex files and sends structured knowledge items 
    to Tempo as OpenTelemetry spans via OTLP protocol.
    
    Features:
    - Hierarchical span structure (tier -> items)
    - Rich attribute mapping for all knowledge item types
    - Guaranteed span flushing via shutdown()
    - Dry-run mode for testing
    - Comprehensive error handling
    """

    def __init__(self, endpoint: str = DEFAULT_OTLP_ENDPOINT, dry_run: bool = False) -> None:
        """
        Initialize the SquirrelEmitter.
        
        Args:
            endpoint: OTLP gRPC endpoint (e.g., "http://localhost:4317")
            dry_run: If True, print spans to console instead of sending to Tempo
        """
        self.dry_run = dry_run
        self.endpoint = endpoint
        self.tracer_provider: Optional[TracerProvider] = None
        self.tracer: Optional[trace.Tracer] = None
        self.exporter = None
        self.shutdown_called = False

        # Statistics tracking
        self.stats = {
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
            # Create resource with service identity
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
                # Configure OTLP exporter
                endpoint = self._normalize_endpoint(self.endpoint)
                logger.info(f"Initializing OTLP exporter for: {endpoint}")
                
                self.exporter = OTLPSpanExporter(
                    endpoint=endpoint,
                    insecure=True,  # Use insecure=True for local development
                    timeout=30  # 30 second timeout
                )
                
                batch_processor = BatchSpanProcessor(
                    self.exporter,
                    max_queue_size=2048,
                    max_export_batch_size=512,
                    export_timeout_millis=30000
                )
                self.tracer_provider.add_span_processor(batch_processor)

            # Set global tracer provider and get tracer
            trace.set_tracer_provider(self.tracer_provider)
            self.tracer = trace.get_tracer(__name__, version="1.0.0")
            
            logger.info("OpenTelemetry SDK initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize OpenTelemetry SDK: {e}")
            self.shutdown()
            raise

    def _normalize_endpoint(self, endpoint: str) -> str:
        """Normalize endpoint URL for OTLP exporter."""
        if not endpoint:
            return DEFAULT_OTLP_ENDPOINT
        
        # Remove protocol prefix if present
        endpoint = endpoint.replace("http://", "").replace("https://", "")
        
        # Add default port if missing
        if ':' not in endpoint:
            endpoint += ":4317"
            
        return endpoint

    def _truncate_attribute(self, value: str) -> str:
        """Truncate attribute value to stay within OTel limits."""
        if len(value) > MAX_ATTRIBUTE_LENGTH:
            return value[:MAX_ATTRIBUTE_LENGTH-3] + "..."
        return value

    def _set_common_attributes(self, span: trace.Span, item_type: str, item) -> None:
        """Set common attributes for all knowledge item spans."""
        span.set_attribute("item.type", item_type)
        span.set_attribute("item.id", getattr(item, 'id', ''))
        span.set_attribute("item.name", getattr(item, 'name', ''))
        span.set_attribute("item.tier", getattr(item, 'tier', ''))
        
        # Optional common attributes
        if hasattr(item, 'category'):
            span.set_attribute("item.category", getattr(item, 'category', ''))
        if hasattr(item, 'tags'):
            span.set_attribute("item.tags", getattr(item, 'tags', ''))
        if hasattr(item, 'description'):
            description = self._truncate_attribute(getattr(item, 'description', ''))
            span.set_attribute("item.description", description)
        if hasattr(item, 'source_file'):
            span.set_attribute("item.source_file", getattr(item, 'source_file', ''))

    def emit_endpoint(self, endpoint: Endpoint, parent_context: Optional[Context] = None) -> None:
        """Emit endpoint knowledge item as OTel span."""
        span_name = f"endpoint:{endpoint.id}"
        
        with self.tracer.start_as_current_span(span_name, context=parent_context) as span:
            self._set_common_attributes(span, "endpoint", endpoint)
            
            # Endpoint-specific attributes
            span.set_attribute("endpoint.url", getattr(endpoint, 'url', ''))
            span.set_attribute("endpoint.port", getattr(endpoint, 'port', 0))
            
            self.stats["endpoints_emitted"] += 1
            self.stats["total_spans"] += 1

    def emit_skill(self, skill: Skill, parent_context: Optional[Context] = None) -> None:
        """Emit skill knowledge item as OTel span."""
        span_name = f"skill:{skill.id}"
        
        with self.tracer.start_as_current_span(span_name, context=parent_context) as span:
            self._set_common_attributes(span, "skill", skill)
            
            # Skill-specific attributes
            token_budget = getattr(skill, 'token_budget', None)
            if token_budget is not None:
                try:
                    budget = int(token_budget)
                    span.set_attribute("skill.token_budget", budget)
                    self.stats["total_tokens"] += budget
                except (ValueError, TypeError):
                    span.set_attribute("skill.token_budget", -1)  # Invalid marker
            
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
        span_name = f"workflow