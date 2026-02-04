# Dev Tour Guide - Knowledge Document for Claude

This document provides orientation to local development infrastructure, helping you discover existing tools, processes, and capabilities before building new ones.

**Core Principle:** Use existing tools and processes before building new ones.

---

## Quick Reference

| Resource | Purpose |
|----------|---------|
| **Observability** | Grafana (port 3000), Prometheus (9090), Loki (3100) |
| **Debugging** | Use `o11y` skill - never grep logs manually |
| **Dashboards** | Use `grafana-dashboards` skill |
| **Session End** | Run `/end-session` to capture learnings |

---

## Local Observability Stack

### Endpoints

| Service | Port | Purpose |
|---------|------|---------|
| Grafana | 3000 | Dashboards and visualization |
| Prometheus | 9090 | Metrics collection |
| Mimir | 9009 | Long-term metrics storage |
| Loki | 3100 | Log aggregation |
| Tempo | 3200 | Distributed tracing |
| Pyroscope | 4040 | Continuous profiling |

### When to Use o11y Skill

- Production issues
- Error spike analysis
- Latency debugging
- System behavior investigation
- Correlating metrics, logs, traces, and profiles with source code

### Environment Variables

```bash
export PROMETHEUS_URL=http://localhost:9090
export LOKI_URL=http://localhost:3100
export TEMPO_URL=http://localhost:3200
export PYROSCOPE_URL=http://localhost:4040
```

---

## Local Development Conventions

### Package Management

**Prefer Homebrew over pip for system-level packages.**

| Task | Use | Avoid |
|------|-----|-------|
| Python installation | `brew install python@3.12` | System Python |
| CLI tools | `brew install <tool>` | `pip install <tool>` |
| Project dependencies | `brew install` + local virtualenv | Global pip install |

**Why Homebrew:**
- Consistent PATH management across tools
- Avoids Python version conflicts
- System-wide visibility for CLI commands
- Cleaner uninstall/upgrade process

**Installing Python packages locally:**

```bash
# Install Python via Homebrew
brew install python@3.12

# For project-specific dependencies, use a virtualenv
cd /path/to/project
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

**Common Homebrew packages:**

```bash
# Development tools
brew install node npm pnpm
brew install go rust
brew install docker docker-compose

# CLI utilities
brew install jq yq gh fzf ripgrep
brew install kubectl helm k9s
```

---

## Available Skills Catalog

### Observability & Infrastructure

| Skill | Purpose |
|-------|---------|
| **o11y** | AI-powered root cause analysis. Queries Prometheus, Loki, Tempo, Pyroscope. |
| **grafana-dashboards** | Create, import, manage Grafana dashboards programmatically. |

### Development & Code

| Skill | Purpose |
|-------|---------|
| **code-review** | Comprehensive code reviews (brittleness, reliability, performance) |
| **mcp-builder** | Build MCP servers for LLM tool integrations |
| **webapp-testing** | Test local web apps using Playwright |
| **skill-creator** | Create new Claude skills |

### Game Development

| Skill | Purpose |
|-------|---------|
| **skill-html_game_dev** | Build HTML5 canvas games |
| **skill-react-game-enhancer** | Enhance React/TypeScript games |
| **ttrpg-games** | TTRPG character management and stat tracking |
| **choice-adventure-builder** | Interactive text adventure games |

### Document Processing

| Skill | Purpose |
|-------|---------|
| **docx** | Word document creation, editing, tracked changes |
| **pdf** | PDF manipulation, extraction, forms |
| **xlsx** | Spreadsheet creation, formulas, analysis |
| **pptx** | Presentation creation and editing |

### iOS Development

| Skill | Purpose |
|-------|---------|
| **ios** | Production iOS apps (Swift 6, SwiftUI, MVVM) |
| **ios-testing** | Swift Testing, XCTest, TDD |
| **ios-project-manager** | Feature planning, multi-agent coordination |
| **iOS_OCR** | OCR & data extraction using Vision framework |

### Design & Visuals

| Skill | Purpose |
|-------|---------|
| **frontend-design** | Production-grade UI development |
| **canvas-design** | Visual art in .png and .pdf |
| **algorithmic-art** | Generative art with p5.js |
| **brand-guidelines** | Anthropic brand colors and typography |
| **theme-factory** | Style artifacts with themes |

### Data & Backend

| Skill | Purpose |
|-------|---------|
| **database-administrator** | Supabase/PostgreSQL administration |
| **sdk-developer** | Python SDK development guide |

### Meta Skills

| Skill | Purpose |
|-------|---------|
| **context_setter** | Rapidly establish project context |
| **skill-creator** | Create new Claude skills |

---

## Lessons Learned Library

Domain-specific knowledge captured from development sessions.

**Location:** `~/Documents/craft/Lessons_Learned/`

| Domain | File |
|--------|------|
| Infrastructure | `infrastructure/Infrastructure_LESSONS_LEARNED.md` |
| Interactive Text Games | `Interactive_text_game/Interactive_Text_Game_LESSONS_LEARNED.md` |
| MCP Server | `mcp/MCP_developer_LESSONS_LEARNED.md` |
| SDK Development | `sdk/SDK_developer_LESSONS_LEARNED.md` |
| GUI Games | `GUI_Game/GUI_Game_Developer_LESSONS_LEARNED.md` |
| Knowledge Management | `knowledge_management/knowledge_mgmt_LESSONS_LEARNED.md` |
| TTRPG Games | `ttrpg/TTRPG_Games_LESSONS_LEARNED.md` |

**Lesson Format:**
- **Context:** What were you trying to do?
- **Problem:** What obstacle did you encounter?
- **Solution:** How did you resolve it?
- **Reusable:** Heuristic/Pattern/Checklist/Anti-pattern

---

## 4-Tier Capability Index

Capabilities are organized by sharing scope. Higher tiers override lower tiers.

| Tier | Location | Use For |
|------|----------|---------|
| Personal | `~/Documents/craft/local-index/` | Private credentials, personal scripts |
| Narrowly Shared | `~/Documents/craft/shared-index/` | Team tools, internal workflows |
| Widely Shared | `~/Documents/craft/Lessons_Learned/index/` | Cross-project capabilities |
| Public | `~/.claude/skills/dev-tour-guide/index/` | Skill defaults |

### 7 Capability Categories

1. **Endpoints** - Services, APIs, databases, infrastructure URLs
2. **Workflows** - Multi-step processes, pipelines, methodologies
3. **Tools** - CLI tools, scripts, utilities
4. **Skills** - Claude skills and capabilities
5. **Processes** - Standards, conventions, patterns
6. **Projects** - Project references
7. **Credentials** - Secret references (personal tier only)

---

## GitHub Actions Auto-Fix Pipeline

Automated error detection and fix workflow.

### Architecture

```
Loki (logs) → Grafana Alert → Webhook → GitHub Actions → Claude Agent → PR
```

### Flow

1. **Error Detection**: Loki receives error logs
2. **Alert Trigger**: Grafana alerting rules fire
3. **Webhook**: Alert sends payload to GitHub Actions
4. **Agent Dispatch**: GitHub Action triggers Claude agent
5. **Auto-Fix**: Agent investigates using o11y, proposes fix
6. **PR Creation**: Fix submitted as PR for review

### When to Use

- Recurring errors with known fix patterns
- Infrastructure issues (restarts, scaling)
- Configuration drift
- Dependency updates

### When NOT to Use

- Security vulnerabilities (require human review)
- Business logic changes
- Database migrations
- Breaking changes

---

## Secure Secrets Management

API keys are managed through the Secrets Manager.

### Commands

```bash
# Store a secret (prompts for value)
~/.claude/scripts/secrets.sh set ANTHROPIC_API_KEY

# Retrieve a secret
~/.claude/scripts/secrets.sh get ANTHROPIC_API_KEY

# Use inline (most secure)
ANTHROPIC_API_KEY=$("$HOME/.claude/scripts/secrets.sh" get ANTHROPIC_API_KEY) python3 server.py

# List stored secrets
~/.claude/scripts/secrets.sh list
```

### Registered Secrets

| Key | Purpose |
|-----|---------|
| `ANTHROPIC_API_KEY` | Claude API access |
| `GRAFANA_TOKEN` | Grafana API access |
| `GITHUB_TOKEN` | GitHub API access |

---

## Default Behaviors

When starting any task:

1. **Check existing skills** - Use skill catalog before building new capabilities
2. **Read lessons learned** - Apply domain patterns, avoid known anti-patterns
3. **Use o11y for debugging** - Don't manually grep logs
4. **Use prompt templates** - Don't write prompts from scratch
5. **Run /end-session** - Always capture learnings at session end

---

## Navigation Quick Reference

| I want to... | Use... |
|--------------|--------|
| Debug a production issue | `o11y` skill |
| Create a dashboard | `grafana-dashboards` skill |
| Review code | `code-review` skill |
| Build an MCP server | `mcp-builder` skill |
| Work with documents | `docx`, `pdf`, `xlsx`, `pptx` skills |
| Build a web UI | `frontend-design` skill |
| Build a game | `skill-html_game_dev` or `ttrpg-games` |
| Learn from past work | Lessons Learned library |
| Find a capability | 4-tier capability index |
| Create a new skill | `skill-creator` skill |

---

## Key Locations

| Resource | Path |
|----------|------|
| Observability | http://localhost:3000 (Grafana) |
| Lessons Learned | `~/Documents/craft/Lessons_Learned/` |
| Prompt Framework | `~/Documents/craft/Prompt_Engineering/` |
| Skills Directory | `~/.claude/skills/` |
| Secrets Manager | `~/.claude/scripts/secrets.sh` |

---

*This document is auto-generated from the dev-tour-guide skill for use in Claude projects.*
