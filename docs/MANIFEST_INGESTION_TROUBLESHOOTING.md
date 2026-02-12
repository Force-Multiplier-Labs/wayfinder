# Manifest Ingestion Troubleshooting Guide

Common issues when running `scripts/run_manifest_generate_ingestion.py`.

## Missing Onboarding Metadata

### Symptom

- Seed does not have `artifact_manifest_path`, `project_context_path`, or `onboarding` section
- Hint message: "Run contextcore manifest export..."

### Cause

`onboarding-metadata.json` is not in `out/contextcore-export/`. The ContextCore export produces it by default.

### Resolution

From the **ContextCore** repository:

```bash
cd ~/Documents/dev/ContextCore
contextcore manifest export \
  -p ../wayfinder/.contextcore.yaml \
  -o ../wayfinder/out/contextcore-export
```

This creates `wayfinder/out/contextcore-export/onboarding-metadata.json`. Re-run the ingestion script.

---

## Checksum Mismatch

### Symptom

- Seed has `artifact_manifest_checksum` and `project_context_checksum`
- Downstream step reports "context file checksum does not match"

### Cause

The artifact manifest or project context was modified after export. Checksums are computed at export time.

### Resolution

1. Re-run ContextCore export to regenerate all files
2. Re-run ingestion to refresh the seed with new checksums
3. Ensure no manual edits to generated YAML files between export and consumption

---

## Plan vs Context Mismatch

### Symptom

- Plan says "77 artifacts (7 × 11 services)" but manifest has 6 artifacts
- Plan is generic (e.g., Online Boutique) while context is project-specific (wayfinder-core)

### Cause

Expected when using a template plan with project-specific context. The plan describes a full example; the actual artifact count comes from the manifest.

### Resolution

- Document the mismatch in the plan or seed
- The `plan_vs_context_note` (if present) in the seed explains the difference
- Use `onboarding.artifact_types` and `artifact_manifest_path` from the seed for the actual artifact count

---

## Context File Not Found

### Symptom

```
Warning: Context file not found: .../wayfinder-artifact-manifest.yaml
```

### Cause

ContextCore export has not been run, or output is in a different directory.

### Resolution

1. Run ContextCore manifest export (see above)
2. Ensure output goes to `wayfinder/out/contextcore-export/`
3. Verify files exist: `wayfinder-artifact-manifest.yaml`, `wayfinder-projectcontext.yaml`

---

## Related Documentation

- [ContextCore MANIFEST_TROUBLESHOOTING](../ContextCore/docs/MANIFEST_TROUBLESHOOTING.md)
- [ContextCore ONBOARDING_METADATA_SCHEMA](../ContextCore/docs/ONBOARDING_METADATA_SCHEMA.md)
- [Wayfinder IMPROVEMENT_SUGGESTIONS_2026-02-12](./IMPROVEMENT_SUGGESTIONS_2026-02-12.md)
