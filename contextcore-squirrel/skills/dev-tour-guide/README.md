# dev-tour-guide

A Claude Code skill that provides onboarding and orientation to local development infrastructure, helping AI agents (and developers) discover existing tools, processes, and capabilities before building new ones.

## What It Does

**Core Value:** Avoid reinventing wheels. This skill ensures agents know what already exists.

- **Infrastructure Discovery:** Shows available observability stack (Grafana, Prometheus, Loki, etc.)
- **Skills Catalog:** References 40+ existing Claude skills by category
- **Lessons Learned Integration:** Points to domain-specific knowledge bases
- **Session Management:** Entry (`dev-tour-guide`) and exit (`/end-session`) workflows
- **4-Tier Capability Index:** Organizes capabilities from personal to public scope
- **Auto-Fix Pipeline:** GitHub Actions templates for automated error investigation

## Installation

### For Claude Code (CLI)

```bash
# Clone to your skills directory
git clone https://github.com/YOUR_USERNAME/dev-tour-guide.git ~/.claude/skills/dev-tour-guide
```

### For claude.ai (Web)

Upload `claude-ai/dev-tour-guide.md` to your Claude project as a knowledge document.

## Repository Structure

```
dev-tour-guide/
├── README.md                 # This file
├── SKILL.md                  # Main skill definition (invoke with /dev-tour-guide)
├── CLAUDE.md                 # Project development instructions
├── claude-ai/
│   └── dev-tour-guide.md     # Consolidated file for claude.ai upload
├── references/
│   └── skills-catalog.md     # Complete skills reference
├── scripts/
│   ├── auto-fix.yml          # GitHub Actions workflow template
│   ├── grafana-alert-rules.yaml
│   └── setup-auto-fix.sh     # One-command deployment script
├── prompts/
│   ├── dev-tour.md           # Harbor tour prompt
│   ├── index-review.md       # Index review slash command
│   └── review-for-index.md   # Index extraction template
├── index/
│   ├── index.yaml            # Public tier configuration
│   └── capabilities/         # Capability files by category
│       ├── endpoints.yaml
│       ├── workflows.yaml
│       ├── tools.yaml
│       ├── skills.yaml
│       ├── processes.yaml
│       └── projects.yaml
└── insights.md               # Usage patterns and lessons learned
```

## Key Features

### Harbor Manifest Protection

Prevents duplicate infrastructure by checking `~/.claude/harbor-manifest.yaml` before creating services:

```yaml
# Protected services (auto-blocked by infra-guard hook)
- Grafana (localhost:3000)
- Prometheus (localhost:9090)
- Loki (localhost:3100)
- Tempo (localhost:3200)
- Pyroscope (localhost:4040)
```

### 4-Tier Capability Index

| Tier | Location | Scope |
|------|----------|-------|
| Personal | `~/Documents/craft/local-index/` | Private credentials, personal scripts |
| Narrowly Shared | `~/Documents/craft/shared-index/` | Team tools |
| Widely Shared | `~/Documents/craft/Lessons_Learned/index/` | Cross-project |
| Public | `./index/` | Skill defaults |

### Auto-Fix Pipeline

Automated error detection and fix workflow:

```
Loki (logs) → Grafana Alert → Webhook → GitHub Actions → Claude Agent → PR
```

Deploy with:
```bash
./scripts/setup-auto-fix.sh --project-dir /path/to/project
```

## Usage

### In Claude Code

The skill is invoked automatically at session start or manually:

```
/dev-tour-guide
```

This triggers a "harbor tour" that orients you to:
- Available observability endpoints
- Skills catalog
- Lessons learned library
- Session management commands

### Key Commands

| Command | Purpose |
|---------|---------|
| `/dev-tour-guide` | Full orientation tour |
| `/end-session` | Capture learnings before closing |
| `o11y` skill | Debug production issues |
| `grafana-dashboards` skill | Create visualizations |

## Customization

### Adding Capabilities to the Index

1. Identify the appropriate tier (personal/shared/public)
2. Add entry to the relevant `capabilities/*.yaml` file
3. Follow the standard format:

```yaml
- id: my_capability
  name: My Capability
  description: What it does
  tags: [relevant, tags]
  tier_origin: public
  added: "2026-01-13"
  added_by: claude_code
```

### Extending the Skills Catalog

Edit `references/skills-catalog.md` to add new skill references.

## Dependencies

This skill references but doesn't require:
- Local observability stack (Grafana, Prometheus, Loki, Tempo, Pyroscope)
- Lessons Learned library at `~/Documents/craft/Lessons_Learned/`
- Prompt Engineering framework at `~/Documents/craft/Prompt_Engineering/`

The skill gracefully handles missing dependencies by pointing to what *should* exist.

## Related Projects

- [StartD8 SDK](https://github.com/YOUR_USERNAME/startd8-sdk) - Multi-LLM agent SDK
- [011yBubo](https://github.com/YOUR_USERNAME/011yBubo) - AI agent interaction from Grafana

## License

MIT

## Contributing

1. Fork the repository
2. Create a feature branch
3. Update relevant capability indexes
4. Submit a pull request

---

> Built for Claude Code - the CLI for Claude by Anthropic
