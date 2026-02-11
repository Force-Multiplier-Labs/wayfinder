---
description: Take a harbor tour of local development capabilities - discover what exists and where to accomplish tasks
arguments: []
---

# Dev Tour: Harbor Tour of Capabilities

Welcome aboard! This tour introduces you to the local development infrastructure, tools, and capabilities already available. Like a harbor tour showing a city's landmarks from the water, this gives you the lay of the land so you can navigate with confidence.

## Your Tour Stops

### 🔭 Stop 1: Observability Harbor

**What's here:** A complete observability stack for understanding system behavior.

| Service | Port | Purpose |
|---------|------|---------|
| Grafana | 3000 | Dashboards and visualization |
| Prometheus | 9090 | Metrics collection |
| Loki | 3100 | Log aggregation |
| Tempo | 3200 | Distributed tracing |
| Pyroscope | 4040 | Continuous profiling |

**Key Value:** Never grep logs manually again. The `o11y` skill correlates metrics, logs, traces, and profiles with your source code for AI-powered root cause analysis.

**When to use:**
- Production issues → `o11y`
- Need a dashboard → `grafana-dashboards`
- Error spike analysis → `o11y`
- Performance debugging → `o11y`

---

### 📚 Stop 2: Knowledge Archives

**What's here:** Captured wisdom from past development sessions.

| Archive | Location | Contains |
|---------|----------|----------|
| Lessons Learned | `~/Documents/craft/Lessons_Learned/` | Domain-specific patterns, anti-patterns, solutions |
| Prompt Framework | `~/Documents/craft/Prompt_Engineering/` | Templates, workflows, prompt library |
| Project Index | `~/Documents/pers/persOS/index/` | Active project tracking |

**Key Value:** Don't repeat past mistakes. Read the lessons learned for your domain before starting work.

**Domains with lessons:**
- Interactive Text Games
- MCP Server Development
- SDK Development
- GUI Games
- Knowledge Management
- TTRPG Games

---

### 🧰 Stop 3: Skills Shipyard

**What's here:** Pre-built capabilities for common tasks.

| Category | Skills | Use For |
|----------|--------|---------|
| **Observability** | o11y, grafana-dashboards | Debugging, visualization |
| **Development** | code-review, mcp-builder, webapp-testing | Quality, integrations, testing |
| **Documents** | docx, pdf, xlsx, pptx | Office document manipulation |
| **Design** | frontend-design, canvas-design | UI and visual design |
| **Games** | skill-html_game_dev, ttrpg-games | Game development |
| **Data** | database-administrator | PostgreSQL/Supabase |
| **iOS** | ios, ios-testing | Swift/SwiftUI development |
| **Meta** | skill-creator, context_setter | Building new capabilities |

**Key Value:** Check the skill catalog before building anything new. The capability likely already exists.

---

### 🗄️ Stop 4: Capability Index

**What's here:** A 4-tier system organizing all capabilities by sharing level.

```
┌─────────────────────────────────────────────────────────┐
│  PERSONAL (local-index/)                                │
│  Private credentials, personal scripts                  │
│  🔒 Never committed to version control                  │
├─────────────────────────────────────────────────────────┤
│  NARROWLY SHARED (shared-index/)                        │
│  Team tools, internal workflows                         │
├─────────────────────────────────────────────────────────┤
│  WIDELY SHARED (Lessons_Learned/index/)                 │
│  Cross-project capabilities                             │
├─────────────────────────────────────────────────────────┤
│  PUBLIC (skills/dev-tour-guide/index/)                  │
│  Skill defaults, standard infrastructure                │
└─────────────────────────────────────────────────────────┘
```

**7 Capability Types:**
1. **Endpoints** - Services, APIs, infrastructure URLs
2. **Workflows** - Multi-step processes, pipelines
3. **Tools** - Scripts, utilities, directories
4. **Skills** - Claude skills
5. **Processes** - Standards, conventions, patterns
6. **Projects** - Project references
7. **Credentials** - Secret references (personal tier only)

**Key Value:** Find the authoritative source for any capability. Higher tiers override lower ones.

---

### 🔄 Stop 5: Automation Dock

**What's here:** Self-healing infrastructure and automated workflows.

**GitHub Actions Auto-Fix Pipeline:**
```
Error in logs → Loki → Grafana Alert → Webhook → GitHub Actions → Claude Agent → PR
```

**Setup:** `~/.claude/skills/dev-tour-guide/scripts/setup-auto-fix.sh`

**Key Value:** Recurring errors can trigger automatic investigation and fix proposals.

---

### 🚪 Stop 6: Session Gateway

**What's here:** Entry and exit rituals that preserve knowledge.

| Command | When | What It Does |
|---------|------|--------------|
| `dev-tour-guide` | Session start | Orient to capabilities, establish defaults |
| `/end-session` | Session end | Capture learnings, update indexes |

**Key Value:** Knowledge compounds. What you learn today is available tomorrow.

---

## Navigation Quick Reference

| I want to... | Go to... |
|--------------|----------|
| Debug a production issue | `o11y` skill |
| Create a dashboard | `grafana-dashboards` skill |
| Review code | `code-review` skill |
| Build an MCP server | `mcp-builder` skill |
| Work with documents | `docx`, `pdf`, `xlsx`, `pptx` skills |
| Build a web UI | `frontend-design` skill |
| Build a game | `skill-html_game_dev` or `ttrpg-games` |
| Learn from past work | `~/Documents/craft/Lessons_Learned/` |
| Find a capability | Check the 4-tier index |
| Create a new skill | `skill-creator` skill |
| Set up project context | `context_setter` skill |

---

## Default Behaviors (Your Standing Orders)

1. **Use existing skills** before building new capabilities
2. **Use o11y** for debugging - never grep logs manually
3. **Read lessons learned** for your domain before starting
4. **Use prompt templates** - don't write prompts from scratch
5. **Run /end-session** to capture learnings before closing

---

## Tour Complete!

You now know:
- ✅ Where the observability stack lives (localhost:3000)
- ✅ Where captured knowledge is stored (Lessons_Learned/)
- ✅ What skills are available (check the catalog)
- ✅ How capabilities are organized (4-tier index)
- ✅ How to preserve your learnings (/end-session)

**Next steps:**
- Explore the capability index: `./index/capabilities/`
- Read your domain's lessons learned
- Check the skills catalog before your next task

Welcome to the harbor. You're ready to navigate.
