# Remaining Work: kubernetes-mixin Conventions, Fox, Mixin

Session date: 2026-02-03. Captures remaining tasks from the kubernetes-mixin
naming conventions, recording rules, Fox integration, and Jsonnet mixin plan.

See also: `~/Documents/dev/ContextCore/docs/PHASE3_HANDOFF.md` for broader
Phase 3 context and architecture decisions.

---

## Completed

| # | Initiative | Commit | Status |
|---|-----------|--------|--------|
| 1 | Spec: recording rule + alert naming conventions | `cedc7a1` (ContextCore) | Done |
| 2 | Recording rules: Loki, Mimir, configs, dashboards, contracts | `4246c40` | Done |
| 3 | Fox: standalone package with telemetry, enricher, router, tests | `509b272` | Done |
| 4 | Mixin: scaffold, config, lib helpers, installation PoC, smoke test | `d1d7abd` | Done |
| R1 | Fix validate_metric_name() + add recording rule/alert validators | `ecdda0d` (CC), `5c5395e` (WF) | Done |
| R2 | Vendor spec sync (semantic-conventions.md) | `7cf07e5` | Done |
| R3 | Fox → Rabbit integration (FoxEnrichAction) | `b28ad86` | Done |
| R4 | Alertmanager routing config for ContextCore alerts | `dffac47` | Done |
| R5 | K8s rabbit.yaml: Fox sidecar + RBAC | `ef33197` | Done |
| R6 | Jsonnet dependencies (jb install) | `60e2b0d` | Done |
| R7 | Golden file tests for wayfinder-mixin | `60e2b0d` | Done |
| R8 | Operational runbook anchors for all 4 alerts | `8fa4a6c` | Done |
| R9 | Fox status updated in EXPANSION_PACKS.md + .contextcore.yaml | `fef0e79` (ContextCore) | Done |

---

## Remaining Tasks

### R10. Remaining Dashboard Migrations (Initiative 4)

**Priority**: Low (gradual, one at a time)
**Repo**: Wayfinder (`wayfinder-mixin/`)
**Blocked by**: R6, R7

12 dashboards remain to migrate from hand-crafted JSON to Jsonnet.
Migration order (simplest first):

| # | Dashboard | Datasources | Complexity |
|---|-----------|-------------|------------|
| 1 | project-progress.json | Tempo only | Low |
| 2 | project-tasks.json | Tempo only | Low |
| 3 | skills-browser.json | Tempo only | Low |
| 4 | value-capabilities.json | Tempo only | Low |
| 5 | agent-trigger.json | Loki only | Low |
| 6 | sprint-metrics.json | Tempo only | Medium |
| 7 | project-operations.json | Tempo only | Medium |
| 8 | fox-alert-automation.json | Tempo + Loki | Medium |
| 9 | workflow.json | Mixed | Medium |
| 10 | code-generation-health.json | Mixed | Medium |
| 11 | beaver-lead-contractor.json | Tempo + Mimir | Medium |
| 12 | portfolio.json | Loki + Mimir | High |

Each migration: write .libsonnet → generate JSON → diff against existing →
update golden file → uncomment in mixin.libsonnet.

---

## Architecture Decisions (Do Not Revisit)

From PHASE3_HANDOFF.md — these decisions are encoded in committed code:

1. **Model C**: ContextCore = library (contracts). Wayfinder = deployment.
2. **`CONTEXTCORE_EMIT_MODE` > `OTEL_SEMCONV_STABILITY_OPT_IN`** precedence.
3. **Sampler factory defaults to `parentbased_always_on`** (SDK default).
4. **Propagator is idempotent** (module-level flag, safe to call multiple times).
5. **Recording rules use kubernetes-mixin colons** (deliberate deviation from
   underscore-only metric convention).

---

## Uncommitted Files to Be Aware Of

### ContextCore (unstaged, intentional)
- `src/contextcore/agent/handoff.py` — OTel GenAI span naming
- `src/contextcore/agent/insights.py` — GenAIMessage dataclass, message events

Merge carefully if your work touches these files.
