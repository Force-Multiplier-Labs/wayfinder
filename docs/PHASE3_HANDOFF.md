# Phase 3 Handoff: What You Need to Know

Session date: 2026-02-03 (updated 2026-02-12). This document captures context
from Phase 3 implementation for the agent picking up remaining work.

---

## Summary

Phase 3 focused on three strategic areas:
1. **OTel Propagation & Mixin Infrastructure** — COMPLETE
2. **Phase 3 Strategic Features** (Knowledge Graph, Agent Learning Loop, VSCode Extension) — COMPLETE
3. **Fox/Rabbit/Mixin Integration** — COMPLETE

All originally-identified remaining work items (R1-R9) have been completed.
See `plans/KUBERNETES_MIXIN_REMAINING.md` for the full tracking table.

---

## What Was Done (Phase 3 Foundation)

### Wayfinder Commits

| Commit | Summary |
|--------|---------|
| `3e01296` | Phase 3 OTel propagation: sampler factory, W3C baggage, A2A trace middleware, `get_emit_mode()` with `OTEL_SEMCONV_STABILITY_OPT_IN` |
| `4246c40` | Deploy kubernetes-mixin recording rules and alerts (Loki rules, Mimir rules, docker-compose mounts, K8s ConfigMaps, portfolio dashboard updated to use new metric names) |
| `509b272` | Add wayfinder-fox package (standalone enricher, not yet wired to Rabbit) |
| `d1d7abd` | Add wayfinder-mixin Jsonnet scaffold (libsonnet files, Makefile, smoke test) |

### ContextCore Commits

| Commit | Summary |
|--------|---------|
| `bd05662` | Phase 3 contracts: `get_emit_mode()` with `OTEL_SEMCONV_STABILITY_OPT_IN`, `RecordingRuleName` enum (6 members), `AlertRuleName` enum (4 members) |
| `cedc7a1` | kubernetes-mixin naming conventions added to `docs/semantic-conventions.md` (recording rule naming pattern, alert naming pattern, updated Loki rule YAML examples) |

### Completed Follow-Up Items (R1-R9)

| # | Initiative | Status |
|---|-----------|--------|
| R1 | Fix `validate_metric_name()` + add recording rule/alert validators | ✅ Done |
| R2 | Vendor spec sync (`semantic-conventions.md`) | ✅ Done |
| R3 | Fox → Rabbit integration (`FoxEnrichAction`) | ✅ Done |
| R4 | Alertmanager routing config for ContextCore alerts | ✅ Done |
| R5 | K8s `rabbit.yaml`: Fox sidecar + RBAC | ✅ Done |
| R6 | Jsonnet dependencies (`jb install`) | ✅ Done |
| R7 | Golden file tests for wayfinder-mixin | ✅ Done |
| R8 | Operational runbook anchors for all 4 alerts | ✅ Done |
| R9 | Fox status updated in `EXPANSION_PACKS.md` + `.contextcore.yaml` | ✅ Done |

---

## Phase 3 Strategic Features — COMPLETE

### Feature 3.1: Project Knowledge Graph

**Location**: `src/contextcore/graph/`

| File | Purpose |
|------|---------|
| `schema.py` | `NodeType`, `EdgeType` enums; `Node`, `Edge`, `Graph` dataclasses |
| `builder.py` | `GraphBuilder` class — builds graph from ProjectContext CRDs |
| `queries.py` | `GraphQueries` class — impact analysis, dependency reports, path finding |
| `cli.py` | Click commands: `graph build`, `graph impact`, `graph deps`, `graph path` |
| `__init__.py` | Package exports |

**CLI Usage**:
```bash
contextcore graph build --output graph.json
contextcore graph impact --project my-project --depth 3
contextcore graph deps --project my-project
contextcore graph path --from proj-a --to proj-b
```

### Feature 3.2: VSCode Extension

**Location**: `extensions/vscode/`

Fully scaffolded TypeScript VSCode extension with:
- **Context Providers**: Local config, CLI, Kubernetes — loads `ProjectContext`
- **Context Mapper**: Maps files to their relevant `ProjectContext`
- **Status Bar**: Shows project criticality with icons (flame, warning, etc.)
- **Side Panel**: Tree view with project, business, risks, requirements, targets
- **Decorations**: Inline SLO hints near HTTP handlers, gutter icons for files in risk scope
- **Commands**: `contextcore.refresh`, `contextcore.showImpact`, `contextcore.openDashboard`, `contextcore.showRisks`

**Build**:
```bash
cd extensions/vscode
npm install
npm run compile
```

### Feature 3.3: Agent Learning Loop

**Location**: `src/contextcore/learning/`

| File | Purpose |
|------|---------|
| `models.py` | `Lesson`, `LessonCategory`, `LessonSource`, `LessonQuery`, `LessonApplication` |
| `emitter.py` | `LessonEmitter` — emit lessons as OTel spans to Tempo |
| `retriever.py` | `LessonRetriever` — query lessons from Tempo via TraceQL |
| `loop.py` | `LearningLoop` — high-level integration for agent workflows |
| `__init__.py` | Package exports |

**Usage**:
```python
from contextcore.learning import LearningLoop

loop = LearningLoop(project_id="my-project", agent_id="claude-code")

# Before starting work
lessons = loop.before_task(task_type="testing", files=["src/auth/oauth.py"])
for lesson in lessons:
    print(f"Tip: {lesson.summary}")

# After completing work
loop.after_task_blocker(
    blocker="OAuth token refresh failed in tests",
    resolution="Mock the token refresh endpoint in conftest.py",
    affected_files=["tests/conftest.py", "src/auth/oauth.py"]
)
```

---

## Remaining Work

### R10. Dashboard Migrations (Low Priority)

**Repo**: Wayfinder (`wayfinder-mixin/`)

12 dashboards remain to migrate from hand-crafted JSON to Jsonnet. See
`plans/KUBERNETES_MIXIN_REMAINING.md` for the full migration order. This is
gradual, low-priority work — existing JSON dashboards continue to work.

### R11. Coyote Integration with Dev Mode

Recent commits (`42e4fab`, `cc711bf`) added dev mode auto-repair with Coyote
pipeline. The integration is working but could use:
- More robust error handling in the watcher script
- Documentation of the dev mode workflow

### R12. Manifest Generation Tooling (In Progress)

Several `scripts/run_manifest_generate_*.sh` scripts exist for automating
ContextCore manifest generation. These are being developed but not yet
documented. See `plans/wayfinder-contextcore-manifest-generate-plan.md`.

---

## Architecture Decisions (Do Not Revisit)

These decisions are encoded in committed code:

1. **Model C confirmed**: ContextCore = library (contracts, types, enums).
   Wayfinder = deployment (sampler wiring, propagator setup, middleware, rules).
   Litmus test: "Would a third-party developer need this?" Yes = ContextCore.

2. **`CONTEXTCORE_EMIT_MODE` takes precedence over `OTEL_SEMCONV_STABILITY_OPT_IN`**.
   The project-specific env var wins. The OTel standard var is a fallback.
   Token to match: `gen_ai_latest_experimental`. Both repos have this logic.

3. **Sampler factory defaults to `parentbased_always_on`** (SDK default).
   No behavior change unless env vars are set. This is intentional — sampling
   is a deployment concern, not a library default.

4. **Propagator is idempotent**. `configure_propagator()` uses a module-level
   flag. Safe to call from both `TaskTracker.__init__` and `A2AServer.__init__`.

5. **Recording rule names use kubernetes-mixin convention** with colons.
   This is a deliberate deviation from the metric naming convention (underscores
   only). The enum docstrings explain the pattern.

---

## Current Uncommitted Files in Wayfinder

As of 2026-02-12, the following files are modified or untracked:

### Modified (staged changes)

| File | Content |
|------|---------|
| `.contextcore.yaml` | Project metadata updates |
| `CLAUDE.md` | Documentation updates |
| `docs/capability-index/wayfinder.agent.yaml` | Agent capability manifest |
| `docs/capability-index/wayfinder.benefits.yaml` | Benefits manifest |
| `docs/capability-index/wayfinder.pain_points.yaml` | Pain points documentation |
| `docs/capability-index/wayfinder.user.yaml` | User capability manifest |
| `k8s/observability/deployments.yaml` | K8s deployment configuration |

### Untracked (new files)

| File/Directory | Purpose |
|----------------|---------|
| `.startd8_state/` | Startd8 SDK state directory |
| `docs/PHASE3_HANDOFF.md` | This document |
| `docs/plans/wayfinder-contextcore-manifest-generate-plan.md` | Manifest generation plan |
| `out/` | Generated output directory |
| `plans/.startd8/` | Startd8 planning state |
| `plans/wayfinder-contextcore-manifest-generate-plan.md` | Duplicate plan file |
| `reflection/` | Reflection/retrospective notes |
| `scripts/_activate_sdk_venv.sh` | SDK venv activation helper |
| `scripts/_activate_wayfinder_venv.sh` | Wayfinder venv activation helper |
| `scripts/run_coyote_watcher.sh` | Coyote watcher script |
| `scripts/run_manifest_generate_*.sh` | Manifest generation scripts (6 files) |
| `scripts/watch_artisan_errors.py` | Artisan error watcher |

---

## Useful Commands

```bash
# Run all tests
uv run pytest tests/ wayfinder-fox/tests/

# Type checking
uv run mypy src/contextcore

# Build VSCode extension
cd extensions/vscode && npm run compile

# Run graph commands
contextcore graph build
contextcore graph impact --project my-project

# Run learning loop (requires Tempo)
python -c "from contextcore.learning import LearningLoop; print('OK')"
```

---

## Related Documentation

| Document | Purpose |
|----------|---------|
| `plans/KUBERNETES_MIXIN_REMAINING.md` | Detailed tracking of mixin work |
| `docs/WAYFINDER_PHASE2_PROPAGATION.md` | Phase 2 OTel propagation guide |
| `docs/EXPANSION_PACKS.md` | Expansion pack design boundaries |
| `docs/OPERATIONAL_RUNBOOK.md` | Alert runbooks with anchors |
| `scripts/run_lead_contractor_phase3.py` | Lead Contractor workflow for Phase 3 features |

---

*Last updated: 2026-02-12*
