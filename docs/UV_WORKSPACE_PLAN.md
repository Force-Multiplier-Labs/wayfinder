# UV Workspace Plan for Wayfinder

A phased migration from scattered repos to a unified uv workspace monorepo.

**Progression**: Phase 1 (this repo only) → Phase 2 (consolidate active packages) → Phase 3 (full monorepo)

---

## Ecosystem Inventory

### Python packages in this repo (wayfinder)

| Package | Location | Build Backend | Commits | Status |
|---------|----------|---------------|---------|--------|
| `contextcore` | `./` (src/contextcore/) | hatchling | Many | Active, working |
| `wayfinder-fox` | `./wayfinder-fox/` | setuptools | 12 | Active, working |

Non-Python: `wayfinder-mixin` (Jsonnet dashboards/rules) — excluded from uv workspace.

### Python packages in separate repos (~/Documents/dev/)

| Package | Repo | Build Backend | Commits | Remote | Maturity |
|---------|------|---------------|---------|--------|----------|
| `contextcore-rabbit` | contextcore-rabbit | hatchling | 1 | GitHub (FML) | Scaffold |
| `contextcore-fox` | contextcore-fox | hatchling | 1 | GitHub (FML) | Scaffold |
| `contextcore-coyote` | contextcore-coyote | hatchling | 3 | GitHub (personal) | Early impl |
| `contextcore-owl` | contextcore-owl | hatchling | 1 | GitHub (FML) | Scaffold |
| `contextcore-skills` | contextcore-skills | setuptools | 12 | Local only | Working |
| `contextcore-mole` | contextcore-mole | setuptools | 2 | Local only | Working |

Not Python packages (permanently out of scope):
- `contextcore-beaver` — shell env/registry, no pyproject.toml
- `contextcore-spec` — pure documentation (separate by design per ADR-002)
- `contextcore-dot-me` — HTML docs site, not a git repo
- `contextcore-viewer` — standalone HTML utility

### contextcore-fox vs wayfinder-fox

Two different packages solving the same problem at different layers:

| Aspect | wayfinder-fox | contextcore-fox |
|--------|---------------|-----------------|
| **Location** | Embedded in wayfinder monorepo | Standalone repo |
| **Architecture** | Pure enrichment library (no server) | Full Flask webhook server + CLI |
| **Core deps** | OTel + PyYAML only | OTel + Flask + httpx + contextcore + rabbit |
| **Rabbit dep** | Optional (`pip install wayfinder-fox[rabbit]`) | Hard requirement |
| **Entry point** | Python API only | `contextcore-fox serve`, Flask server |
| **Maturity** | 12 commits, iterated, tested | 1 commit, scaffolded |

**Decision needed before Phase 2**: Consolidate into one package or keep as library + application split. See Open Questions.

### Current dependency graph

```
contextcore-coyote ──optional──> contextcore

contextcore-fox ──hard──> contextcore-rabbit
       │
       └──hard──> contextcore

wayfinder-fox ──optional──> contextcore-rabbit
       │
       └──optional──> contextcore

contextcore-rabbit (standalone, no ecosystem deps)

contextcore-skills (standalone)

contextcore-mole (standalone)

contextcore-owl ──optional scaffold──> contextcore-beaver
```

### What's broken today

1. **`pip install wayfinder-fox[rabbit]` fails from clean env** — `contextcore-rabbit` and `contextcore` aren't on PyPI
2. **`pip install contextcore-fox` fails from clean env** — same, but worse: rabbit and contextcore are hard deps
3. **No lock file** — non-reproducible dependency resolution
4. **wayfinder-fox not in CI** — 23 tests across 4 files never run
5. **Build backend inconsistency** — hatchling vs setuptools across packages

---

## Phase 1: Wayfinder-Only Workspace (COMPLETE)

**Status**: Complete (committed as `3b7ba38`, pushed).

**Goal**: Get uv working for the two packages already in this repo. Fix broken installs, add lock file, get fox into CI.

**Prerequisite**: None.

### 1.1 Add `.python-version`

```
3.11
```

### 1.2 Add workspace config to root `pyproject.toml`

```toml
[tool.uv.workspace]
members = ["wayfinder-fox"]
```

### 1.3 Add source override in `wayfinder-fox/pyproject.toml`

```toml
[tool.uv.sources]
contextcore = { workspace = true }
```

When wayfinder-fox declares `contextcore>=0.1.0` as an optional dep, uv resolves it from the workspace instead of PyPI.

### 1.4 Add dev path override for rabbit in root `pyproject.toml`

```toml
[tool.uv.sources]
contextcore-rabbit = { path = "../contextcore-rabbit", editable = true }
```

Resolves rabbit from the sibling directory during local dev. CI skips rabbit tests via `pytest.importorskip` (already in place).

### 1.5 Normalize wayfinder-fox to hatchling

Switch wayfinder-fox from setuptools to hatchling. Not required by uv, but establishes the convention that all workspace members use hatchling. This matters for Phase 2 when more packages move in.

### 1.6 Generate and commit lock file

```bash
uv lock
git add uv.lock
```

### 1.7 Update Makefile

```makefile
install:
    uv sync --all-extras

install-core:
    uv sync --package contextcore --all-extras

install-fox:
    uv sync --package wayfinder-fox --all-extras

test:
    uv run pytest tests/

test-fox:
    uv run pytest wayfinder-fox/tests/

test-all:
    uv run pytest tests/ wayfinder-fox/tests/

lint:
    uv run ruff check src/ wayfinder-fox/src/

typecheck:
    uv run mypy src/contextcore
```

### 1.8 Update CI (.github/workflows/ci.yml)

```yaml
- uses: astral-sh/setup-uv@v5
  with:
    version: "latest"

- run: uv sync --all-extras

# Existing core tests
- run: uv run pytest tests/

# New: fox tests
- run: uv run pytest wayfinder-fox/tests/
```

Rabbit-dependent fox tests are skipped in CI (already handled by `pytest.importorskip`).

### 1.9 Update CLAUDE.md

Reflect `uv sync` / `uv run` in the Commands section.

### 1.10 Verify

```bash
rm -rf .venv
uv sync --all-extras
uv run pytest tests/
uv run pytest wayfinder-fox/tests/
uv run contextcore --help
```

### Phase 1 files changed

| File | Change |
|------|--------|
| `.python-version` | New (1 line) |
| `pyproject.toml` | Add `[tool.uv.workspace]`, `[tool.uv.sources]` (~8 lines) |
| `wayfinder-fox/pyproject.toml` | Add `[tool.uv.sources]`, switch to hatchling (~10 lines) |
| `uv.lock` | New (auto-generated) |
| `Makefile` | Replace pip targets with uv (~20 lines) |
| `.github/workflows/ci.yml` | Add uv, add fox tests (~15 lines) |
| `CLAUDE.md` | Update commands section (~10 lines) |

### Phase 1 outcome

- `uv sync` installs both packages from a clean env
- Lock file ensures reproducible builds
- wayfinder-fox tests run in CI
- Local dev with rabbit works via path override
- Foundation is in place for adding more workspace members

---

## Phase 2: Consolidate Active Packages (COMPLETE)

**Status**: Complete (committed as `8b363eb`).

**Goal**: Move packages with working code into the monorepo as workspace members. Atomic cross-package changes. Single CI.

**Prerequisite**: Phase 1 complete. Decision on contextcore-fox vs wayfinder-fox resolved.

### Packages to move in (as workspace members)

| Package | Current Repo | Why move |
|---------|-------------|----------|
| `contextcore-rabbit` | contextcore-rabbit | wayfinder-fox depends on it; 1 commit, no significant independent history |
| `contextcore-mole` | contextcore-mole | Working code (2 commits), parses Wayfinder trace exports |

### Also subtree'd in (NOT a workspace member)

| Directory | Current Repo | Why move | Why not a workspace member |
|-----------|-------------|----------|---------------------------|
| `contextcore-skills` | contextcore-skills | Working code (12 commits), integrated with core CLI (`contextcore skill emit`) | Data/scripts directory (YAML skill definitions + standalone Python scripts). Has no `pyproject.toml` and is not a pip-installable package. |

Leave in separate repos for now:
- `contextcore-coyote` — different GitHub org (personal), early impl, deliberately independent pipeline
- `contextcore-owl` — TypeScript Grafana plugins, different toolchain
- `contextcore-fox` — depends on resolution of the fox naming question

### 2.1 Move packages into repo

For each package, use `git subtree add` to preserve commit history:

```bash
git subtree add --prefix=contextcore-rabbit ../contextcore-rabbit main
git subtree add --prefix=contextcore-skills ../contextcore-skills main
git subtree add --prefix=contextcore-mole ../contextcore-mole main
```

This creates directories:
```
wayfinder/
├── contextcore-rabbit/      # NEW workspace member
│   ├── pyproject.toml
│   └── src/contextcore_rabbit/
├── contextcore-mole/        # NEW workspace member
│   ├── pyproject.toml
│   └── src/contextcore_mole/
├── contextcore-skills/      # Subtree'd in, NOT a workspace member (data/scripts, no pyproject.toml)
├── wayfinder-fox/           # Existing workspace member
├── wayfinder-mixin/         # Not a workspace member (Jsonnet)
├── src/contextcore/         # Workspace root package
└── pyproject.toml           # Workspace root
```

### 2.2 Normalize build backends

Switch any setuptools packages to hatchling for consistency:
- `contextcore-mole/pyproject.toml` → hatchling
- `contextcore-rabbit/pyproject.toml` → already hatchling

### 2.3 Normalize Python version floor

`contextcore-mole` currently targets `>=3.9`. Align to `>=3.11` to match the rest of the workspace.

### 2.4 Update workspace config

Root `pyproject.toml`:

```toml
[tool.uv.workspace]
members = [
    "wayfinder-fox",
    "contextcore-rabbit",
    "contextcore-mole",
]
```

Note: `contextcore-skills` is explicitly NOT a workspace member — it has no `pyproject.toml` and is not a pip-installable package.

### 2.5 Update source overrides

Remove the path override for rabbit (it's now a workspace member):

```toml
[tool.uv.sources]
contextcore-rabbit = { workspace = true }
```

Update `wayfinder-fox/pyproject.toml`:

```toml
[tool.uv.sources]
contextcore = { workspace = true }
contextcore-rabbit = { workspace = true }
```

### 2.6 Remove the `[rabbit]` optional extra workaround from wayfinder-fox

With rabbit in the workspace, `contextcore-rabbit>=0.1.0` resolves. Two options:

- **Keep it optional**: Good API design if fox should work without rabbit. The `try/except ImportError` guard in `fox_enrich.py` stays.
- **Make it a hard dep**: If fox always ships with rabbit in practice. Simplifies the import.

Recommendation: keep it optional. The enrichment library (enricher, router, tracer) has value without rabbit.

### 2.7 Regenerate lock file

```bash
uv lock
```

Now covers all 4 workspace members.

### 2.8 Update CI

Add test steps for each new package:

```yaml
- run: uv run pytest contextcore-rabbit/tests/
- run: uv run pytest contextcore-mole/tests/
```

Rabbit is now in the workspace, so wayfinder-fox's rabbit tests no longer need to be skipped.

### 2.9 Add cross-package linting

```yaml
- run: uv run ruff check src/ wayfinder-fox/src/ contextcore-rabbit/src/ contextcore-mole/src/
```

### 2.10 Archive original repos

After verifying everything works:
- Archive `contextcore-rabbit` on GitHub (mark as archived, point README to wayfinder monorepo)
- Local repos for `contextcore-skills` and `contextcore-mole` can be removed (no remotes to archive)

### Phase 2 files changed

| File | Change |
|------|--------|
| `pyproject.toml` | Update workspace members, update sources |
| `wayfinder-fox/pyproject.toml` | Add rabbit workspace source |
| `contextcore-rabbit/pyproject.toml` | Moved in (possibly minor edits) |
| `contextcore-mole/pyproject.toml` | Moved in, switch to hatchling, bump Python floor |
| `uv.lock` | Regenerated |
| `.github/workflows/ci.yml` | Add test steps for new packages |
| `Makefile` | Add targets for new packages |

### Phase 2 outcome

- `uv sync --all-extras` installs the entire active ecosystem
- Cross-package changes are atomic commits
- Single CI tests everything
- Rabbit integration tests run in CI (no longer skipped)
- Lock file covers all 4 workspace members
- Path overrides for external repos eliminated for moved packages
- `contextcore-skills` subtree'd in for co-location but not a workspace member (data/scripts only)

---

## Phase 3: Full Monorepo

**Goal**: All Python packages in one workspace. Single source of truth for the Wayfinder implementation.

**Prerequisite**: Phase 2 complete. Remaining packages have matured beyond scaffolds.

### Packages to move in (when ready)

| Package | Trigger to move | Notes |
|---------|-----------------|-------|
| `contextcore-coyote` | When it has >10 commits and stable tests | Currently on personal GitHub org; transfer to FML first |
| `contextcore-fox` (external) | After fox naming decision is resolved | See Open Questions — may be merged into wayfinder-fox or kept as a separate app layer |
| `contextcore-owl` | When plugins are buildable | TypeScript plugins need npm workspace alongside uv; or keep Owl's Python helpers only |

### 3.1 Move packages in

Same `git subtree add` pattern as Phase 2.

### 3.2 Update workspace config

```toml
[tool.uv.workspace]
members = [
    "wayfinder-fox",
    "contextcore-rabbit",
    "contextcore-mole",
    "contextcore-coyote",
    "contextcore-fox",    # or merged into wayfinder-fox
]
```

Note: `contextcore-skills` remains excluded — it is a data/scripts directory, not a pip-installable package.

### 3.3 Handle contextcore-owl (mixed language)

Owl is primarily TypeScript (Grafana plugins) with Python scaffold helpers. Options:

- **Python-only workspace member**: Include only the Python provisioning helpers in the workspace. The TypeScript plugins are built separately with npm.
- **Separate toolchain**: Keep Owl out of the uv workspace entirely. Its Python code is minimal and can depend on contextcore via a path override.

Recommendation: include Python helpers only. The TypeScript build is orthogonal.

### 3.4 Handle contextcore-coyote's Python floor

Coyote currently targets `>=3.9`. Aligning to `>=3.11` is required to join the workspace. This is acceptable — Coyote's scaffolded code doesn't exercise anything 3.9-specific.

### 3.5 Resolve contextcore-fox vs wayfinder-fox

Three options (must pick one before moving external fox in):

**Option A — Archive external fox**: `wayfinder-fox` is the canonical fox. External `contextcore-fox` is archived. Flask server + CLI features are added to wayfinder-fox if needed.

**Option B — Library + Application split**: `wayfinder-fox` remains the enrichment library. `contextcore-fox` becomes `wayfinder-fox-server` (or similar) — a thin Flask wrapper that imports from wayfinder-fox. Both live in the workspace.

**Option C — Merge into one**: Combine both into a single `wayfinder-fox` with optional `[server]` extra that brings in Flask.

### 3.6 Final workspace structure

```
wayfinder/
├── src/contextcore/              # Core (Spider/Asabikeshiinh)
├── wayfinder-fox/                # Fox enrichment library
├── contextcore-rabbit/           # Rabbit alert framework
├── contextcore-skills/           # Squirrel skills library
├── contextcore-mole/             # Mole task recovery
├── contextcore-coyote/           # Coyote incident pipeline
├── contextcore-owl/              # Owl (Python helpers only)
├── wayfinder-mixin/              # Jsonnet (not in uv workspace)
├── pyproject.toml                # Workspace root
└── uv.lock                       # Unified lock file
```

### 3.7 CI structure at full monorepo

```yaml
jobs:
  lint:
    steps:
      - run: uv run ruff check src/ wayfinder-fox/src/ contextcore-*/src/

  test:
    strategy:
      matrix:
        package: [contextcore, wayfinder-fox, contextcore-rabbit, contextcore-skills, contextcore-mole, contextcore-coyote]
    steps:
      - run: uv sync --all-extras
      - run: uv run pytest ${{ matrix.package }}/tests/
```

### Phase 3 outcome

- Every Python package in one repo with one lock file
- `uv sync --all-extras` is the only install command anyone needs
- Cross-package changes (e.g., updating a span contract that affects core, fox, and rabbit) are single PRs
- CI matrix tests each package independently
- External repos archived with pointers to monorepo

---

## Open Questions

1. **contextcore-fox vs wayfinder-fox** — What's the intended relationship? This blocks the fox decision in Phase 3. Options:
   - Archive external `contextcore-fox`, keep `wayfinder-fox` as canonical
   - Keep both as library + application split
   - Merge features into single package with optional `[server]` extra

2. **contextcore-coyote GitHub org** — Coyote is under `neil-the-nowledgable`, not `Force-Multiplier-Labs`. Transfer needed before Phase 3?

3. **Private package index** — Even with the full monorepo, external consumers (Docker builds, other repos) can't `pip install contextcore`. Options:
   - GitHub Packages (simplest for GitHub-hosted repos)
   - Self-hosted (e.g., devpi)
   - Public PyPI (when packages are stable enough)
   - No index, use `pip install git+https://...` (works but fragile)

4. **Beaver future** — If `contextcore-beaver` becomes a Python package (LLM abstraction with cost tracking per CLAUDE.md), does it join the workspace? Currently it's a shell registry with no Python code.

5. **Owl TypeScript builds** — Should the monorepo eventually have both `uv.lock` (Python) and `package-lock.json` (TypeScript) at the root? Or keep Owl's TypeScript plugins in a separate build pipeline?

---

## Summary

| Phase | What moves in | Workspace members | Key outcome | Status |
|-------|--------------|-------------------|-------------|--------|
| **1** | Nothing (already here) | contextcore, wayfinder-fox (2) | uv works, lock file, fox in CI | COMPLETE (`3b7ba38`) |
| **2** | rabbit, mole (+ skills subtree, not a member) | + rabbit, mole (4 total) | Full active ecosystem, atomic changes | COMPLETE (`8b363eb`) |
| **3** | coyote, fox/owl (when ready) | + 2-3 packages (6-7 total) | Complete monorepo | Planned |

Each phase is independently valuable and can be shipped without committing to the next.
