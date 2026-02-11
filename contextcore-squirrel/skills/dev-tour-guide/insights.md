# dev-tour-guide Skill Insights

Lessons learned from using the dev-tour-guide skill for session orientation and infrastructure awareness.

---

## Overview

**Purpose:** Onboarding guide for local development infrastructure, processes, and capabilities.

**When to use:** Start of any development session to understand existing assets.

**Key value:** Avoid reinventing wheels by knowing what tools already exist.

---

## Insights

### Session Initialization Pattern

**Date:** 2026-01-11

**Context:** Starting a new development session

**Discovery:** The dev-tour-guide skill is most effective when invoked at session start before diving into tasks. It establishes default behaviors that prevent common mistakes like manually grepping logs instead of using o11y.

**Pattern:**
- Invoke dev-tour-guide before any task work
- Review the "Default Behaviors" section
- Check skill catalog for relevant capabilities
- Note the Lessons Learned location for the current domain

**Anti-pattern:**
- Skipping orientation and jumping straight into implementation
- Building new tools without checking existing skills

---

## Integration with Other Skills

| Skill | Integration Pattern |
|-------|---------------------|
| o11y | dev-tour-guide points to o11y for all debugging; never grep logs manually |
| grafana-dashboards | Use for visualization after o11y investigation |
| /end-session | Always run at session end to capture learnings |

---

## Key Reminders from dev-tour-guide

1. **Observability stack:** localhost:3000 (Grafana), 9090 (Prometheus), 3100 (Loki)
2. **Lessons Learned:** `$HOME/Documents/craft/Lessons_Learned/`
3. **Prompt Framework:** `$HOME/Documents/craft/Prompt_Engineering/`
4. **Skills Directory:** `~/.claude/skills/`

---

## Anti-Patterns

### Ephemeral Elaborate Workflows

**Date:** 2026-01-27

**Context:** Executing a 6-task Prime Contractor workflow (Squirrel implementation) that successfully ran through Spec → Draft → Review → Integrate phases but produced no persisted output files.

**Problem:** The workflow completed all phases successfully, generated code via the Prime Contractor pattern (Claude Sonnet specifying, Gemini Flash drafting, Claude reviewing), but the generated artifacts were only stored in memory/result objects. No files were written to disk.

**Anti-pattern:**
> Elaborate multi-step workflows that consume significant compute/cost but do not persist their outputs by default.

**Why this is problematic:**
1. **Wasted compute** - Expensive LLM calls produce artifacts that evaporate
2. **No audit trail** - Cannot verify what was generated vs what was reviewed
3. **Manual extraction required** - Human must dig through JSON results to extract code
4. **Breaks the "integration" promise** - Integration phase implies code is ready to use, not ready to copy-paste

**Heuristic:**
> Any workflow with 3+ steps or $0.10+ estimated cost MUST persist outputs by default. Ephemeral mode should require explicit `--no-persist` or `--dry-run` flag.

**Pattern (Correct Behavior):**
```yaml
# Task should specify output target
config:
  task_description: "Create the schema file..."
  context:
    output_file: schemas/squirrel-knowledge-schema.yaml  # WHERE to write

# Workflow runner should:
# 1. Extract final_implementation from result
# 2. Write to context.output_file
# 3. Log: "Wrote 245 lines to schemas/squirrel-knowledge-schema.yaml"
```

**Checklist for Workflow Design:**
- [ ] Does the workflow persist outputs by default?
- [ ] Is there a `--dry-run` flag for ephemeral execution?
- [ ] Are output paths specified in task context?
- [ ] Does the runner log what files were written?
- [ ] Can outputs be verified after completion?

**Tags:** [workflow, anti-pattern, persistence, prime-contractor, beaver, startd8]

---

## Future Discoveries

<!-- Add new insights below as you learn more about effective dev-tour-guide usage -->
