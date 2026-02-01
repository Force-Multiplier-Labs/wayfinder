# ContextCore Capability Roadmap Prompt

A structured workflow for adding capabilities to the ContextCore roadmap using benefit-driven design.

---

## Context

**Project**: ContextCore
**Mission**: Project management as observability—eliminate the PM data silo by treating tasks as telemetry.
**Repository**: `/Users/neilyashinsky/Documents/dev/ContextCore`

**Key Insight**: You already have observability infrastructure (Grafana, Tempo, Loki). ContextCore lets you use it for project tracking without new tools.

---

## Existing Assets

### Capability Manifests
| Manifest | Audience | Capabilities | Path |
|----------|----------|--------------|------|
| `contextcore.agent.yaml` | AI Agents | 8 | `docs/capability-index/` |
| `contextcore.user.yaml` | Users/GTM | 16 | `docs/capability-index/` |
| `contextcore.benefits.yaml` | Planning | 8 benefits | `docs/capability-index/` |

### Defined Personas
| Persona | Primary Value | Key Pain Point |
|---------|---------------|----------------|
| **Developer** | No context switching | "I update Jira, then GitHub, then Slack—same info 3 places" |
| **Project Manager** | Real-time accurate data | "Status reports are stale by the time I compile them" |
| **Engineering Leader** | Portfolio visibility | "I can't see across all projects without opening 5 tools" |
| **Operator** | Incident context | "Alert fires at 2am, I don't know why this service matters" |
| **Compliance** | Evidence trail | "Audit asks for history, I grep through chat logs" |
| **AI Agent** | Shared knowledge | "Every session I rediscover what was decided before" |

### Current Gaps (from benefits.yaml)
| Benefit ID | Name | Priority | Effort |
|------------|------|----------|--------|
| `time.status_compilation_eliminated` | Eliminate Status Compilation Time | high | medium |
| `ai.orchestration_multi` | Multi-Agent Orchestration | medium | large |

---

## Phase 1: Identify New Benefits

### Prompt

```
You are a product strategist analyzing user needs for ContextCore.

CONTEXT:
- ContextCore treats project tasks as OpenTelemetry spans
- Data flows to Tempo (traces), Loki (logs), Mimir (metrics)
- Users query via Grafana dashboards and CLI
- Existing personas: developer, project_manager, engineering_leader, operator, compliance, ai_agent

EXISTING BENEFITS (already delivered or in progress):
- time.status_updates_eliminated (delivered)
- time.status_compilation_eliminated (gap - high priority)
- visibility.portfolio_unified (delivered)
- visibility.cycle_time_realtime (partial)
- incident.context_instant (delivered)
- compliance.audit_instant (delivered)
- ai.memory_persistent (delivered)
- ai.orchestration_multi (gap - medium priority)

TASK:
Identify NEW user benefits not currently in the benefits manifest.

Sources to consider:
- User interviews or feedback
- Support tickets or common questions
- Competitor analysis
- Incident post-mortems
- AI agent observations during sessions

FOR EACH NEW BENEFIT, PROVIDE:

```yaml
- benefit_id: [domain.outcome]
  name: "[Outcome-focused name]"
  value_statement: "Users can [outcome] so they [higher-order value]"

  personas:
    - persona_id: [developer|project_manager|engineering_leader|operator|compliance|ai_agent]
      pain_point: "[First person, their words]"
      value_received: "[Specific benefit for this persona]"
      importance: [critical|high|medium|low]

  measurable_outcome: "[Quantifiable outcome]"
  measurement_method: "[How to measure]"
  baseline: "[Current state without this benefit]"

  origin:
    type: [user_interview|support_ticket|competitor|vision|incident|agent_insight]
    ref: "[reference]"
    date: [YYYY-MM-DD]

  delivered_by: []  # Empty = gap
  delivery_status: gap
  priority: [critical|high|medium|low]
  effort_estimate: [small|medium|large|unknown]
```

GUIDELINES:
- Focus on OUTCOMES, not features
- Use ContextCore's observability-first framing
- Benefits should leverage existing OTel infrastructure
- Each benefit should be independently valuable
- Prefer benefits that serve multiple personas
```

---

## Phase 2: Gap Analysis for ContextCore

### Prompt

```
You are a capability analyst evaluating gaps in ContextCore.

INPUTS:
- Benefits manifest: docs/capability-index/contextcore.benefits.yaml
- User capabilities: docs/capability-index/contextcore.user.yaml
- Agent capabilities: docs/capability-index/contextcore.agent.yaml

EXISTING INFRASTRUCTURE:
- Tempo: Trace storage (tasks as spans)
- Loki: Log storage (structured logs)
- Mimir: Metrics storage (derived metrics)
- Grafana: Dashboards and alerting
- Kubernetes: ProjectContext CRD
- Python SDK: contextcore package

TASK:
For benefit [BENEFIT_ID], analyze what's missing to deliver it.

ANALYSIS TEMPLATE:

```markdown
## Gap Analysis: [benefit_id]

### Benefit Summary
- **Name**: [benefit_name]
- **Value**: [value_statement]
- **Primary Personas**: [list]
- **Priority**: [priority]

### Current State
[What exists today that partially addresses this]

### Gap Description
[What's missing to fully deliver this benefit]

### Technical Requirements

#### Data Layer
- [ ] What data needs to be collected?
- [ ] What schema/attributes are needed?
- [ ] Where does it get stored? (Tempo/Loki/Mimir/CRD)

#### Processing Layer
- [ ] What computation/derivation is needed?
- [ ] Real-time or batch?
- [ ] What triggers the processing?

#### Presentation Layer
- [ ] How does the user see/interact?
- [ ] Dashboard? CLI? API?
- [ ] What Grafana panels are needed?

#### Integration Layer
- [ ] External systems involved?
- [ ] Git/GitHub integration?
- [ ] Other tools?

### Dependencies
- **Benefits**: [other benefit_ids this depends on]
- **Capabilities**: [existing capability_ids required]
- **Infrastructure**: [platform requirements]

### Risks
- **Technical**: [implementation risks]
- **Adoption**: [user adoption risks]
- **Dependencies**: [external dependency risks]

### Effort Estimate
- **Size**: [small|medium|large]
- **Rationale**: [why this estimate]

### Recommendation
[Priority and sequencing recommendation]
```
```

---

## Phase 3: Derive Functional Requirements

### Prompt

```
You are a requirements engineer for ContextCore.

BENEFIT: [BENEFIT_ID] - [BENEFIT_NAME]
GAP ANALYSIS: [From Phase 2]

CONTEXTCORE PATTERNS TO FOLLOW:
- Tasks are OTel spans with parent-child relationships
- Status derived from span events, not manual updates
- Metrics derived from span aggregations
- Logs structured JSON to Loki
- Dashboards query via PromQL/LogQL/TraceQL
- CLI uses Click framework
- CRDs for Kubernetes-native configuration

TASK:
Derive functional requirements to deliver this benefit.

FOR EACH REQUIREMENT:

```yaml
- id: FR-[NNN]
  description: "[What the system must do - WHAT not HOW]"
  type: [data|integration|computation|presentation|automation]

  acceptance_criteria:
    - "[Testable criterion]"

  depends_on: [FR-IDs]

  implementation_hints:
    otel_signal: [traces|logs|metrics|none]
    storage: [tempo|loki|mimir|crd|file]
    interface: [cli|api|dashboard|webhook]

  maps_to_capability: "[existing capability_id or 'new: suggested.id']"
```

REQUIREMENT CATEGORIES:

**Data Requirements** (FR-1xx):
- What spans/events/metrics need to be emitted?
- What attributes are required?

**Integration Requirements** (FR-2xx):
- What external systems are involved?
- What webhooks/APIs are needed?

**Computation Requirements** (FR-3xx):
- What derivations/aggregations are needed?
- What queries need to be supported?

**Presentation Requirements** (FR-4xx):
- What dashboards/panels are needed?
- What CLI commands are needed?

**Automation Requirements** (FR-5xx):
- What happens automatically?
- What alerts/notifications are needed?

OUTPUT:
```yaml
functional_requirements:
  benefit_id: [benefit_id]
  benefit_name: "[name]"

  requirements:
    - id: FR-101
      # ... [as above]

  implementation_order:
    - phase_1: [FR-101, FR-102]  # Foundation
    - phase_2: [FR-201, FR-301]  # Core value
    - phase_3: [FR-401]          # Polish
```
```

---

## Phase 4: Design ContextCore Capabilities

### Prompt

```
You are a capability architect for ContextCore.

INPUTS:
- Functional requirements from Phase 3
- Existing capabilities in contextcore.user.yaml and contextcore.agent.yaml
- Capability schema at capability-index/schema/capability.schema.yaml

CONTEXTCORE CAPABILITY PATTERNS:

**Naming Convention**:
- `contextcore.[domain].[action]`
- Examples: `contextcore.status.auto_derive`, `contextcore.dashboard.portfolio`

**Categories Used**:
- `action`: State-changing operations (task start, insight emit)
- `query`: Data retrieval (insight query, metrics summary)
- `observe`: Monitoring/alerting (stale detection, alert enrichment)
- `generate`: Content generation (report generation)

**Audience Split**:
- Agent capabilities → contextcore.agent.yaml (technical, terse)
- User capabilities → contextcore.user.yaml (value-focused)

TASK:
Design capabilities to implement the functional requirements.

FOR EACH CAPABILITY:

```yaml
- capability_id: contextcore.[domain].[action]
  category: [action|query|observe|generate]
  maturity: draft  # New capabilities start as draft
  summary: "[≤150 chars, searchable]"

  audiences: [human, gtm]  # or [agent, human] for technical

  description:
    agent: |
      [Terse: Input/Output/Behavior ≤200 chars]
    human: |
      [Full technical documentation ≤1000 chars]
    gtm: |
      [Value proposition ≤500 chars]

  user_benefit: |
    [Why this matters to users]

  delivers_benefit: [benefit_id]

  triggers:
    - "[discovery keyword]"

  inputs:
    type: object
    required: [field1]
    properties:
      field1:
        type: string
        description: "[description]"

  outputs:
    type: object
    properties:
      result:
        type: [type]

  evidence:
    - type: [code|api|test|doc|trace|metric|log]
      ref: "[path - can be planned]"
      description: "[what it proves]"

  confidence: 0.5  # Draft = 0.5, implemented = 0.8+

  # ContextCore-specific
  otel_integration:
    signal: [traces|logs|metrics]
    storage: [tempo|loki|mimir]
    query_language: [TraceQL|LogQL|PromQL]

  cli_command: "[contextcore subcommand if applicable]"

  # Roadmap metadata
  roadmap:
    phase: [1|2|3]
    depends_on: [capability_ids]
    estimated_effort: [small|medium|large]
    implements_frs: [FR-101, FR-102]
```

VALIDATION:
- [ ] capability_id follows contextcore.[domain].[action] pattern
- [ ] Every FR maps to at least one capability
- [ ] No capability without user_benefit
- [ ] Evidence paths are valid (even if planned)
- [ ] otel_integration specified for data capabilities
```

---

## Phase 5: Update ContextCore Manifests

### Prompt

```
You are integrating new capabilities into ContextCore's capability index.

NEW CAPABILITIES: [From Phase 4]

FILES TO UPDATE:

1. **contextcore.benefits.yaml**
   - Update delivery_status for addressed benefits
   - Add delivered_by capability links
   - Update delivery timestamps

2. **contextcore.user.yaml** (for user-facing capabilities)
   - Add new capabilities in appropriate category section
   - Update manifest version
   - Add changelog entry

3. **contextcore.agent.yaml** (for agent-facing capabilities)
   - Add new capabilities
   - Update manifest version
   - Add changelog entry

4. **Create/Update roadmap.yaml** (if doesn't exist)
   - Define phases with capability sequences
   - Include dependencies
   - Add exit criteria

CHANGELOG FORMAT:
```yaml
changelog:
  - version: "[new version]"
    date: "[YYYY-MM-DD]"
    changes:
      - "[capability_id]: [brief description]"
      - "Benefits addressed: [benefit_ids]"
```

VERSION RULES:
- New capabilities → increment MINOR (1.0.0 → 1.1.0)
- Bug fixes/clarifications → increment PATCH (1.1.0 → 1.1.1)
- Breaking changes → increment MAJOR (1.1.1 → 2.0.0)

OUTPUT:
Provide the exact edits needed for each file.
```

---

## Quick Reference: ContextCore-Specific

### OTel Signal Mapping

| User Need | OTel Signal | Storage | Query |
|-----------|-------------|---------|-------|
| Task lifecycle | Traces (spans) | Tempo | TraceQL |
| Status changes | Span events | Tempo | TraceQL |
| Audit trail | Structured logs | Loki | LogQL |
| Metrics/KPIs | Derived metrics | Mimir | PromQL |
| Configuration | CRD | Kubernetes | kubectl |

### Common TraceQL Patterns

```
# Tasks by status
{ span.task.status = "in_progress" }

# Blocked tasks
{ span.task.blocked = true }

# Tasks for a project
{ resource.project.id = "my-project" }

# Agent insights
{ span.insight.type = "decision" && span.insight.confidence > 0.8 }
```

### Common LogQL Patterns

```
# Task status changes
{job="contextcore"} | json | event_type="task.status_changed"

# Audit trail for specific task
{job="contextcore"} | json | task_id="PROJ-123"
```

### CLI Command Patterns

```bash
# Task tracking
contextcore task start --id TASK-1 --title "Feature"
contextcore task update --id TASK-1 --status in_progress
contextcore task complete --id TASK-1

# Insights
contextcore insight emit --type decision --summary "..." --confidence 0.9
contextcore insight query --project my-project --type lesson

# Metrics
contextcore metrics summary --project my-project --days 14
```

---

## Example: Adding Status Report Generation

### Input Benefit (from benefits.yaml gap)

```yaml
benefit_id: time.status_compilation_eliminated
name: "Eliminate Status Compilation Time"
priority: high
effort_estimate: medium
```

### Phase 2: Gap Analysis

```markdown
## Gap Analysis: time.status_compilation_eliminated

### Current State
- Portfolio dashboard shows live data
- Data is queryable via TraceQL/PromQL
- No export/report generation capability

### Gap
- No templated report generation
- No one-click export
- Manual formatting still required

### Technical Requirements
- Data: Already available in Tempo/Mimir
- Processing: Aggregation queries exist
- Presentation: Need report template engine
- Automation: Need CLI command and dashboard button

### Dependencies
- Benefits: visibility.portfolio_unified (delivered ✓)
- Capabilities: contextcore.dashboard.portfolio (stable ✓)
```

### Phase 3: Functional Requirements

```yaml
functional_requirements:
  benefit_id: time.status_compilation_eliminated

  requirements:
    - id: FR-301
      description: "Aggregate project status from task spans for reporting period"
      type: computation
      implementation_hints:
        otel_signal: traces
        storage: tempo
        query_language: TraceQL
      maps_to_capability: contextcore.dashboard.portfolio

    - id: FR-401
      description: "Format status data into configurable report template"
      type: presentation
      implementation_hints:
        interface: cli
      maps_to_capability: "new: contextcore.report.status_generate"

    - id: FR-402
      description: "One-click report generation from Grafana dashboard"
      type: presentation
      implementation_hints:
        interface: dashboard
      maps_to_capability: "new: contextcore.report.status_generate"
```

### Phase 4: New Capability

```yaml
- capability_id: contextcore.report.status_generate
  category: generate
  maturity: draft
  summary: "Generate formatted status reports from live project data in one click"

  audiences: [human, gtm]

  description:
    human: |
      Generate status reports directly from portfolio data. Select reporting
      period and template format (Markdown, HTML). Reports include task
      progress, blockers, velocity, and custom sections.
    gtm: |
      Reclaim 2+ hours per week spent compiling status reports. One-click
      generation from live data—always current, always consistent.

  user_benefit: "Generate accurate status reports in seconds instead of hours"
  delivers_benefit: time.status_compilation_eliminated

  triggers: ["status report", "generate report", "weekly update"]

  cli_command: "contextcore report generate --project PROJECT --format markdown"

  otel_integration:
    signal: traces
    storage: tempo
    query_language: TraceQL

  roadmap:
    phase: 2
    depends_on: [contextcore.dashboard.portfolio]
    estimated_effort: medium
    implements_frs: [FR-401, FR-402]
```

---

## Files in this Directory

| File | Purpose |
|------|---------|
| `contextcore.agent.yaml` | Agent-focused capabilities (8) |
| `contextcore.user.yaml` | User-focused capabilities (16) |
| `contextcore.benefits.yaml` | Benefits manifest (8) |
| `CONTEXTCORE_ROADMAP_PROMPT.md` | This file |

---

*ContextCore: Project management as observability.*
