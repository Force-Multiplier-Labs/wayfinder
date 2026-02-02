# CLAUDE.md

This file provides guidance to Claude Code for the Wayfinder project.

## Project Overview

**Wayfinder** (codename: Project Muad'Dib) is the reference implementation of the **ContextCore** metadata standard — a project management observability framework that models tasks as OpenTelemetry spans. It eliminates manual status reporting by deriving project health from existing artifact metadata (commits, PRs, CI results) and exports via OTLP to any compatible backend.

**Core insight**: Tasks share the same structure as distributed trace spans — start time, end time, status, hierarchy, events. By storing tasks in observability infrastructure, you get unified querying, time-series persistence, and correlation with runtime telemetry.

**Architecture**: Dual-telemetry emission — spans to Tempo (hierarchy, timing, TraceQL) and structured logs to Loki (events, status changes, metrics derivation via recording rules). Mimir metrics are derived from Loki logs, not directly emitted.

## Project Context

See @.contextcore.yaml for live project metadata including:
- Business criticality and ownership
- SLO requirements (availability, latency, throughput)
- Ecosystem package registry

### Terminology Reference

See @terminology/MANIFEST.yaml for authoritative definitions. Key distinctions:

| Term | Type | What it is |
|------|------|------------|
| **ContextCore** | Standard | The metadata model/specification (separate `contextcore-spec` repo) |
| **Wayfinder** | Implementation | The reference implementation suite (this repo) |
| **Business Observability** | Paradigm | Grounding observability in business context |
| **Language Model 1.0** | Era | Current computing era defined by conversational interfaces |

Use `contextcore terminology lookup <term>` for full definitions.

### History: Separation from ContextCore Monorepo

This repo was extracted from the original `ContextCore` monorepo (at `~/Documents/dev/ContextCore`) which combined both the spec and the implementation. Per [ADR-002](https://github.com/Force-Multiplier-Labs/contextcore-spec/blob/main/docs/adr/002-naming-wayfinder.md):

- **ContextCore** = the standard/specification (schemas, semantic conventions, protocols) — now in `contextcore-spec` repo
- **Wayfinder** = Force Multiplier Labs' reference implementation — this repo

The separation enables ecosystem growth and clarifies that the metadata model has value independent of specific tooling. Package names (`contextcore`, `contextcore-rabbit`, etc.) remain unchanged because they implement the ContextCore standard. The `contextcore` CLI command and `contextcore.io` CRD API group also remain unchanged.

## Tech Stack

- **Language**: Python 3.11+ (async-first design)
- **Models**: Pydantic v2 (strict validation)
- **CLI**: Click 8.1+
- **Telemetry**: OpenTelemetry SDK, OTLP export
- **CRD Framework**: kopf (Kubernetes Operator Framework)
- **K8s Client**: kubernetes >= 28.1.0
- **HTTP**: httpx (async), aiohttp
- **TUI**: Textual >= 0.47.0
- **Reference Backend**: Grafana (Tempo, Mimir, Loki) with Alloy collector
- **Build**: Hatchling

## Repository Layout

This is the **Wayfinder implementation repo**. The ContextCore specification (schemas, semantic conventions, protocols, terminology) lives in the separate `contextcore-spec` repo.

```
wayfinder/
├── src/contextcore/            # Python package (package name stays "contextcore")
│   ├── __init__.py
│   ├── tracker.py              # TaskTracker — tasks as OTel spans (1110 LOC)
│   ├── logger.py               # TaskLogger — structured JSON logs for Loki
│   ├── state.py                # StateManager — span persistence across restarts
│   ├── metrics.py              # TaskMetrics — lead time, cycle time, WIP, velocity
│   ├── detector.py             # ProjectContextDetector — OTel ResourceDetector
│   ├── config.py               # Configuration management
│   ├── models_v2.py            # Pydantic models for CRD spec
│   ├── operator.py             # Kopf K8s operator (1070 LOC)
│   ├── crd_helpers.py          # CRD utility functions
│   ├── cli_legacy.py           # Legacy CLI (being replaced by modular cli/)
│   ├── cli/                    # Modular CLI commands (24 files)
│   │   ├── __init__.py         # Click group entry point
│   │   ├── task.py             # task start/update/block/complete/list
│   │   ├── sprint.py           # sprint start/update/complete
│   │   ├── dashboards.py       # dashboards provision/list/get
│   │   ├── install.py          # install init/verify
│   │   ├── demo.py             # demo generate/load/setup
│   │   ├── terminology.py      # terminology list/lookup
│   │   ├── insight.py          # insight emit/query/lessons
│   │   ├── skill.py            # skill emit/query/list
│   │   ├── knowledge.py        # knowledge import/convert
│   │   ├── rbac.py             # rbac grant/revoke/list
│   │   ├── value.py            # value track/report
│   │   ├── metrics.py          # metrics list/show
│   │   ├── sync.py             # sync jira/github/notion
│   │   ├── git.py              # git link-task/commit-to-task
│   │   ├── ops.py              # ops health/backup/restore
│   │   ├── core.py             # create/annotate/generate/runbook/controller
│   │   ├── tui.py              # tui start
│   │   ├── contract.py         # contract validate (Phase 2)
│   │   ├── review.py           # review request/approve (Phase 2)
│   │   ├── slo_tests.py        # slo-tests run/report (Phase 2)
│   │   ├── graph.py            # graph query/visualize (Phase 3)
│   │   ├── _common.py          # Shared CLI utilities
│   │   └── _generators.py      # Code generation utilities
│   ├── agent/                  # Agent communication layer
│   │   ├── insights.py         # InsightEmitter, InsightQuerier
│   │   ├── guidance.py         # GuidanceReader, GuidanceResponder
│   │   ├── handoff.py          # HandoffManager, HandoffReceiver
│   │   ├── personalization.py  # PersonalizedQuerier
│   │   ├── a2a_adapter.py      # Agent-to-Agent protocol adapter
│   │   ├── a2a_server.py       # A2A server implementation
│   │   ├── a2a_messagehandler.py
│   │   ├── a2a_client.py       # A2A client
│   │   ├── a2a_package.py      # A2A package definitions
│   │   ├── code_generation.py  # Code generation utilities
│   │   ├── artifact.py         # Artifact model
│   │   ├── events.py           # Event type definitions
│   │   └── size_estimation.py  # Token/size estimation
│   ├── contracts/              # Type safety and validation
│   │   ├── types.py            # Central enums (TaskStatus, TaskType, Priority, etc.)
│   │   ├── metrics.py          # Metric contract definitions
│   │   ├── queries.py          # PromQL/LogQL/TraceQL builders
│   │   ├── validate.py         # Contract validation engine
│   │   └── timeouts.py         # Central timeout constants
│   ├── models/                 # Domain models
│   │   ├── core.py             # ProjectSpec, BusinessSpec, RequirementsSpec
│   │   ├── part.py             # Part model (A2A evidence)
│   │   ├── message.py          # Agent message model
│   │   └── artifact.py         # Versioned artifact model
│   ├── skill/                  # Skill telemetry
│   │   ├── emitter.py          # SkillCapabilityEmitter
│   │   ├── querier.py          # SkillCapabilityQuerier
│   │   ├── parser.py           # Parse skill definitions
│   │   └── models.py           # SkillCapability, SkillManifest
│   ├── rbac/                   # Role-based access control
│   │   ├── models.py           # Role, RoleBinding, PolicyRule
│   │   ├── enforcer.py         # PolicyEnforcer
│   │   ├── store.py            # K8s-backed RoleStore
│   │   ├── decorators.py       # @require_permission
│   │   ├── audit.py            # Access audit logging
│   │   └── k8s_sync.py         # K8s RBAC sync
│   ├── knowledge/              # Markdown-to-telemetry
│   │   ├── emitter.py          # KnowledgeEmitter
│   │   └── md_parser.py        # MarkdownParser
│   ├── terminology/            # Terminology management
│   │   ├── emitter.py          # TerminologyEmitter
│   │   ├── parser.py           # YAML parser
│   │   └── models.py           # TermDefinition, TermManifest
│   ├── tracing/                # Tracing utilities
│   │   └── insight_emitter.py
│   ├── compat/                 # OTel compatibility layer
│   │   ├── otel_genai.py       # Dual-emit for OTel GenAI conventions
│   │   ├── operations.py       # Compatibility operations
│   │   └── docs_unifiedupdate.py
│   ├── tui/                    # Terminal UI (Textual)
│   │   ├── installer.py        # TUI installer
│   │   ├── screens/            # TUI screens (welcome, install, configure, status, etc.)
│   │   └── utils/              # TUI utilities (config, health_checker, script_templates)
│   ├── demo/                   # Demo data generation
│   │   ├── generator.py        # HistoricalTaskTracker
│   │   ├── exporter.py         # Dual-emit to Tempo/Loki
│   │   └── project_data.py     # Microservices-demo POC data
│   └── install/                # Installation verification (self-monitoring)
│       ├── verifier.py         # InstallationVerifier
│       ├── requirements.py     # Check requirements
│       ├── installtracking_*.py  # Installation tracking components
│       ├── mimir_query.py      # Mimir metric queries
│       └── debug_display.py    # Debug output formatting
├── tests/                      # Test suite (13 test files + conftest.py)
├── grafana/provisioning/       # 13 auto-provisioned Grafana dashboards
│   ├── dashboards/
│   │   ├── core/               # portfolio, sprint-metrics, installation, etc.
│   │   ├── fox/                # fox-alert-automation
│   │   ├── squirrel/           # skills-browser, value-capabilities
│   │   ├── beaver/             # beaver-lead-contractor-progress
│   │   └── external/           # agent-trigger
│   └── datasources/            # Tempo, Mimir, Loki configs
├── k8s/observability/          # Kubernetes manifests (Grafana, Tempo, Mimir, Loki, Alloy)
├── helm/contextcore/           # Helm chart
├── extensions/vscode/          # VSCode extension (TypeScript)
├── examples/                   # Practical examples (3 Python + sample CRD)
├── scripts/                    # Build and operational scripts
│   ├── lead_contractor/        # Lead contractor workflow (25 files)
│   ├── prime_contractor/       # Prime contractor workflow (9 files)
│   └── *.py                    # Utility scripts
├── terminology/                # Wayfinder terminology definitions (Squirrel pattern)
│   ├── MANIFEST.yaml           # Entry point (~200 tokens)
│   └── definitions/            # Full term definitions
├── docs/                       # Implementation documentation (49+ files)
│   ├── EXPANSION_PACKS.md      # Design boundaries for each pack
│   ├── INSTALLATION.md         # Setup guide
│   ├── KNOWN_ISSUES.md         # Known limitations
│   ├── blueprint-*.md          # Implementation blueprints (7 files)
│   ├── capability-index/       # Capability documentation (18 files)
│   ├── adr/                    # Architecture decision records
│   └── dashboards/             # Dashboard specifications
└── .contextcore.yaml           # Project metadata (CRD instance)
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

# CLI usage — Task tracking
contextcore task start --id PROJ-123 --title "Feature" --type story
contextcore task update --id PROJ-123 --status in_progress
contextcore task block --id PROJ-123 --reason "Waiting on API"
contextcore task complete --id PROJ-123
contextcore task list

# CLI usage — Sprint tracking
contextcore sprint start --id sprint-3 --name "Sprint 3" --goal "Auth flow"
contextcore sprint end --id sprint-3 --points 21

# Dashboard provisioning
contextcore dashboards provision
contextcore dashboards provision --grafana-url URL
contextcore dashboards provision --dry-run
contextcore dashboards list

# Installation verification (self-monitoring)
contextcore install init
contextcore install verify
contextcore install verify --format json
contextcore install status

# Terminology management
contextcore terminology list -p terminology/
contextcore terminology lookup -p terminology/ wayfinder
contextcore terminology emit -p terminology/

# Agent insights
contextcore insight emit --type decision --summary "Chose X"
contextcore insight query --project my-project --type decision

# Skill management
contextcore skill emit
contextcore skill list

# Git integration
contextcore git link-task --commit abc123 --message "feat: auth [PROJ-123]"

# Metrics
contextcore metrics summary --project my-project

# Demo data
contextcore demo generate
contextcore demo load
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GRAFANA_URL` | `http://localhost:3000` | Grafana base URL |
| `GRAFANA_USER` | `admin` | Grafana admin username |
| `GRAFANA_PASSWORD` | `admin` | Grafana admin password |
| `TEMPO_URL` | `http://localhost:3200` | Tempo base URL |
| `MIMIR_URL` | `http://localhost:9009` | Mimir base URL |
| `LOKI_URL` | `http://localhost:3100` | Loki base URL |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `localhost:4317` | OTLP gRPC endpoint |
| `CONTEXTCORE_EMIT_MODE` | `dual` | OTel emit mode: `dual`, `legacy`, or `otel` |

## Key Patterns

### Tasks as Spans

The core abstraction. Tasks are modeled as OpenTelemetry spans with state persisted via `StateManager` to `~/.contextcore/state/<project>/`:

```python
from contextcore import TaskTracker

tracker = TaskTracker(project="my-project")

# Start task (creates span, logs to Loki)
tracker.start_task(
    task_id="PROJ-123",
    title="Implement auth",
    task_type="story",
    parent_id="EPIC-42"  # Creates parent-child hierarchy
)

# Status update (adds span event)
tracker.update_status("PROJ-123", "in_progress")

# Block/unblock
tracker.block_task("PROJ-123", reason="Waiting on API")
tracker.unblock_task("PROJ-123")

# Complete (ends span)
tracker.complete_task("PROJ-123")
```

### Dual Telemetry Emission

- **Spans to Tempo** — Task hierarchy, timing, TraceQL queries
- **Logs to Loki** — Status change events, JSON-formatted for Loki pickup
- **Metrics to Mimir** — Derived from Loki logs via recording rules (lead time, cycle time, throughput, WIP, velocity)

### Agent Insights

Supports two modes: production (OTel to Tempo) and development (local JSON files, no infrastructure needed):

```python
from contextcore.agent import InsightEmitter, InsightQuerier

# Emit insights (stored as spans in Tempo)
emitter = InsightEmitter(project_id="checkout", agent_id="claude")
emitter.emit_decision("Selected event-driven architecture", confidence=0.92)
emitter.emit_lesson(
    summary="Always mock OTLP exporter in tests",
    category="testing",
    applies_to=["src/contextcore/tracker.py"]
)

# Query insights from other agents
querier = InsightQuerier()
decisions = querier.query(project_id="checkout", insight_type="decision")
```

### Human Guidance (CRD-driven)

```python
from contextcore.agent import GuidanceReader

reader = GuidanceReader(project_id="my-project")
constraints = reader.get_active_constraints()
questions = reader.get_open_questions()
```

### Resource Detector (Context Injection)

Reads K8s annotations and injects project context into all telemetry:

```python
from contextcore import ProjectContextDetector
from opentelemetry.sdk.resources import get_aggregated_resources

resource = get_aggregated_resources([ProjectContextDetector()])
# All traces/metrics/logs now include project.id, business.criticality, etc.
```

### State Persistence

Cross-process task tracking with file locking (`fcntl` on Unix, `msvcrt` on Windows):

```python
from contextcore.state import StateManager

state = StateManager(project="my-project")
# Persists to ~/.contextcore/state/<project>/
# Spans survive process restarts
```

### Contract Types (Central Enums)

All domain types are in `src/contextcore/contracts/types.py`:
- `TaskStatus`: backlog, todo, in_progress, blocked, done, cancelled
- `TaskType`: epic, story, task, subtask, bug, spike, incident
- `Priority`: critical, high, medium, low

## Architecture Decisions

| ADR | Decision | Confidence |
|-----|----------|------------|
| [001](https://github.com/Force-Multiplier-Labs/contextcore-spec/blob/main/docs/adr/001-tasks-as-spans.md) | Model tasks as OpenTelemetry spans | 0.95 |
| [002](https://github.com/Force-Multiplier-Labs/contextcore-spec/blob/main/docs/adr/002-naming-wayfinder.md) | Separate naming: ContextCore (standard) vs Wayfinder (implementation) | Accepted |

## Must Do

- Use ProjectContext CRD as the source of truth for project metadata
- Derive observability config from business metadata (criticality -> sampling rate)
- Export via OTLP (vendor-agnostic)
- Provision dashboards on install (idempotent)
- Dashboards must use ContextCore semantic conventions for all queries
- Validate CRD schema strictly with Pydantic
- Include context in all generated artifacts (alerts, dashboards)

## Must Avoid

- Duplicating context in multiple places
- Manual annotation of K8s resources (use controller)
- Storing sensitive data in ProjectContext
- Vendor-specific code in core SDK
- Over-generating artifacts (derive only what's needed)
- Using "native" in product naming (see terminology/definitions/naming-principles.yaml)

## Naming Conventions

When referring to the project:
- **"ContextCore"** = the standard, specification, semantic conventions, CRD API group
- **"Wayfinder"** = the suite of tools, the fleet, the reference implementation
- Package names (`contextcore`, `contextcore-rabbit`) stay lowercase — they implement the standard
- The `contextcore` CLI command and `contextcore.io` CRD API group are unchanged

## Wayfinder Expansion Pack Ecosystem

Animal-named packages using Anishinaabe (Ojibwe) names honoring the indigenous peoples of Michigan and the Great Lakes region:

| Package | Animal | Anishinaabe | Purpose | Status |
|---------|--------|-------------|---------|--------|
| **contextcore** | Spider | Asabikeshiinh | Core framework — tasks as spans, agent insights | beta |
| **contextcore-rabbit** | Rabbit | Waabooz | Alert automation (webhooks, parsers, actions) | beta |
| **contextcore-fox** | Fox | Waagosh | Context enrichment for alert automation | beta |
| **contextcore-coyote** | Coyote | Wiisagi-ma'iingan | Multi-agent incident resolution | beta |
| **contextcore-beaver** | Beaver | Amik | LLM provider abstraction with cost tracking | beta |
| **contextcore-squirrel** | Squirrel | Ajidamoo | Skills library for token-efficient agent discovery | beta |
| **contextcore-owl** | Owl | Gookooko'oo | Grafana plugins (**internal**, not user-facing) | internal |

### Dependency Graph

```
contextcore-beaver (LLM abstraction)
         │
         ▼
contextcore-coyote (multi-agent pipeline)
         │
         ▼
contextcore-fox (context enrichment)        contextcore-squirrel (skills library)
         │                                           │
         ▼                                           │
contextcore-rabbit (alert automation)                │
         │                                           │
         └───────────────┬───────────────────────────┘
                         ▼
                    contextcore (core)
```

## Testing

Tests use pytest with fixtures providing mock exporters and temporary state:

```bash
python3 -m pytest                          # All tests
python3 -m pytest tests/test_tracker.py    # Specific module
python3 -m pytest -k "test_start_task"     # Specific test
```

Key test files:
- `tests/test_tracker.py` — TaskTracker lifecycle (span creation, status, completion)
- `tests/test_logger.py` — TaskLogger JSON output for Loki
- `tests/test_state.py` — StateManager persistence and file locking
- `tests/test_models.py` — Pydantic model validation
- `tests/test_detector.py` — ResourceDetector K8s annotation extraction
- `tests/test_contracts.py` — Contract/type validation

## OTel GenAI Semantic Conventions

Wayfinder is migrating to [OTel GenAI Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/). The `CONTEXTCORE_EMIT_MODE` variable controls attribute emission:

| Mode | Behavior |
|------|----------|
| `dual` | Emits both `agent.*` (legacy) and `gen_ai.*` (OTel standard) — **default** |
| `legacy` | Emits only `agent.*` attributes (rollback option) |
| `otel` | Emits only `gen_ai.*` attributes (target state) |

## Kubernetes Deployment

```bash
kubectl apply -k k8s/observability/
contextcore install init --endpoint tempo.observability:4317
```

Deploys: Grafana, Tempo, Mimir, Loki, Alloy (OTLP collector).

## Documentation

- [README.md](README.md) — Vision, benefits, quick start
- [docs/EXPANSION_PACKS.md](docs/EXPANSION_PACKS.md) — Design boundaries for each pack
- [docs/INSTALLATION.md](docs/INSTALLATION.md) — Setup guide
- [docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md) — Known limitations
- [docs/semantic-conventions.md](https://github.com/Force-Multiplier-Labs/contextcore-spec/blob/main/docs/semantic-conventions.md) — Full attribute reference (spec)
- [docs/agent-communication-protocol.md](https://github.com/Force-Multiplier-Labs/contextcore-spec/blob/main/docs/agent-communication-protocol.md) — Agent integration (spec)
- [docs/adr/](https://github.com/Force-Multiplier-Labs/contextcore-spec/blob/main/docs/adr/) — Architecture decision records (spec)
