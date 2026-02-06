# Wayfinder

**Wayfinder** is the reference implementation of the [ContextCore](https://github.com/Force-Multiplier-Labs/contextcore-spec) metadata standard — a project management observability framework that models tasks as OpenTelemetry spans.

It eliminates manual status reporting by deriving project health from existing artifact metadata (commits, PRs, CI results) and exports via OTLP to any compatible backend.

## Core Insight

Tasks share the same structure as distributed trace spans — start time, end time, status, hierarchy, events. By storing tasks in observability infrastructure, you get unified querying, time-series persistence, and correlation with runtime telemetry.

## Architecture

Dual-telemetry emission:
- **Spans to Tempo** — hierarchy, timing, TraceQL queries
- **Structured logs to Loki** — events, status changes, metrics derivation via recording rules
- **Mimir metrics** — derived from Loki logs, not directly emitted

## Quick Start

```bash
# Install (recommended: uv workspace)
uv sync --all-extras

# Verify CLI
uv run contextcore --version

# Start the observability stack
make full-setup
# (Windows PowerShell alternative: .\setup.ps1 up)

# Track a task
uv run contextcore task start --id PROJ-123 --title "Feature" --type story
uv run contextcore task update --id PROJ-123 --status in_progress
uv run contextcore task complete --id PROJ-123

# View dashboards
open http://localhost:3000
```

## Tech Stack

- **Language**: Python 3.12+
- **CRD Framework**: kopf (Kubernetes Operator Framework)
- **Telemetry**: OpenTelemetry SDK, OTLP export
- **Reference Backend**: Grafana (Tempo, Mimir, Loki)
- **CLI**: Click
- **Models**: Pydantic v2

## Expansion Packs

Animal-named packages using Anishinaabe (Ojibwe) names honoring the indigenous peoples of Michigan and the Great Lakes region.

| Package | Animal | Anishinaabe | Purpose |
|---------|--------|-------------|---------|
| **contextcore** | Spider | Asabikeshiinh | Core framework |
| **contextcore-rabbit** | Rabbit | Waabooz | Alert automation |
| **contextcore-fox** | Fox | Waagosh | Context enrichment |
| **contextcore-coyote** | Coyote | Wiisagi-ma'iingan | Multi-agent incident resolution |
| **contextcore-beaver** | Beaver | Amik | LLM provider abstraction |
| **contextcore-squirrel** | Squirrel | Ajidamoo | Skills library |

## The ContextCore Standard

This implementation is built on the **ContextCore specification** — a vendor-agnostic metadata standard that defines how business context is structured and exchanged. The spec lives in a [separate repository](https://github.com/Force-Multiplier-Labs/contextcore-spec) and includes:

- CRD schemas (`ProjectContext`)
- Semantic conventions (attribute vocabulary)
- Agent communication protocol
- Terminology definitions

See [ADR-002](https://github.com/Force-Multiplier-Labs/contextcore-spec/blob/main/docs/adr/002-naming-wayfinder.md) for the naming decision.

## License

See [LICENSE.md](LICENSE.md) and [EQUITABLE-USE-LICENSE.md](EQUITABLE-USE-LICENSE.md).
