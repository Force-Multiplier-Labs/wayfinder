# CLAUDE.md

This file provides guidance to Claude Code for the contextcore-mole project.

## Project Context

**contextcore-mole** is a CLI tool for recovering deleted, archived, or lost task data from ContextCore Tempo trace exports. Like a mole digging through soil to unearth buried things, this tool digs through trace JSON files to find and restore tasks that were removed—whether knowingly or unknowingly.

### Anishinaabe Name

**Namegos** (nah-MEH-gos) — "Mole" in Ojibwe. The mole lives underground, navigating through darkness to find what's hidden beneath the surface.

*Note: Verify this name against the [Ojibwe People's Dictionary](https://ojibwe.lib.umn.edu) before finalizing.*

## Purpose

Recover task data from ContextCore trace JSON exports (Tempo), including:
- Tasks marked as `cancelled` or `done` that need to be restored
- Tasks that disappeared from active tracking
- Historical task states from trace exports
- Task events and status transitions

## Source Data: Tasks as Spans

ContextCore models tasks as OpenTelemetry spans stored in Tempo. When exported, these appear as JSON with the following structure:

### Task Span Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `task.id` | string | Unique task identifier (e.g., `"PROJ-123"`) |
| `task.type` | string | `epic`, `story`, `task`, `subtask`, `bug`, `spike`, `incident` |
| `task.title` | string | Task title/summary |
| `task.status` | string | `backlog`, `todo`, `in_progress`, `in_review`, `blocked`, `done`, `cancelled` |
| `task.priority` | string | `critical`, `high`, `medium`, `low` |
| `task.assignee` | string | Person assigned |
| `task.story_points` | int | Story point estimate |
| `task.labels` | string[] | Task labels/tags |
| `task.parent_id` | string | Parent task ID (for hierarchy) |
| `project.id` | string | Project identifier |
| `sprint.id` | string | Sprint identifier |

### Task Span Events

| Event Name | Description | Attributes |
|------------|-------------|------------|
| `task.created` | Task was created | `task.title`, `task.type` |
| `task.status_changed` | Status transition | `from`, `to` |
| `task.blocked` | Task became blocked | `reason`, `blocker_id` |
| `task.completed` | Task finished | - |
| `task.cancelled` | Task cancelled | `reason` |

### Example Tempo JSON Export (simplified)

```json
{
  "batches": [
    {
      "resource": {
        "attributes": [
          {"key": "service.name", "value": {"stringValue": "contextcore"}}
        ]
      },
      "scopeSpans": [
        {
          "spans": [
            {
              "traceId": "abc123...",
              "spanId": "def456...",
              "name": "task.PROJ-123",
              "startTimeUnixNano": "1706284800000000000",
              "endTimeUnixNano": "1706371200000000000",
              "attributes": [
                {"key": "task.id", "value": {"stringValue": "PROJ-123"}},
                {"key": "task.title", "value": {"stringValue": "Implement auth"}},
                {"key": "task.status", "value": {"stringValue": "cancelled"}},
                {"key": "task.type", "value": {"stringValue": "story"}},
                {"key": "project.id", "value": {"stringValue": "my-project"}}
              ],
              "events": [
                {
                  "name": "task.status_changed",
                  "timeUnixNano": "1706300000000000000",
                  "attributes": [
                    {"key": "from", "value": {"stringValue": "in_progress"}},
                    {"key": "to", "value": {"stringValue": "cancelled"}}
                  ]
                }
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

## Tech Stack

- **Language**: Python 3.9+
- **CLI Framework**: Click
- **Data Models**: Pydantic v2
- **Output**: Rich (terminal formatting)
- **Testing**: pytest, pytest-cov
- **Linting**: ruff, mypy

## Project Structure

```
contextcore-mole/
├── src/contextcore_mole/
│   ├── __init__.py         # Package init, version
│   ├── cli.py              # Click CLI with scan/list/show/export
│   ├── models.py           # Pydantic models (Project, Task, TaskFile)
│   └── parser.py           # Parse task JSON, scan directories
├── tests/
│   ├── __init__.py
│   └── test_parser.py      # Parser unit tests
├── docs/
│   └── session-logs/       # Development session logs
├── .venv/                  # Virtual environment
├── pyproject.toml          # Package config (setuptools)
├── CLAUDE.md
└── README.md
```

## Development Setup

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run CLI
mole --help

# Run tests
pytest

# Type checking
mypy src/contextcore_mole

# Linting
ruff check src/
```

## Commands (CLI stubs implemented)

```bash
# Scan trace exports for recoverable tasks
mole scan <trace-export.json>           # Scan a single file
mole scan <directory>                   # Scan all JSON files in directory

# List tasks by status
mole list <file.json>                   # Show all tasks
mole list --status cancelled            # Filter by status
mole list --status done                 # Show completed tasks
mole list --project my-project          # Filter by project

# Show task details
mole show <file.json> <task-id>         # Show full task with events

# Export tasks for re-import
mole export <file.json> <task-id>       # Export task as ContextCore JSON
mole export --status cancelled --out recovered.json  # Export all cancelled
```

## System Requirements

**Python Command**: Use `python3` and `pip3`, not `python` and `pip`.

## Related Projects

| Package | Animal | Anishinaabe | Purpose |
|---------|--------|-------------|---------|
| **contextcore** | Spider | Asabikeshiinh | Core framework—tasks as spans |
| **contextcore-beaver** | Beaver | Amik | LLM provider abstraction |
| **contextcore-mole** | Mole | Namegos | Task recovery from traces |

See `../ContextCore/docs/NAMING_CONVENTION.md` for full naming guidelines.

## Data Flow

```
Tempo (traces) --> Export JSON --> mole scan --> Identify recoverable tasks
                                           |
                                           v
                                  mole export --> ContextCore JSON
                                           |
                                           v
                              Re-import to ContextCore (future)
```

## Must Do

- Parse OTel trace JSON format correctly (Tempo export format)
- Preserve all task attributes and events
- Support filtering by status, project, date range
- Output in ContextCore-compatible JSON for re-import
- Handle large trace files efficiently

## Must Avoid

- Corrupting trace data during parsing
- Silent failures when encountering unknown attributes
- Assuming specific attribute ordering in JSON

## Current Status

**Completed:**
- Project scaffolding (pyproject.toml, package structure)
- `models.py` — Pydantic models for task JSON (Project, Task, TaskFile)
- `parser.py` — Parse task JSON files, scan directories
- `cli.py` — Full CLI with Rich tables
  - `mole scan` — Find and summarize task files
  - `mole list` — List tasks with filtering (--status, --tag, --type)
  - `mole show` — Display full task details
  - `mole export` — Export filtered tasks (JSON/JSONL)
- Test suite (7 tests passing)

**Next Steps:**
1. Add Tempo trace JSON parsing (OTel span format from session log)
2. Add `--since` / `--until` time range filtering
3. Add TraceQL query builder for live Tempo queries
4. Add recovery workflow (restore cancelled tasks)
