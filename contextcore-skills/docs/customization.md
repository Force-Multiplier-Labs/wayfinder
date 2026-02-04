# Customization Guide

This guide explains how to adapt the skills in ContextCore Squirrel (Ajidamoo) to your environment.

## Environment-Specific Paths

The skills were developed in a specific environment and contain paths that you'll need to update.

### dev-tour-guide

#### Infrastructure Endpoints

Update these in `SKILL.md` and capability files:

| Default | Description | Your Value |
|---------|-------------|------------|
| `http://localhost:3000` | Grafana URL | |
| `http://localhost:9090` | Prometheus URL | |
| `http://localhost:9009` | Mimir URL | |
| `http://localhost:3100` | Loki URL | |
| `http://localhost:3200` | Tempo URL | |
| `http://localhost:4040` | Pyroscope URL | |

#### File Paths

| Default | Description | Your Value |
|---------|-------------|------------|
| `~/.claude/skills/` | Skill installation directory | |
| `~/.claude/harbor-manifest.yaml` | Infrastructure registry | |
| `~/.claude/scripts/secrets.sh` | Secrets manager | |
| `/Users/neilyashinsky/Documents/craft/` | Lessons learned library | |
| `/Users/neilyashinsky/Documents/dev/` | Development projects | |

#### Quick Find & Replace

```bash
# Update user home directory references
find skills/dev-tour-guide -type f -name "*.yaml" -o -name "*.md" | \
  xargs sed -i '' 's|/Users/neilyashinsky|/Users/YOUR_USERNAME|g'

# Update skill installation path
find skills/dev-tour-guide -type f -name "*.yaml" -o -name "*.md" | \
  xargs sed -i '' 's|~/.claude/skills|YOUR_SKILL_PATH|g'
```

### capability-value-promoter

#### File Paths

| Default | Description | Your Value |
|---------|-------------|------------|
| `~/.claude/skills/capability-value-promoter/` | Installed location | |

## Creating Your Own Skills

### Required Files

At minimum, a skill needs:

```
your-skill/
├── MANIFEST.yaml    # Entry point for token-efficient discovery
└── SKILL.md         # Human-readable documentation
```

### MANIFEST.yaml Template

```yaml
# Minimal manifest for agent discovery
skill_id: your-skill-name
name: Your Skill Name
version: "1.0.0"
description: Brief description for routing decisions

# Quick actions (no schema lookup needed)
quick_actions:
  action_name:
    delegate_to: another-skill  # Or: read → file_path

# Entry points for deeper discovery
entry_points:
  index: agent/_index.yaml
  capabilities: agent/capabilities/

# Token budget info
token_budget:
  manifest: 100
  index: 200
  avg_capability: 400
```

### SKILL.md Template

```markdown
---
name: your-skill-name
description: Full description of what this skill does
---

# Your Skill Name

Brief overview of the skill's purpose.

## When to Use

- Trigger condition 1
- Trigger condition 2

## Capabilities

### capability-1

Description and usage.

### capability-2

Description and usage.

## Examples

Show practical usage examples.
```

## Adding New Skills to This Pack

1. Create your skill directory:
   ```bash
   mkdir -p skills/your-skill/{agent/capabilities,agent/protocols,references}
   ```

2. Add required files (MANIFEST.yaml, SKILL.md)

3. Test emission to Tempo:
   ```bash
   contextcore skill emit --path skills/your-skill --dry-run
   ```

4. Verify queries work:
   ```traceql
   { skill.id = "your-skill" }
   ```

5. Submit a pull request

## Persona Customization

The `capability-value-promoter` skill includes 11 standard personas. You can customize these in `references/personas.md`:

| Persona | Target Audience |
|---------|-----------------|
| developer | Individual contributors writing code |
| operator | DevOps/SRE managing production |
| architect | System designers making technology decisions |
| creator | Content creators, designers |
| manager | Engineering managers |
| executive | VP/CTO level |
| product | Product managers |
| security | Security engineers |
| data | Data engineers/scientists |
| designer | UX/UI designers |
| any | Catch-all for universal capabilities |

To add custom personas, extend the `personas.md` file and update the capability extraction script.

## Channel Customization

The 12 default channels can be extended in `references/channel-templates.md`:

| Channel | Use Case |
|---------|----------|
| slack | Team communication |
| email | Formal notifications |
| docs | Documentation sites |
| in_app | Product UI messaging |
| meeting | Presentations, demos |
| social | Twitter, LinkedIn |
| blog | Long-form content |
| press | Press releases |
| video | Video scripts |
| alert | Automated alerts |
| changelog | Release notes |
| sales_deck | Sales presentations |

Add new channels by extending the templates file with your messaging patterns.
