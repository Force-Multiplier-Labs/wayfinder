# Next Steps: Dev Tour Guide & LLM Formatting

Deep reflection on what we've built and where to go next.

---

## What We Accomplished

1. **Packaged dev-tour-guide** for GitHub and claude.ai distribution
2. **Created agent-optimized layer** with progressive disclosure (~95% token reduction)
3. **Defined agent-to-agent protocols** (discovery, invocation, handoff)
4. **Established LLM Formatting** as a new lessons learned domain

---

## Strategic Questions

### 1. Does This Actually Work?

We've built a theoretical improvement. We have no empirical evidence that:
- Agents actually use the structured files over SKILL.md
- Token savings translate to real-world benefits
- The handoff protocol reduces delegation failures
- Progressive disclosure is followed vs full-file loading

**Needed:** Instrumentation and measurement.

### 2. Is This the Right Abstraction Level?

The format assumes:
- Skills have typed inputs/outputs
- Capabilities are discrete and composable
- Agents can parse YAML reliably
- Progressive disclosure is worth the file fragmentation

**Risk:** Over-engineering for simple use cases. A skill that's just "apply brand colors" doesn't need 5 capability files.

### 3. Who Is This For?

Three potential audiences:
1. **Personal use** - Your agents, your infrastructure
2. **Team use** - Shared within an organization
3. **Public use** - Open source for anyone

Each requires different levels of abstraction. Current version is heavily personalized (hardcoded paths, local infrastructure).

---

## Prioritized Next Steps

### Tier 1: Validate & Publish (This Week)

| Step | Rationale | Effort |
|------|-----------|--------|
| **Push to GitHub** | Get real feedback, establish public artifact | 5 min |
| **Apply format to o11y skill** | Test if format works for a complex skill | 2-3 hours |
| **Instrument one agent session** | Measure actual token usage with new format | 1 hour |

**Validation criteria:**
- Does an agent naturally find and use MANIFEST.yaml?
- Are capability lookups faster/cheaper?
- Do handoff messages actually get used?

### Tier 2: Tooling & Templates (This Month)

| Step | Rationale | Effort |
|------|-----------|--------|
| **Create skill-template generator** | Lower friction for adopting the format | 4-6 hours |
| **Build protocol validator** | Ensure skills conform to the schema | 4-6 hours |
| **Add to skill-creator skill** | New skills automatically use the format | 2-3 hours |

**Skill template should scaffold:**
```
my-skill/
├── MANIFEST.yaml           # Pre-filled template
├── SKILL.md                # With agent section at top
├── agent/
│   ├── _index.yaml
│   ├── capabilities/
│   │   └── main.yaml
│   ├── protocols/          # Symlink to shared protocols?
│   └── actions/
└── README.md
```

### Tier 3: Ecosystem Integration (Next Quarter)

| Step | Rationale | Effort |
|------|-----------|--------|
| **MCP server for skill discovery** | Expose protocol via MCP tools | 1-2 days |
| **Convert existing skills** | Consistent format across skill library | 1-2 weeks |
| **Dashboard for agent metrics** | Visualize adoption, success rates | 2-3 days |
| **Integration with StartD8 workflows** | Skills as workflow steps | 1 week |

---

## Open Design Questions

### Q1: Required vs Optional Format

Should all skills use the agent-optimized format?

| Option | Pros | Cons |
|--------|------|------|
| **Required** | Consistency, guaranteed protocol | High friction, overkill for simple skills |
| **Optional** | Low friction, flexibility | Inconsistent agent experience |
| **Tiered** | Simple skills get basic format, complex skills get full | Complexity in the meta-layer |

**Recommendation:** Tiered. Define "basic" (just MANIFEST.yaml) and "full" (complete agent/ directory) conformance levels.

### Q2: Shared vs Copied Protocols

The protocols (discovery, invocation, handoff) should be consistent across skills. Two approaches:

| Option | Pros | Cons |
|--------|------|------|
| **Copied into each skill** | Self-contained, no dependencies | Drift, duplication |
| **Shared reference** | Single source of truth | Dependency management |

**Recommendation:** Define protocols in a central location (`~/.claude/protocols/`), skills reference by version.

### Q3: Portability vs Personalization

Current skill has paths like `$HOME/Documents/craft/...`. For public distribution:

| Option | Pros | Cons |
|--------|------|------|
| **Keep personalized** | Works immediately for you | Useless for others |
| **Make portable** | Shareable | Requires variable substitution |
| **Two versions** | Best of both | Maintenance burden |

**Recommendation:** Use environment variables or `~` expansion for paths. Create a "generic" branch for public distribution.

### Q4: Protocol Versioning

When the handoff protocol changes, how do agents handle version mismatches?

```yaml
# In handoff message
protocol_version: "2.0"

# Receiver checks compatibility
if message.protocol_version > supported_version:
  # Fallback? Error? Partial parse?
```

**Recommendation:** Semantic versioning. Major version = breaking change. Include `min_supported_version` in MANIFEST.yaml.

---

## Risks to Monitor

### 1. Complexity Creep
The format could become so complex that it's harder to use than prose. Watch for:
- More than 3 levels of indirection
- Agents failing to find capabilities
- Humans unable to understand the structure

**Mitigation:** Regularly test with fresh agents. If they struggle, simplify.

### 2. Maintenance Burden
Now there are two things to maintain: SKILL.md and agent/. They can drift.

**Mitigation:** Generate agent/ from SKILL.md? Or generate SKILL.md from agent/? Pick a source of truth.

### 3. Adoption Failure
If no one else uses this format, it's just personal overhead.

**Mitigation:** Dog-food aggressively. If it doesn't help YOUR agents, it won't help anyone's.

### 4. Premature Standardization
The format might be wrong. Locking it in too early prevents learning.

**Mitigation:** Mark as "experimental" for 3-6 months. Collect feedback before declaring stable.

---

## Experiments to Run

### Experiment 1: A/B Token Usage
- Session A: Agent uses only SKILL.md (old way)
- Session B: Agent uses MANIFEST.yaml + progressive loading (new way)
- Measure: Total tokens consumed for equivalent tasks

### Experiment 2: Handoff Success Rate
- Create 10 test handoff scenarios
- Run with structured handoff messages
- Run with prose handoff messages
- Measure: Success rate, retry count, time to completion

### Experiment 3: Cold Start Discovery
- Fresh agent, no prior context
- Task: "Find the right skill to debug a production error"
- Measure: Steps to find o11y, tokens consumed, accuracy

### Experiment 4: Cross-Skill Routing
- Task requires multiple skills (o11y → code-review → auto-fix)
- Measure: Can agents chain capabilities using the protocol?

---

## Longer-Term Vision

### The Skill Ecosystem

```
                    ┌─────────────────────────────────────┐
                    │         Skill Registry               │
                    │   (indexes all compliant skills)     │
                    └─────────────────────────────────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
              ┌─────▼─────┐   ┌─────▼─────┐   ┌─────▼─────┐
              │  Skill A   │   │  Skill B   │   │  Skill C   │
              │ MANIFEST   │   │ MANIFEST   │   │ MANIFEST   │
              │ agent/     │   │ agent/     │   │ agent/     │
              └───────────┘   └───────────┘   └───────────┘
                    │                │                │
                    └────────────────┼────────────────┘
                                     │
                    ┌─────────────────────────────────────┐
                    │      Shared Protocol Library         │
                    │  (discovery, invocation, handoff)    │
                    └─────────────────────────────────────┘
```

### Agent-Native Development

Eventually, the format could enable:
- **Auto-generated UIs** from capability schemas
- **Type checking** for agent invocations
- **Workflow composition** by chaining capabilities
- **Cost prediction** from token budget annotations
- **Compatibility checking** between skills

---

## Immediate Actions

### Today
- [ ] Push dev-tour-guide to GitHub
- [ ] Write a brief announcement/explanation

### This Week
- [ ] Apply format to o11y skill (validation)
- [ ] Run Experiment 1 (A/B token usage)
- [ ] Decide: Required vs Optional format

### This Month
- [ ] Create skill-template generator
- [ ] Build protocol validator
- [ ] Update skill-creator skill
- [ ] Run Experiments 2-4

---

## Success Criteria

How do we know this effort was worthwhile?

| Metric | Target | Measurement |
|--------|--------|-------------|
| Token reduction | >50% for typical operations | Before/after comparison |
| Adoption | 5+ skills using format | Skill audit |
| Handoff success | >90% structured handoffs succeed | Instrumentation |
| Developer experience | Format feels natural, not burdensome | Self-assessment |
| Community interest | Stars, forks, issues on GitHub | GitHub metrics |

---

## Final Reflection

We've built infrastructure for a problem we believe exists (agent-to-agent communication is inefficient) but haven't proven exists. The scientific approach would be:

1. **Measure** current state (how bad is it really?)
2. **Hypothesize** intervention (this format will help)
3. **Experiment** (A/B test with real agents)
4. **Analyze** (did it actually help?)
5. **Iterate** (refine based on evidence)

We're currently at step 2. The temptation is to keep building (more features, more protocols, more tooling). The discipline is to pause and validate.

**Recommended next action:** Run Experiment 1 before building anything else. If token savings aren't real, the entire premise is flawed.

---

*Generated: 2025-01-13*
*Status: Reflection complete, awaiting validation*
