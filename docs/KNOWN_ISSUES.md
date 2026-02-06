# Known Issues and Fixes

This document catalogs known issues in the ContextCore codebase and their solutions.

## Table of Contents

- [Workflow Trigger Shows "0/N Steps"](#workflow-trigger-shows-0n-steps)
- [Prime Contractor Merge Corrupts Python Files](#prime-contractor-merge-corrupts-python-files) *(resolved)*
- [Module Import Errors](#module-import-errors) *(resolved)*
- [Example Code Executed at Import Time](#example-code-executed-at-import-time) *(resolved)*
- [Missing Module Files](#missing-module-files) *(resolved)*
- [Windows-Specific Notes](#windows-specific-notes)

---

## Workflow Trigger Shows "0/N Steps"

**Symptom:** The Grafana workflow trigger panel shows "0/8 steps" and completes in ~2 seconds without processing any features.

**Root Cause:** One of:
1. The first feature in the queue has a syntax/import error, causing immediate failure
2. All features are already marked as complete in the queue
3. The `generated/` directory has no `*_code.*` files

**Diagnosis:**
```bash
# Check feature queue status
python3 -c "
from scripts.prime_contractor.feature_queue import FeatureQueue
queue = FeatureQueue()
queue.print_status()
"

# Check for syntax errors in target files
python3 -m py_compile src/contextcore/agent/parts.py

# Check what features would run
curl -s -X POST http://localhost:8082/trigger \
  -H 'Content-Type: application/json' \
  -d '{"action": "beaver_workflow_dry_run", "payload": {"project_id": "contextcore"}}' | jq
```

**Fix:**
1. If syntax errors: Restore corrupted file from git or fix manually
2. If queue issues: Reset feature queue state
3. If no generated files: Run Lead Contractor first

```bash
# Restore corrupted file
git checkout src/contextcore/agent/parts.py

# Reset failed features to retry
python3 -c "
from scripts.prime_contractor.feature_queue import FeatureQueue, FeatureStatus
queue = FeatureQueue()
for fid, f in queue.features.items():
    if f.status == FeatureStatus.FAILED:
        f.status = FeatureStatus.GENERATED
        f.error_message = None
queue.save_state()
"
```

---

## Prime Contractor Merge Corrupts Python Files

> **RESOLVED (2026-02-02):** The AST merge pipeline now handles all four root causes. `__main__` guards and bare module-level calls are filtered during parsing, `__all__` preserves the target file's explicit exports, the legacy text-based merge fallback is disabled (returns empty string with error instead of corrupting files), and the three duplicate merge functions in `merge_conflicts.py` are consolidated into a single shared helper. 47 tests pass including 5 new regression tests. Kept for historical reference.

**Symptom:** After running `python3 scripts/prime_contractor/cli.py run --import-backlog`, target Python files become syntactically invalid with:
- Imports scattered throughout the file
- Class definitions mixed with example code
- Missing decorators (@dataclass, @classmethod)
- Code outside class bodies

**Root Cause:** Four gaps in the AST merge pipeline:
1. `parse_python_file()` sent `if __name__ == "__main__":` blocks and bare module-level calls into `other_statements`, which `merge_parsed_files()` blindly appended to output
2. `merge_parsed_files()` always regenerated `__all__` from all merged names, overwriting the target file's intentional subset (exporting private helpers)
3. `integrate_backlog.py` and `merge_conflicts.py` fell back to the legacy text-based merge on any exception, which produced the corrupted output
4. Three duplicate merge functions in `merge_conflicts.py` each independently repeated the same try/except/parse/merge pattern

**Fix applied (commit 8ea61ce):**
- `ast_merge.py`: Added `_is_main_guard()` and `_is_type_checking()` helpers; parser now filters `__main__` guards and bare `ast.Expr(ast.Call)` nodes; `merge_parsed_files()` excludes `other_statements` from output with a warning; `__all__` logic preserves first file's explicit exports and excludes `_private` names from auto-generated exports
- `integrate_backlog.py`: Feature flag fallback and exception handlers return `""` with error messages instead of calling `_merge_files_legacy()`; legacy function marked deprecated
- `merge_conflicts.py`: `merge_parts_files()`, `merge_otel_genai_files()`, `merge_handoff_files()` consolidated into shared `_merge_python_sources()` with no legacy fallback

---

## Module Import Errors

> **RESOLVED (2026-02-02):** All four import issues below have been fixed. `discovery/__init__.py` imports from `.agentcard` correctly, `generators/__init__.py` no longer exports `write_tests`, and all modules pass `python3 -c "import ..."` cleanly. Kept for historical reference.

### `from __future__ imports must occur at the beginning`

**Symptom:**
```
SyntaxError: from __future__ imports must occur at the beginning of the file
```

**Cause:** The merge process placed `from __future__ import annotations` after other imports.

**Fix:**
```python
# Move to immediately after the docstring
"""Module docstring."""

from __future__ import annotations  # Must be first!

from dataclasses import dataclass
# ... other imports
```

### `cannot import name 'X' from 'module'`

**Symptom:**
```
ImportError: cannot import name 'write_tests' from 'contextcore.generators.slo_tests'
```

**Cause:** The `__init__.py` exports a name that doesn't exist in the module.

**Fix:** Remove the non-existent import from `__init__.py`:
```python
# In src/contextcore/generators/__init__.py
# Remove 'write_tests' from imports and __all__
```

### `No module named 'contextcore.X.models'`

**Symptom:**
```
ModuleNotFoundError: No module named 'contextcore.discovery.models'
```

**Cause:** Import path references a non-existent file.

**Fix:** Update to correct path:
```python
# Wrong
from .models import AgentCard

# Correct
from .agentcard import AgentCard
```

### `NameError: name 'X' is not defined`

**Symptom:**
```
NameError: name 'MessageRole' is not defined
```

**Cause:** Class/enum referenced before it's defined (wrong order in file).

**Fix:** Reorder definitions so dependencies come first:
```python
# Define MessageRole BEFORE Message class
class MessageRole(str, Enum):
    USER = "user"
    AGENT = "agent"

@dataclass
class Message:
    role: MessageRole = MessageRole.USER  # Now works
```

---

## Example Code Executed at Import Time

> **RESOLVED (2026-02-02):** `endpoint.py` and `docs_unifiedupdate.py` no longer contain module-level executable code. Kept for historical reference.

**Symptom:** Module import fails with errors like:
```
TypeError: AgentCard.__init__() missing 3 required positional arguments
```

**Cause:** Generated files contain example/demo code at module level that executes during import:
```python
# This runs at import time!
agent = AgentCard(name="MyAgent")  # Missing required args
endpoint = DiscoveryEndpoint(agent)
```

**Affected Files:**
- `src/contextcore/discovery/endpoint.py`
- `src/contextcore/compat/docs_unifiedupdate.py`

**Fix:** Remove or guard example code:

Option 1: Delete example code section
```bash
# Find and remove lines after the last class/function definition
```

Option 2: Guard with `if __name__ == "__main__":`
```python
if __name__ == "__main__":
    # Example code here - only runs when file is executed directly
    agent = AgentCard(...)
```

Option 3: Rename non-module files
```bash
mv src/contextcore/compat/docs_unifiedupdate.py \
   src/contextcore/compat/docs_unifiedupdate.py.example
```

---

## Missing Module Files

> **RESOLVED (2026-02-02):** `agent/part.py` exists and imports succeed. `discovery/__init__.py` imports from `.agentcard` correctly. Kept for historical reference.

### `part.py` Missing (Part and PartType classes)

**Symptom:**
```
ModuleNotFoundError: No module named 'contextcore.agent.part'
```

**Cause:** The `parts.py` file expects to import from `part.py` which doesn't exist.

**Fix:** Create `src/contextcore/agent/part.py` with Part and PartType:
```bash
# Copy from generated source
cp generated/phase3/a2a/parts/parts_partmodel_code.py src/contextcore/agent/part.py

# Remove example code at the end (after __all__ = [...])
```

The file should contain:
- `PartType` enum (TEXT, FILE, TRACE, etc.)
- `Part` dataclass with factory methods

### `discovery/models.py` Missing

**Symptom:**
```
ModuleNotFoundError: No module named 'contextcore.discovery.models'
```

**Cause:** Import path is wrong - classes are in `agentcard.py`, not `models.py`.

**Fix:** Update `discovery/__init__.py`:
```python
# Change this:
from .models import AgentCard, AgentCapabilities, ...

# To this:
from .agentcard import AgentCard, AgentCapabilities, ...
```

---

## Quick Reference: Health Check Commands

```bash
# Check all critical modules import correctly
python3 -c "
import sys
sys.path.insert(0, 'src')
for mod in ['contextcore.agent.part', 'contextcore.agent.parts',
            'contextcore.agent.handoff', 'contextcore.generators',
            'contextcore.discovery']:
    try:
        __import__(mod)
        print(f'✓ {mod}')
    except Exception as e:
        print(f'✗ {mod}: {e}')
"

# Check syntax of a specific file
python3 -m py_compile src/contextcore/agent/parts.py

# Check workflow trigger health
curl -s http://localhost:8082/health

# View feature queue status
python3 -c "
from scripts.prime_contractor.feature_queue import FeatureQueue
FeatureQueue().print_status()
"
```

---

## Windows-Specific Notes

### `make` Targets Not Available in Native PowerShell

**Symptom:** Running `make full-setup`, `make up`, etc. fails in PowerShell.

**Cause:** The Makefile uses bash constructs. Windows does not ship with `make`.

**Recommended:** Use the included `setup.ps1` wrapper script:
```powershell
.\setup.ps1 full-setup    # Complete setup (up + wait-ready + seed-metrics)
.\setup.ps1 up            # Start the stack
.\setup.ps1 health        # Check component health
.\setup.ps1 smoke-test    # Validate entire stack
.\setup.ps1 down          # Stop the stack
```

Or run Docker Compose directly:
```powershell
docker compose up -d
docker compose ps
docker compose down
```

Or install Make via `winget install GnuWin32.Make` and use Git Bash.

### PowerShell `curl` Alias

**Symptom:** `curl http://localhost:3000/api/health` returns an error or unexpected object output in PowerShell.

**Cause:** PowerShell aliases `curl` to `Invoke-WebRequest`, which has different behavior.

**Fix:** Use `curl.exe` (the real curl) instead:
```powershell
curl.exe http://localhost:3000/api/health
```

### Execution Policy Blocks `.ps1` Scripts

**Symptom:** `.venv\Scripts\Activate.ps1` or generated install scripts fail with a security error.

**Fix:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### State File Locking Differences

**Note:** On Windows, `msvcrt` only supports exclusive locks (no shared/read lock mode). This is handled transparently — the `exclusive` parameter in `state.py` is accepted for API compatibility but always acquires an exclusive lock. This means concurrent reads are serialized on Windows, which is fine for typical usage but may affect performance under heavy parallel access.

### `nc` (netcat) Not Available

**Symptom:** Verification command `nc -z localhost 4317` fails.

**Workaround:** Use PowerShell to test port connectivity:
```powershell
Test-NetConnection -ComputerName localhost -Port 4317
```

---

## Prevention

1. **Before running Prime Contractor:** Check that target files have no uncommitted changes
2. **After merge failures:** Always restore from git before retrying
3. **AST merge protections:** The AST merge pipeline now filters example code, preserves `__all__`, and refuses to fall back to legacy text-based merge
4. **Test imports:** Run module health check after any integration

---

*Last updated: 2026-02-06*
