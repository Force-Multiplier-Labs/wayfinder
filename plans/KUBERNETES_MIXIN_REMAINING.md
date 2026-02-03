# Remaining Work: kubernetes-mixin Conventions, Fox, Mixin

Session date: 2026-02-03. Captures remaining tasks from the kubernetes-mixin
naming conventions, recording rules, Fox integration, and Jsonnet mixin plan.

See also: `~/Documents/dev/ContextCore/docs/PHASE3_HANDOFF.md` for broader
Phase 3 context and architecture decisions.

---

## Completed (4 commits Wayfinder, 1 commit ContextCore)

| # | Initiative | Commit | Status |
|---|-----------|--------|--------|
| 1 | Spec: recording rule + alert naming conventions | `cedc7a1` (ContextCore) | Done |
| 2 | Recording rules: Loki, Mimir, configs, dashboards, contracts | `4246c40` | Done |
| 3 | Fox: standalone package with telemetry, enricher, router, tests | `509b272` | Done |
| 4 | Mixin: scaffold, config, lib helpers, installation PoC, smoke test | `d1d7abd` | Done |

---

## Remaining Tasks

### R1. Fix validate_metric_name() for Colon-Delimited Names

**Priority**: High (blocks contract validation of recording rules)
**Repos**: Both ContextCore and Wayfinder (contracts are mirrored)

`validate_metric_name()` in `src/contextcore/contracts/metrics.py` uses:

```python
re.match(r"^[a-z][a-z0-9_]*$", name)
```

This rejects colons and CamelCase. Three naming conventions now coexist:

| Convention | Example | Current Validation |
|------------|---------|-------------------|
| Regular metrics | `gen_ai.client.token.usage` | Partial (dots not handled) |
| Recording rules | `project:contextcore_task_percent_complete:max_over_time5m` | Fails (colons) |
| Alert rules | `ContextCoreExporterFailure` | Fails (uppercase) |

**Recommendation**: Add `validate_recording_rule_name()` and
`validate_alert_rule_name()` functions, or add a `name_type` parameter to
the existing function. Update in both repos.

### R2. Vendor Spec Sync (Initiative 1.4)

**Priority**: Medium
**Repo**: Wayfinder

The vendor directory `wayfinder/vendor/contextcore-spec/` does not exist.
Either:
1. Create it and copy `docs/semantic-conventions.md` from ContextCore, or
2. Remove vendor sync from the plan if Wayfinder always reads from its own
   copy of the spec in `src/`

If creating vendor:
```
Source: ~/Documents/dev/ContextCore/docs/semantic-conventions.md
Target: ~/Documents/dev/wayfinder/vendor/contextcore-spec/docs/semantic-conventions.md
```

### R3. Fox → Rabbit Integration (Initiative 3.4)

**Priority**: Medium
**Repo**: Wayfinder (`wayfinder-fox/`)

Fox works standalone but is not wired into Rabbit's dispatch system. Need:

1. A `FoxEnrichAction` class in `wayfinder-fox/src/wayfinder_fox/actions/`
   that wraps `ProjectContextEnricher` + `CriticalityRouter`
2. Registration via `@action_registry.register("fox_enrich")` (look at
   existing Rabbit actions for the pattern)
3. When alert arrives at Rabbit with `rabbit_action: "fox_enrich"` label,
   Rabbit dispatches to `FoxEnrichAction.execute()`

Flow: Rabbit receives alert → dispatches to Fox → Fox enriches → Fox routes
→ Fox dispatches sub-actions (claude_analysis, context_notify)

### R4. Alertmanager Routing Config (Initiative 3.5)

**Priority**: Low (can be deferred until Rabbit is deployed)
**Repo**: Wayfinder

Need Alertmanager config that routes kubernetes-mixin alerts through Fox:

```yaml
route:
  receiver: 'fox-enrichment'
  routes:
    - match_re:
        alertname: 'ContextCore.*'
      receiver: 'fox-enrichment'
receivers:
  - name: 'fox-enrichment'
    webhook_configs:
      - url: 'http://rabbit.observability:8080/webhook/alertmanager'
```

Also add `rabbit_action: "fox_enrich"` label via relabeling rules.

### R5. K8s rabbit.yaml Updates (Initiative 3.7)

**Priority**: Low (can be deferred until K8s deployment)
**Repo**: Wayfinder

`k8s/observability/rabbit.yaml` does not exist in Wayfinder (it was in the
pre-separation monorepo). When creating it, include:

- Fox sidecar or separate Deployment alongside Rabbit
- RBAC: ClusterRole with `get`/`list` on `projectcontexts.contextcore.io`
  (Fox enricher needs to read ProjectContext CRDs)
- `OTEL_EXPORTER_OTLP_ENDPOINT` env var for Fox span export
- Service exposing Rabbit webhook port (8080)

### R6. Jsonnet Dependencies (Initiative 4.4)

**Priority**: High (blocks all Jsonnet operations)
**Repo**: Wayfinder (`wayfinder-mixin/`)

`jb install` has never been run. The `vendor/` directory does not exist.
Until dependencies are fetched, `jsonnet` and `make generate` will fail.

```bash
cd wayfinder-mixin && jb install
```

Requires `go-jsonnet` and `jsonnet-bundler` (jb) to be installed:
```bash
go install github.com/google/go-jsonnet/cmd/jsonnet@latest
go install github.com/jsonnet-bundler/jsonnet-bundler/cmd/jb@latest
```

### R7. Golden File Tests (Initiative 4)

**Priority**: Medium (blocks regression testing)
**Repo**: Wayfinder (`wayfinder-mixin/`)
**Blocked by**: R6

`tests/golden/` exists but is empty. After `jb install` and a successful
`make generate`, snapshot the output as golden files:

```bash
cd wayfinder-mixin
make generate
cp generated/dashboards/*.json tests/golden/
```

Then update the `test` target in the Makefile to diff against golden files.

### R8. Operational Runbook Anchors

**Priority**: Medium
**Repo**: Wayfinder

`docs/OPERATIONAL_RUNBOOK.md` exists but does **not** contain the anchors
referenced by alert `runbook_url` annotations. Need to add sections:

- `## OTLP Exporter Failure` (anchor: `#otlp-exporter-failure`)
- `## Span State Loss` (anchor: `#span-state-loss`)
- `## Insight Latency` (anchor: `#insight-latency`)
- `## Task Stalled` (anchor: `#task-stalled`)

Each section should describe: symptoms, diagnosis steps, remediation.

### R9. Expansion Pack Status Updates (Initiative 3)

**Priority**: Low
**Repos**: ContextCore

Update Fox status in:
- `docs/EXPANSION_PACKS.md` — Fox status from "Beta" to "Implemented"
  (note: imports reference `contextcore_fox` but implementation is
  `wayfinder_fox`; update import examples too)
- `.contextcore.yaml` — `ecosystem.packages[fox].status` field

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
