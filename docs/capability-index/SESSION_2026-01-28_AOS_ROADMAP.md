# Session Summary: AOS Standards Alignment Roadmap

**Date:** 2026-01-28
**Objective:** Document OWASP AOS compliance as a ContextCore roadmap item using the benefit-driven capability workflow.

---

## What Was Done

### 1. Created Dashboard Registry

**File:** `/Users/neilyashinsky/Documents/ContextCore/DASHBOARDS.md`

Catalogued 59+ Grafana dashboards across the system:
- ContextCore core dashboards (7)
- Animal subsystem dashboards (Beaver, Squirrel, Fox)
- Proto-ContextCore systems (contextcore-fox, contextcore-startd8, contextcore-rabbit)
- Agent framework iterations (v1 through v14)
- Deployment locations (k8s, production)

### 2. Created Mole Dashboard Restoration Guide

**File:** `/Users/neilyashinsky/Documents/dev/contextcore-mole/docs/DASHBOARD_RESTORATION.md`

Documented how to use the mole subsystem to recover dashboards and their related telemetry data from Tempo trace exports.

### 3. Created Standards Alignment Document

**File:** `/Users/neilyashinsky/Documents/dev/ContextCore/docs/STANDARDS_ALIGNMENT.md`

Mapped ContextCore's implementation against:
- OpenTelemetry Semantic Conventions
- OTel GenAI Conventions
- OWASP Agent Observability Standard (AOS)
- A2A Protocol
- Model Context Protocol (MCP)

Identified alignment gaps and created a phased roadmap.

### 4. Documented AOS Compliance as Roadmap Item

Used the 5-phase workflow from `CONTEXTCORE_ROADMAP_PROMPT.md`:

| Phase | Output |
|-------|--------|
| 1. Identify Benefits | Added `interop.aos_compliance` to benefits.yaml |
| 2. Gap Analysis | Created `gap-analysis/interop.aos_compliance.md` |
| 3. Functional Requirements | Defined FR-100 through FR-201 |
| 4. Design Capabilities | Added 5 `contextcore.aos.*` capabilities |
| 5. Update Manifests | Created `roadmap.yaml`, updated versions |

---

## How It Was Done

### Phase 1: Benefit Identification

Added new benefit to `contextcore.benefits.yaml`:

```yaml
- benefit_id: interop.aos_compliance
  name: "OWASP AOS Standards Compliance"
  value_statement: "Users can integrate ContextCore with AOS-compliant agent tools..."

  personas:
    - persona_id: ai_agent
      pain_point: "My events don't follow standard formats..."
      importance: high
    - persona_id: operator
      pain_point: "Different agent frameworks emit incompatible telemetry..."
      importance: high

  delivery_status: gap
  priority: medium
  effort_estimate: medium
```

### Phase 2: Gap Analysis

Created structured gap analysis following the template:

1. **Current State** — What ContextCore already implements
2. **Gap Description** — What's missing for AOS compliance
3. **Technical Requirements** — Data, processing, presentation, integration layers
4. **Dependencies** — Benefits, capabilities, infrastructure
5. **Risks** — Technical, adoption, dependency risks
6. **Effort Estimate** — Size and rationale
7. **Recommendation** — Priority and sequencing

### Phase 3: Functional Requirements

Derived requirements from gap analysis:

| FR ID | Description | Type |
|-------|-------------|------|
| FR-100 | Emit steps/message events with AOS attributes | data |
| FR-101 | Add trigger.type to guidance for autonomous triggers | data |
| FR-102 | Add DecisionOutcome enum (Allow/Deny/Modify) | data |
| FR-103 | Add structured reason codes to decisions | data |
| FR-200 | Emit protocols/MCP events for tool access | integration |
| FR-201 | Map MCP tools to ContextCore capabilities | integration |

### Phase 4: Capability Design

Created 5 new capabilities following `contextcore.[domain].[action]` pattern:

```yaml
- capability_id: contextcore.aos.message_emit
  category: action
  maturity: draft
  delivers_benefit: interop.aos_compliance
  roadmap:
    phase: 1
    implements_frs: [FR-100]

- capability_id: contextcore.aos.decision_emit
  # ... Allow/Deny/Modify outcomes

- capability_id: contextcore.aos.trigger_emit
  # ... Autonomous trigger tracking

- capability_id: contextcore.aos.mcp_emit
  # ... MCP protocol telemetry

- capability_id: contextcore.aos.validate
  # ... Compliance validation
```

### Phase 5: Manifest Updates

1. **benefits.yaml** — Version 1.0.0 → 1.1.0
   - Added INTEROPERABILITY category
   - Updated gap_summary (now 3 gaps)
   - Added changelog entry

2. **agent.yaml** — Version 1.0.0 → 1.1.0
   - Added AOS COMPLIANCE CAPABILITIES section
   - 8 → 13 total capabilities
   - Added changelog entry

3. **roadmap.yaml** — New file
   - Tracks all 3 gap benefits
   - Defines implementation phases with exit criteria
   - Includes timeline estimates and sequencing

---

## Why It Was Done

### Business Value

1. **Interoperability** — AOS compliance enables ContextCore to work with any AOS-compliant observability tool without custom adapters.

2. **Standards Alignment** — Following OWASP standards provides credibility and reduces integration friction for enterprise adoption.

3. **Ecosystem Participation** — Positions ContextCore to contribute back to OTel and AOS communities with production-tested patterns.

### Technical Rationale

1. **Dual-Emit Pattern** — Reuses existing GenAI migration infrastructure. AOS events can be emitted alongside native spans without breaking changes.

2. **Incremental Implementation** — 5 phases allow shipping value early (Phase 1 = low effort) while deferring complex work (MCP = Phase 2).

3. **Schema Extensions** — Adds structured enums (`DecisionOutcome`, `trigger.type`) that improve queryability over freeform strings.

### Workflow Rationale

The 5-phase workflow from `CONTEXTCORE_ROADMAP_PROMPT.md` was used because:

1. **Benefit-First** — Starting with user value prevents feature creep
2. **Gap Analysis** — Structured analysis catches dependencies and risks early
3. **Traceable Requirements** — FR-xxx IDs link benefits → requirements → capabilities
4. **Manifest-Driven** — YAML manifests enable tooling (token budgets, capability discovery)
5. **Version Control** — Changelogs document evolution

---

## Files Created/Modified

```
/Users/neilyashinsky/Documents/ContextCore/
└── DASHBOARDS.md                           # NEW - Dashboard registry

/Users/neilyashinsky/Documents/dev/contextcore-mole/docs/
└── DASHBOARD_RESTORATION.md                # NEW - Mole restoration guide

/Users/neilyashinsky/Documents/dev/ContextCore/docs/
├── STANDARDS_ALIGNMENT.md                  # NEW - Standards mapping
└── capability-index/
    ├── contextcore.benefits.yaml           # UPDATED v1.1.0
    ├── contextcore.agent.yaml              # UPDATED v1.1.0
    ├── roadmap.yaml                        # NEW - Implementation phases
    └── gap-analysis/
        └── interop.aos_compliance.md       # NEW - Gap analysis
```

---

## Next Steps

Per the roadmap, recommended implementation sequence:

1. **time.status_compilation_eliminated** (high priority, medium effort)
   - Build on existing dashboard infrastructure
   - 2 phases

2. **interop.aos_compliance** (medium priority, medium effort)
   - Phase 1A-1D: AOS events (small effort each)
   - Phase 2: MCP telemetry (medium effort)

3. **ai.orchestration_multi** (medium priority, large effort)
   - Design phase first
   - 3 phases total

---

## References

- [OWASP AOS Specification](https://aos.owasp.org/spec/trace/events/)
- [OTel GenAI Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/)
- [ContextCore Roadmap Prompt](./CONTEXTCORE_ROADMAP_PROMPT.md)
- [A2A Protocol](https://a2a-protocol.org)

---

*Session completed: 2026-01-28*
