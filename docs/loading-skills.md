# Loading Skills into ContextCore

This guide explains how to load skills from this expansion pack into ContextCore's Tempo backend for querying via TraceQL.

## Prerequisites

1. **ContextCore installed**
   ```bash
   cd /path/to/ContextCore
   pip install -e ".[dev]"
   ```

2. **Observability stack running**
   ```bash
   # Using ContextCore's docker-compose
   cd /path/to/ContextCore
   make up
   make wait-ready
   ```

3. **Verify Tempo is accessible**
   ```bash
   curl http://localhost:3200/ready
   ```

## Loading Skills

### Method 1: CLI (Recommended)

```bash
# Activate ContextCore environment
cd /path/to/ContextCore
source .venv/bin/activate

# Emit a single skill
contextcore skill emit --path /path/to/contextcore-skills/skills/dev-tour-guide

# Emit all skills in the pack
for skill in /path/to/contextcore-skills/skills/*/; do
  contextcore skill emit --path "$skill"
done
```

### Method 2: Python API

```python
from contextcore.skill import SkillEmitter
from pathlib import Path

# Initialize emitter
emitter = SkillEmitter(
    agent_id="your-agent-id",
    session_id="your-session-id"
)

# Load and emit a skill
skill_path = Path("/path/to/contextcore-skills/skills/dev-tour-guide")
emitter.emit_skill(skill_path)

# Emit multiple skills
skills_dir = Path("/path/to/contextcore-skills/skills")
for skill_path in skills_dir.iterdir():
    if skill_path.is_dir():
        emitter.emit_skill(skill_path)
```

### Method 3: Dry Run (Preview)

Preview what would be emitted without sending to Tempo:

```bash
contextcore skill emit --path skills/dev-tour-guide --dry-run
```

Output shows:
- Skill manifest attributes
- Capability count
- Token budgets
- Evidence references

## Verifying Skills Loaded

### Grafana Explore

1. Open Grafana: `http://localhost:3000`
2. Go to Explore
3. Select Tempo datasource
4. Run TraceQL query:

```traceql
{ name =~ "skill:.*" }
```

### CLI Query

```bash
# List all skills
contextcore skill query --all

# Query by trigger
contextcore skill query --trigger "format"

# Query by category
contextcore skill query --category "transform"
```

## TraceQL Query Examples

### Find All Skills

```traceql
{ name =~ "skill:.*" }
```

### Find Specific Skill

```traceql
{ skill.id = "dev-tour-guide" }
```

### Find All Capabilities for a Skill

```traceql
{ skill.id = "dev-tour-guide" && name =~ "capability:.*" }
```

### Find Capabilities by Trigger Keyword

```traceql
{ capability.triggers =~ ".*debug.*" }
```

### Find Capabilities Under Token Budget

```traceql
{ capability.token_budget < 300 }
```

### Find Agent-Friendly Capabilities

```traceql
{ capability.audience = "agent" }
```

### Find Value Capabilities by Persona

```traceql
{ value.persona = "developer" }
```

### Find Direct Value Capabilities

```traceql
{ value.type = "direct" }
```

## Token-Efficient Discovery Pattern

Skills use progressive disclosure to minimize token usage:

### Level 0: Manifest Only (~100 tokens)

```bash
# Agent reads manifest for quick routing
cat skills/dev-tour-guide/MANIFEST.yaml
```

```traceql
# Or query from Tempo
{ skill.id = "dev-tour-guide" && name = "skill:dev-tour-guide" }
| select(skill.description, skill.capability_count)
```

### Level 1: Index (~200 tokens)

```bash
# Agent loads index for capability routing
cat skills/dev-tour-guide/agent/_index.yaml
```

### Level 2: Full Capability (~300-500 tokens)

```bash
# Agent loads full capability only when needed
cat skills/dev-tour-guide/agent/capabilities/observability.yaml
```

```traceql
# Or query specific capability from Tempo
{ skill.id = "dev-tour-guide" && capability.id = "investigate_error" }
```

## Troubleshooting

### Skills Not Appearing in Queries

1. **Check Tempo is receiving data**
   ```bash
   curl http://localhost:3200/api/traces
   ```

2. **Verify OTLP endpoint**
   ```bash
   export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
   ```

3. **Check for emission errors**
   ```bash
   contextcore skill emit --path skills/dev-tour-guide --verbose
   ```

### Query Returns Empty

1. **Check time range** - Grafana defaults to last 6 hours
2. **Verify skill.id spelling** - Case-sensitive
3. **Try broader query first**:
   ```traceql
   { name =~ ".*" } | limit 10
   ```

### Token Budget Not Showing

Ensure the skill's MANIFEST.yaml includes token budget:

```yaml
token_budget:
  manifest: 100
  index: 200
  total: 1500
```

## Re-emitting Skills

Skills can be re-emitted to update their content:

```bash
# Re-emit with force flag
contextcore skill emit --path skills/dev-tour-guide --force
```

This creates a new span with updated attributes while preserving history.

## Batch Loading

For CI/CD pipelines:

```bash
#!/bin/bash
# load-skills.sh

SKILLS_DIR="${1:-./skills}"
CONTEXTCORE_DIR="${2:-/path/to/ContextCore}"

cd "$CONTEXTCORE_DIR"
source .venv/bin/activate

for skill in "$SKILLS_DIR"/*/; do
  echo "Loading skill: $skill"
  contextcore skill emit --path "$skill" || echo "Failed: $skill"
done

echo "Done. Verify with: contextcore skill query --all"
```
