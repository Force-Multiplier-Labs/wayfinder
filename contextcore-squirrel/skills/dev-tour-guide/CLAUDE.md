# CLAUDE.md

This file provides guidance to Claude Code for this repository.

## Project Overview

This is the **development home** for the dev-tour-guide skill - where insights, capability indexes, and prompts live. The skill itself is installed at `~/.claude/skills/dev-tour-guide/`. This folder manages the skill's knowledge layer and 4-tier capability index system.

## Purpose

- Capture insights and lessons learned from using the dev-tour-guide skill
- Manage the **public tier** capability index (skill defaults)
- Store prompts for extracting capabilities from markdown files
- Coordinate with other tiers (personal, narrowly shared, widely shared)

## Project Structure

```
dev-tour-guide/
├── CLAUDE.md              # This file
├── insights.md            # Lessons learned from skill usage
├── index/                 # PUBLIC tier capability index
│   ├── index.yaml         # Main index, tier config
│   └── capabilities/      # Capability files by category
│       ├── endpoints.yaml
│       ├── workflows.yaml
│       ├── tools.yaml
│       ├── skills.yaml
│       ├── processes.yaml
│       └── projects.yaml
└── prompts/               # Prompts for index management
    ├── index-review.md    # Slash command for reviewing files
    └── review-for-index.md # Detailed extraction template
```

## 4-Tier Capability Index System

| Tier | Location | Use For |
|------|----------|---------|
| Personal | `~/Documents/craft/local-index/` | Private credentials, personal scripts |
| Narrowly Shared | `~/Documents/craft/shared-index/` | Team tools, internal workflows |
| Widely Shared | `~/Documents/craft/Lessons_Learned/index/` | Cross-project capabilities |
| **Public** | `./index/` (this folder) | Skill defaults |

Higher tiers override lower tiers. Personal tier includes `credentials.yaml` (references only, never actual secrets).

## Capability Categories

7 categories indexed across all tiers:

1. **Endpoints** - Services, APIs, databases, infrastructure URLs
2. **Workflows** - Multi-step processes, pipelines, methodologies
3. **Tools** - CLI tools, scripts, utilities, directories
4. **Skills** - Claude skills and skill-like capabilities
5. **Processes** - Standards, conventions, patterns, checklists
6. **Projects** - Project references and associations
7. **Credentials** - Secret references (personal tier only)

## Conventions

### YAML Entry Format
```yaml
- id: snake_case_id
  name: Human Readable Name
  description: What it does
  # ... type-specific fields
  tags: [relevant, tags]
  tier_origin: public|widely_shared|narrowly_shared|personal
  added: "YYYY-MM-DD"
  added_by: claude_code
```

### Reviewing Files for Index Entries
Use the prompts in `prompts/` to extract capabilities from markdown files:
- `prompts/index-review.md` - Slash command with `$ARGUMENTS.file`
- `prompts/review-for-index.md` - Detailed template with `{{file_path}}`

## Key Files

| File | Purpose |
|------|---------|
| `insights.md` | Lessons learned from using the skill |
| `index/index.yaml` | Public tier config, lists capability files |
| `prompts/index-review.md` | Slash command for file review |

## Related Locations

- **Installed skill**: `~/.claude/skills/dev-tour-guide/SKILL.md`
- **Skill scripts**: `~/.claude/skills/dev-tour-guide/scripts/`
- **Skill references**: `~/.claude/skills/dev-tour-guide/references/`

## Must Do

- Use existing capability categories; don't invent new ones
- Include `tier_origin` on all entries
- Put credential references in personal tier only
- Update `insights.md` when discovering new patterns

## Must Avoid

- Never store actual secrets in any tier (only references)
- Don't commit `local-index/` to version control
- Don't duplicate entries that exist in higher tiers
- Don't add capabilities without `id`, `name`, and `tier_origin`
