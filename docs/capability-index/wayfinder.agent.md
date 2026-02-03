# Wayfinder Agent Capabilities

**Version:** 1.0.0 | **Generated:** 2026-01-28 13:55

Agent-focused capabilities for ContextCore SDK.
Tasks as OTel spans, insights as knowledge, handoffs as coordination.

## Metadata

- **Owner:** force-multiplier-labs
- **Repository:** [https://github.com/Force-Multiplier-Labs/contextcore](https://github.com/Force-Multiplier-Labs/contextcore)
- **Domain:** observability
- **Tier:** sdk
- **Audience:** agent

## Capability Summary

| Capability | Category | Maturity | Confidence |
|------------|----------|----------|------------|
| [`contextcore.insight.emit`](#contextcoreinsightemit) | action | 🟢 Stable | 95% |
| [`contextcore.insight.query`](#contextcoreinsightquery) | query | 🟢 Stable | 90% |
| [`contextcore.handoff.initiate`](#contextcorehandoffinitiate) | action | 🟡 Beta | 85% |
| [`contextcore.handoff.receive`](#contextcorehandoffreceive) | action | 🟡 Beta | 80% |
| [`contextcore.guidance.read_constraints`](#contextcoreguidanceread_constraints) | query | 🟡 Beta | 85% |
| [`contextcore.guidance.answer_question`](#contextcoreguidanceanswer_question) | action | 🟡 Beta | 85% |
| [`contextcore.code_generation.contract`](#contextcorecode_generationcontract) | action | 🟡 Beta | 80% |
| [`contextcore.size_estimation.estimate`](#contextcoresize_estimationestimate) | query | 🟡 Beta | 75% |

## Table of Contents

### ⚡ Action

- [`contextcore.insight.emit`](#contextcoreinsightemit) - Emit agent-generated insights as OTel spans for cross-agent ...
- [`contextcore.handoff.initiate`](#contextcorehandoffinitiate) - Start agent-to-agent task delegation with size constraints a...
- [`contextcore.handoff.receive`](#contextcorehandoffreceive) - Poll for and process incoming handoffs as receiving agent...
- [`contextcore.guidance.answer_question`](#contextcoreguidanceanswer_question) - Answer open questions from humans with confidence and eviden...
- [`contextcore.code_generation.contract`](#contextcorecode_generationcontract) - Define code generation contracts with size limits and comple...

### 🔍 Query

- [`contextcore.insight.query`](#contextcoreinsightquery) - Query prior insights from Tempo by project, type, confidence...
- [`contextcore.guidance.read_constraints`](#contextcoreguidanceread_constraints) - Read human-defined constraints from ProjectContext CRD...
- [`contextcore.size_estimation.estimate`](#contextcoresize_estimationestimate) - Estimate code output size before generation using heuristics...

## Capabilities

### ⚡ `contextcore.insight.emit`

**🟢 Stable** | **Category:** action | **Confidence:** 95%

> Emit agent-generated insights as OTel spans for cross-agent collaboration

#### Description

Persists agent-generated knowledge as OpenTelemetry spans in Tempo. Supports
multiple insight types (decisions, blockers, lessons, etc.) with confidence
scoring and evidence linking. Insights are queryable by other agents and
visible in Grafana dashboards. Supports file-path scoping via `applies_to`
for context-specific lessons.

#### Triggers

`emit insight | record decision | log blocker | save lesson | agent knowledge`

#### Inputs

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `insight_type` | `analysis | recommendation | decision | question | blocker | discovery | risk | progress | lesson` | ✓ |  |
| `summary` | string | ✓ | Brief description of the insight |
| `confidence` | number | ✓ |  |
| `audience` | `agent | human | both` |  |  |
| `rationale` | string |  | Explanation supporting the insight |
| `evidence` | array[object] |  |  |
| `applies_to` | array[string] |  | File paths or patterns this insight applies to |
| `category` | string |  | Categorization for lessons (e.g., testing, architecture) |

#### Outputs

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string |  |  |
| `trace_id` | string |  |  |
| `timestamp` | string |  |  |

#### Evidence

- **code**: `src/contextcore/agent/insights.py` - InsightEmitter class with emit() method (lines 85-200)
- **code**: `src/contextcore/agent/insights.py` - InsightType enum defining all insight categories (lines 33-43)
- **test**: `tests/agent/test_insights.py` - Unit tests for insight emission

#### Anti-Patterns

- ⚠️ Never emit insights without confidence scores—they're required for prioritization
- ⚠️ Don't use audience=agent for blockers humans need to see

#### TraceQL Examples

**Find high-confidence decisions**
```traceql
{ span.insight.type = "decision" && span.insight.confidence > 0.8 }
```

**Find blockers for a specific project**
```traceql
{ span.insight.type = "blocker" && resource.project.id = "myproject" }
```

---

### 🔍 `contextcore.insight.query`

**🟢 Stable** | **Category:** query | **Confidence:** 90%

> Query prior insights from Tempo by project, type, confidence, or file path

#### Description

Retrieves previously emitted insights from Tempo using TraceQL queries.
Supports filtering by project, insight type, confidence threshold, time
range, and file path scope. The `get_blockers()` method specifically
retrieves unresolved blocker insights for a project.

#### Triggers

`query insights | get decisions | find blockers | search lessons | prior knowledge`

#### Inputs

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project_id` | string | ✓ |  |
| `insight_type` | `analysis | recommendation | decision | question | blocker | discovery | risk | progress | lesson` |  |  |
| `min_confidence` | number |  |  |
| `time_range` | string |  | Duration string (e.g., "24h", "7d") |
| `applies_to` | string |  | Filter by file path or pattern |
| `limit` | integer |  |  |

#### Evidence

- **code**: `src/contextcore/agent/insights.py` - InsightQuerier class with query() method (lines 397-876)
- **code**: `src/contextcore/agent/insights.py` - get_blockers() method for unresolved blockers (lines 878-883)
- **test**: `tests/agent/test_insights.py` - Query tests with various filters

#### TraceQL Examples

**Find lessons about testing**
```traceql
{ span.insight.type = "lesson" && span.insight.applies_to =~ ".*test.*" }
```

**Get summaries of high-confidence insights**
```traceql
{ span.insight.confidence >= 0.9 } | select(span.insight.summary)
```

---

### ⚡ `contextcore.handoff.initiate`

**🟡 Beta** | **Category:** action | **Confidence:** 85%

> Start agent-to-agent task delegation with size constraints and expected output

#### Description

Initiates structured task delegation between agents. The requesting agent
specifies what capability is needed, inputs, and expected output format
including size constraints (max_lines, max_tokens). Supports priority levels
and timeout configuration. Uses pluggable storage (K8s CRD or file-based).

#### Triggers

`handoff to | delegate task | agent coordination | request capability`

#### Inputs

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `to_agent` | string | ✓ | Target agent identifier |
| `capability_id` | string | ✓ | Capability being requested (e.g., "investigate_error") |
| `task` | string | ✓ | Task description |
| `inputs` | object | ✓ | Input data for the task |
| `expected_output` | object | ✓ |  |
| `priority` | `critical | high | normal | low` |  |  |
| `timeout_ms` | integer |  |  |

#### Outputs

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `handoff_id` | string |  |  |
| `status` | `pending | accepted | in_progress | completed | failed | timeout` |  |  |
| `result_trace_id` | string |  |  |
| `error_message` | string |  |  |

#### Evidence

- **code**: `src/contextcore/agent/handoff.py` - HandoffManager class with create_and_await() method (lines 119-350)
- **code**: `src/contextcore/agent/handoff.py` - ExpectedOutput dataclass with size constraints (lines 65-89)
- **test**: `tests/agent/test_handoff.py` - Handoff lifecycle tests

#### Anti-Patterns

- ⚠️ Don't set max_lines > 150 for LLM-generated code—truncation risk
- ⚠️ Always specify completeness_markers for code generation

---

### ⚡ `contextcore.handoff.receive`

**🟡 Beta** | **Category:** action | **Confidence:** 80%

> Poll for and process incoming handoffs as receiving agent

#### Description

Enables agents to receive and process delegated tasks from other agents.
Uses polling pattern with configurable interval. Receiving agent must
call complete() or fail() to update handoff status. Supports graceful
shutdown via context manager or shutdown() method.

#### Triggers

`receive handoff | poll for tasks | accept delegation | process handoff`

#### Inputs

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project_id` | string | ✓ |  |
| `poll_interval_s` | number |  |  |
| `timeout_s` | number |  | Max time to poll before returning |

#### Outputs

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string |  |  |
| `from_agent` | string |  |  |
| `to_agent` | string |  |  |
| `capability_id` | string |  |  |
| `task` | string |  |  |
| `inputs` | object |  |  |
| `expected_output` | object |  |  |

#### Evidence

- **code**: `src/contextcore/agent/handoff.py` - HandoffReceiver class with poll_handoffs() method (lines 353-470)

---

### 🔍 `contextcore.guidance.read_constraints`

**🟡 Beta** | **Category:** query | **Confidence:** 85%

> Read human-defined constraints from ProjectContext CRD

#### Description

Retrieves human-defined constraints from the ProjectContext Kubernetes CRD.
Constraints define what agents must NOT do, with severity levels (blocking,
warning, advisory). The `get_constraints_for_path()` method filters constraints
relevant to a specific file path or scope pattern.

#### Triggers

`read constraints | check rules | human guidance | project constraints`

#### Inputs

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project_id` | string | ✓ |  |
| `path` | string |  | Optional file path to filter constraints |

#### Evidence

- **code**: `src/contextcore/agent/guidance.py` - GuidanceReader class with get_constraints_for_path() (lines 96-280)
- **code**: `src/contextcore/agent/guidance.py` - Constraint dataclass with severity enum (lines 51-57)

#### Anti-Patterns

- ⚠️ Never ignore BLOCKING constraints—they are mandatory

---

### ⚡ `contextcore.guidance.answer_question`

**🟡 Beta** | **Category:** action | **Confidence:** 85%

> Answer open questions from humans with confidence and evidence

#### Description

Enables agents to answer questions posed by humans in the ProjectContext CRD.
Updates the question status to "answered" and emits an insight span containing
the answer with confidence and evidence. This creates a persistent, queryable
record of agent answers.

#### Triggers

`answer question | respond to human | provide answer`

#### Inputs

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `question_id` | string | ✓ |  |
| `answer` | string | ✓ |  |
| `confidence` | number | ✓ |  |
| `evidence` | array[object] |  |  |

#### Outputs

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `success` | boolean |  |  |
| `insight_id` | string |  |  |

#### Evidence

- **code**: `src/contextcore/agent/guidance.py` - GuidanceResponder.answer_question() method (lines 310-426)

---

### ⚡ `contextcore.code_generation.contract`

**🟡 Beta** | **Category:** action | **Confidence:** 80%

> Define code generation contracts with size limits and completeness markers

#### Description

Specialized handoff for code generation with proactive truncation prevention.
The requesting agent specifies size constraints (max_lines, max_tokens) and
required exports. The receiving agent estimates output size BEFORE generation
and triggers decomposition if limits would be exceeded. All decisions are
recorded as OTel spans.

#### Triggers

`generate code | code contract | size-limited generation | truncation prevention`

#### Inputs

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `to_agent` | string | ✓ |  |
| `spec` | object | ✓ |  |

#### Outputs

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `result` | `generated | decomposed | rejected` |  |  |
| `trace_id` | string |  |  |
| `chunks` | array[string] |  |  |

#### Evidence

- **code**: `src/contextcore/agent/code_generation.py` - CodeGenerationHandoff class with request_code() (lines 1-100)
- **code**: `src/contextcore/agent/code_generation.py` - CodeGenerationSpec dataclass (lines 77-100)

#### Anti-Patterns

- ⚠️ Never skip size estimation—truncated code is worse than no code
- ⚠️ Always specify required_exports for verification

---

### 🔍 `contextcore.size_estimation.estimate`

**🟡 Beta** | **Category:** query | **Confidence:** 75%

> Estimate code output size before generation using heuristics

#### Description

Provides heuristics-based estimation of code output size before generation.
Analyzes task description for complexity keywords and counts expected
constructs (classes, methods, functions). Returns line/token estimates
with confidence scoring. Used by code_generation.contract for pre-flight
validation.

#### Triggers

`estimate size | predict lines | output size | before generation`

#### Inputs

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `task` | string | ✓ | Task description to analyze |
| `inputs` | object |  |  |

#### Outputs

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `lines` | integer |  |  |
| `tokens` | integer |  |  |
| `complexity` | `low | medium | high` |  |  |
| `confidence` | number |  |  |
| `reasoning` | string |  |  |

#### Evidence

- **code**: `src/contextcore/agent/size_estimation.py` - SizeEstimator class with estimate() method (lines 50-100)
- **code**: `src/contextcore/agent/size_estimation.py` - Heuristic constants and keyword patterns (lines 61-96)

---

## Risk Flags

### `risk:no-retry-on-export-failure`

OTel span export failures are not retried—telemetry may be silently lost

**Affects:** `contextcore.insight.emit`, `contextcore.handoff.initiate`

### `risk:k8s-restart-loses-in-flight`

Kubernetes pod restarts may lose in-flight handoffs not yet persisted

**Affects:** `contextcore.handoff.initiate`, `contextcore.handoff.receive`

## Pivoted Work

Documented pivots to prevent re-attempting failed approaches:

### text-merge-to-ast

- **Original:** Text-based merge_files_intelligently() using diff/patch
- **Outcome:** Corrupted Python files when merging class definitions
- **Lesson:** Text-based merging is insufficient for code; use language-aware tools (AST)

### single-emit-to-dual

- **Original:** Emit task data to Tempo only (spans are sufficient)
- **Outcome:** Portfolio dashboard couldn't derive metrics from spans alone
- **Lesson:** Different backends excel at different queries; dual-emit to Tempo AND Loki

## Global Evidence

- **doc**: [`docs/semantic-conventions.md`](https://github.com/Force-Multiplier-Labs/contextcore-spec/blob/main/docs/semantic-conventions.md) - Attribute definitions for insight.*, handoff.*, agent.*
- **doc**: `inbox/OTEL_ALIGNED_MATURITY_MODEL.md` - Maturity level definitions and transition criteria

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-01-28 | Initial capability index for agent-focused capabilities; 8 capabilities indexed: insight (2), handoff (2), guidance (2), code_generation (1), size_estimation (1); Evidence verified against source files; OTel-aligned maturity: stable (2), experimental/beta (6); Risk flags and pivoted work documented |

---

*Generated by capability-index generate_markdown.py*