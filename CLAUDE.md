# CLAUDE.md

This file provides guidance to Claude Code for the Wayfinder project.

## Project Context

See @.contextcore.yaml for live project metadata including:
- Business criticality and ownership
- Active risks with priorities (P1-P4) and mitigations
- SLO requirements (availability, latency, throughput)
- Design decisions with confidence scores

### Terminology Reference

See @terminology/MANIFEST.yaml for authoritative definitions. Key distinctions:

| Term | Type | What it is |
|------|------|------------|
| **ContextCore** | Standard | The metadata model/specification (separate repo) |
| **Wayfinder** | Implementation | The reference implementation suite (this repo) |
| **Business Observability** | Paradigm | Grounding observability in business context |

Use `contextcore terminology lookup <term>` for full definitions.

### Repository Layout

This is the **Wayfinder implementation repo**. The ContextCore specification (schemas, semantic conventions, protocols, terminology) lives in a separate `contextcore-spec` repo.

```
wayfinder/
├── src/contextcore/          # Python package (package name stays "contextcore")
│   ├── __init__.py
│   ├── models.py             # Pydantic models for CRD spec
│   ├── tracker.py            # TaskTracker (tasks as spans)
│   ├── state.py              # Span state persistence
│   ├── metrics.py            # Derived project metrics
│   ├── logger.py             # TaskLogger (structured logs)
│   ├── detector.py           # OTel Resource Detector
│   ├── cli/                  # CLI commands (modular)
│   ├── agent/                # Agent communication layer
│   ├── skill/                # Skill telemetry
│   ├── demo/                 # Demo data generation
│   └── install/              # Installation verification
├── tests/                    # Test suite
├── contextcore-rabbit/       # Expansion pack: alert automation
├── contextcore-owl/          # Expansion pack: Grafana plugins
├── grafana/provisioning/     # Grafana auto-provisioning
├── k8s/                      # Kubernetes manifests
├── helm/contextcore/         # Helm chart
├── extensions/vscode/        # VSCode extension
├── examples/                 # Practical examples
├── scripts/                  # Build and operational scripts
├── terminology/              # Expansion pack terminology definitions
├── docs/                     # Implementation documentation
└── .contextcore.yaml         # Project metadata
```

### Quick Commands

- `/project-context` - Display full project context summary
- `/show-risks` - Show active risks sorted by priority

## System Requirements

**Python Command (macOS/Linux)**: This system only has `python3`, not `python`. Always use:
- `python3` instead of `python`
- `pip3` instead of `pip`
- `python3 -m module` instead of `python -m module`

## Commands

```bash
# Install
pip3 install -e ".[dev]"

# Run tests
python3 -m pytest

# Type checking
mypy src/contextcore

# Linting
ruff check src/
black src/

# CLI usage
contextcore task start --id PROJ-123 --title "Feature" --type story
contextcore task update --id PROJ-123 --status in_progress
contextcore task complete --id PROJ-123

# Dashboard provisioning
contextcore dashboards provision
contextcore dashboards list

# Installation verification
contextcore install init
contextcore install verify

# Terminology management
contextcore terminology list -p terminology/
contextcore terminology lookup -p terminology/ wayfinder
```

## Key Patterns

### Tasks as Spans

```python
from contextcore import TaskTracker

tracker = TaskTracker(project="my-project")
tracker.start_task(task_id="PROJ-123", title="Implement auth", task_type="story")
tracker.update_status("PROJ-123", "in_progress")
tracker.complete_task("PROJ-123")
```

### Agent Insights

```python
from contextcore.agent import InsightEmitter, InsightQuerier

emitter = InsightEmitter(project_id="checkout", agent_id="claude")
emitter.emit_decision("Selected event-driven architecture", confidence=0.92)

querier = InsightQuerier()
decisions = querier.query(project_id="checkout", insight_type="decision")
```

## Must Do

- Use ProjectContext CRD as the source of truth for project metadata
- Derive observability config from business metadata (criticality -> sampling rate)
- Export via OTLP (vendor-agnostic)
- Provision dashboards on install (idempotent)
- Dashboards must use ContextCore semantic conventions for all queries

## Must Avoid

- Duplicating context in multiple places
- Manual annotation of K8s resources (use controller)
- Storing sensitive data in ProjectContext
- Vendor-specific code in core SDK

## Expansion Pack Ecosystem

| Package | Animal | Anishinaabe | Purpose |
|---------|--------|-------------|---------|
| **contextcore** | Spider | Asabikeshiinh | Core framework |
| **contextcore-rabbit** | Rabbit | Waabooz | Alert automation |
| **contextcore-fox** | Fox | Waagosh | Context enrichment |
| **contextcore-coyote** | Coyote | Wiisagi-ma'iingan | Multi-agent incident resolution |
| **contextcore-beaver** | Beaver | Amik | LLM provider abstraction |
| **contextcore-squirrel** | Squirrel | Ajidamoo | Skills library |
| **contextcore-owl** | Owl | Gookooko'oo | Grafana plugins (internal) |

## Documentation

- [README.md](README.md) — Vision, benefits, quick start
- [docs/semantic-conventions.md](docs/semantic-conventions.md) — Full attribute reference (spec)
- [docs/agent-communication-protocol.md](docs/agent-communication-protocol.md) — Agent integration (spec)
