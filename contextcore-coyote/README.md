# ContextCore Coyote (Wiisagi-ma'iingan)

### Multi-Agent Incident Resolution Pipeline

*Formerly known as agent-pipeline*

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: Equitable Use](https://img.shields.io/badge/License-Equitable%20Use-green.svg)](LICENSE.md)
[![ContextCore](https://img.shields.io/badge/ContextCore-expansion%20pack-purple)](https://github.com/contextcore/contextcore)

## About the Name

**Wiisagi-ma'iingan** (wee-SAH-gee-MAH-een-gahn) is the Anishinaabe (Ojibwe) word for coyote. We use Anishinaabe names to honor the indigenous peoples of Michigan and the Great Lakes region.

In many indigenous traditions, Coyote is the **trickster**—clever, resourceful, and adaptable. Coyote solves problems in unexpected ways, learns from mistakes, and shares knowledge with others. This embodies our incident resolution pipeline: it investigates tricky production issues, designs clever fixes, and captures lessons for the future.

Learn more about our [naming convention](https://github.com/contextcore/contextcore/blob/main/docs/NAMING_CONVENTION.md).

## What is ContextCore Coyote?

Coyote is a **multi-agent incident resolution pipeline** that automates the debugging lifecycle:

```
Error Detection → Investigation → Fix Design → Implementation → Testing → Knowledge Capture
```

Each stage is handled by a specialized agent with a defined personality and expertise. The pipeline can run autonomously or with human checkpoints at each stage.

### Key Features

- **Pipeline Orchestration**: Define and execute multi-stage incident resolution workflows
- **Specialized Agents**: Pre-built agent personalities for investigation, design, implementation, testing, and learning
- **O11y Integration**: Query Prometheus, Loki, Tempo, and Pyroscope for root cause analysis
- **Knowledge Capture**: Automatically document lessons learned from each incident
- **ContextCore Telemetry**: Pipeline execution emitted as OpenTelemetry spans
- **Flexible Execution**: Run locally, in CI/CD, or as part of larger automation

## Quick Start

### Installation

```bash
pip install contextcore-coyote

# With all integrations
pip install contextcore-coyote[all]

# Just LLM support
pip install contextcore-coyote[llm]
```

### Basic Usage

```python
from contextcore_coyote import Pipeline, Incident
from contextcore_coyote.agents import Investigator, Designer, Implementer

# Create an incident from an error
incident = Incident.from_error(
    error_message="TypeError: Cannot read property 'id' of undefined",
    stack_trace="...",
    source="production-logs",
)

# Create and run the pipeline
pipeline = Pipeline(
    stages=[
        Investigator(),
        Designer(),
        Implementer(),
    ]
)

result = pipeline.run(incident)
print(result.summary())
```

### With ContextCore Integration

```python
from contextcore_coyote import Pipeline, configure
from contextcore_coyote.agents import full_pipeline

# Configure with ContextCore telemetry
configure(
    contextcore_enabled=True,
    otel_endpoint="http://localhost:4317",
)

# Use the full pre-configured pipeline
pipeline = Pipeline.full()
result = pipeline.run(incident)

# Pipeline execution is automatically traced as ContextCore spans
```

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           INCIDENT                                       │
│  Error message, stack trace, logs, context                              │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STAGE 1: INVESTIGATE                                                    │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  Investigator Agent                                              │    │
│  │  - Parse stack trace                                             │    │
│  │  - Query observability (metrics, logs, traces, profiles)        │    │
│  │  - Trace to originating PR via git blame                        │    │
│  │  - Identify root cause                                           │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│  Output: Investigation report with root cause and affected code         │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STAGE 2: DESIGN                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  Designer Agent                                                  │    │
│  │  - Analyze investigation findings                                │    │
│  │  - Propose minimal fix with preserved intent                    │    │
│  │  - Document tradeoffs and alternatives                          │    │
│  │  - Estimate risk and impact                                      │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│  Output: Fix specification with implementation guidance                  │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STAGE 3: IMPLEMENT                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  Implementer Agent                                               │    │
│  │  - Write production-quality code                                 │    │
│  │  - Match existing patterns and conventions                      │    │
│  │  - Add professional comments                                     │    │
│  │  - Create PR or patch                                            │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│  Output: Code changes ready for review                                   │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STAGE 4: TEST                                                           │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  Tester Agent                                                    │    │
│  │  - Validate fix addresses root cause                            │    │
│  │  - Check for regressions                                         │    │
│  │  - Test edge cases                                               │    │
│  │  - Provide pass/fail recommendation                             │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│  Output: Test report with validation results                             │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STAGE 5: LEARN                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  Knowledge Agent                                                 │    │
│  │  - Extract lessons from incident                                │    │
│  │  - Document patterns for future prevention                      │    │
│  │  - Update knowledge base                                         │    │
│  │  - Emit insights to ContextCore                                 │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│  Output: Lessons learned documentation                                   │
└─────────────────────────────────────────────────────────────────────────┘
```

## Agents

Each agent has a specialized personality defined in prompt templates:

### Investigator

Expert at tracing errors to their root cause:
- Parses stack traces and error messages
- Uses git blame to find originating commits/PRs
- Queries observability backends for correlated signals
- Produces investigation reports

### Designer

Architect who plans minimal, targeted fixes:
- Analyzes investigation findings
- Proposes fixes that preserve original intent
- Documents tradeoffs and alternatives
- Considers risk and rollback strategies

### Implementer

Precision coder who matches team conventions:
- Writes production-quality code
- Matches existing naming patterns
- Adds professional comments
- Creates clean, reviewable changes

### Tester

QA specialist who validates fixes:
- Confirms fix addresses root cause
- Detects potential regressions
- Tests edge cases
- Provides clear pass/fail recommendation

### Knowledge Agent

Learning specialist who captures insights:
- Extracts lessons from the incident
- Documents patterns for prevention
- Updates team knowledge base
- Emits insights to ContextCore

## Observability Integration

Coyote can query your observability stack to investigate incidents:

```python
from contextcore_coyote.o11y import O11yClient

client = O11yClient(
    prometheus_url="http://prometheus:9090",
    loki_url="http://loki:3100",
    tempo_url="http://tempo:3200",
)

# Query metrics around error time
metrics = client.query_metrics(
    query='rate(http_requests_total{status="500"}[5m])',
    start=incident.timestamp - timedelta(hours=1),
    end=incident.timestamp + timedelta(minutes=30),
)

# Search logs for context
logs = client.query_logs(
    query='{job="api"} |= "error"',
    start=incident.timestamp - timedelta(minutes=5),
    end=incident.timestamp + timedelta(minutes=5),
)

# Find related traces
traces = client.query_traces(
    query='{ status = error }',
    start=incident.timestamp - timedelta(minutes=1),
    end=incident.timestamp + timedelta(minutes=1),
)
```

## Knowledge Management

Coyote automatically captures lessons learned:

```python
from contextcore_coyote.knowledge import LessonsLearned

lessons = LessonsLearned()

# Add a lesson from an incident
lessons.add(
    incident_id="INC-123",
    category="null-reference",
    lesson="Always validate API responses before accessing nested properties",
    prevention="Add null checks or use optional chaining",
    related_files=["src/api/client.py"],
)

# Query lessons for similar incidents
relevant = lessons.query(
    categories=["null-reference", "type-error"],
    files=["src/api/"],
)
```

With ContextCore integration, lessons are emitted as agent insights:

```python
from contextcore_coyote import configure

configure(contextcore_enabled=True)

# Lessons automatically emit to ContextCore InsightEmitter
# Query them later via InsightQuerier
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `COYOTE_LLM_PROVIDER` | `anthropic` | LLM provider (anthropic, openai) |
| `ANTHROPIC_API_KEY` | — | Anthropic API key |
| `OPENAI_API_KEY` | — | OpenAI API key (if using) |
| `PROMETHEUS_URL` | — | Prometheus endpoint |
| `LOKI_URL` | — | Loki endpoint |
| `TEMPO_URL` | — | Tempo endpoint |
| `COYOTE_CONTEXTCORE_ENABLED` | `false` | Enable ContextCore integration |
| `COYOTE_OTEL_ENDPOINT` | `localhost:4317` | OTLP endpoint |

### Programmatic Configuration

```python
from contextcore_coyote import configure

configure(
    llm_provider="anthropic",
    contextcore_enabled=True,
    otel_endpoint="http://localhost:4317",
    prometheus_url="http://prometheus:9090",
    loki_url="http://loki:3100",
    tempo_url="http://tempo:3200",
)
```

## CLI Usage

```bash
# Investigate an incident from a log file
coyote investigate --log-file errors.log

# Run full pipeline on an incident
coyote run --incident INC-123

# Query lessons learned
coyote lessons list --category null-reference

# Check pipeline status
coyote status
```

## GitHub Actions Integration

Coyote can be used with GitHub Actions for automated incident response:

```yaml
name: Incident Pipeline
on:
  issues:
    types: [labeled]

jobs:
  investigate:
    if: contains(github.event.label.name, 'incident')
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install contextcore-coyote[all]
      - run: coyote investigate --issue ${{ github.event.issue.number }}
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## Philosophy: Nowledgable

Coyote embodies the **Nowledgable** philosophy:

> "The true measure of wealth is not what we extract, but what we sustain."

We use AI to **amplify human capability**, not replace human judgment:

- **Checkpoints**: Human approval between stages (configurable)
- **Transparency**: All reasoning documented and traceable
- **Learning**: Knowledge compounds with each incident
- **Empowerment**: Teams become more capable over time

## Restorative Justice Statement

This project is developed on the ancestral lands of the Anishinaabe peoples. The Coyote/Trickster archetype appears across many indigenous cultures as a teacher who learns through experience and shares wisdom with others.

We honor this tradition by:
- Using AI to capture and share knowledge
- Building systems that learn and improve
- Crediting indigenous wisdom in our naming

## License

[Equitable Use License v1.0](LICENSE.md)

## Related Projects

- [ContextCore](https://github.com/contextcore/contextcore) — Core observability framework (Spider/Asabikeshiinh)
- [contextcore-rabbit](https://github.com/contextcore/contextcore-rabbit) — Alert automation framework (Rabbit/Waabooz)
- [contextcore-fox](https://github.com/contextcore/contextcore-fox) — ContextCore alert integration (Fox/Waagosh)

---

**ContextCore Coyote (Wiisagi-ma'iingan)** — The trickster who turns incidents into insights.
