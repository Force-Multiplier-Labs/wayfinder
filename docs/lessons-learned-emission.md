# Lessons Learned Emission to ContextCore Squirrel

This document describes how to load engineering lessons learned into ContextCore's time-series database (Tempo) for agent-optimized querying.

## Overview

The lessons learned system stores structured engineering knowledge as OpenTelemetry spans in Tempo. This enables:

- **Token-efficient discovery**: Agents query summaries first (~50 tokens), load full content only when needed (~400-1000 tokens)
- **Semantic filtering**: Find lessons by domain, tags, patterns, anti-patterns, actors
- **Progressive disclosure**: Browse → Filter → Select → Load full content
- **Cross-domain insights**: Query across all engineering domains with TraceQL

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Lessons Learned Markdown Files                                         │
│  /Users/.../Lessons_Learned/{domain}/lessons/*.md                       │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Parser (lessons_learned_parser.py)                                     │
│  - Extracts structured fields (Context, Problem, Solution, Reusable)    │
│  - Calculates token estimates                                           │
│  - Generates summaries for progressive disclosure                       │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Emitter (lessons_learned_emitter.py)                                   │
│  - Creates OTel spans with schema-compliant attributes                  │
│  - Emits via OTLP to Tempo                                              │
│  - Maintains span hierarchy: domain → leg → lesson                      │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Tempo (localhost:3200)                                                 │
│  - Stores spans with full attribute indexing                            │
│  - Enables TraceQL queries for agent discovery                          │
│  - Grafana dashboards for human browsing                                │
└─────────────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

```bash
# Install OpenTelemetry dependencies
pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp-proto-grpc

# Ensure Tempo is running (typically via Kind cluster)
curl -s http://localhost:3200/ready
# Should return: ready
```

### Emit All Lessons

```bash
cd /Users/neilyashinsky/Documents/dev/contextcore-skills

# Dry run to see what would be emitted
python scripts/lessons_learned_emitter.py \
  /Users/neilyashinsky/Documents/craft/Lessons_Learned/ \
  --dry-run

# Emit to Tempo
python scripts/lessons_learned_emitter.py \
  /Users/neilyashinsky/Documents/craft/Lessons_Learned/ \
  --endpoint http://localhost:4317
```

### Emit Specific Domain

```bash
# Emit only observability lessons
python scripts/lessons_learned_emitter.py \
  /Users/neilyashinsky/Documents/craft/Lessons_Learned/observability \
  --endpoint http://localhost:4317
```

### Save Parsed Data to JSON

```bash
# Parse and save to JSON for inspection
python scripts/lessons_learned_parser.py \
  /Users/neilyashinsky/Documents/craft/Lessons_Learned/ \
  --output /tmp/lessons.json
```

## Span Schema

### Hierarchy

```
lesson_domain:observability           # Root span - domain level
  └── lesson_leg:observability-tracing    # Child span - topic group
        ├── lesson:observability-tracing-14  # Leaf span - individual lesson
        └── lesson:observability-tracing-15  # Leaf span - individual lesson
```

### Key Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `lesson.id` | string | Unique identifier (e.g., `observability-tracing-14`) |
| `lesson.title` | string | Descriptive title |
| `lesson.domain` | string | Parent domain |
| `lesson.leg` | string | Parent topic/leg |
| `lesson.tags` | string | Comma-separated tags |
| `lesson.context_summary` | string | 1-2 sentence context |
| `lesson.problem_summary` | string | 1-2 sentence problem |
| `lesson.solution_summary` | string | 1-2 sentence solution |
| `lesson.heuristic` | string | Rule of thumb (if present) |
| `lesson.pattern_name` | string | Pattern name (if present) |
| `lesson.anti_pattern` | string | What NOT to do (if present) |
| `lesson.has_checklist` | bool | Whether lesson includes checklist |
| `lesson.token_budget` | int | Estimated tokens for full content |
| `lesson.source_file` | string | Path to original markdown |
| `lesson.source_line` | int | Starting line number |

## TraceQL Query Patterns

### Find Lessons by Domain

```traceql
{ name =~ "lesson:.*" && span.lesson.domain = "observability" }
```

### Find Lessons by Tag

```traceql
{ name =~ "lesson:.*" && span.lesson.tags =~ ".*traceql.*" }
```

### Find Anti-Patterns

```traceql
{ name =~ "lesson:.*" && span.lesson.anti_pattern != "" }
```

### Find Lessons with Checklists

```traceql
{ name =~ "lesson:.*" && span.lesson.has_checklist = true }
```

### Browse Summaries (Token-Efficient)

```traceql
{ name =~ "lesson:.*" && span.lesson.domain = "observability" }
| select(span.lesson.id, span.lesson.title, span.lesson.problem_summary, span.lesson.heuristic)
```

### Find High-Value Lessons (Multiple Reusable Elements)

```traceql
{ name =~ "lesson:.*" && span.lesson.heuristic != "" && span.lesson.pattern_name != "" }
```

### Find Quick Reference Lessons (Small Token Budget)

```traceql
{ name =~ "lesson:.*" && span.lesson.token_budget < 300 }
```

## Agent Usage Patterns

### Discovery Workflow

1. **Search by tags** matching problem domain:
   ```traceql
   { name =~ "lesson:.*" && span.lesson.tags =~ ".*grafana.*dashboard.*" }
   ```

2. **Filter by problem keywords** in summary:
   ```traceql
   ... && span.lesson.problem_summary =~ ".*empty.*panel.*"
   ```

3. **Load summaries** for top matches (~50 tokens each):
   ```traceql
   ... | select(span.lesson.id, span.lesson.title, span.lesson.solution_summary)
   ```

4. **Load full content** only for selected lesson:
   - Read `source_file` at `source_line`

### Prevention Workflow

Before implementing something new, check for anti-patterns:

```traceql
{ name =~ "lesson:.*"
  && span.lesson.domain = "observability"
  && span.lesson.anti_pattern != ""
  && span.lesson.tags =~ ".*tempo.*" }
| select(span.lesson.title, span.lesson.anti_pattern)
```

### Checklist Workflow

Find actionable checklists for a task:

```traceql
{ name =~ "lesson:.*"
  && span.lesson.has_checklist = true
  && span.lesson.tags =~ ".*grafana.*" }
| select(span.lesson.id, span.lesson.title, span.lesson.pattern_name)
```

Then load full content from `source_file` for detailed checklist.

## Token Economics

| Access Level | Tokens | Use Case |
|--------------|--------|----------|
| Summary attributes | ~50 | Routing decisions |
| Full lesson | 300-1000 | Deep investigation |
| Domain scan (10 lessons) | ~500 | Problem discovery |
| Full domain (50 lessons) | ~25,000 | Comprehensive review |

**Compression ratio**: Summary (~50 tokens) vs Full (~500 tokens) = **90% token savings** for discovery.

## Verification

### Check Data in Tempo

```bash
# Basic search
curl -s "http://localhost:3200/api/search?q={name=~\"lesson:.*\"}&limit=10" | jq

# Count lessons
curl -s "http://localhost:3200/api/search?q={name=~\"lesson:.*\"}&limit=500" | jq '.traces | length'

# Search by domain
curl -s "http://localhost:3200/api/search?q={name=~\"lesson:.*\"%26%26span.lesson.domain=\"observability\"}&limit=50" | jq
```

### View in Grafana

1. Open Grafana Explore: http://localhost:3000/explore
2. Select Tempo datasource
3. Query: `{ name =~ "lesson:.*" } | select(span.lesson.id, span.lesson.title, span.lesson.tags)`
4. Set Table Format: Spans

## Files

| File | Purpose |
|------|---------|
| `schemas/lesson-learned-schema.yaml` | Schema definition |
| `scripts/lessons_learned_parser.py` | Markdown parser |
| `scripts/lessons_learned_emitter.py` | Tempo emitter |
| `docs/lessons-learned-emission.md` | This documentation |

## Current Statistics

As of last emission:
- **Domains**: 7 (observability, mcp, sdk, interactive-text-game, gui-game, knowledge-management, ttrpg)
- **Legs/Topics**: 45
- **Lessons**: 358
- **Total estimated tokens**: ~200,000

## Maintenance

### Re-emit After Updates

When lessons are added or updated:

```bash
# Re-emit specific domain (won't duplicate - Tempo handles idempotency)
python scripts/lessons_learned_emitter.py \
  /Users/neilyashinsky/Documents/craft/Lessons_Learned/observability \
  --endpoint http://localhost:4317
```

### Add New Domain

1. Create directory structure:
   ```
   /Lessons_Learned/{new_domain}/
     ├── lessons/
     │   ├── 01-topic-one.md
     │   └── 02-topic-two.md
     └── {new_domain}_LESSONS_LEARNED.md
   ```

2. Follow lesson format (see existing files for examples)

3. Emit:
   ```bash
   python scripts/lessons_learned_emitter.py \
     /Users/neilyashinsky/Documents/craft/Lessons_Learned/{new_domain}
   ```
