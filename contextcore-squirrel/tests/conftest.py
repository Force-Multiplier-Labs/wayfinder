"""
Test fixtures for contextcore-squirrel tests.
"""

import pytest
from pathlib import Path

import yaml


@pytest.fixture
def tmp_index(tmp_path: Path) -> Path:
    """Create a temporary index directory with sample YAML files."""
    caps_dir = tmp_path / "capabilities"
    caps_dir.mkdir()

    # endpoints.yaml
    endpoints_data = {
        "endpoints": [
            {
                "id": "grafana_local",
                "name": "Grafana Dashboard",
                "description": "Local Grafana instance for monitoring",
                "tags": ["grafana", "monitoring"],
                "url": "http://localhost:3000",
                "port": 3000,
                "protocol": "http",
                "authentication": "basic",
            },
            {
                "id": "tempo_local",
                "name": "Tempo Tracing",
                "description": "Tempo distributed tracing backend",
                "tags": ["tempo", "tracing"],
                "url": "http://localhost:3200",
                "port": 3200,
            },
        ]
    }
    (caps_dir / "endpoints.yaml").write_text(yaml.dump(endpoints_data))

    # skills.yaml
    skills_data = {
        "skills": [
            {
                "id": "o11y",
                "name": "Observability Analysis",
                "description": "Analyze system observability metrics and traces",
                "tags": ["monitoring", "metrics"],
                "token_budget": 2000,
                "skill_category": "analysis",
                "use_when": "investigating production issues",
            },
        ]
    }
    (caps_dir / "skills.yaml").write_text(yaml.dump(skills_data))

    # tools.yaml
    tools_data = {
        "tools": [
            {
                "id": "curl_wrapper",
                "name": "Enhanced cURL Tool",
                "description": "Wrapper around cURL with retry and error handling",
                "tags": "http,api",
                "tool_type": "script",
                "location": "/usr/local/bin/curl-enhanced",
            },
        ]
    }
    (caps_dir / "tools.yaml").write_text(yaml.dump(tools_data))

    # workflows.yaml
    workflows_data = {
        "workflows": [
            {
                "id": "deploy_service",
                "name": "Service Deployment",
                "description": "Standard workflow for deploying microservices",
                "tags": ["deploy", "ci"],
                "workflow_type": "automation",
                "step_count": 5,
                "steps_summary": "validate, build, test, deploy, verify",
            },
        ]
    }
    (caps_dir / "workflows.yaml").write_text(yaml.dump(workflows_data))

    # processes.yaml
    processes_data = {
        "processes": [
            {
                "id": "incident_response",
                "name": "Incident Response Process",
                "description": "Process for handling production incidents",
                "tags": ["incident", "sre"],
                "process_type": "methodology",
                "is_anti_pattern": False,
            },
        ]
    }
    (caps_dir / "processes.yaml").write_text(yaml.dump(processes_data))

    # projects.yaml
    projects_data = {
        "projects": [
            {
                "id": "contextcore",
                "name": "ContextCore Platform",
                "description": "AI-powered context management system",
                "tags": ["ai", "context"],
                "path": "/home/user/contextcore",
                "status": "active",
            },
        ]
    }
    (caps_dir / "projects.yaml").write_text(yaml.dump(projects_data))

    return tmp_path


@pytest.fixture
def tmp_lessons(tmp_path: Path) -> Path:
    """Create a temporary lessons directory with sample markdown files."""
    domain_dir = tmp_path / "observability"
    lessons_dir = domain_dir / "lessons"
    lessons_dir.mkdir(parents=True)

    # Create domain index file
    index_content = """# Observability Lessons Learned
Lessons from building observability infrastructure.
"""
    (domain_dir / "observability_LESSONS_LEARNED.md").write_text(index_content)

    # Create a leg file with lessons
    leg_content = """# Leg 1: Tracing Fundamentals

## 1. Always Use Structured Logging

**Version:** 3.0.0
**Actor:** agent:claude-code
**Context:** Building a microservices application that needed distributed tracing.
**Problem:** Plain text logs were impossible to correlate across services.
**Solution:** Switched to structured JSON logging with trace context propagation.
**Reusable:**
- **Heuristic:** Always start with structured logging before adding tracing.
- **Pattern:** `Structured-First Observability`
- **Anti-pattern:** Retrofitting structure onto unstructured logs is costly.
**Tags:** [logging, tracing, microservices]

## 2. Trace Context Propagation Matters

**Version:** 3.1.0
**Actor:** human
**Context:** Debugging a latency issue spanning multiple services.
**Problem:** Traces were broken at service boundaries due to missing context headers.
**Solution:** Ensured W3C Trace Context headers propagate through all HTTP clients.
**Reusable:**
- **Heuristic:** Verify trace context propagation in integration tests.
- **Checklist:**
  - [ ] HTTP client propagates traceparent
  - [ ] Message queue preserves trace context
**Tags:** [tracing, distributed-systems, w3c]
"""
    (lessons_dir / "01-tracing.md").write_text(leg_content)

    # Second leg file
    leg2_content = """# Leg 2: Metrics Collection

## 1. Use Counters Not Gauges for Throughput

**Context:** Measuring request throughput in a load-balanced environment.
**Problem:** Gauge-based throughput metrics lost data during scrape intervals.
**Solution:** Use monotonic counters with rate() for throughput measurement.
**Tags:** [metrics, prometheus]

```python
# Example counter usage
counter.add(1, {"method": "GET", "status": "200"})
```
"""
    (lessons_dir / "02-metrics.md").write_text(leg2_content)

    return tmp_path


@pytest.fixture
def single_lesson_content() -> str:
    """A single lesson markdown block for unit testing parse_lesson."""
    return """## 1. Always Validate OTLP Endpoints

**Version:** 2.0.0
**Date:** 2025-01-15
**Actor:** human
**Context:** Setting up a new Tempo backend for trace collection.
**Problem:** Application started but silently dropped all spans because the OTLP endpoint was unreachable.
**Solution:** Added startup health check that verifies OTLP endpoint connectivity before starting span emission.
**Reusable:**
- **Heuristic:** Always validate external endpoints at startup, not first use.
- **Pattern:** `Fail-Fast Connectivity Check`
**Tags:** [otlp, tempo, health-check]
**Scope:** backend
**Root Cause:** No connection validation at startup
"""


@pytest.fixture
def empty_yaml_index(tmp_path: Path) -> Path:
    """Create an index directory with empty YAML files."""
    caps_dir = tmp_path / "capabilities"
    caps_dir.mkdir()
    (caps_dir / "endpoints.yaml").write_text("")
    (caps_dir / "skills.yaml").write_text("")
    return tmp_path
