# ADR-003: Monorepo Separation

**Status:** Accepted
**Date:** 2026-02-01
**Author:** Neil Yashinsky

---

## Context

The ContextCore monorepo contained both the specification (schemas, semantic conventions, protocols, terminology) and the reference implementation (Python SDK, CLI, dashboards, expansion packs). As the project matured and the distinction between standard and implementation crystallized (per [ADR-002](https://github.com/contextcore/contextcore-spec/blob/main/docs/adr/002-naming-wayfinder.md)), these needed physical separation into distinct repositories.

A single repository conflated two concerns:

1. **The ContextCore specification** -- schemas, semantic conventions, protocols, and terminology that define the metadata standard. This is meant to be adopted independently by anyone.
2. **The Wayfinder implementation** -- the Python SDK (`contextcore` package), CLI, Grafana dashboards, expansion packs, and infrastructure that implement the standard.

Keeping both in one repository created confusion about what constituted the "standard" versus the "tooling," made it harder for others to adopt just the spec, and muddled the commit history with unrelated changes.

---

## Decision

**Split the monorepo into two repositories.**

| Repository | Purpose | Contents |
|-----------|---------|----------|
| **`contextcore-spec`** | The metadata standard | Schemas, semantic conventions, protocols, CRDs, terminology, ADRs |
| **`wayfinder`** | The reference implementation | Python package `contextcore`, CLI, expansion packs, dashboards, infrastructure |

### What Stays the Same

Several names intentionally remain unchanged despite the split, because they refer to the ContextCore standard (not the repository):

| Artifact | Name | Reason |
|----------|------|--------|
| Python package | `contextcore` | Implements the ContextCore standard |
| CLI command | `contextcore` | Implements the ContextCore standard |
| Expansion packs | `contextcore-*` | Part of the ContextCore ecosystem |
| K8s annotations | `contextcore.io/*` | Defined by the spec |
| CRDs | `contextcore.io` API group | Defined by the spec |

### Fresh Git History

Both repositories start with clean first commits rather than using `git filter-repo` to transplant history. The original monorepo is preserved with a `pre-separation-snapshot` tag for historical reference.

**Rationale:**
- Clean history is easier to navigate
- No risk of filter-repo artifacts or orphaned references
- The original monorepo remains available as an archive

### Spec Artifacts in Wayfinder

Runtime spec artifacts needed by the implementation are vendored into the wayfinder repository:

```
wayfinder/
  vendor/
    contextcore-spec/     # Vendored spec artifacts
      schemas/
      semantic-conventions/
      ...
```

Documentation that references spec files uses GitHub URLs pointing to the `contextcore-spec` repository rather than relative paths.

---

## Consequences

### Positive

1. **Clear separation of standard vs implementation** -- Contributors and adopters can immediately understand which repo serves which purpose
2. **Spec can be adopted independently** -- Organizations can implement the ContextCore standard without depending on Wayfinder
3. **Focused scope per repo** -- Each repository has a clear mission, simpler CI, and targeted issue tracking
4. **Ecosystem credibility** -- A standalone spec repository signals that ContextCore is a standard, not just a product

### Neutral

1. **Spec updates require vendoring** -- When the spec changes, vendored copies in wayfinder must be updated. This is a deliberate friction that ensures implementation changes are intentional.
2. **Two repos to maintain** -- Slightly more overhead for a solo/small team, but manageable given the clear boundaries.

### Negative

1. **External doc links** -- Some documentation links that were previously relative paths within the monorepo are now external GitHub URLs. These are less resilient to reorganization.
2. **Cross-repo coordination** -- Breaking changes to the spec require coordinated updates across repositories.

---

## Alternatives Considered

### 1. Keep the Monorepo

Continue with a single repository, using directory structure to separate spec from implementation.

**Rejected because:**
- Blurs the line between standard and tooling
- Makes independent spec adoption harder
- Commit history mixes unrelated concerns

### 2. Git Filter-Repo Split

Use `git filter-repo` to create new repositories with transplanted history from the monorepo.

**Rejected because:**
- Risk of artifacts and orphaned references
- Transplanted history carries irrelevant commits into each repo
- Clean first commits are simpler and communicate intent clearly

### 3. Git Submodules

Keep the spec as a git submodule within wayfinder.

**Rejected because:**
- Submodules add workflow complexity (init, update, sync)
- Poor developer experience for contributors unfamiliar with submodules
- Vendoring is simpler and more explicit

---

## References

- [ADR-002: Naming Convention -- Wayfinder and ContextCore](https://github.com/contextcore/contextcore-spec/blob/main/docs/adr/002-naming-wayfinder.md)
- [ADR-001: Model Tasks as OpenTelemetry Spans](https://github.com/contextcore/contextcore-spec/blob/main/docs/adr/001-tasks-as-spans.md)

---

## Changelog

| Date | Change |
|------|--------|
| 2026-02-01 | Initial decision documented |
