---
name: capability-value-promoter
description: Systematically extract, articulate, and communicate the value of system capabilities to users. Use when generating user-facing documentation, onboarding content, feature announcements, marketing materials, or personalized guidance. Bridges developer-centric capability descriptions to user-centric value propositions. Supports multi-channel communication (in-app, email, social, press, documentation). Includes "Audience of 1" mode for creators who need reminding of the value behind their own work - covering direct value (time saved, cognitive load reduced), indirect value (skills, confidence, portfolio), and ripple effects (family, friends, community).
---

# Capability Value Promoter

Transform technical capabilities into user-centric value propositions and communicate them effectively across channels.

## Conceptual Framework

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SHARED LANGUAGE                               │
│  ┌──────────────────┐                    ┌──────────────────┐       │
│  │   DEVELOPERS     │                    │     USERS        │       │
│  │                  │    Capability      │                  │       │
│  │  Build features  │───────────────────▶│  Gain benefits   │       │
│  │  Write code      │    Value Map       │  Solve problems  │       │
│  │  Create tools    │                    │  Achieve goals   │       │
│  └──────────────────┘                    └──────────────────┘       │
│           │                                       ▲                  │
│           │                                       │                  │
│           ▼                                       │                  │
│  ┌──────────────────┐                    ┌──────────────────┐       │
│  │ dev-tour-guide   │                    │ capability-value │       │
│  │ (Inward-facing)  │◀───── Mirror ─────▶│    -promoter     │       │
│  │                  │                    │ (Outward-facing) │       │
│  └──────────────────┘                    └──────────────────┘       │
└─────────────────────────────────────────────────────────────────────┘
```

### The Mirror Relationship

| dev-tour-guide | capability-value-promoter |
|----------------|---------------------------|
| What assets exist? | What value do they provide? |
| How do I use this? | Why should users care? |
| Technical documentation | User-centric messaging |
| Developer onboarding | User onboarding |
| Internal efficiency | External adoption |

## Core Workflow

### 1. Capability Extraction
Identify capabilities from code, documentation, or existing skill definitions.

```yaml
capability:
  id: auto-fix-workflow
  name: Automated Error Resolution
  technical_description: |
    GitHub Actions workflow triggered by Grafana alerts that uses
    Claude to investigate errors and create fix PRs automatically.
  source:
    - .github/workflows/auto-fix.yml
    - grafana-alert-rules.yaml
```

### 2. Value Proposition Mapping
Transform technical capabilities into user benefits.

```yaml
value_proposition:
  capability_id: auto-fix-workflow

  # Who benefits
  personas:
    - id: developer
      pain_point: "Woken up at 3am for production errors"
      benefit: "Errors investigated and fixed while you sleep"
    - id: ops_manager
      pain_point: "Mean time to resolution (MTTR) too high"
      benefit: "Reduce MTTR from hours to minutes"
    - id: cto
      pain_point: "Engineering time spent on reactive firefighting"
      benefit: "Reclaim engineering capacity for strategic work"

  # Value articulation levels
  messaging:
    tagline: "Fix errors before you know they exist"
    one_liner: "AI-powered error detection and resolution"
    elevator_pitch: |
      When production errors occur, our system automatically
      detects them, investigates root causes, and proposes fixes—
      often before your team even notices the problem.
    detailed: See references/value-propositions/auto-fix.md
```

### 3. Channel Adaptation
Format value propositions for target channels.

| Channel | Format | Tone | Length |
|---------|--------|------|--------|
| In-app tooltip | Micro-copy | Helpful | 10-20 words |
| Email | Narrative | Personal | 100-200 words |
| Documentation | Tutorial | Instructive | 500+ words |
| Social media | Punchy | Conversational | 50-100 words |
| Press release | Formal | Authoritative | 400-600 words |
| Sales deck | Benefit-focused | Persuasive | Bullets |

### 4. Personalization Layer
Match capabilities to user context.

```yaml
personalization:
  user_context:
    role: developer
    usage_patterns:
      - frequent: [code-review, testing]
      - rare: [auto-fix, observability]
      - never: [documentation-generation]
    pain_points_inferred:
      - manual_testing
      - slow_code_reviews

  recommendations:
    - capability: auto-fix-workflow
      relevance: high
      reason: "You frequently review code but rarely use auto-fix"
      message: "Let AI handle routine fixes so you can focus on complex reviews"

    - capability: observability-dashboards
      relevance: medium
      reason: "Testing frequency suggests debugging needs"
      message: "See exactly where issues occur with pre-built dashboards"
```

## Value Proposition Templates

### For Feature Announcements

```markdown
## [Capability Name]

**The Problem:** [Pain point in user language]

**The Solution:** [Capability framed as benefit]

**How It Works:**
1. [Simple step]
2. [Simple step]
3. [Outcome]

**Get Started:** [Single clear action]
```

### For Onboarding Sequences

```markdown
### Day 1: [Most valuable capability]
Welcome! Here's the one thing that will immediately save you time...

### Day 3: [Second capability]
Now that you've seen [first capability], here's something that works even better with it...

### Day 7: [Advanced capability]
You're ready for the power features...
```

### For Usage-Based Prompts

```markdown
# When user does X but hasn't tried Y

"You've been [doing X] a lot. Did you know [Y] can [benefit]?"

# When user struggles with task

"Having trouble with [task]? [Capability] was designed exactly for this."

# When user hasn't returned

"We noticed you haven't tried [high-value capability].
Here's what you're missing: [specific benefit]"
```

## Capability Extraction

Run the capability extractor on a project:

```bash
python scripts/extract_capabilities.py /path/to/project \
  --output capabilities.yaml \
  --sources "skills,workflows,apis,readme"
```

The extractor identifies:
- Skills (from `~/.claude/skills/`)
- GitHub Actions workflows
- API endpoints
- CLI commands
- Configuration options
- Documentation sections

## Enterprise Use Case: Feature Adoption

For enterprise software where customers pay for features they don't use:

### Usage Gap Analysis
```yaml
customer_analysis:
  customer_id: acme-corp
  license_tier: enterprise
  features_licensed: 45
  features_used: 12
  features_never_tried: 28
  adoption_rate: 27%

  high_value_gaps:
    - feature: advanced-analytics
      annual_value: $50k
      usage: 0%
      likely_barrier: "Unaware it exists"
      intervention: "Executive demo"

    - feature: workflow-automation
      annual_value: $30k
      usage: 5%
      likely_barrier: "Perceived complexity"
      intervention: "Guided setup session"
```

### Intervention Strategies

| Barrier | Strategy | Channel |
|---------|----------|---------|
| Unaware | Visibility campaign | In-app, email |
| Uncertain how | Tutorial + demo | Documentation, video |
| Perceived complex | Guided onboarding | Customer success |
| Tried & abandoned | Feedback + improvement | Direct outreach |
| No perceived need | ROI demonstration | Case studies |

## Integration with dev-tour-guide

The two skills share a common capability model:

```
dev-tour-guide                    capability-value-promoter
     │                                      │
     │    ┌────────────────────────┐       │
     └───▶│   Shared Capability    │◀──────┘
          │        Model           │
          │                        │
          │  - id                  │
          │  - name                │
          │  - technical_desc      │
          │  - user_benefit        │
          │  - usage_patterns      │
          └────────────────────────┘
```

When updating dev-tour-guide with new capabilities, also update capability-value-promoter to generate corresponding user-facing content.

## Onboarding Anti-Patterns

| Anti-Pattern | Problem | Better Approach |
|--------------|---------|-----------------|
| Feature dump | Overwhelms users | Progressive disclosure |
| Technical jargon | Alienates users | User-centric language |
| One-size-fits-all | Irrelevant messaging | Persona-based content |
| No context | Feature without why | Problem → Solution frame |
| Hidden features | Never discovered | Contextual suggestions |
| Front-loaded | Cognitive overload | Drip-based introduction |

## References

- **Capability-value schema**: See [references/capability-value-schema.yaml](references/capability-value-schema.yaml)
- **Channel templates**: See [references/channel-templates.md](references/channel-templates.md)
- **Persona definitions**: See [references/personas.md](references/personas.md)

## Audience of 1 Mode

A reflective mode for **creators** who need reminding of the value behind what they built. Combats the common pattern where builders undervalue their own work or forget why they created something.

### When to Use

- Feeling disconnected from past work
- Questioning whether a project was worth the effort
- Need motivation to maintain or extend a capability
- Preparing to explain your work to others
- Annual review or portfolio reflection
- Deciding whether to continue investing in a project

### The Creator's Value Framework

```
┌─────────────────────────────────────────────────────────────────────┐
│                     AUDIENCE OF 1: THE CREATOR                       │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    DIRECT VALUE TO SELF                      │    │
│  │  • Time saved (hours/week reclaimed)                         │    │
│  │  • Cognitive load reduced (decisions automated)              │    │
│  │  • Problems eliminated (friction removed)                    │    │
│  │  • Capabilities unlocked (things now possible)               │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                              │                                       │
│                              ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                   INDIRECT VALUE TO SELF                     │    │
│  │  • Skills deepened (expertise gained)                        │    │
│  │  • Confidence built (proof of capability)                    │    │
│  │  • Portfolio enhanced (demonstrable work)                    │    │
│  │  • Satisfaction earned (craft practiced)                     │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                              │                                       │
│                              ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                   VALUE TO INNER CIRCLE                      │    │
│  │  Family: More present time, reduced work stress, stability   │    │
│  │  Friends: Shared tools, knowledge transfer, collaboration    │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                              │                                       │
│                              ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                   VALUE TO COMMUNITY                         │    │
│  │  • Open source contributions                                 │    │
│  │  • Knowledge sharing (blog posts, talks, examples)           │    │
│  │  • Raising the bar (showing what's possible)                 │    │
│  │  • Enabling others (tools they can build on)                 │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

### Creator Value Proposition Template

```yaml
creator_reflection:
  capability_id: my-capability

  # The origin story
  origin:
    trigger: "What problem pushed me to build this?"
    frustration: "What was I tired of doing manually?"
    vision: "What did I imagine being possible?"

  # Direct value to creator
  direct_value:
    time_saved:
      per_use: "X minutes"
      frequency: "Y times per week"
      annual_hours: "Z hours/year reclaimed"
    cognitive_load_reduced:
      - "No longer need to remember X"
      - "Don't have to decide Y each time"
      - "Eliminated context-switching for Z"
    problems_eliminated:
      - "Used to fail at X, now automatic"
      - "No more manual Y"
    capabilities_unlocked:
      - "Can now do X (wasn't practical before)"
      - "Y is now trivial instead of daunting"

  # Indirect value to creator
  indirect_value:
    skills_deepened:
      - "Learned X technology deeply"
      - "Understood Y pattern through implementation"
    confidence_built:
      - "Proved I could build X from scratch"
      - "Demonstrated ability to Y"
    portfolio_value:
      - "Showcases expertise in X"
      - "Demonstrates end-to-end Y thinking"
    satisfaction:
      - "Craftsmanship in X"
      - "Elegance of Y solution"

  # Value to family
  family_value:
    presence: "X fewer hours of frustrating work = more quality time"
    stress: "Y automated = less mental load carried home"
    stability: "Z reliability = fewer emergency work sessions"
    modeling: "Shows kids that problems can be solved systematically"

  # Value to friends
  friends_value:
    shared_tools: "Friends can use X for their projects"
    knowledge_transfer: "Taught Y to colleague who was stuck"
    collaboration: "Z enabled joint project that wasn't feasible before"

  # Value to community
  community_value:
    contributions:
      - "Open sourced X for others to use"
      - "Documented Y pattern for community"
    knowledge_sharing:
      - "Blog post on X helped N people"
      - "Talk on Y inspired similar projects"
    raising_bar:
      - "Showed that X is achievable"
      - "Demonstrated Y approach others can adopt"
    enabling_others:
      - "Z is foundation for others' projects"
```

### Reflection Prompts

Use these prompts to extract creator value:

**Origin Story**
- "What was the moment you decided to build this?"
- "What manual process were you tired of?"
- "What would you have to do without this?"

**Time Value**
- "How long did X take before? How long now?"
- "How often do you use this? Daily? Weekly?"
- "What would you do with 100 extra hours per year?"

**Cognitive Value**
- "What decisions does this make for you?"
- "What do you no longer have to remember?"
- "What context-switching does this eliminate?"

**Capability Value**
- "What can you do now that wasn't practical before?"
- "What's trivial now that used to be daunting?"
- "What new possibilities did this open up?"

**Ripple Effects**
- "How has this affected your time with family?"
- "Have you shared this with friends or colleagues?"
- "Has anyone else benefited from this existing?"

### Output Format: Creator Value Summary

```markdown
# [Capability Name]: Value Reflection

## Why I Built This
[Origin story - the frustration or vision that triggered creation]

## What It Gives Me

### Time Reclaimed
- **Per use**: [X minutes saved]
- **Frequency**: [Y times per week]
- **Annual impact**: [Z hours/year] - that's [equivalent: "a full work week", "a vacation", etc.]

### Mental Space Freed
- [Decisions automated]
- [Things I don't have to remember]
- [Context-switches eliminated]

### Problems Solved
- [What used to fail that now works]
- [Manual processes eliminated]

### New Capabilities
- [What's now possible that wasn't before]
- [What's trivial that used to be hard]

## Ripple Effects

### For My Family
[How this translates to presence, reduced stress, stability]

### For Friends & Colleagues
[Shared benefits, knowledge transferred, collaborations enabled]

### For the Community
[Contributions, knowledge shared, others enabled]

## The Real ROI
[Single sentence capturing the full value, e.g., "This skill gives me back
2 hours every week, eliminates a category of frustrating debugging, and
has helped 3 colleagues solve similar problems - that's worth far more
than the weekend I spent building it."]
```

### Example: Audience of 1 for "o11y" Skill

```yaml
creator_reflection:
  capability_id: o11y

  origin:
    trigger: "Third time this month debugging a production issue by grepping logs"
    frustration: "Spending 2 hours to find what should take 5 minutes"
    vision: "What if Claude could query my observability stack directly?"

  direct_value:
    time_saved:
      per_use: "45 minutes average"
      frequency: "3-4 times per week"
      annual_hours: "~120 hours/year"
    cognitive_load_reduced:
      - "Don't need to remember PromQL syntax"
      - "Don't need to context-switch between terminal and Grafana"
      - "Don't need to manually correlate metrics/logs/traces"
    problems_eliminated:
      - "No more 'which dashboard was that metric on?'"
      - "No more copy-pasting trace IDs between tools"
    capabilities_unlocked:
      - "Can investigate issues while pair programming"
      - "Can do root cause analysis without breaking flow"

  family_value:
    presence: "2 fewer hours of frustrating debugging = dinner with family"
    stress: "Production issues less anxiety-inducing"
    stability: "Faster incident resolution = fewer late nights"

  community_value:
    contributions:
      - "Open sourced the skill"
      - "Documented the Prometheus/Loki/Tempo query patterns"
    enabling_others:
      - "Template for others building observability integrations"
```

### Invocation

```
# Full reflection mode
Use capability-value-promoter in audience-of-1 mode for [capability]

# Quick value summary
Remind me why I built [capability] and what value it provides

# Specific dimension
What time does [capability] save me? How does it help my family?
```

---

## Quick Start

1. **Extract** capabilities from codebase/documentation
2. **Map** each capability to user value propositions
3. **Identify** personas who benefit
4. **Generate** channel-appropriate content
5. **Personalize** based on usage patterns
6. **Measure** adoption and iterate

## Modes Summary

| Mode | Audience | Purpose |
|------|----------|---------|
| Standard | External users | Drive adoption, explain benefits |
| Enterprise | Customers | Increase feature utilization |
| **Audience of 1** | **Creator** | **Reconnect with personal value** |
