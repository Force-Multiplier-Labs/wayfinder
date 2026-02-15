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
