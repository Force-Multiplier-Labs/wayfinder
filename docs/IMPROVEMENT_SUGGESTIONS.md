# Wayfinder Improvement Suggestions

Suggestions to improve output quality for the plan ingestion and observability generation pipeline. Wayfinder runs the plan ingestion script and consumes ContextCore export outputs.

## Plan Ingestion Step (`scripts/run_manifest_generate_ingestion.py`)

| # | Suggestion | Rationale |
|---|------------|-----------|
| 1 | **Merge onboarding metadata into seed** | If `onboarding-metadata.json` exists in the export directory, merge `artifact_manifest_path`, `project_context_path`, `artifact_types`, `output_path_conventions`, and `semantic_conventions` into the artisan-context-seed `artifacts` / `onboarding` section. |
| 2 | **Add context file checksums to seed** | Store checksums of artifact manifest and project context in the seed so downstream steps can detect drift. |
| 3 | **Artifact count consistency check** | Compare plan "77 artifacts" vs manifest "6 artifacts" and add a warning or `plan_vs_context_note` so the mismatch is explicit. |
| 4 | **Validate artifact manifest schema** | Before enrichment, validate that the artifact manifest matches the expected schema. |
| 5 | **Ingestion provenance in seed** | Add an `ingestion_provenance` section (or reference) in the seed for full traceability. |
| 6 | **Cost estimate pre-run** | Show estimated cost before running and allow confirmation step. |

## Context File Paths

| # | Suggestion | Rationale |
|---|------------|-----------|
| 7 | **Onboarding metadata as context file** | When `onboarding-metadata.json` exists in the export dir, add it to context files for the architectural review. |
| 8 | **Relative paths in config** | Use paths relative to wayfinder root for portability across environments. |

## Pipeline Integration

| # | Suggestion | Rationale |
|---|------------|-----------|
| 9 | **Pipeline diagram** | Add a diagram of export → ingestion → artisan → generation in docs. |
| 10 | **Schema reference** | Document the expected structure of `artisan-context-seed.json` and its `onboarding` section. |
| 11 | **Troubleshooting guide** | Add a doc for common issues (checksum mismatch, plan vs context mismatch, missing onboarding metadata). |

## Artifact Generation (when `manifest generate` exists)

| # | Suggestion | Rationale |
|---|------------|-----------|
| 12 | **Default output-dir from onboarding** | Use `output_path_conventions` from onboarding metadata as default output structure. |
| 13 | **Pre-generation validation** | Before running generate, validate artifact manifest and project context exist and match checksums. |

---

## Priority Order

| Priority | Items | Effort |
|----------|-------|--------|
| High | 1, 2, 7 | 1–2 days |
| Medium | 3, 4, 5, 6, 8 | 1–2 days |
| Low | 9, 10, 11, 12, 13 | 1 day |

## Implementation Notes

- **Item 1**: Requires changes to `run_manifest_generate_ingestion.py` and/or the startd8 `PlanIngestionWorkflow` to read `onboarding-metadata.json` from the context file paths and merge into the seed.
- **Item 7**: Update `CONTEXT_FILES` in `run_manifest_generate_ingestion.py` to include `onboarding-metadata.json` when present.

## Related Repos

- **ContextCore** — [docs/IMPROVEMENT_SUGGESTIONS.md](../ContextCore/docs/IMPROVEMENT_SUGGESTIONS.md) (export command, artifact manifest)
- **startd8-sdk** — [docs/IMPROVEMENT_SUGGESTIONS.md](../startd8-sdk/docs/IMPROVEMENT_SUGGESTIONS.md) (PlanIngestionWorkflow, Artisan workflow)
