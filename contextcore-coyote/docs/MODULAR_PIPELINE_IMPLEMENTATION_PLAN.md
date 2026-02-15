# Coyote Modular Pipeline Implementation Plan

**Date:** 2026-02-14  
**Status:** Approved plan, implementation starts on explicit go-ahead  
**Requirements Source:** `MODULAR_PIPELINE_DESIGN.md` (design decisions D1-D22)  
**Upstream:** ContextCore A2A Contracts Design (`contextcore-a2a-comms-design.md`)

---

## 1. Overview

### What
Replace Coyote's untyped, regex-parsed, god-object pipeline stages with typed Pydantic contracts, composable validation gates, and structured A2A handoffs — without breaking the existing HOWL pipeline.

### Why
The current HOWL pipeline has three structural weaknesses that limit Coyote's reliability and evolution:
1. **Silent data-shape drift** — Stages communicate via `StageResult` (15+ optional fields, any stage can write any field). No stage declares what it produces or what it requires.
2. **Prose-first parsing** — LLM outputs are extracted via regex against markdown headings. Format changes break silently.
3. **No boundary validation** — Outputs are never validated between stages. A malformed investigation result flows unchecked into design, implementation, and beyond.

This plan adds typed boundaries, gate validation, and A2A-aligned handoffs incrementally — one stage at a time, with HOWL running in parallel until parity is proven.

### Goals
- Typed stage outputs validated at every boundary (gates).
- Structured LLM output parsing with observable fallback.
- End-to-end fingerprint chain for data integrity.
- Complexity-based routing for incident triage.
- ContextCore A2A interoperability (HandoffContract, GateResult, TaskSpanContract).
- Zero regressions in existing HOWL behavior throughout migration.

---

## 2. Execution Scope

This plan executes Steps 4-6 from the design doc, preceded by A2A contract alignment:
- **Step 3.5**: A2A contract alignment (enrich models, add new contracts, close alignment gaps) — **done**
- **Step 4**: Typed agent stages
- **Step 5**: Context fingerprint chain
- **Step 6**: Complexity routing + diagnostic protocol

HOWL remains in place during migration.

---

## 3. Guardrails

- Do not remove/refactor HOWL in this phase.
- Keep migration additive and reversible.
- Keep gates synchronous (D8).
- Keep typed agents under `agents/typed/` (D9).
- Use structured-first hybrid parsing for typed stages (D10).
- A2A contract alignment is additive to existing models (no breaking changes to Gate protocol).
- ContextCore JSON schemas are the source of truth for field names and enums in aligned contracts.
- All contract models use `extra = "forbid"` (D18).

---

## 4. Phase Plan

### Phase 0 — Scope Lock (0.5 day)

#### Tasks
- Confirm resolved decisions from design doc (D8-D22).
- Confirm feature-flag strategy and default mode.
- Confirm acceptance criteria for Steps 3.5-6.

#### Deliverables
- Finalized execution checklist.
- Explicit rollout and rollback mode table.

---

### Phase 0.5 — A2A Contract Alignment (1 day)

Enriches existing pipeline contracts to align with ContextCore A2A schemas. All changes are additive.

#### Tasks

**Expand `ViolationSeverity` to 4 levels (D16):**
- Add `INFO` and `CRITICAL` to existing `ERROR`, `WARNING`.
- Update `ContractViolation.__str__` for new severity prefixes.

**Add `Evidence` model (D17):**
- Pydantic model: `type` (str), `ref` (str), `description` (str).
- Used in `GateResult.evidence` and by gate implementations.

**Add `PipelinePhase` enum and `STAGE_PHASE_MAP` (D13):**
- Enum with all 11 ContextCore span phases.
- Dict mapping Coyote stage names to phases.

**Enrich `GateResult` (D12, D16, D17):**
- Add `schema_version`, `phase`, `severity`, `blocking`, `evidence`, `next_action`, `checked_at`, `trace_id`, `task_id`.
- Add computed `result` property ("pass"/"fail") for ContextCore interop.
- All new fields optional with backward-compatible defaults.

**Add `schema_version` and `extra = "forbid"` to `StageOutput` (D15, D18):**
- `schema_version: str = "v1"`.
- `model_config` gains `"extra": "forbid"`.

**Introduce `StageHandoff` model (D14):**
- Pydantic model implementing ContextCore `HandoffContract` shape.
- Fields: `schema_version`, `handoff_id`, `from_agent`, `to_agent`, `capability_id`, `inputs`, `expected_output`, `status`, `priority`, `trace_id`, `result_trace_id`, `created_at`.
- Add `HandoffStatus` enum.

**Introduce `PipelineLifecycle` model (D12, D19, D20):**
- Pydantic model implementing ContextCore `TaskSpanContract` shape.
- Fields: `schema_version`, `project_id`, `task_id`, `phase`, `status`, `checksums`, `metrics`, `acceptance_criteria`, `blocked_reason`, `next_action`, `timestamp`.
- `ModularPipelineResult.to_lifecycle()` produces this model.

**Update all gate implementations (D16, D17):**
- Each gate sets `blocking`, `severity`, `evidence`, `next_action` on returned `GateResult`.
- `CompositeGate` derives blocking/severity from sub-gate results.

**Update `ModularPipeline.run()` (D14):**
- Build `StageHandoff` record before each stage execution.
- Enrich `GateResult` with `phase` from `STAGE_PHASE_MAP` after each gate.
- Populate `ModularPipelineResult.handoffs`.

#### Validation
- All new fields have defaults; existing tests pass without modification.
- Unit tests for `StageHandoff` construction and serialization.
- Unit tests for enriched `GateResult` with phase, evidence, next_action.
- Unit tests for `PipelineLifecycle` from `ModularPipelineResult`.
- Unit tests for 4-level severity and `ContractViolation.__str__`.
- Unit tests for `extra = "forbid"` rejecting unknown fields.
- Schema compatibility tests: model exports validate against ContextCore JSON schemas.

#### Exit Criteria
- Enriched contracts pass full existing test suite with no regressions.
- New models validate against ContextCore JSON schemas.
- `ModularPipeline.run()` populates handoffs and enriched gate results.

---

### Phase 1 — Step 4 Typed Agents (2-3 days)

#### Tasks
- Create `agents/typed/` package structure.
- Implement `TypedInvestigator`.
- Implement `TypedDesigner`.
- Implement shared parsing utility (primary structured path + controlled fallback).
- Add fallback telemetry and structured logging.
- Ensure prompt loading is configurable (no module-level prompt constants).
- Pipeline runner builds `StageHandoff` records for each typed stage transition.

#### Validation
- Unit tests for typed output parsing and model validation.
- Integration test for typed + legacy mixed-mode run.
- Tests that intentionally trigger fallback path.
- Existing HOWL tests remain green.
- `StageHandoff` records populated with correct phase, from_agent, to_agent, expected_output.

#### Exit Criteria
- Typed agents produce valid typed outputs in modular pipeline.
- Fallback path is observable and tested.
- Handoff records are complete and schema-compatible.

---

### Phase 2 — Step 5 Fingerprint Chain (1-1.5 days)

#### Tasks
- Define canonical input normalization for hashing.
- Compute pipeline-start fingerprint.
- Propagate `context_fingerprint` across stage outputs.
- Enforce `IntegrityGate` at configured boundaries.
- Define and implement mixed-mode semantics for adapter-generated outputs.
- Map `context_fingerprint` to `checksums.source_checksum` in `PipelineLifecycle`.

#### Validation
- Determinism tests with semantically equivalent inputs.
- Tamper/mutation tests fail at expected gate boundaries.
- Mixed-mode integrity behavior test (typed -> legacy-wrapped -> typed).

#### Exit Criteria
- Fingerprint chain is deterministic, enforced, and diagnosable.
- `PipelineLifecycle.checksums.source_checksum` populated from pipeline fingerprint.

---

### Phase 3 — Step 6 Routing + Diagnostics (2 days)

#### Tasks
- Implement complexity classifier for `brief|standard|comprehensive`.
- Define classifier features and thresholds.
- Add confidence-based fallback to `standard`.
- Add manual routing override.
- Implement routing profile -> pipeline config mapping.
- Implement diagnostic protocol linking `GateResult.evidence` and `GateResult.next_action`.
- Routing decisions recorded as `ROUTING_DECISION` phase.
- `PipelineLifecycle.metrics.complexity_score` populated from classifier.

#### Validation
- Labeled scenario tests for route correctness.
- Boundary tests near classifier thresholds.
- Override path tests.
- Diagnostic output tests for completeness/actionability (evidence, next_action populated).

#### Exit Criteria
- Route selection is testable and stable.
- Diagnostic protocol provides structured, actionable outputs with evidence chain.

---

### Phase 4 — Hardening and Rollout (1-2 days)

#### Tasks
- End-to-end tests for CLI, webhook, and dev-mode entry points.
- Implement rollout sequence: shadow -> opt-in -> default-on.
- Shadow mode records comparisons without triggering operational action callbacks.
- Document rollback policy (deployment-level + in-flight handling).
- Enforce telemetry budget guardrails (D21).
- Define and verify day-1 queries (D22).

#### Validation
- End-to-end suite green.
- Rollout mode transitions tested.
- Rollback path tested.
- Day-1 queries return expected results against actual telemetry.

#### Exit Criteria
- Controlled rollout and rollback paths verified.
- Telemetry budget within ContextCore guidelines.

---

## 5. Deliverables

- A2A-aligned contract models (`StageHandoff`, enriched `GateResult`, `PipelineLifecycle`, `Evidence`, `PipelinePhase`).
- Four-level severity with declarative blocking on all gates.
- `extra = "forbid"` on all contract models.
- Schema compatibility tests against ContextCore JSON schemas.
- Typed stage implementations in `agents/typed/`.
- Shared structured parsing utility with observable fallback.
- End-to-end fingerprint chain semantics and enforcement.
- Complexity router with thresholds and override support.
- Structured diagnostic protocol with evidence chain.
- Expanded unit/integration/e2e test coverage.
- Updated runbook and architecture docs.

---

## 6. Definition of Done

- [ ] A2A contract alignment complete and validated (Phase 0.5).
- [ ] Step 4 complete and validated.
- [ ] Step 5 complete and validated.
- [ ] Step 6 complete and validated.
- [ ] E2E tests pass on all three entry paths.
- [ ] Shadow mode and rollback policies validated.
- [ ] HOWL remains stable throughout migration.
- [ ] Coyote contract models validate against ContextCore JSON schemas.
- [ ] Telemetry budget within guidelines.

---

## 7. Immediate Start Checklist (When Authorized)

1. Expand `ViolationSeverity` to 4 levels; add `Evidence` model.
2. Add `PipelinePhase` enum and `STAGE_PHASE_MAP`.
3. Enrich `GateResult` with phase, severity, blocking, evidence, next_action, checked_at.
4. Add `schema_version` and `extra = "forbid"` to `StageOutput`.
5. Implement `StageHandoff` model and `HandoffStatus` enum.
6. Implement `PipelineLifecycle` model.
7. Update all gate implementations to populate new `GateResult` fields.
8. Update `ModularPipeline.run()` to build handoffs and enrich gate results.
9. Update `__init__.py` exports.
10. Run full test suite — verify no regressions.
11. Create `agents/typed/` scaffolding and exports.
12. Implement `TypedInvestigator` + tests.
13. Implement `TypedDesigner` + tests.
14. Add mixed-mode integration tests.
15. Implement canonical fingerprint normalization and chain tests.
16. Implement routing classifier + profile mapping + tests.
17. Run full test suite and publish readiness report.

---

## Appendix: Iterative Review Log (Applied / Rejected Suggestions)

This appendix is intentionally **append-only**. New reviewers (human or model) should add suggestions to Appendix C, and then once validated, record the final disposition in Appendix A (applied) or Appendix B (rejected with rationale).

### Reviewer Instructions (for humans + models)

- **Before suggesting changes**: Scan Appendix A and Appendix B first. Do **not** re-suggest items already applied or explicitly rejected.
- **When proposing changes**: Append them to Appendix C using a unique suggestion ID (`R{round}-S{n}`).
- **When endorsing prior suggestions**: If you agree with an untriaged suggestion from a prior round, list it in an **Endorsements** section after your suggestion table. This builds consensus signal — suggestions endorsed by multiple reviewers should be prioritized during triage.
- **When validating**: For each suggestion, append a row to Appendix A (if applied) or Appendix B (if rejected) referencing the suggestion ID. Endorsement counts inform priority but do not auto-apply suggestions.
- **If rejecting**: Record **why** (specific rationale) so future models don't re-propose the same idea.

### Appendix A: Applied Suggestions

| ID | Suggestion | Source | Implementation / Validation Notes | Date |
|----|------------|--------|----------------------------------|------|
| R1-F1 | Add a feature requirement for non-gate error handling semantics covering LLM errors, timeouts, and parse failures. | claude-4 (claude-opus-4-6) | This is the feature-requirements counterpart to R1-S1. The design doc extensively covers gate failures but is silent on operational failures. Typed agents making LLM calls need a defined error contract to maintain pipeline integrity. | 2026-02-14 07:10:14 UTC |
| R1-F2 | Add a feature requirement specifying the type safety strategy for StageHandoff.inputs. | claude-4 (claude-opus-4-6) | This is the feature-requirements counterpart to R1-S8. The asymmetry between typed expected_output and unconstrained inputs should be an explicit requirement-level decision, not left to implementation discretion. | 2026-02-14 07:10:14 UTC |
| R1-F3 | Step 5 acceptance criteria should specify hashing algorithm and normalization rules, not just outcome-based determinism tests. | claude-4 (claude-opus-4-6) | This is the feature-requirements counterpart to R1-S3. For an integrity mechanism, the algorithm must be documented and portable. Outcome-based criteria alone could pass tests but produce chains that aren't independently verifiable. | 2026-02-14 07:10:14 UTC |
| R1-F4 | Add a feature requirement defining shadow mode comparison dimensions, divergence measurement, and alerting thresholds. | claude-4 (claude-opus-4-6) | This is the feature-requirements counterpart to R1-S5. Shadow mode is referenced throughout but has no defined behavior beyond 'don't trigger callbacks.' This is a critical gap since the entire rollout safety depends on shadow mode evaluation. | 2026-02-14 07:10:14 UTC |
| R2-F1 | Add acceptance criterion for typed-to-typed stage consumption integration test. | gemini-2.5 (gemini-2.5-pro) | The mixed-mode test validates typed-to-legacy interop, but a pure typed-to-typed integration test is needed to validate the primary happy path. This is a straightforward gap in test coverage for the core design intent. | 2026-02-14 07:10:14 UTC |
| R2-F2 | Quantify routing classifier acceptance criteria with specific accuracy, precision, and recall targets. | gemini-2.5 (gemini-2.5-pro) | The current AC 'labeled routing test set passes threshold targets' is unmeasurable without defined thresholds. Quantified targets (even provisional ones that can be refined during the discovery sub-phase from R2-S3) are necessary to make the acceptance criterion meaningful and testable. | 2026-02-14 07:10:14 UTC |

### Appendix B: Rejected Suggestions (with Rationale)

| ID | Suggestion | Source | Rejection Rationale | Date |
|----|------------|--------|---------------------|------|
| (none yet) |  |  |  |

### Appendix C: Incoming Suggestions (Untriaged, append-only)

#### Review Round R1

- **Reviewer**: claude-4 (claude-opus-4-6)
- **Date**: 2026-02-14 07:08:29 UTC
- **Scope**: Architecture-focused review

#### Feature Requirements Suggestions

| ID | Area | Severity | Suggestion | Rationale | Proposed Placement | Validation Approach |
| ---- | ---- | ---- | ---- | ---- | ---- | ---- |
| R1-F1 | Risks | high | Add a requirement for non-gate error handling semantics. The design doc defines gate failure behavior extensively (D16 blocking, D17 next_action, override callbacks) but is silent on non-gate failures: LLM API errors, parsing failures beyond fallback, infrastructure timeouts. The requirements should specify expected behavior for these failure classes. | The design doc's "fail-fast on integrity" principle applies to contract violations but doesn't cover operational failures. Without this, Step 4's typed agents (which make LLM calls) have no defined error contract. | Section 6, Step 4 Requirements — add requirement: "Define and implement error handling for non-gate failures (LLM errors, timeouts, parse failures beyond fallback) including retry policy, state preservation, and lifecycle status transitions" | Acceptance criteria: "Non-gate failure produces a PipelineLifecycle with appropriate status and blocked_reason; partial outputs are preserved" |
| R1-F2 | Interfaces | medium | Add a requirement specifying `StageHandoff.inputs` type safety strategy. D14 lists `inputs` as a field but doesn't constrain its type. The requirements should specify whether inputs are typed per-stage (generic), validated at runtime, or left as `dict[str, Any]` with documented rationale. | This is a gap in the "typed over narrative" principle. The handoff envelope types `expected_output` with `type + schema_ref` but leaves inputs unconstrained, creating an asymmetry in the contract. | Section 6, Step 4 Requirements or Design Doc D14 — add: "Define type constraint strategy for StageHandoff.inputs; if unconstrained, document rationale and add runtime validation" | Acceptance criteria: "StageHandoff.inputs type strategy documented; if typed, validation tests pass; if dict, runtime check tests pass" |
| R1-F3 | Validation | medium | Step 5 acceptance criteria should specify the hashing algorithm and normalization rules, not just "determinism tests pass." The current criteria are outcome-based without constraining the mechanism, which could lead to an implementation that passes tests but isn't portable or auditable. | The fingerprint chain is an integrity mechanism. Leaving algorithm choice entirely to implementation means the chain can't be independently verified by external tools or ContextCore consumers. The design doc's D5 says "integrity-oriented (not cryptographic)" but this doesn't narrow the algorithm space sufficiently. | Section 6, Step 5 Requirements — add: "Fingerprint algorithm and normalization spec must be documented and deterministic across Python 3.10+; algorithm choice must be justified against D5 constraints" | Acceptance criteria: "Fingerprint spec document exists; cross-version determinism test passes; external verification example included" |
| R1-F4 | Ops | high | Add a requirement for shadow mode comparison semantics. Section 8 says "shadow mode must collect comparison signal" but neither the design doc nor requirements define what is compared, how divergences are measured, or how results are surfaced. This is a critical operational gap since shadow mode is the safety gate for the entire rollout. | Shadow mode is referenced in multiple places (Section 8, Phase 4, rollout sequence) but has no defined behavior beyond "don't trigger operational callbacks." Without comparison semantics, there's no way to evaluate whether the modular pipeline is safe to promote from shadow to opt-in. | Section 8 or Section 6 Step 6 — add: "Define shadow mode comparison dimensions (output shape, content, gate results, timing), divergence measurement, storage format, and alerting thresholds" | Acceptance criteria: "Shadow mode produces structured comparison report; divergence above threshold triggers alert; comparison covers output shape, gate result parity, and timing delta" |

#### Review Round R2

- **Reviewer**: gemini-2.5 (gemini-2.5-pro)
- **Date**: 2026-02-14 07:09:21 UTC
- **Scope**: Architecture-focused review

#### Feature Requirements Suggestions
| ID | Area | Severity | Suggestion | Rationale | Proposed Placement | Validation Approach |
| ---- | ---- | ---- | ---- | ---- | ---- | ---- |
| R2-F1 | Validation | medium | Add an acceptance criterion for typed-to-typed stage consumption. | The requirement "Typed stages must consume upstream typed outputs without ad-hoc parsing" is not directly validated by any acceptance criterion. The mixed-mode test validates typed-to-legacy, but a pure typed-to-typed integration test is needed to fully cover the requirement. | `MODULAR_PIPELINE_DESIGN.md` Section 6, Step 4 Acceptance Criteria | Add new AC: "At least one integration test passes for a fully typed pipeline (e.g., `TypedInvestigator` -> `TypedDesigner`) demonstrating correct consumption of typed inputs." |
| R2-F2 | Validation | high | Quantify the acceptance criteria for the routing classifier. | The Step 6 AC "Labeled routing test set passes threshold targets" is too vague. To be a meaningful requirement, it needs specific, measurable targets for the classifier's performance (e.g., accuracy, precision, recall) for each routing profile. | `MODULAR_PIPELINE_DESIGN.md` Section 6, Step 6 Acceptance Criteria | Refine the AC: "Labeled routing test set passes threshold targets (e.g., >95% accuracy for `brief` vs. `comprehensive`, with fallback to `standard` not exceeding 10% of cases)." |

