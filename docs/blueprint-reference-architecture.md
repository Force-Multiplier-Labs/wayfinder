# ContextCore: OTel Blueprint Reference Architecture

> **Phase 1 Deliverable**: Reference Architecture Documentation for Project Management Observability

---

## Summary

This blueprint outlines a strategic reference for **Platform Engineering teams** and **AI/ML Platform teams** operating in **Kubernetes environments with complex project portfolios**. It addresses the friction often found when attempting to **unify project management telemetry with runtime observability**.

By implementing the patterns in this blueprint, organizations can expect to shift from **fragmented, team-specific project tracking with manual status reporting** to **automated, telemetry-driven project health derived from artifact metadata**.

### Target Audience

| Persona | Pain Point | Value Delivered |
|---------|------------|-----------------|
| **Platform Engineers** | "Every team uses different project tracking, making portfolio health invisible" | Single telemetry model for all project data |
| **Project Managers** | "I spend hours compiling status reports from multiple sources" | Automated dashboards derived from real activity |
| **AI/ML Teams** | "AI agents can't access project context or communicate decisions" | Structured telemetry for agent insights and guidance |
| **Observability Teams** | "Runtime telemetry and project data live in separate silos" | Unified query interface across Tempo/Mimir/Loki |
| **Engineering Leadership** | "No real-time visibility into portfolio health across teams" | Executive dashboards with drill-down to task level |

### Environment Scope

- Kubernetes clusters (single or multi-tenant)
- OTLP-compatible observability backends
- Project management tools (Jira, GitHub Projects, Linear, etc.)
- AI agent workflows (Claude, GPT, custom agents)

---

## Diagnosis: Common Challenges

### Challenge 1: Fragmented Project Metadata

**Symptoms**:
- Project context scattered across Jira, Confluence, Slack, and tribal knowledge
- AI agents lack access to project requirements, risks, and design decisions
- No correlation between runtime errors and the tasks that introduced them

**Impact**:
- Engineers waste 2-3 hours/week searching for project context
- Incidents take longer to resolve due to missing business context
- AI agents make recommendations without understanding project constraints

**Root Cause**: Project management systems and observability systems evolved separately, with no shared data model.

### Challenge 2: Manual Status Reporting

**Symptoms**:
- Weekly status meetings require manual data compilation
- Progress percentages are estimates, not measurements
- Blocked tasks discovered in meetings, not in real-time

**Impact**:
- 4-6 hours/week of engineering time spent on status reporting
- Stale information drives decisions
- Blocked work remains unaddressed for days

**Root Cause**: Project status exists in human-readable formats (tickets, docs) not machine-queryable telemetry.

### Challenge 3: Human-Agent Information Asymmetry

**Symptoms**:
- AI agents can't access the same project context humans see in Jira/Confluence
- Agent decisions and lessons learned disappear when sessions end
- No way for humans to guide agent behavior with project constraints

**Impact**:
- Agents repeat mistakes or contradict prior decisions
- Human guidance requires re-stating context every session
- No audit trail of agent reasoning

**Root Cause**: Agent communication lacks structured, persistent telemetry.

### Challenge 4: Business-Technical Disconnect

**Symptoms**:
- Observability configuration doesn't reflect business importance
- Critical services have same sampling rates as internal tools
- Alerts don't include business context for prioritization

**Impact**:
- Critical incidents under-sampled, making debugging harder
- On-call engineers lack business context for triage
- Executive dashboards require manual data export

**Root Cause**: No mechanism to propagate business metadata into observability configuration.

---

## Guiding Policies

### Policy 1: Model Tasks as Spans

**Challenges Addressed**: 1, 2

Tasks share the same structure as distributed trace spans:
- Start time, end time, duration
- Status (pending → in_progress → done)
- Hierarchy (epic → story → task → subtask)
- Events (status changes, blocks, comments)

By storing tasks in trace infrastructure:
- Unified querying via TraceQL/PromQL/LogQL
- Time-series persistence with configurable retention
- Correlation with runtime spans via `project.id` attribute

```
┌─────────────────────────────────────────────────────────────┐
│  Traditional                    ContextCore                 │
│                                                             │
│  ┌──────────┐                  ┌──────────────────────────┐ │
│  │   Jira   │                  │        Tempo             │ │
│  │  (tasks) │                  │   ┌────────────────┐     │ │
│  └────┬─────┘                  │   │  Epic Span     │     │ │
│       │ manual                 │   │  ├─ Story Span │     │ │
│       ▼                        │   │  │  ├─ Task    │     │ │
│  ┌──────────┐                  │   │  │  └─ Task    │     │ │
│  │ Grafana  │                  │   └────────────────┘     │ │
│  │ (metrics)│                  │           ▲              │ │
│  └──────────┘                  │           │ TraceQL      │ │
│       ▲                        │   ┌───────┴──────┐       │ │
│       │ separate               │   │   Grafana    │       │ │
│       │                        │   └──────────────┘       │ │
│  ┌──────────┐                  └──────────────────────────┘ │
│  │  Tempo   │                                               │
│  │ (traces) │                  Same data → Same query       │
│  └──────────┘                                               │
└─────────────────────────────────────────────────────────────┘
```

### Policy 2: Derive Status from Artifacts

**Challenges Addressed**: 2, 4

Instead of asking "What's the status?", derive it from existing signals:
- Commits linked to task IDs → Work started
- PR merged → Task complete
- CI failure → Task blocked
- No activity in N days → Stale detection

This eliminates manual reporting while providing more accurate, real-time data.

| Artifact | Derived Status | Attributes Set |
|----------|----------------|----------------|
| Commit with `PROJ-123` | `in_progress` | `task.last_commit_sha` |
| PR merged | `done` | `task.completed_at` |
| CI failure | `blocked` | `task.blocked_reason` |
| PR review requested | `in_review` | `task.reviewer` |

### Policy 3: Store Agent Insights as Telemetry

**Challenges Addressed**: 3

AI agent decisions, lessons learned, and questions are valuable context that should persist beyond session boundaries. By storing them as spans in Tempo:

- **Decisions**: Architectural choices with confidence scores
- **Lessons**: Patterns learned that apply to future work
- **Questions**: Unresolved items requiring human input
- **Handoffs**: Context for agent-to-agent or agent-to-human transitions

```yaml
# Agent insight stored as span attributes
agent.id: "claude-session-123"
agent.insight.type: "decision"
agent.insight.summary: "Selected event-driven architecture for checkout"
agent.insight.confidence: 0.92
agent.insight.applies_to: ["src/checkout/events.py"]
```

### Policy 4: Propagate Business Context to Observability Config

**Challenges Addressed**: 4

Business metadata should drive technical decisions:

| Business Input | Technical Output |
|----------------|------------------|
| `criticality: critical` | `traceSampling: 1.0`, `alertPriority: P1` |
| `criticality: high` | `traceSampling: 0.5`, `alertPriority: P2` |
| `criticality: medium` | `traceSampling: 0.1`, `alertPriority: P3` |
| `requirement.latency_p99: 200ms` | PrometheusRule threshold |
| `risk.priority: P1` | Extended audit logging |

This ensures observability investment scales with business importance.

---

## Coherent Actions

### Action 1: Deploy ProjectContext CRD

**Policies Supported**: 1, 4

Create a Kubernetes Custom Resource Definition as the source of truth for project metadata.

```yaml
apiVersion: contextcore.io/v1
kind: ProjectContext
metadata:
  name: checkout-service
  namespace: commerce
spec:
  project:
    id: "commerce-platform"
    epic: "EPIC-42"
  business:
    criticality: critical
    owner: commerce-team
    value: revenue-primary
  requirements:
    availability: "99.95"
    latencyP99: "200ms"
  risks:
    - risk: "Payment gateway timeout"
      priority: P1
      mitigation: "Circuit breaker with fallback"
  design:
    adr: "docs/adr/001-event-driven-checkout.md"
    doc: "https://docs.internal/checkout-redesign"
```

**Documentation**: [CRD Schema Reference](https://github.com/forcemultiplier-labs/contextcore-spec/blob/main/crds/projectcontext.yaml)

### Action 2: Configure TaskTracker SDK

**Policies Supported**: 1, 2

Initialize the TaskTracker to emit task spans to your OTLP endpoint.

```python
from contextcore import TaskTracker

# Initialize with project context
tracker = TaskTracker(
    project_id="commerce-platform",
    otlp_endpoint="http://tempo:4317"
)

# Start a task (creates span)
tracker.start_task(
    task_id="PROJ-123",
    title="Implement checkout flow",
    task_type="story",
    parent_id="EPIC-42"
)

# Update status (adds span event)
tracker.update_status("PROJ-123", "in_progress")

# Complete task (ends span)
tracker.complete_task("PROJ-123")
```

**Documentation**: [TaskTracker API](../src/contextcore/tracker.py)

### Action 3: Configure Agent Insight Emission

**Policies Supported**: 3

Enable AI agents to persist decisions and lessons as queryable telemetry.

```python
from contextcore.agent import InsightEmitter

emitter = InsightEmitter(
    project_id="commerce-platform",
    agent_id="claude-checkout-session"
)

# Emit a decision
emitter.emit_decision(
    summary="Selected event-driven architecture for order processing",
    confidence=0.92,
    rationale="Decouples payment from fulfillment, enables retry",
    context={"file": "src/checkout/events.py"}
)

# Emit a lesson learned
emitter.emit_lesson(
    summary="Always mock payment gateway in integration tests",
    category="testing",
    applies_to=["src/checkout/tests/"]
)
```

**Documentation**: [Agent Communication Protocol](https://github.com/forcemultiplier-labs/contextcore-spec/blob/main/docs/agent-communication-protocol.md)

### Action 4: Provision Grafana Dashboards

**Policies Supported**: 1, 4

Auto-provision dashboards that use ContextCore semantic conventions.

```bash
# Provision on install
contextcore dashboards provision --grafana-url http://localhost:3000

# Or via Helm
helm install contextcore contextcore/contextcore \
  --set grafana.url=http://grafana:3000 \
  --set dashboards.autoProvision=true
```

Two dashboards are provisioned:

1. **Project Portfolio Overview**: Cross-project health matrix, blocked tasks, velocity trends
2. **Project Details**: Sprint burndown, Kanban board, cycle time, blocker analysis

**Documentation**: [Dashboard Specifications](dashboards/)

### Action 5: Configure Value-Based Derivation

**Policies Supported**: 4

Enable automatic derivation of observability config from business metadata.

```yaml
# In ProjectContext CRD
spec:
  business:
    criticality: critical
  observability:
    # These are auto-derived from criticality if not specified
    traceSampling: 1.0      # 100% for critical
    metricsInterval: 10s    # Frequent for critical
    alertChannels:
      - commerce-oncall
      - executive-dashboard
```

The ContextCore controller watches `ProjectContext` resources and generates:
- `PrometheusRule` for SLO alerts
- Sampling configuration for the OTel Collector
- Dashboard placement based on business value

---

## Reference Architectures

The patterns described above have been implemented by:

### ContextCore Project (Dogfooding)

**Environment**: Single Kubernetes cluster, Grafana stack (Tempo/Mimir/Loki)

**Value Realized**:
- Eliminated manual status reporting for ContextCore development
- AI agents (Claude) access project context via TraceQL
- Decisions and lessons persist across coding sessions
- 90%+ alignment with OTel Blueprint Template principles

**Implementation Details**: This repository serves as the reference implementation.

---

## Appendix: Semantic Conventions Summary

### Core Namespaces

| Namespace | Purpose | Example Attributes |
|-----------|---------|-------------------|
| `project.*` | Project identification | `project.id`, `project.epic` |
| `task.*` | Task tracking | `task.id`, `task.status`, `task.type` |
| `sprint.*` | Sprint tracking | `sprint.id`, `sprint.velocity` |
| `business.*` | Business context | `business.criticality`, `business.owner` |
| `requirement.*` | SLO requirements | `requirement.latency_p99` |
| `risk.*` | Risk tracking | `risk.type`, `risk.priority` |
| `agent.*` | Agent telemetry | `agent.id`, `agent.insight.type` |

### Full Reference

See [Semantic Conventions](https://github.com/forcemultiplier-labs/contextcore-spec/blob/main/docs/semantic-conventions.md) for complete attribute definitions.

---

## Value Proposition Summary

| Persona | Before ContextCore | After ContextCore |
|---------|-------------------|-------------------|
| **Platform Engineer** | 3 hrs/week compiling portfolio status | Real-time dashboard, zero manual work |
| **Project Manager** | Status meetings rely on stale data | Live progress derived from commits/PRs |
| **AI Agent** | No access to project context | TraceQL queries for decisions, risks, requirements |
| **On-Call Engineer** | Incidents lack business context | Alerts include criticality, owner, runbook links |
| **Executive** | Weekly PDF reports | Self-serve drill-down from portfolio to task |

---

*This reference architecture was developed following the [OTel Blueprint Template](https://github.com/open-telemetry/community/blob/main/projects/otel-blueprints.md) structure.*
