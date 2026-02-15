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
- **Defense in Depth**: Validation gates between every stage enforce typed contracts and integrity chains
- **Typed Stage Contracts**: Pydantic models for each stage's output replace the god-object `StageResult`
- **HOWL Watcher**: Human-Orchestrated Watchdog Loop that monitors for errors and auto-dispatches the pipeline
- **Error Evaluation**: Dual-filter system (skip blocklist + positive allowlist) with observe mode for tuning
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

## Defense in Depth: Validation Gates

Coyote implements **Defense in Depth** principles between every pipeline stage. Validation gates catch contract violations at each handoff, preventing cascading failures from bad stage outputs.

### Principles

| Principle | Gate | What it Enforces |
|-----------|------|------------------|
| P1: Validate at Boundary | **SchemaGate** | Output matches expected Pydantic model |
| P2: Treat as Adversarial | **CompletenessGate** | Required fields contain meaningful content |
| P3: Checksums as Circuit Breakers | **IntegrityGate** | Context fingerprint chain is unbroken |
| P4: Fail Loud, Early, Specific | **QualityGate** | Output quality above threshold (no placeholders) |

### Gate Types

**SchemaGate** — Validates output type matches `STAGE_OUTPUT_REGISTRY` and status is terminal (not PENDING/RUNNING). Blocking on failure.

**CompletenessGate** — Checks summary length (default 10+ chars), failed stages have error messages, completed stages have `completed_at` timestamps and non-empty details. Configurable:

```python
from contextcore_coyote.pipeline.gates import CompletenessGate

gate = CompletenessGate(
    min_summary_length=20,
    require_details_on_success=True,
)
```

**IntegrityGate** — Verifies SHA256 context fingerprints chain from the original incident through every stage. A broken chain means a stage is operating on stale/modified data. Always blocking (`ViolationSeverity.CRITICAL`):

```python
from contextcore_coyote.pipeline.gates import IntegrityGate

gate = IntegrityGate(expected_fingerprint="a1b2c3d4e5f6g7h8")
```

**QualityGate** — Soft gate checking output quality heuristics. Detects placeholder phrases ("todo", "not implemented", "lorem ipsum"). Non-blocking by default, blocking in strict mode:

```python
from contextcore_coyote.pipeline.gates import QualityGate

gate = QualityGate(min_details_length=50, strict=False)
```

**CompositeGate** — Combines multiple gates into a single validation checkpoint. Aggregates violations, warnings, and evidence from all sub-gates:

```python
from contextcore_coyote.pipeline.gates import CompositeGate, standard_gate, strict_gate

# Pre-built configurations
gate = standard_gate()       # SchemaGate + CompletenessGate + QualityGate
gate = strict_gate()         # All of the above + IntegrityGate (all strict)
gate = strict_gate(expected_fingerprint="abc123")  # With integrity chain
```

### Gate Results

Every gate returns a `GateResult` with structured diagnostics:

```python
from contextcore_coyote.pipeline.contracts import GateResult, ContractViolation, ViolationSeverity

result = gate.validate(stage_output)
print(result.summary())           # "Gate 'schema' PASSED" or "FAILED with 2 error(s)"
print(result.passed)              # bool
print(result.blocking)            # Should pipeline stop?
print(result.violations)          # List[ContractViolation] — errors
print(result.warnings)            # List[ContractViolation] — non-blocking issues
print(result.evidence)            # List[Evidence] — diagnostic proof
```

## Typed Stage Contracts

Each pipeline stage produces a **typed Pydantic model** instead of a generic `StageResult` god-object. This enforces structure at the boundary — stages can only set fields they're supposed to.

### Stage Output Types

| Stage | Output Class | Required Fields |
|-------|-------------|-----------------|
| Investigate | `InvestigationOutput` | `root_cause` (min 10 chars), `affected_files` |
| Design | `DesignOutput` | `fix_summary` (min 10 chars), `proposed_solution` (min 20 chars) |
| Implement | `ImplementationOutput` | `code_changes` dict |
| Test | `ValidationOutput` | `tests_passed` bool |
| Learn | `LessonOutput` | `lessons` list |

All types share a common base (`StageOutput`) with: `stage_name`, `status`, `summary`, `details`, `started_at`, `completed_at`, `error`, `context_fingerprint`.

```python
from contextcore_coyote.pipeline.contracts import (
    InvestigationOutput, DesignOutput, ImplementationOutput,
    ValidationOutput, LessonOutput, STAGE_OUTPUT_REGISTRY,
    fingerprint, adapt_legacy_result,
)
from contextcore_coyote.models import StageStatus

# Create typed output
output = InvestigationOutput(
    status=StageStatus.COMPLETED,
    summary="Root cause identified: null reference in user handler",
    root_cause="UserHandler.get_profile() does not check for None user_id",
    affected_files=["src/handlers/user.py", "src/models/user.py"],
    severity_assessment="HIGH — affects all authenticated endpoints",
    recommended_steps=["Add null check", "Add regression test"],
    context_fingerprint=fingerprint("original-incident-data"),
)

# Convert legacy StageResult to typed output
typed = adapt_legacy_result(legacy_stage_result)
```

### Context Fingerprinting

SHA256 fingerprints chain integrity from the original incident through every stage. If a downstream stage receives a fingerprint that doesn't match what it expects, the `IntegrityGate` halts the pipeline:

```python
from contextcore_coyote.pipeline.contracts import fingerprint

fp = fingerprint("incident error text")  # Returns 16-char hex string
```

## Modular Pipeline

The `ModularPipeline` wraps typed stages with validation gates at every boundary. It supports both new typed stages and legacy HOWL stages via `LegacyStageAdapter`.

```python
from contextcore_coyote.pipeline.modular import ModularPipeline
from contextcore_coyote.pipeline.gates import standard_gate, strict_gate

pipeline = ModularPipeline(
    gate=standard_gate(),                        # Default gate at every boundary
    auto_proceed=True,                           # Skip human approval prompts
    on_stage_complete=lambda output: print(f"Stage {output.stage_name}: {output.status}"),
    on_gate_failed=lambda result: False,         # Return True to override and continue
)

# Override gate at a specific boundary (e.g., strict after investigation)
pipeline.set_gate_after(0, strict_gate(expected_fingerprint=fp))

# Run the pipeline
result = pipeline.run(
    incident=incident,
    project_root="/path/to/project",
    project_name="my-service",
    project_language="python",
)

# Inspect results
print(result.status)                  # "completed", "failed", "gate_failed"
print(result.successful)              # All stages passed AND all gates passed
print(result.diagnostic_summary())    # Answers: What failed? Why? What next?
print(result.all_violations)          # Aggregated from all gate results
print(result.duration_seconds)        # Total pipeline time
```

## HOWL Watcher

The **Human-Orchestrated Watchdog Loop** (HOWL) is a file-based error monitoring system that watches for errors from multiple sources and dispatches the Coyote pipeline when issues are detected.

### Starting the Watcher

```bash
# Start in observe mode (default — logs verdicts, pipeline OFF)
./scripts/run_coyote_watcher.sh

# Start with pipeline enabled
OBSERVE=0 ./scripts/run_coyote_watcher.sh

# Background with custom options
POLL_INTERVAL=5 AUTO_APPLY=1 OBSERVE=0 ./scripts/run_coyote_watcher.sh &
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OBSERVE` | `1` | Observe mode: log verdicts only, pipeline OFF. Set `0` to enable. |
| `POLL_INTERVAL` | `10` | Seconds between scans |
| `AUTO_APPLY` | `0` | Auto-apply generated fixes to disk |
| `FORCE` | `0` | Bypass skip filter |
| `SEVERITY` | `HIGH` | Minimum severity for dispatch |
| `HOWL_PAUSE` | `10` | Seconds to display HOWL banner before pipeline starts |
| `PROJECT_ROOT` | `~/Documents/dev/startd8-sdk` | Project root for error store |
| `OUTPUT_DIR` | `out/manifest-generate-ingestion` | Directory to scan for errors |

### Error Sources

The watcher ingests errors from four sources:

1. **Checkpoint errors** — `checkpoints/*.checkpoint.json` (pipeline phase failures)
2. **Workflow results** — `workflow-result.json`, `implement-workflow-result.json`
3. **startd8 error store** — `.startd8/task_errors/errors.jsonl` and per-error JSON files
4. **Task errors** — `PI-*-error.json`, `PI-*-error.txt`, `PI-*-result.json` with `success=false`

### Observe Mode

Observe mode (default ON) evaluates every error through the skip filter and positive filter, logging `ALLOW` or `DENY` verdicts without dispatching the pipeline. This is the recommended way to tune filters before enabling the pipeline:

```
[OBSERVE] DENY cost_budget  — not a code bug — "CostBudgetExceeded: $2.50 > $2.00"
[OBSERVE] DENY llm_parse    — not a code bug — "JSONDecodeError: Expecting value"
[OBSERVE] ALLOW runtime_error — "UnboundLocalError: local variable 'result'..."
```

Set `OBSERVE=0` to enable the full HOWL pipeline.

### Test Workflow Filter

Errors from test workflows are automatically skipped. Workflows matching these prefixes are filtered: `test-`, `test_`, `pytest-`, `unittest-`, `dry-run-`.

## Error Evaluation

Coyote uses a dual-filter system to determine whether an error is suitable for automated resolution.

### Skip Filter (Blocklist)

28 regex categories identify errors that Coyote **cannot fix** — infrastructure issues, configuration problems, cost limits, etc. If an error matches any skip pattern, it is immediately rejected.

| Category | What it Catches |
|----------|----------------|
| `auth` | 401/403, unauthorized, credential failures |
| `rate_limit` | 429, throttle, quota exceeded |
| `infrastructure` | Connection refused, DNS, 502-504 |
| `tls` | Certificate errors |
| `resources` | OOM, disk full |
| `cost_budget` | Cost limit exceeded |
| `llm_parse` | LLM JSON parsing failures |
| `quality_gate` | Output quality gate failures |
| `validation_config` | Workflow misconfiguration |
| `pipeline_orchestration` | Generic pipeline failures |
| `timeout` | Assessment/evaluation timeouts |
| `api_key_missing` | Missing environment variables |
| `dependency_missing` | pip install needed |
| `handler_config` | Workflow setup changes |
| `schema_drift` | Re-export needed |
| `validation_review` | Prompt design issues |
| `coyote_self` | Recursion guard (never fix the fixer) |
| `truncation` | Output hit max_tokens |
| `safety_filter` | Provider content policy blocks |
| `model_unavailable` | Model API access issues |
| `circuit_breaker` | Resilience pattern firing |
| `max_retries` | Persistent transient failures |
| `env_blocked` | Missing tools (git, npm, etc.) |
| `context_window` | Input too large for model |
| `multifile_incomplete` | LLM output cut off mid-file |
| `loc_mismatch` | Size estimation wrong |

### Positive Filter (Allowlist)

4 regex categories identify errors that **look like code bugs** and are good candidates for automated resolution:

| Category | What it Matches |
|----------|----------------|
| `runtime_error` | `UnboundLocalError`, `NameError`, `AttributeError`, `TypeError`, `KeyError`, `IndexError` |
| `assertion` | `AssertionError` (non-test contexts) |
| `traceback_src` | File tracebacks in `src/` or `lib/` directories |
| `exception_chain` | Full traceback chains with runtime errors |

### Evaluation Logic

The skip filter takes precedence. An error must pass the skip filter AND match a positive pattern to be allowed:

```python
from scripts.dev_repair import evaluate_error

verdict = evaluate_error("UnboundLocalError: local variable 'result' referenced before assignment")
# {"allow": True, "positive_match": "runtime_error", "skip_match": None,
#  "reason": "Allowed (runtime_error): looks like a code bug"}

verdict = evaluate_error("CostBudgetExceeded: $2.50 exceeds limit $2.00")
# {"allow": False, "positive_match": None, "skip_match": "cost_budget",
#  "reason": "cost_budget"}
```

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

### CoyoteConfig

All configuration is managed via `CoyoteConfig`, loaded from environment variables or set programmatically.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| **LLM** | | |
| `COYOTE_LLM_PROVIDER` | `anthropic` | LLM provider (`anthropic`, `openai`) |
| `COYOTE_LLM_MODEL` | `claude-sonnet-4-20250514` | Model to use |
| `ANTHROPIC_API_KEY` | — | Anthropic API key |
| `OPENAI_API_KEY` | — | OpenAI API key (if using) |
| **Pipeline** | | |
| `COYOTE_AUTO_PROCEED` | `false` | Skip human approval checkpoints |
| `COYOTE_MAX_RETRIES` | `3` | Max retries per stage |
| `COYOTE_TIMEOUT_SECONDS` | `300` | Stage timeout (seconds) |
| **Observability** | | |
| `PROMETHEUS_URL` | — | Prometheus endpoint |
| `LOKI_URL` | — | Loki endpoint |
| `TEMPO_URL` | — | Tempo endpoint |
| `PYROSCOPE_URL` | — | Pyroscope endpoint |
| **ContextCore** | | |
| `COYOTE_CONTEXTCORE_ENABLED` | `false` | Enable ContextCore telemetry |
| `COYOTE_OTEL_ENDPOINT` | `localhost:4317` | OTLP endpoint |
| `COYOTE_OTEL_SERVICE_NAME` | `contextcore-coyote` | OTel service name |
| **GitHub** | | |
| `GITHUB_TOKEN` | — | GitHub personal access token |
| `GITHUB_REPOSITORY` | — | GitHub repo (`owner/repo`) |
| **Other** | | |
| `COYOTE_USE_STARTD8` | `false` | Use Beaver/startd8 LLM abstraction |
| `COYOTE_LESSONS_FILE` | `LESSONS_LEARNED.md` | Knowledge base file path |
| `COYOTE_LOG_LEVEL` | `INFO` | Log level |

### Programmatic Configuration

```python
from contextcore_coyote import configure
from contextcore_coyote.config import CoyoteConfig

# From environment (recommended)
config = CoyoteConfig.from_env()

# Programmatic with OTel auto-setup
configure(
    llm_provider="anthropic",
    llm_model="claude-sonnet-4-20250514",
    contextcore_enabled=True,
    otel_endpoint="http://localhost:4317",
    prometheus_url="http://prometheus:9090",
    loki_url="http://loki:3100",
    tempo_url="http://tempo:3200",
    auto_proceed=True,
)
```

## CLI Reference

### `coyote investigate`

Investigate an incident from various sources:

```bash
coyote investigate --log-file errors.log          # From log file
coyote investigate --error "TypeError: ..."        # From error string
coyote investigate --issue 42                      # From GitHub issue
coyote investigate --log-file errors.log --output json --debug
```

Options: `--log-file/-f`, `--error/-e`, `--issue/-i`, `--output/-o` (text|json), `--debug`

### `coyote run`

Run the full pipeline on an incident:

```bash
coyote run --incident INC-123                     # Full pipeline
coyote run --incident INC-123 --stages investigate  # Single stage
coyote run --incident INC-123 --auto              # No human checkpoints
coyote run --incident INC-123 --output json
```

Options: `--incident/-i` (required), `--stages/-s` (full|investigate|design-implement), `--auto`, `--output/-o` (text|json)

### `coyote lessons`

Manage the knowledge base:

```bash
coyote lessons list                               # All lessons
coyote lessons list --category null-reference      # Filter by category
coyote lessons list --file src/api/ --limit 10     # Filter by file path
coyote lessons list --search "timeout"             # Full-text search
coyote lessons add --incident INC-123 --category type-error \
    --lesson "Validate inputs" --prevention "Add type checks" \
    --file src/api/handler.py --tag python --tag validation
coyote lessons categories                          # List all categories
```

### `coyote config`

Display current configuration (LLM provider, model, endpoints, features):

```bash
coyote config
```

### `coyote status`

Health check for all Coyote dependencies:

```bash
coyote status
# Checks: LLM availability, observability stack, GitHub token, knowledge base
```

### `pup` CLI

Quick-start companion for stack diagnostics:

```bash
pup                                               # Launch TUI (welcome screen)
pup launch --screen install                        # TUI: specific screen
pup check                                          # Health check (Grafana, Prom, Loki, Tempo)
pup check --json                                   # JSON output
pup hello                                          # Smoke test: send test log to Loki
pup hello --no-animation                           # Skip the pup animation
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
