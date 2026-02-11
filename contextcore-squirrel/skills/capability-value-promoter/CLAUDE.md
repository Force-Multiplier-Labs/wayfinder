# Capability Value Promoter - Skill Development Project

This is the **development workspace** for the `capability-value-promoter` skill.

## Skill Overview

**Purpose:** Transform technical capabilities into user-centric value propositions and communicate them effectively across channels.

**Installed Location:** `~/.claude/skills/capability-value-promoter/`

**Core Function:** Bridges developer-facing capability descriptions to user-facing benefits, supporting:
- Capability extraction from code/docs
- Value proposition mapping to personas
- Multi-channel content generation (in-app, email, docs, social, press)
- "Audience of 1" mode for creator self-reflection

## Architecture

```
capability-value-promoter/
├── SKILL.md                           # Main skill definition
├── references/
│   ├── capability-value-schema.yaml   # Structured capability schema
│   ├── channel-templates.md           # Communication channel templates
│   └── personas.md                     # Standard persona definitions
└── scripts/
    └── extract_capabilities.py         # Capability extraction tool
```

## Key Relationships

### Mirror Skill: dev-tour-guide
- **dev-tour-guide**: Inward-facing (what assets exist, how to use them)
- **capability-value-promoter**: Outward-facing (what value they provide, why users should care)
- Share common capability model

### Downstream: channel-adapter
- Takes value propositions from this skill
- Adapts them for specific distribution channels
- Routes to appropriate communication systems

## Development Guidelines

### When Modifying SKILL.md
1. Changes here affect the installed skill at `~/.claude/skills/capability-value-promoter/`
2. Sync changes to installed location after development
3. Test with various capability types before finalizing

### Schema Changes (capability-value-schema.yaml)
- Maintain backwards compatibility
- Document migration path for existing capability definitions
- Update extract_capabilities.py if schema structure changes

### Adding New Personas
- Add to `references/personas.md`
- Include: id, characteristics, goals, pain_points, communication_preferences
- Update messaging matrix

### Adding New Channel Templates
- Add to `references/channel-templates.md`
- Provide clear variable placeholders
- Include format constraints (length, tone, CTA requirements)

## Testing

### Manual Testing
```bash
# Test capability extraction
python ~/.claude/skills/capability-value-promoter/scripts/extract_capabilities.py /path/to/project

# Test skill invocation
# In Claude Code, use: capability-value-promoter for [capability-name]
```

### Validation Checklist
- [ ] Capability extraction identifies expected assets
- [ ] Value propositions map correctly to personas
- [ ] Channel templates produce well-formatted output
- [ ] "Audience of 1" mode generates meaningful reflections

## Sync to Installed Location

After making changes in this development folder:
```bash
# Copy to installed location
cp -r ./* ~/.claude/skills/capability-value-promoter/
```

## Related Skills

| Skill | Relationship | Purpose |
|-------|-------------|---------|
| dev-tour-guide | Mirror | Internal capability documentation |
| channel-adapter | Downstream | Channel-specific distribution |
| internal-comms | Template source | Communication formats |
| skill-creator | Meta | Creating new skills |

## Modes

| Mode | Audience | Trigger |
|------|----------|---------|
| Standard | External users | Default |
| Enterprise | Paying customers | Feature adoption gaps |
| Audience of 1 | Creator | Self-reflection on value |

## Key Concepts

- **Capability**: Technical feature or tool (what it does)
- **Value Proposition**: User benefit (why it matters)
- **Persona**: Target user archetype (who cares)
- **Channel**: Communication medium (where to say it)
- **Trigger**: Contextual moment (when to say it)
