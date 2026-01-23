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

## Future Discoveries

<!-- Add new insights below as you learn more about effective dev-tour-guide usage -->
