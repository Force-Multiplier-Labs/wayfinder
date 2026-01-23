# ContextCore Skills Expansion Pack

Skills and capabilities for use with the [ContextCore](https://github.com/your-org/contextcore) project observability framework.

## Overview

This expansion pack provides ready-to-use skills that can be loaded into ContextCore's Tempo backend for token-efficient agent discovery. While ContextCore provides the infrastructure for storing and querying skills as OTel spans, this pack provides the **content**—real-world skills with capabilities, protocols, and workflows.

### What's Included

| Skill | Purpose | Use When |
|-------|---------|----------|
| **dev-tour-guide** | Onboarding guide for local development infrastructure | Starting sessions, avoiding reinventing wheels |
| **capability-value-promoter** | Extract and communicate capability value | Creating documentation, marketing, onboarding |

## Prerequisites

- [ContextCore](https://github.com/your-org/contextcore) installed and configured
- Tempo running (for skill storage)
- Python 3.9+

## Installation

### 1. Clone the Expansion Pack

```bash
git clone https://github.com/your-org/contextcore-skills.git
cd contextcore-skills
```

### 2. Emit Skills to Tempo

Use ContextCore's skill emitter to load skills into your observability backend:

```bash
# Activate ContextCore environment
cd /path/to/ContextCore
source .venv/bin/activate

# Emit dev-tour-guide skill
contextcore skill emit --path /path/to/contextcore-skills/skills/dev-tour-guide

# Emit capability-value-promoter skill
contextcore skill emit --path /path/to/contextcore-skills/skills/capability-value-promoter
```

### 3. Verify in Grafana

Query your skills in Tempo:

```traceql
# Find all loaded skills
{ name =~ "skill:.*" }

# Find capabilities by trigger
{ capability.triggers =~ ".*format.*" }
```

## Skills

### dev-tour-guide

Onboarding guide for Claude and other agents about local development infrastructure. Establishes default behaviors that leverage existing infrastructure.

**Key Features:**
- Progressive disclosure pattern (MANIFEST → index → capabilities)
- Agent-to-agent handoff protocols
- Infrastructure registry (prevents duplicate services)
- Skill delegation patterns

**Directory Structure:**
```
dev-tour-guide/
├── MANIFEST.yaml          # Entry point (~100 tokens)
├── agent/
│   ├── _index.yaml        # Capability routing (~200 tokens)
│   ├── capabilities/      # Full schemas (~300-500 tokens each)
│   ├── protocols/         # Communication standards
│   └── actions/           # Pre-packaged workflows
└── SKILL.md               # Human-readable documentation
```

**Usage:**
```yaml
# Agent reads manifest first (minimal tokens)
cat skills/dev-tour-guide/MANIFEST.yaml

# Then loads specific capabilities as needed
cat skills/dev-tour-guide/agent/capabilities/observability.yaml
```

### capability-value-promoter

Systematically extract, articulate, and communicate the value of system capabilities to users.

**Key Features:**
- Value type classification (direct, indirect, ripple)
- Persona mapping (11 standard personas)
- Channel adaptation (12 communication channels)
- "Audience of 1" mode for creator self-reflection

**Directory Structure:**
```
capability-value-promoter/
├── SKILL.md                      # Full skill documentation
├── references/
│   ├── capability-value-schema.yaml  # Structured schema
│   ├── personas.md               # 11 persona definitions
│   └── channel-templates.md      # 12 channel templates
└── scripts/
    └── extract_capabilities.py   # Capability extraction tool
```

**Usage:**
```bash
# Extract capabilities from a project
python scripts/extract_capabilities.py --project /path/to/project

# Output includes persona-mapped value propositions
```

## Customization

These skills contain some environment-specific paths. See [docs/customization.md](docs/customization.md) for how to adapt them to your environment.

### Key Paths to Update

| Skill | Path | Description |
|-------|------|-------------|
| dev-tour-guide | `~/.claude/skills/` | Skill installation directory |
| dev-tour-guide | `localhost:3000` | Grafana URL |
| dev-tour-guide | `~/.claude/harbor-manifest.yaml` | Infrastructure registry |

## Integration with ContextCore

### Value Capabilities Dashboard

ContextCore includes a Value Capabilities Dashboard that queries skills loaded from this pack:

- **Filter by persona**: developer, operator, architect, etc.
- **Filter by value type**: direct, indirect, ripple
- **Filter by channel**: slack, email, docs, in_app, etc.
- **Browse capabilities**: Table with pain points and benefits

Access at: `http://localhost:3000/d/contextcore-value-capabilities`

### TraceQL Queries

```traceql
# Find all dev-tour-guide capabilities
{ skill.id = "dev-tour-guide" && name =~ "capability:.*" }

# Find capabilities for developers
{ value.persona = "developer" }

# Find direct value capabilities
{ value.type = "direct" }

# Find capabilities with time savings
{ value.time_savings != "" }
```

## Contributing

1. Fork the repository
2. Add your skill in `skills/your-skill-name/`
3. Follow the structure in existing skills
4. Submit a pull request

### Skill Requirements

- Include `MANIFEST.yaml` for token-efficient discovery
- Include `SKILL.md` for human documentation
- Use ContextCore semantic conventions for attributes
- Test emission to Tempo before submitting

## License

MIT License - See [LICENSE](LICENSE) for details.

## Related

- [ContextCore](https://github.com/your-org/contextcore) - Project observability framework
- [Skill Semantic Conventions](https://github.com/your-org/contextcore/blob/main/docs/skill-semantic-conventions.md) - Attribute reference
