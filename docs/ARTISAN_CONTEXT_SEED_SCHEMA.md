# Artisan Context Seed Schema Reference

The `artisan-context-seed.json` is produced by the Plan Ingestion workflow (`scripts/run_manifest_generate_ingestion.py`) and consumed by the startd8 Artisan workflow. It provides project context, architectural constraints, and artifact metadata for code generation.

## Top-Level Structure

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `version` | string | yes | Schema version (e.g. `"1.0.0"`) |
| `generated_at` | string (ISO 8601) | yes | Timestamp when the seed was generated |
| `generator` | string | yes | Source generator (e.g. `"plan-ingestion"`) |
| `plan` | object | yes | Parsed plan with goals, features, dependency graph |
| `artifacts` | object | no | Paths and checksums for context files |
| `onboarding` | object | no | Merged from onboarding-metadata.json when present |
| `ingestion_provenance` | object | no | Traceability to ingestion run |
| `plan_vs_context_note` | string | no | Note when plan artifact count differs from manifest |
| `complexity` | object | yes | Complexity score and routing decision |
| `tasks` | array | yes | Task breakdown for Artisan workflow |
| `architectural_context` | object | yes | Goals, constraints, preferences for generation |
| `ingestion_metrics` | object | no | Cost breakdown from ingestion |
| `design_calibration` | object | no | Per-task design depth settings |

---

## `plan`

Parsed output from the plan document.

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Plan title |
| `goals` | array of strings | High-level goals |
| `features` | array | Feature definitions (see below) |
| `dependency_graph` | object | Map of feature_id → list of dependency IDs |
| `mentioned_files` | array of strings | Files referenced in the plan |
| `raw_text` | string | Original plan text (optional) |

### Feature Object

| Field | Type | Description |
|-------|------|-------------|
| `feature_id` | string | Unique ID (e.g. `"F-001"`) |
| `name` | string | Feature name |
| `description` | string | Feature description |
| `target_files` | array of strings | Files to create or modify |
| `dependencies` | array of strings | Feature IDs this depends on |
| `estimated_loc` | number | Estimated lines of code |
| `labels` | array of strings | Labels (e.g. `"infrastructure"`, `"core"`) |

---

## `artifacts`

Paths and checksums for downstream consumers. Paths are relative to the project root when merged from onboarding.

| Field | Type | Description |
|-------|------|-------------|
| `plan_document_path` | string | Path to ingested plan markdown |
| `review_config_path` | string | Path to review configuration |
| `artifact_manifest_path` | string | Path to artifact manifest YAML |
| `project_context_path` | string | Path to project context YAML |
| `artifact_manifest_checksum` | string | SHA-256 of artifact manifest |
| `project_context_checksum` | string | SHA-256 of project context |

---

## `onboarding`

Merged from `onboarding-metadata.json` when present. Provides artifact type definitions and conventions for generators.

| Field | Type | Description |
|-------|------|-------------|
| `artifact_types` | object | Per-type definitions (output_ext, output_path, parameter_keys, etc.) |
| `output_path_conventions` | object | Per-type output path templates (e.g. `grafana/dashboards/{target}-dashboard.json`) |
| `parameter_schema` | object | Per-type parameter keys |
| `semantic_conventions` | object | OTel attribute namespaces, metrics, query templates |
| `source_checksum` | string | Checksum of onboarding source |
| `artifact_manifest_checksum` | string | Checksum of artifact manifest |
| `project_context_checksum` | string | Checksum of project context |
| `default_output_dir` | string | Default output directory for manifest generate (when present) |

### `artifact_types` Entry

| Field | Type | Description |
|-------|------|-------------|
| `output_ext` | string | File extension (e.g. `.json`, `.yaml`) |
| `output_path` | string | Path template with `{target}` placeholder |
| `description` | string | Human-readable description |
| `parameter_keys` | array | Parameter names |
| `parameter_sources` | object | Map of parameter → manifest field |
| `example_output_path` | string | Example path |
| `schema_url` | string | External schema reference |

---

## `ingestion_provenance`

Traceability to the ingestion run that produced this seed.

| Field | Type | Description |
|-------|------|-------------|
| `ref` | string | Path to ingestion-provenance.json (relative to project root) |
| `checksum` | string | SHA-256 of provenance file for verification |

---

## `plan_vs_context_note`

Optional string explaining when the plan describes a generic example (e.g. "77 artifacts") while the actual manifest has fewer. Helps downstream consumers avoid confusion.

---

## `complexity`

| Field | Type | Description |
|-------|------|-------------|
| `composite` | number | Aggregated complexity score |
| `dimensions` | object | Per-dimension scores (feature_count, cross_file_deps, etc.) |
| `reasoning` | string | Human-readable rationale |
| `route` | string | `"prime"` or `"artisan"` |

---

## `tasks`

Array of task objects for the Artisan workflow.

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | string | Unique ID (e.g. `"PI-001"`) |
| `title` | string | Task title |
| `task_type` | string | e.g. `"task"` |
| `story_points` | number | Effort estimate |
| `priority` | string | e.g. `"high"` |
| `labels` | array | Task labels |
| `depends_on` | array | Task IDs this depends on |
| `config` | object | Task-specific config (task_description, context) |

---

## `architectural_context`

| Field | Type | Description |
|-------|------|-------------|
| `project_goals` | array of strings | Project goals |
| `objectives` | array | OKR-style objectives with key_results |
| `constraints` | array | Rules with severity (blocking, warning) and scope |
| `preferences` | array of strings | Design preferences |
| `focus_areas` | array of strings | Areas to emphasize |
| `shared_modules` | array | Modules shared across features |
| `import_conventions` | array | Import path conventions |
| `domain_concepts` | array | Domain terms |
| `dependency_clusters` | array | Feature dependency groupings |

---

## Related Documentation

- [MANIFEST_INGESTION_TROUBLESHOOTING.md](MANIFEST_INGESTION_TROUBLESHOOTING.md) — Common ingestion issues
- [IMPROVEMENT_SUGGESTIONS_2026-02-12.md](IMPROVEMENT_SUGGESTIONS_2026-02-12.md) — Pipeline improvements
- ContextCore `docs/ONBOARDING_METADATA_SCHEMA.md` — Onboarding metadata schema
