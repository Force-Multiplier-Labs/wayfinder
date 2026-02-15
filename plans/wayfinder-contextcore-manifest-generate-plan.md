# Plan: Implement `contextcore manifest generate` Command

## Context

The `contextcore manifest export` command produces an artifact manifest that identifies 77 observability artifacts needed for the Online Boutique project (7 types x 11 services). The artifact manifest is a contract specifying WHAT to generate, with type-specific parameters and derivation audit trails. But no consumer exists -- there is no `generate` command that reads this contract and produces real files (ServiceMonitor YAMLs, PrometheusRule YAMLs, Grafana dashboard JSONs, markdown runbooks, etc.).

This plan builds that consumer iteratively, one small step at a time, ordered by complexity. Each step is a self-contained Artisan task producing a testable result.

## Architecture

```
artifact-manifest.yaml ──→ manifest generate ──→ generated/
                              │                     ├── service-monitors/*.yaml
                              │                     ├── prometheus-rules/*.yaml
                              │                     ├── loki-rules/*.yaml
                              │                     ├── slo-definitions/*.yaml
                              │                     ├── notification-policies/*.yaml
                              │                     ├── runbooks/*.md
                              │                     └── dashboards/*.json
                              │
                              ├── artifact_generators.py  (dispatcher + registry)
                              └── templates/*.j2          (Jinja2 templates)
```

**Key decisions:**
- Jinja2 templates (already in `pyproject.toml` dependencies)
- Generator registry pattern: `Dict[ArtifactType, generator_func]`
- Uniform generator signature: `generate_X(artifact: ArtifactSpec, env: Environment, output_dir: Path) -> Path`
- Errors per-artifact, not abort-all

## Files

| File | Action |
|------|--------|
| `src/contextcore/generators/__init__.py` | CREATE (may already exist) |
| `src/contextcore/generators/artifact_generators.py` | CREATE |
| `src/contextcore/generators/templates/` | CREATE directory |
| `src/contextcore/generators/templates/service_monitor.yaml.j2` | CREATE |
| `src/contextcore/generators/templates/prometheus_rule.yaml.j2` | CREATE |
| `src/contextcore/generators/templates/loki_rule.yaml.j2` | CREATE |
| `src/contextcore/generators/templates/slo_definition.yaml.j2` | CREATE |
| `src/contextcore/generators/templates/notification_policy.yaml.j2` | CREATE |
| `src/contextcore/generators/templates/runbook.md.j2` | CREATE |
| `src/contextcore/generators/templates/dashboard.json.j2` | CREATE |
| `src/contextcore/cli/manifest.py` | EDIT - add `generate` subcommand |
| `tests/test_artifact_generators.py` | CREATE |

## Reference Files (read-only)

| File | Why |
|------|-----|
| `src/contextcore/models/artifact_manifest.py` | ArtifactManifest, ArtifactSpec, ArtifactType, ArtifactStatus models |
| `src/contextcore/cli/manifest.py` | CLI patterns (Click options, error handling, dry-run) |
| `src/contextcore/models/manifest_v2.py:478-809` | How parameters are populated per type |
| `loki/rules/fake/contextcore-rules.yaml` | Real Loki rules format reference |
| `grafana/provisioning/dashboards/json/*.json` | Real Grafana dashboard JSON reference |

## Parameter Reference (per artifact type)

| Type | Parameters | Output Format |
|------|-----------|---------------|
| `service_monitor` | `metricsInterval`, `namespace` | YAML |
| `prometheus_rule` | `alertSeverity`, `availabilityThreshold`, `latencyThreshold` | YAML |
| `loki_rule` | `logSelectors` (list) | YAML |
| `slo_definition` | `availability`, `latencyP99`, `errorBudget` | YAML |
| `notification_policy` | `alertChannels` (list), `owner` | YAML |
| `runbook` | `risks` (list of dicts), `escalationContacts` | Markdown |
| `dashboard` | `criticality`, `dashboardPlacement` | JSON |

All ArtifactSpec objects also carry: `id`, `type`, `name`, `target`, `priority`, `status`, `derivedFrom`.

---

## Steps

### Step 1: Create generator module skeleton

Create `src/contextcore/generators/__init__.py` and `src/contextcore/generators/artifact_generators.py` with:
- `GeneratedFile` dataclass (`path`, `artifact_id`, `artifact_type`, `success`, `error`)
- `GENERATOR_REGISTRY: Dict[str, Callable]` (empty)
- `_get_jinja_env() -> Environment` using `FileSystemLoader` pointing to templates dir
- `generate_artifact(artifact, env, output_dir) -> GeneratedFile` dispatcher (looks up registry, calls generator)
- `generate_all(manifest, output_dir, dry_run, force, type_filter) -> List[GeneratedFile]` orchestrator

**Verify:** `python3 -c "from contextcore.generators.artifact_generators import generate_all; print('OK')"`

### Step 2: Create empty templates directory

Create `src/contextcore/generators/templates/` with a `.gitkeep` file so the directory is tracked.

**Verify:** `python3 -c "from contextcore.generators.artifact_generators import _get_jinja_env; print(_get_jinja_env())"`

### Step 3: Wire `manifest generate` CLI command

Add `@manifest.command("generate")` to `src/contextcore/cli/manifest.py` with options:
- `--manifest-path / -m` (required, path to artifact manifest YAML)
- `--output-dir / -o` (default `./generated`)
- `--dry-run` (flag)
- `--force` (flag, overwrite existing)
- `--types / -t` (optional, comma-separated artifact type filter)

The command loads the artifact manifest via `yaml.safe_load` + `ArtifactManifest(**data)`, calls `generate_all()`, prints summary.

**Verify:** `contextcore manifest generate --help`

### Step 4: Add test infrastructure

Create `tests/test_artifact_generators.py` with:
- `_make_artifact_spec(type, target, params)` helper
- `_make_artifact_manifest(specs)` helper
- Test: `generate_all` with empty registry returns all as skipped
- Test: output directory structure is created

**Verify:** `python3 -m pytest tests/test_artifact_generators.py -v`

### Step 5: service_monitor template

Create `src/contextcore/generators/templates/service_monitor.yaml.j2`. Produces `monitoring.coreos.com/v1` ServiceMonitor YAML. Variables: `target_name`, `namespace`, `metrics_interval`.

**Verify:** Render template with sample data, confirm valid YAML.

### Step 6: service_monitor generator + register

Add `generate_service_monitor()` to `artifact_generators.py`. Extracts `metricsInterval`, `namespace` from `artifact.parameters`. Writes to `service-monitors/{target}-service-monitor.yaml`. Register in `GENERATOR_REGISTRY`.

**Verify:** `python3 -m pytest tests/test_artifact_generators.py -k service_monitor -v`

### Step 7: service_monitor tests

Add tests: valid YAML output, correct file path, handles missing params with defaults.

**Verify:** `python3 -m pytest tests/test_artifact_generators.py -k service_monitor -v`

### Step 8: prometheus_rule template

Create `prometheus_rule.yaml.j2`. Produces `monitoring.coreos.com/v1` PrometheusRule YAML with `HighLatency` and `LowAvailability` alert rules. Variables: `target_name`, `namespace`, `alert_severity`, `availability_threshold`, `latency_threshold`.

**Verify:** Render with sample data.

### Step 9: prometheus_rule generator + register

Add `generate_prometheus_rule()`. Extracts `alertSeverity`, `availabilityThreshold`, `latencyThreshold`. Writes to `prometheus-rules/{target}-prometheus-rules.yaml`.

**Verify:** `python3 -m pytest tests/test_artifact_generators.py -k prometheus -v`

### Step 10: prometheus_rule tests

Tests: valid YAML, alert severity from params, threshold values in expressions.

**Verify:** `python3 -m pytest tests/test_artifact_generators.py -k prometheus -v`

### Step 11: loki_rule template

Create `loki_rule.yaml.j2`. Reference `loki/rules/fake/contextcore-rules.yaml` for format. Variables: `target_name`, `log_selectors` (list).

**Verify:** Render with sample data.

### Step 12: loki_rule generator + tests + register

Add `generate_loki_rule()`. Extracts `logSelectors`. Writes to `loki-rules/{target}-loki-rules.yaml`. Add 2 tests.

**Verify:** `python3 -m pytest tests/test_artifact_generators.py -k loki -v`

### Step 13: slo_definition template

Create `slo_definition.yaml.j2`. OpenSLO-inspired SLO spec. Variables: `target_name`, `availability`, `latency_p99`, `error_budget`.

**Verify:** Render with sample data.

### Step 14: slo_definition generator + tests + register

Add `generate_slo_definition()`. Extracts `availability`, `latencyP99`, `errorBudget`. Writes to `slo-definitions/{target}-slo-definition.yaml`. Add 2 tests.

**Verify:** `python3 -m pytest tests/test_artifact_generators.py -k slo -v`

### Step 15: notification_policy template

Create `notification_policy.yaml.j2`. Alert routing config with conditional channel blocks. Variables: `target_name`, `alert_channels` (list), `owner`.

**Verify:** Render with and without channels.

### Step 16: notification_policy generator + tests + register

Add `generate_notification_policy()`. Extracts `alertChannels`, `owner`. Writes to `notification-policies/{target}-notification-policy.yaml`. Add 2 tests (with channels, empty channels).

**Verify:** `python3 -m pytest tests/test_artifact_generators.py -k notification -v`

### Step 17: runbook template

Create `runbook.md.j2`. Markdown document with sections: Overview, Risks & Mitigations (loop over risks list), Escalation, Common Procedures. Variables: `target_name`, `risks` (list of `{type, description}`), `escalation_contacts`, `generated_at`.

**Verify:** Render with sample risks list.

### Step 18: runbook generator + tests + register

Add `generate_runbook()`. Extracts `risks`, `escalationContacts`. Writes to `runbooks/{target}-runbook.md`. Add 3 tests (with risks, empty risks, markdown structure).

**Verify:** `python3 -m pytest tests/test_artifact_generators.py -k runbook -v`

### Step 19: dashboard template

Create `dashboard.json.j2`. Minimal Grafana dashboard JSON with panels for: request rate, latency P99, error rate, availability. Use `{{ var | tojson }}` for safe JSON values. Variables: `target_name`, `criticality`, `dashboard_placement`, `uid` (derived from target name).

**Verify:** Render and validate output parses as JSON.

### Step 20: dashboard generator + tests + register

Add `generate_dashboard()`. Extracts `criticality`, `dashboardPlacement`. Writes to `dashboards/{target}-dashboard.json`. Add 3 tests (valid JSON, correct panels, tags).

**Verify:** `python3 -m pytest tests/test_artifact_generators.py -k dashboard -v`

### Step 21: End-to-end CLI test

Add integration test that:
1. Uses the real Online Boutique artifact manifest at `micro-service-demo/microservices-demo/output/online-boutique-artifact-manifest.yaml`
2. Runs `generate_all()` against it
3. Verifies all 7 output subdirectories created
4. Verifies 77 files generated (7 types x 11 services)
5. Spot-checks one file of each type is parseable

**Verify:** `python3 -m pytest tests/test_artifact_generators.py -k e2e -v`

### Step 22: Coverage-aware generation (skip existing)

Update `generate_all()` to check if output file already exists. If so and `force=False`, skip it. Print coverage summary: generated / skipped / failed / total.

**Verify:** Run generate twice -- second run should skip all.

### Step 23: Update artifact manifest after generation

Add `--update-manifest` flag to CLI. After generating, rewrite the artifact manifest with `status: exists` and `existingPath` set for each generated artifact. Recompute coverage.

**Verify:** Generate, then inspect updated manifest -- coverage should be >0%.

## Verification (end-to-end)

```bash
# Full pipeline test with Online Boutique
contextcore manifest generate \
  -m ~/Documents/dev/micro-service-demo/microservices-demo/output/online-boutique-artifact-manifest.yaml \
  -o ~/Documents/dev/micro-service-demo/microservices-demo/generated/ \
  --dry-run

# Actual generation
contextcore manifest generate \
  -m ~/Documents/dev/micro-service-demo/microservices-demo/output/online-boutique-artifact-manifest.yaml \
  -o ~/Documents/dev/micro-service-demo/microservices-demo/generated/

# Verify output
ls ~/Documents/dev/micro-service-demo/microservices-demo/generated/
# Should show: dashboards/ loki-rules/ notification-policies/ prometheus-rules/ runbooks/ service-monitors/ slo-definitions/

# Run tests
python3 -m pytest tests/test_artifact_generators.py -v
```

---

## Appendix: Iterative Review Log (Applied / Rejected Suggestions)

This appendix is intentionally **append-only**. New reviewers (human or model) should add suggestions to Appendix C, and then once validated, record the final disposition in Appendix A (applied) or Appendix B (rejected with rationale).

### Reviewer Instructions (for humans + models)

- **Before suggesting changes**: Scan Appendix A and Appendix B first. Do **not** re-suggest items already applied or explicitly rejected.
- **When proposing changes**: Append them to Appendix C using a unique suggestion ID (`R{round}-S{n}`).
- **When endorsing prior suggestions**: If you agree with an untriaged suggestion from a prior round, list it in an **Endorsements** section after your suggestion table. This builds consensus signal — suggestions endorsed by multiple reviewers should be prioritized during triage.
- **When validating**: For each suggestion, append a row to Appendix A (if applied) or Appendix B (if rejected) referencing the suggestion ID. Endorsement counts inform priority but do not auto-apply suggestions.
- **If rejecting**: Record **why** (specific rationale) so future models don't re-propose the same idea.

### Areas Needing Further Review

All areas have reached the substantially addressed threshold.

### Areas Substantially Addressed

- **architecture**: 6 suggestions applied (R1-S1, R1-S4, R1-S7, R1-S12, R2-S1, R2-S14)
- **data**: 5 suggestions applied (R1-S2, R1-S6, R2-S2, R2-S6, R2-S11)
- **interfaces**: 8 suggestions applied (R3-S1, R3-S6, R3-S9, R3-S14, R1-S3, R1-S20, R2-S3, R2-S17)
- **ops**: 7 suggestions applied (R3-S3, R3-S7, R3-S10, R1-S8, R1-S16, R2-S8, R2-S15)
- **risks**: 7 suggestions applied (R3-S4, R3-S11, R3-S15, R1-S10, R1-S17, R2-S4, R2-S12)
- **security**: 6 suggestions applied (R3-S2, R3-S5, R3-S12, R1-S15, R2-S9, R2-S18)
- **validation**: 5 suggestions applied (R1-S5, R1-S11, R1-S18, R2-S7, R2-S20)

### Appendix A: Applied Suggestions

| ID | Suggestion | Source | Implementation / Validation Notes | Date |
|----|------------|--------|----------------------------------|------|
| R1-S1 | Add explicit error handling strategy for partial generation failures | claude-4 (claude-opus-4-20250514) | Critical for robust error reporting and recovery in multi-artifact generation scenarios | 2026-02-11 21:56:56 UTC |
| R1-S2 | Add validation for required parameters before generation | claude-4 (claude-opus-4-20250514) | Prevents runtime errors and provides clear feedback on missing required parameters | 2026-02-11 21:56:56 UTC |
| R1-S3 | Implement --scan-existing flag to match contract spec | claude-4 (claude-opus-4-20250514) | Contract compliance requirement for coverage tracking capability | 2026-02-11 21:56:56 UTC |
| R1-S4 | Add derivation rule tracking to generated artifacts | claude-4 (claude-opus-4-20250514) | Critical for audit trail and traceability as emphasized in the contract | 2026-02-11 21:56:56 UTC |
| R1-S5 | Add contract schema validation on manifest load | claude-4 (claude-opus-4-20250514) | Critical for early error detection and clear error messages for invalid manifests | 2026-02-11 21:56:56 UTC |
| R1-S6 | Handle null existingPath gracefully | claude-4 (claude-opus-4-20250514) | Contract explicitly shows null values that must be handled correctly | 2026-02-11 21:56:56 UTC |
| R1-S7 | Add template versioning mechanism | claude-4 (claude-opus-4-20250514) | Important for tracking which template version generated each artifact for debugging and evolution | 2026-02-11 21:56:56 UTC |
| R1-S8 | Implement progress reporting for large manifests | claude-4 (claude-opus-4-20250514) | Essential UX improvement for 77+ artifact generation providing user feedback | 2026-02-11 21:56:56 UTC |
| R1-S10 | Add rollback mechanism for failed generations | claude-4 (claude-opus-4-20250514) | Critical for maintaining consistent state and preventing partial updates | 2026-02-11 21:56:56 UTC |
| R1-S11 | Validate generated artifacts against their schemas | claude-4 (claude-opus-4-20250514) | Ensures generated artifacts are actually valid for their intended consumers | 2026-02-11 21:56:56 UTC |
| R1-S12 | Extract common template variables | claude-4 (claude-opus-4-20250514) | Reduces duplication and ensures consistency across all templates | 2026-02-11 21:56:56 UTC |
| R1-S15 | Sanitize template inputs | claude-4 (claude-opus-4-20250514) | Important security measure to prevent template injection attacks | 2026-02-11 21:56:56 UTC |
| R1-S16 | Add dry-run preview of changes | claude-4 (claude-opus-4-20250514) | Valuable enhancement to show actual content changes not just file list | 2026-02-11 21:56:56 UTC |
| R1-S17 | Handle filesystem permissions errors | claude-4 (claude-opus-4-20250514) | Critical for graceful failure and clear error messages | 2026-02-11 21:56:56 UTC |
| R1-S18 | Implement the contract's validation_errors field | claude-4 (claude-opus-4-20250514) | Contract compliance - must populate validationErrors field in manifest updates | 2026-02-11 21:56:56 UTC |
| R1-S20 | Honor the contract's priority field | claude-4 (claude-opus-4-20250514) | Contract specifies priority levels that should be filterable | 2026-02-11 21:56:56 UTC |
| R2-S1 | Add validation against derivedFrom rules before generation | claude-3-5-sonnet-20241022 | Critical for data consistency - ensures generated artifacts respect the derivation rules specified in the contract | 2026-02-11 22:02:31 UTC |
| R2-S2 | Implement artifact version tracking mechanism | claude-3-5-sonnet-20241022 | Required to implement the 'outdated' status detection specified in the contract - without versioning, coverage tracking is incomplete | 2026-02-11 22:02:31 UTC |
| R2-S3 | Add schema validation for generated artifacts | claude-3-5-sonnet-20241022 | Contract requires valid artifacts but plan lacks validation - essential for ensuring generated files work with target systems | 2026-02-11 22:02:31 UTC |
| R2-S4 | Handle partial generation failures gracefully | claude-3-5-sonnet-20241022 | Critical for system consistency - current plan could leave artifacts in inconsistent state on partial failures | 2026-02-11 22:02:31 UTC |
| R2-S6 | Load CRD when parameters reference it | claude-3-5-sonnet-20241022 | Contract explicitly mentions CRD loading for context but plan only uses manifest - needed for complex derivations | 2026-02-11 22:02:31 UTC |
| R2-S7 | Implement coverage threshold enforcement | claude-3-5-sonnet-20241022 | Contract calculates coverage but plan doesn't enforce thresholds - important for quality gates in CI/CD | 2026-02-11 22:02:31 UTC |
| R2-S8 | Add rollback capability for failed generations | claude-3-5-sonnet-20241022 | Critical for production safety - no way to undo partial generation failures could leave system broken | 2026-02-11 22:02:31 UTC |
| R2-S9 | Validate template injection risks | claude-3-5-sonnet-20241022 | Security vulnerability with user-controlled data in Jinja2 templates - must sanitize inputs | 2026-02-11 22:02:31 UTC |
| R2-S11 | Preserve custom fields in manifest updates | claude-3-5-sonnet-20241022 | Step 23 could lose user customizations - merge strategy is essential for preserving manual additions | 2026-02-11 22:02:31 UTC |
| R2-S12 | Add generation dependency ordering | claude-3-5-sonnet-20241022 | Some artifacts logically depend on others - proper ordering prevents generation failures and ensures consistency | 2026-02-11 22:02:31 UTC |
| R2-S14 | Implement generator result caching | claude-3-5-sonnet-20241022 | Efficiency improvement for large manifests - avoid regenerating unchanged artifacts | 2026-02-11 22:02:31 UTC |
| R2-S15 | Add progress reporting for large manifests | claude-3-5-sonnet-20241022 | User experience improvement - 77 artifacts could take significant time without feedback | 2026-02-11 22:02:31 UTC |
| R2-S17 | Provide manifest validation command | claude-3-5-sonnet-20241022 | Helpful for users to validate manifests before generation - prevents wasted generation attempts | 2026-02-11 22:02:31 UTC |
| R2-S18 | Implement access control for sensitive parameters | claude-3-5-sonnet-20241022 | Escalation contacts and alert channels are sensitive - must not leak in logs or error messages | 2026-02-11 22:02:31 UTC |
| R2-S20 | Add artifact content validation tests | claude-3-5-sonnet-20241022 | Plan only tests structure but semantic correctness is critical - invalid PromQL would break monitoring | 2026-02-11 22:02:31 UTC |
| R3-S1 | Define CRD field extraction mechanism | claude-3.5-sonnet | Step 9 incorrectly assumes alertSeverity comes from manifest when contract shows it derives from CRD fields | 2026-02-11 22:06:10 UTC |
| R3-S2 | Add template injection protection | claude-3.5-sonnet | Security vulnerability - user-supplied values in templates risk XSS/injection attacks | 2026-02-11 22:06:10 UTC |
| R3-S3 | Add generation transaction/rollback | claude-3.5-sonnet | Critical for data integrity - partial generation of 77 files leaves system in inconsistent state | 2026-02-11 22:06:10 UTC |
| R3-S4 | Handle manifest version compatibility | claude-3.5-sonnet | Prevents silent failures when manifest format evolves beyond v1 | 2026-02-11 22:06:10 UTC |
| R3-S5 | Validate output paths | claude-3.5-sonnet | Security vulnerability - path traversal in target names could write files outside output directory | 2026-02-11 22:06:10 UTC |
| R3-S6 | Map derivedFrom to template variables | claude-3.5-sonnet | Lost traceability - templates need derivedFrom for audit comments | 2026-02-11 22:06:10 UTC |
| R3-S7 | Add progress reporting for 77 files | claude-3.5-sonnet | User experience issue - no feedback during long generation process | 2026-02-11 22:06:10 UTC |
| R3-S9 | Specify parameter fallback chain | claude-3.5-sonnet | Undefined behavior for optional parameters could cause template errors | 2026-02-11 22:06:10 UTC |
| R3-S10 | Add generation metrics/telemetry | claude-3.5-sonnet | Operational visibility needed for monitoring generation performance and failures | 2026-02-11 22:06:10 UTC |
| R3-S11 | Handle concurrent manifest updates | claude-3.5-sonnet | Race condition risk when Step 23 rewrites manifest while other tools access it | 2026-02-11 22:06:10 UTC |
| R3-S12 | Validate template output | claude-3.5-sonnet | Malformed YAML/JSON from templates would cause deployment failures | 2026-02-11 22:06:10 UTC |
| R3-S14 | Define alert_template generator | claude-3.5-sonnet | Missing implementation - contract lists 8 types but plan only implements 7 | 2026-02-11 22:06:10 UTC |
| R3-S15 | Validate artifact type enum | claude-3.5-sonnet | Type safety - string lookups in registry could have typos causing runtime errors | 2026-02-11 22:06:10 UTC |

### Appendix B: Rejected Suggestions (with Rationale)

| ID | Suggestion | Source | Rejection Rationale | Date |
|----|------------|--------|---------------------|------|
| R1-S9 | Support YAML anchor expansion in templates | claude-4 (claude-opus-4-20250514) | yaml.safe_load already handles anchors correctly, no additional work needed | 2026-02-11 21:56:56 UTC |
| R1-S13 | Support template customization via config | claude-4 (claude-opus-4-20250514) | Premature flexibility - can add later if users request customization | 2026-02-11 21:56:56 UTC |
| R1-S19 | Support parallel generation for performance | claude-4 (claude-opus-4-20250514) | Premature optimization - 77 files is not enough to justify complexity | 2026-02-11 21:56:56 UTC |
| R2-S5 | Define clear generator extension mechanism | claude-3-5-sonnet-20241022 | Over-engineering at this stage - the 7 generators cover all contract-defined types, extensibility can be added later if needed | 2026-02-11 22:02:31 UTC |
| R2-S13 | Validate parameter completeness per type | claude-3-5-sonnet-20241022 | Plan already handles missing parameters with defaults in each generator - strict validation would reduce flexibility | 2026-02-11 22:02:31 UTC |
| R2-S16 | Support multiple output formats per type | claude-3-5-sonnet-20241022 | Not required by contract and adds complexity - current single format per type is sufficient | 2026-02-11 22:02:31 UTC |
| R2-S19 | Handle template version compatibility | claude-3-5-sonnet-20241022 | Premature optimization - templates are bundled with code, versioning adds unnecessary complexity | 2026-02-11 22:02:31 UTC |
| R3-S8 | Define error recovery behavior | claude-3.5-sonnet | Step 1 already specifies 'errors per-artifact, not abort-all' behavior | 2026-02-11 22:06:10 UTC |
| R3-S13 | Support incremental generation | claude-3.5-sonnet | Step 22 already implements skip-existing behavior for incremental updates | 2026-02-11 22:06:10 UTC |

### Appendix C: Incoming Suggestions (Untriaged, append-only)

#### Review Round R1

**Reviewer**: claude-4 (claude-opus-4-20250514)  
**Date**: 2026-02-11 21:54:59 UTC  
**Scope**: Requirements traceability and architecture review — manifest generation plan vs contract spec

| ID | Area | Severity | Suggestion | Rationale | Proposed Placement | Validation Approach |
| ---- | ---- | ---- | ---- | ---- | ---- | ---- |
| R1-S1 | Architecture | high | Add explicit error handling strategy for partial generation failures | The plan mentions "Errors per-artifact, not abort-all" but doesn't specify how errors are aggregated, reported, or recovered. Need clear error collection and reporting mechanism. | Step 1: Add `errors: List[GenerationError]` to orchestrator return type | Test partial failure scenarios where some generators succeed and others fail |
| R1-S2 | Data | high | Add validation for required parameters before generation | The contract specifies required parameters per artifact type, but the plan doesn't validate these before attempting generation. Missing params could cause runtime errors. | Step 6: Add parameter validation in each generator function | Unit tests with missing required parameters |
| R1-S3 | Interfaces | medium | Implement `--scan-existing` flag to match contract spec | The contract specifies scanning for existing artifacts, but the plan only implements `--force` overwrite. Need to match the contract's coverage tracking capability. | Step 22: Add `--scan-existing` option to CLI | Integration test comparing scan results to generated files |
| R1-S4 | Architecture | high | Add derivation rule tracking to generated artifacts | The contract emphasizes derivation audit trails, but generators don't preserve the `derivedFrom` metadata in output artifacts (e.g., as comments). | Each generator step: Add derivation info as comments in generated files | Verify derivation comments present in output files |
| R1-S5 | Validation | critical | Add contract schema validation on manifest load | The plan loads manifest with `ArtifactManifest(**data)` but doesn't validate against the contract schema first. Invalid manifests could cause cryptic errors. | Step 3: Add schema validation before model instantiation | Test with malformed manifest files |
| R1-S6 | Data | medium | Handle `null` existingPath gracefully | The contract shows `existingPath: null` for non-existing artifacts. Plan should handle this when updating manifest. | Step 23: Add null-safe handling for existingPath updates | Test updating manifest with mixed null/non-null paths |
| R1-S7 | Architecture | high | Add template versioning mechanism | As templates evolve, need way to track which version generated each artifact. Contract has `contextcoreVersion` but templates aren't versioned. | Step 2: Add VERSION constant to each template | Verify version comments in generated artifacts |
| R1-S8 | Ops | medium | Implement progress reporting for large manifests | With 77 artifacts for Online Boutique, generation could take time. Need progress feedback. | Step 1: Add progress callback to generate_all() | Manual test with large manifest |
| R1-S9 | Interfaces | low | Support YAML anchor expansion in templates | Contract parameters might use YAML anchors for shared values. Templates should handle expanded values. | Step 1: Ensure yaml.safe_load with anchor support | Test manifest with YAML anchors |
| R1-S10 | Risks | high | Add rollback mechanism for failed generations | If generation fails partway, could leave inconsistent state. Need atomic generation or rollback. | Step 1: Generate to temp dir first, then move atomically | Test interrupting generation mid-process |
| R1-S11 | Validation | medium | Validate generated artifacts against their schemas | Plan generates files but doesn't validate they conform to Prometheus/Grafana/etc schemas. | Each generator step: Add post-generation validation | Integration tests with schema validators |
| R1-S12 | Architecture | medium | Extract common template variables | All templates need `target_name`, many need `namespace`. Should have base context. | Step 5: Create base template context builder | Verify consistent variable naming across templates |
| R1-S13 | Data | low | Support template customization via config | Hard-coded templates limit flexibility. Allow user-provided template overrides. | Step 2: Add template search path configuration | Test with custom template directory |
| R1-S14 | Interfaces | high | Match contract's artifact ID format | Contract uses IDs like "checkoutservice-prometheus-rules" but plan uses different naming. | Each generator: Use artifact.id for filename, not custom format | Verify output filenames match contract IDs |
| R1-S15 | Security | medium | Sanitize template inputs | User-controlled values in parameters could cause template injection if not escaped. | Step 1: Add input sanitization utilities | Security tests with malicious parameter values |
| R1-S16 | Ops | medium | Add dry-run preview of changes | Dry-run only shows what would be generated, not the actual content changes. | Step 3: Add --preview flag to show diff preview | Manual test comparing preview to actual generation |
| R1-S17 | Risks | critical | Handle filesystem permissions errors | Plan assumes write access to output directory. Need graceful handling of permission denied. | Step 1: Add filesystem permission checks upfront | Test generation to read-only directory |
| R1-S18 | Validation | high | Implement the contract's validation_errors field | Contract has `validationErrors: []` per artifact but plan doesn't populate this. | Step 23: Capture and write validation errors to updated manifest | Verify validation errors appear in updated manifest |
| R1-S19 | Architecture | low | Support parallel generation for performance | With 77 artifacts, serial generation could be slow. Consider concurrent generation. | Step 1: Add optional parallel execution mode | Performance test with/without parallelization |
| R1-S20 | Interfaces | medium | Honor the contract's priority field | Contract specifies priority (required/recommended/optional) but plan treats all equally. | Step 1: Add priority filtering option to CLI | Test filtering by priority level |

#### Requirements Coverage

| Feature Doc Section | Plan Step(s) | Coverage | Gaps |
| ---- | ---- | ---- | ---- |
| Contract purpose (WHAT vs HOW separation) | Architecture section | Full | Plan correctly implements consumer side of contract |
| Artifact Manifest generation via `contextcore manifest export` | Context section (assumes already exists) | Full | Plan consumes the exported manifest |
| Schema compliance (apiVersion, kind, metadata) | Step 3 (loads via ArtifactManifest model) | Partial | No explicit schema validation before loading |
| Artifacts array with required fields | Steps 6-20 (generators use artifact fields) | Full | All required fields are accessed |
| derivedFrom audit trail | Not implemented | Missing | Derivation rules not preserved in generated artifacts |
| Parameters per artifact type | Steps 6-20 (each extracts type-specific params) | Full | All parameter types from contract are handled |
| Coverage tracking (needed/exists/outdated) | Step 23 (updates status to exists) | Partial | Only handles exists status, not outdated detection |
| existingPath population | Step 23 (sets path after generation) | Partial | No --scan-existing to detect pre-existing artifacts |
| Standard derivations table | Not applicable | N/A | This is for export, not generate |
| Coverage states | Step 22-23 (skip existing, update status) | Partial | Missing outdated and skipped state handling |
| Load contract + CRD | Step 3 (loads manifest only) | Partial | Doesn't load CRD for additional context as suggested |
| Iterate over artifacts | Step 1 (generate_all function) | Full | Correctly iterates based on status |
| Use derivation rules | Not implemented | Missing | No access to derivedFrom in generation |
| Report coverage back | Step 23 (--update-manifest) | Full | Updates manifest after generation |
| CI/CD pipeline example | Not implemented | Missing | No pipeline integration examples |
| GitOps structure | Steps 6-20 (output directory structure) | Full | Matches suggested directory layout |
| Validation approach | Step 21 (end-to-end test) | Partial | Only tests parseability, not schema compliance |

#### Feature Requirements Suggestions

| ID | Area | Severity | Suggestion | Rationale | Proposed Placement | Validation Approach |
| ---- | ---- | ---- | ---- | ---- | ---- | ---- |
| R1-F1 | Data | high | Clarify parameter source when CRD is needed | Contract says "Load CRD for additional context" but doesn't specify when generators need CRD data vs manifest parameters | Implementation Guide section | Cross-reference which parameters come from manifest vs CRD |
| R1-F2 | Interfaces | medium | Specify behavior for outdated artifact detection | Contract defines "outdated" status but not how to detect when existing artifacts need updates | Coverage States section | Define version/checksum comparison mechanism |
| R1-F3 | Validation | medium | Define schema URLs for artifact validation | Contract mentions artifacts must be valid but doesn't provide schema references for validation | Artifact Types table | Add schema URL column for each type |
| R1-F4 | Architecture | low | Clarify if generators can modify the manifest | Contract shows manifest updates but doesn't specify if generators can add new fields | Schema section | Document which fields are generator-writable |
| R1-F5 | Risks | medium | Specify error handling for invalid derivation rules | derivedFrom could reference non-existent source fields | Derivation Rules section | Add error handling requirements |

#### Review Round R2

- **Reviewer**: claude-3-5-sonnet-20241022
- **Date**: 2024-11-11 22:00:26 UTC
- **Scope**: Requirements traceability and architecture review — manifest generation plan vs contract spec

| ID | Area | Severity | Suggestion | Rationale | Proposed Placement | Validation Approach |
| ---- | ---- | ---- | ---- | ---- | ---- | ---- |
| R2-S1 | Architecture | critical | Add validation against derivedFrom rules before generation | Plan generates artifacts but doesn't validate that parameters match their derivation rules (e.g., criticality→severity mapping) | Step 1: Add `validate_derivation_rules()` to generator module | Test transformation rules against known mappings |
| R2-S2 | Data | high | Implement artifact version tracking mechanism | Plan updates status to "exists" but contract requires detecting "outdated" status - no versioning strategy | Step 23: Add content hash or version field | Compare hashes on re-generation |
| R2-S3 | Interfaces | high | Add schema validation for generated artifacts | Contract requires artifacts be valid but plan doesn't validate output against official schemas | Each generator step: Add schema validation | Validate against Prometheus/Grafana/OpenSLO schemas |
| R2-S4 | Risks | critical | Handle partial generation failures gracefully | Plan continues on errors but doesn't track which artifacts failed - could leave system in inconsistent state | Step 1: Track failed artifacts in manifest update | Add failure recovery mechanism |
| R2-S5 | Architecture | medium | Define clear generator extension mechanism | Plan hardcodes 7 generators but contract implies extensibility for custom artifact types | Step 1: Document generator plugin interface | Add custom generator registration example |
| R2-S6 | Data | high | Load CRD when parameters reference it | Contract shows CRD loading but plan only uses manifest - missing context for complex derivations | Step 3: Add `--crd-path` option to CLI | Cross-reference CRD fields in generators |
| R2-S7 | Validation | high | Implement coverage threshold enforcement | Contract shows coverage calculation but plan doesn't enforce minimum thresholds | Step 23: Add `--min-coverage` option | Fail if coverage below threshold |
| R2-S8 | Ops | critical | Add rollback capability for failed generations | No way to undo partial generation if errors occur midway | Step 22: Create backup before overwriting | Implement atomic generation with staging |
| R2-S9 | Security | medium | Validate template injection risks | Jinja2 templates with user-controlled data could have injection vulnerabilities | Each template step: Add input sanitization | Escape special characters in parameters |
| R2-S10 | Interfaces | medium | Support batch and individual artifact generation | Plan only supports all-or-filtered generation, not specific artifact IDs | Step 3: Add `--artifact-id` option | Generate single artifact by ID |
| R2-S11 | Data | high | Preserve custom fields in manifest updates | Step 23 rewrites manifest but might lose custom fields/annotations | Step 23: Use merge strategy not overwrite | Test round-trip preservation |
| R2-S12 | Risks | high | Add generation dependency ordering | Some artifacts may depend on others (e.g., SLOs need ServiceMonitors) | Step 1: Add dependency graph resolution | Topological sort before generation |
| R2-S13 | Validation | medium | Validate parameter completeness per type | Plan uses defaults for missing params but contract implies all required params must be present | Each generator: Check required params | Fail on missing required parameters |
| R2-S14 | Architecture | medium | Implement generator result caching | Re-generating unchanged artifacts wastes resources | Step 22: Add content-based caching | Skip if inputs unchanged |
| R2-S15 | Ops | high | Add progress reporting for large manifests | 77 artifacts could take time - no progress feedback | Step 1: Add progress callback to generate_all | Show generation progress bar |
| R2-S16 | Data | medium | Support multiple output formats per type | Contract doesn't specify but some artifacts might need multiple formats (YAML + JSON) | Generator registry: Support format variants | Add `--output-format` option |
| R2-S17 | Interfaces | low | Provide manifest validation command | Users might have invalid manifests before generation | New step: Add `manifest validate` command | Validate before generate |
| R2-S18 | Security | high | Implement access control for sensitive parameters | Escalation contacts and alert channels are sensitive data | Step 18/16: Mask sensitive data in logs | Add `--redact-sensitive` option |
| R2-S19 | Risks | medium | Handle template version compatibility | Templates might change - old manifests might break | Templates directory: Add version markers | Check template compatibility |
| R2-S20 | Validation | high | Add artifact content validation tests | Plan tests structure but not content correctness | Each generator test: Validate semantic content | Check alert expressions are valid PromQL |

**Endorsements** (prior untriaged suggestions this reviewer agrees with):
- R1-F2: Coverage states need clear detection mechanism - this is critical for the "outdated" status to work
- R1-F3: Schema validation URLs would enable proper artifact validation as I suggested in R2-S3
- R1-F5: Error handling for invalid derivation rules aligns with my R2-S1 about validation

#### Requirements Coverage

| Feature Doc Section | Plan Step(s) | Coverage | Gaps |
| ---- | ---- | ---- | ---- |
| Contract Overview (WHAT vs HOW separation) | Architecture section defines dispatcher pattern | Full | None |
| File Structure - manifest export command | Prerequisites (references existing export) | Full | None |
| Schema - all manifest fields | Step 3 loads via ArtifactManifest model | Partial | Missing: validationErrors field handling |
| Artifact Types (8 types) | Steps 5-20 implement 7 types | Partial | Missing: alert_template type generator |
| Derivation Rules - validation | None | Missing | No validation that parameters match derivedFrom rules |
| Derivation Rules - standard transformations | None | Missing | No implementation of criticality→severity mappings |
| Coverage Tracking - status states | Step 22-23 updates status | Partial | Missing: "outdated" detection logic |
| Coverage Tracking - scan existing | Step 22 checks existence | Partial | Missing: content comparison for outdated |
| Implementation Guide - Load CRD | None | Missing | Plan never loads CRD despite contract requirement |
| Implementation Guide - Use derivation rules | None | Missing | Generators don't reference derivedFrom |
| Implementation Guide - Report coverage | Step 23 updates manifest | Full | None |
| Pipeline Integration examples | None | Missing | No CI/CD integration examples |
| Error handling requirements | Step 1 mentions "errors per-artifact" | Partial | No specific error types or recovery |

#### Feature Requirements Suggestions

| ID | Area | Severity | Suggestion | Rationale | Proposed Placement | Validation Approach |
| ---- | ---- | ---- | ---- | ---- | ---- | ---- |
| R2-F1 | Data | high | Add alert_template artifact type specification | Contract lists 8 types but only defines 7 - alert_template is missing | Artifact Types table | Add example parameters and purpose |
| R2-F2 | Interfaces | critical | Define "outdated" detection algorithm | Contract has outdated status but no algorithm for detecting when regeneration needed | Coverage States section | Specify version/checksum comparison |
| R2-F3 | Data | high | Specify CRD schema subset needed | Contract says "load CRD for context" but doesn't specify which fields generators need | Implementation Guide section | List required CRD paths per artifact type |
| R2-F4 | Validation | medium | Add validation schema for derivedFrom | derivedFrom structure needs schema to prevent invalid transformations | Derivation Rules section | Add JSON schema for rule validation |
| R2-F5 | Architecture | medium | Clarify manifest mutation permissions | Contract shows updates but doesn't specify which systems can modify | Schema section | Define read-only vs mutable fields |
| R2-F6 | Risks | high | Add conflict resolution for existing artifacts | Contract doesn't specify behavior when generated conflicts with manual | Coverage Tracking section | Define merge vs overwrite strategy |

#### Review Round R3

- **Reviewer**: claude-3.5-sonnet
- **Date**: 2026-02-11 22:04:20 UTC
- **Scope**: Requirements traceability and architecture review — manifest generation plan vs contract spec

| ID | Area | Severity | Suggestion | Rationale | Proposed Placement | Validation Approach |
| ---- | ---- | ---- | ---- | ---- | ---- | ---- |
| R3-S1 | Interfaces | critical | Define CRD field extraction mechanism | Plan Step 9 says "extracts alertSeverity" but contract shows these come from CRD fields (e.g., spec.business.criticality→P2), not directly from manifest parameters | Step 9 implementation details | Add CRD loading logic to generators that need derivation |
| R3-S2 | Security | high | Add template injection protection | Jinja2 templates with user-supplied values (target names, owner fields) risk XSS/injection in generated JSON/YAML | Step 1 _get_jinja_env() | Enable autoescape, validate inputs before templating |
| R3-S3 | Ops | critical | Add generation transaction/rollback | Plan generates 77 files but has no rollback if generation fails midway, leaving partial/inconsistent state | Step 1 generate_all() | Implement temp dir + atomic move or rollback on failure |
| R3-S4 | Risks | high | Handle manifest version compatibility | Plan assumes v1 manifest format but contract evolves - no version checking could cause silent failures | Step 3 manifest loading | Check manifest version, fail if incompatible |
| R3-S5 | Security | medium | Validate output paths | Generated paths like `{target}-dashboard.json` could have path traversal if target contains `../` | All generator functions | Sanitize target names, validate output paths stay in output_dir |
| R3-S6 | Interfaces | high | Map derivedFrom to template variables | Contract has derivedFrom audit trail but plan doesn't pass this to templates - loses traceability | Generator signature | Add derivedFrom to template context for comments |
| R3-S7 | Ops | high | Add progress reporting for 77 files | Generating 77 files with no progress feedback - users can't tell if hung or working | Step 1 generate_all() | Add progress bar or per-file status output |
| R3-S8 | Risks | medium | Define error recovery behavior | Plan says "errors per-artifact, not abort-all" but doesn't specify recovery/continuation logic | Step 1 generate_artifact() | Clarify error collection and final exit code |
| R3-S9 | Interfaces | medium | Specify parameter fallback chain | Contract shows some params optional but plan doesn't define defaults/fallbacks | Each generator function | Document default values when params missing |
| R3-S10 | Ops | medium | Add generation metrics/telemetry | No visibility into generation performance or common failures across runs | Step 1 generate_all() | Log timing, success rates, common errors |
| R3-S11 | Risks | high | Handle concurrent manifest updates | Step 23 rewrites manifest but could race with other tools reading/writing | Step 23 implementation | Use file locking or atomic write operations |
| R3-S12 | Security | high | Validate template output | Generated YAML/JSON could be malformed, causing deployment failures | Each generator after render | Parse output before writing to catch template errors |
| R3-S13 | Ops | medium | Support incremental generation | Regenerating all 77 files wasteful when only one changed | Step 22 enhancement | Check artifact modification time vs manifest |
| R3-S14 | Interfaces | critical | Define alert_template generator | Contract lists alert_template type but plan has no generator - missing implementation | New step after Step 20 | Add alert_template generator and template |
| R3-S15 | Risks | medium | Validate artifact type enum | Plan uses string lookup in registry but could have typos | Step 1 dispatcher | Validate type against ArtifactType enum |

**Endorsements** (prior untriaged suggestions this reviewer agrees with):
- R1-F1: CRD loading requirement is critical - Step 1 needs explicit guidance on when to load ProjectContext
- R2-F1: Missing alert_template implementation is a contract violation - must be added
- R2-F2: Outdated detection algorithm essential for Step 23's status updates to work correctly

#### Requirements Coverage

| Feature Doc Section | Plan Step(s) | Coverage | Gaps |
| ---- | ---- | ---- | ---- |
| Contract between ContextCore/Wayfinder | Step 1 (dispatcher), Step 3 (CLI) | Full | None |
| File Structure (manifest + CRD inputs) | Step 3 (manifest loading) | Partial | CRD loading not implemented |
| Schema (artifact manifest structure) | Step 3 (ArtifactManifest model) | Full | None |
| Artifact Types (8 types) | Steps 5-20 | Partial | alert_template missing (7/8 implemented) |
| Derivation Rules (derivedFrom) | None | Missing | No steps handle derivedFrom→parameters transformation |
| Coverage Tracking (status updates) | Steps 22-23 | Partial | Outdated detection not specified |
| Implementation Guide (load CRD) | None | Missing | No CRD loading despite contract requirement |
| Pipeline Integration | Not in scope | N/A | Example usage only |

#### Feature Requirements Suggestions

| ID | Area | Severity | Suggestion | Rationale | Proposed Placement | Validation Approach |
| ---- | ---- | ---- | ---- | ---- | ---- | ---- |
| R3-F1 | Data | critical | Clarify CRD requirement scope | Contract says "Load CRD for additional context" but doesn't enumerate which artifact types need CRD data | Implementation Guide | List which types need CRD |
| R3-F2 | Interfaces | high | Define parameter override precedence | When both manifest parameters AND derivedFrom exist, which wins? | Derivation Rules section | Add precedence rules |
| R3-F3 | Validation | medium | Add artifact output examples | Contract defines inputs but not expected outputs - implementers guess format | Artifact Types table | Add "Example Output" column |
| R3-F4 | Risks | high | Specify partial generation recovery | If 50/77 succeed then fail, should status be partially updated? | Coverage Tracking | Define partial update semantics |
| R3-F5 | Security | medium | Define sensitive parameter handling | Some parameters (escalationContacts) may be sensitive | Schema section | Mark sensitive fields |
