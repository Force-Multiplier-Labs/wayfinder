# ContextCore Squirrel (Ajidamoo)

### Squirrel (Ajidamoo) — *"Red squirrel"*

**Skills library for token-efficient agent discovery.**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![ContextCore](https://img.shields.io/badge/ContextCore-expansion%20pack-blueviolet)](https://github.com/contextcore/contextcore)

## What is Squirrel?

**Squirrel** is a skills library for [ContextCore](https://github.com/contextcore/contextcore). Like a squirrel gathering and storing nuts for later retrieval, this expansion pack provides ready-to-use skills that can be loaded into ContextCore's Tempo backend for token-efficient agent discovery.

While ContextCore provides the infrastructure for storing and querying skills as OTel spans, Squirrel provides the **content**—real-world skills with capabilities, protocols, and workflows.

## Why "Squirrel"?

The squirrel is known for gathering, storing, and retrieving nuts with remarkable memory and efficiency. This expansion pack gathers capabilities, protocols, and workflows that agents can retrieve as needed without loading entire context files.

**Ajidamoo** (ah-JID-ah-moo) is the Anishinaabe (Ojibwe) word for "red squirrel", honoring the indigenous peoples of Michigan and the Great Lakes region. See the [ContextCore naming convention](https://github.com/contextcore/contextcore/blob/main/docs/NAMING_CONVENTION.md) for more context.

## What's Included

| Skill | Purpose | Use When |
|-------|---------|----------|
| **dev-tour-guide** | Onboarding guide for local development infrastructure | Starting sessions, avoiding reinventing wheels |
| **capability-value-promoter** | Extract and communicate capability value | Creating documentation, marketing, onboarding |

## Prerequisites

- [ContextCore](https://github.com/contextcore/contextcore) installed and configured
- Tempo running (for skill storage)
- Python 3.9+

## Installation

### Option 1: pip (Recommended)

```bash
pip install contextcore-squirrel
```

### Option 2: From Source

```bash
git clone https://github.com/contextcore/contextcore-squirrel.git
cd contextcore-squirrel
pip install -e .
```

## Quick Start

### Emit Skills to Tempo

```bash
# Emit dev-tour-guide skill
contextcore skill emit --path /path/to/contextcore-squirrel/skills/dev-tour-guide

# Emit capability-value-promoter skill
contextcore skill emit --path /path/to/contextcore-squirrel/skills/capability-value-promoter

# Or emit all skills
squirrel emit --all
```

### Verify in Grafana

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

## Token-Efficient Discovery

Squirrel skills use progressive disclosure to minimize token usage:

| Level | What | Tokens | When |
|-------|------|--------|------|
| **0** | MANIFEST.yaml | ~100 | Quick routing decisions |
| **1** | _index.yaml | ~200 | Capability discovery |
| **2** | Full capability | ~300-500 | Detailed execution |

```yaml
# Agent reads manifest first (minimal tokens)
cat skills/dev-tour-guide/MANIFEST.yaml

# Then loads index for routing
cat skills/dev-tour-guide/agent/_index.yaml

# Finally loads full capability only when needed
cat skills/dev-tour-guide/agent/capabilities/observability.yaml
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

ContextCore includes a Value Capabilities Dashboard that queries skills loaded from Squirrel:

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

## ContextCore Ecosystem

Squirrel is part of the ContextCore expansion pack ecosystem:

| Package | Animal | Anishinaabe | Purpose |
|---------|--------|-------------|---------|
| [contextcore](https://github.com/contextcore/contextcore) | Spider | Asabikeshiinh | Core framework |
| [contextcore-rabbit](https://github.com/contextcore/contextcore-rabbit) | Rabbit | Waabooz | Alert automation |
| [contextcore-fox](https://github.com/contextcore/contextcore-fox) | Fox | Waagosh | Context enrichment |
| [contextcore-coyote](https://github.com/contextcore/contextcore-coyote) | Coyote | Wiisagi-ma'iingan | Multi-agent pipeline |
| [contextcore-beaver](https://github.com/contextcore/contextcore-beaver) | Beaver | Amik | LLM abstraction |
| **contextcore-squirrel** | Squirrel | Ajidamoo | Skills library |

## License

MIT License - See [LICENSE](LICENSE) for details.

## Related

- [ContextCore](https://github.com/contextcore/contextcore) - Project observability framework
- [Skill Semantic Conventions](https://github.com/contextcore/contextcore/blob/main/docs/skill-semantic-conventions.md) - Attribute reference
- [Expansion Packs](https://github.com/contextcore/contextcore/blob/main/docs/EXPANSION_PACKS.md) - All ContextCore expansion packs
- [Naming Convention](https://github.com/contextcore/contextcore/blob/main/docs/NAMING_CONVENTION.md) - Why we use animal names
