# Persona Definitions

Standard personas for capability value mapping.

## Technical Personas

### Developer
```yaml
id: developer
name: Developer
description: Individual contributor writing code

characteristics:
  role: IC Engineer
  experience_level: mid-senior
  technical_depth: high
  decision_authority: user

goals:
  - Ship quality code faster
  - Minimize interruptions and context switching
  - Learn new tools that improve workflow
  - Avoid tedious repetitive tasks

pain_points:
  - Too much time debugging
  - Interrupted by production issues
  - Manual processes that could be automated
  - Documentation that's hard to find or outdated

communication_preferences:
  tone: technical
  detail_level: detailed
  preferred_channels:
    - in_app
    - documentation
    - slack

objections:
  - objection: "I don't have time to learn a new tool"
    response: "Try it for 5 minutes. Most users see immediate value."
  - objection: "I prefer doing things my way"
    response: "This enhances your workflow, doesn't replace it."

value_messaging:
  frame_as: "Work smarter, not harder"
  emphasize: Time savings, reduced friction, automation
  avoid: Management oversight, metrics tracking
```

### Senior/Staff Engineer
```yaml
id: senior-engineer
name: Senior Engineer
description: Technical leader influencing architecture decisions

characteristics:
  role: Senior IC / Tech Lead
  experience_level: senior
  technical_depth: very high
  decision_authority: influencer

goals:
  - Improve team productivity
  - Maintain code quality standards
  - Reduce technical debt
  - Mentor junior developers

pain_points:
  - Time spent reviewing subpar code
  - Recurring production issues
  - Junior devs making avoidable mistakes
  - Tools that don't integrate well

communication_preferences:
  tone: technical with strategic context
  detail_level: moderate to detailed
  preferred_channels:
    - documentation
    - architecture docs
    - technical blog posts

value_messaging:
  frame_as: "Level up the whole team"
  emphasize: Team impact, quality improvements, best practices
  avoid: Basic tutorials, oversimplification
```

### DevOps/SRE
```yaml
id: devops
name: DevOps/SRE
description: Operations-focused engineer

characteristics:
  role: DevOps / SRE
  experience_level: mid-senior
  technical_depth: high
  decision_authority: user to influencer

goals:
  - Maximize system reliability
  - Minimize incident response time
  - Automate operational tasks
  - Improve observability

pain_points:
  - On-call fatigue
  - Manual incident response
  - Lack of visibility into issues
  - Repetitive toil

communication_preferences:
  tone: operational/tactical
  detail_level: detailed
  preferred_channels:
    - runbooks
    - monitoring dashboards
    - alerts

value_messaging:
  frame_as: "Sleep better at night"
  emphasize: Reliability, automation, reduced toil
  avoid: Developer productivity framing
```

---

## Management Personas

### Engineering Manager
```yaml
id: eng-manager
name: Engineering Manager
description: People manager of engineering team

characteristics:
  role: Engineering Manager
  experience_level: senior
  technical_depth: medium-high
  decision_authority: influencer to buyer

goals:
  - Improve team velocity
  - Reduce burnout and turnover
  - Hit delivery commitments
  - Develop team members

pain_points:
  - Unpredictable delivery timelines
  - Engineers blocked or frustrated
  - Too much time in meetings
  - Difficulty measuring productivity

communication_preferences:
  tone: professional with metrics
  detail_level: moderate
  preferred_channels:
    - email
    - dashboards
    - executive summaries

value_messaging:
  frame_as: "Multiply your team's impact"
  emphasize: Team productivity, predictability, reduced friction
  avoid: Deep technical details
```

### VP of Engineering / CTO
```yaml
id: vp-eng
name: VP of Engineering / CTO
description: Executive responsible for engineering

characteristics:
  role: VP/CTO
  experience_level: executive
  technical_depth: medium
  decision_authority: buyer

goals:
  - Scale engineering organization
  - Deliver on business commitments
  - Attract and retain talent
  - Manage technical risk

pain_points:
  - Engineering velocity below expectations
  - Too much time on maintenance vs innovation
  - Difficulty quantifying engineering value
  - Technical debt slowing delivery

communication_preferences:
  tone: strategic/business
  detail_level: high-level with ability to drill down
  preferred_channels:
    - executive briefings
    - email
    - strategic decks

value_messaging:
  frame_as: "Accelerate strategic initiatives"
  emphasize: ROI, competitive advantage, organizational scale
  avoid: Implementation details, tactical features
```

---

## Business Personas

### Product Manager
```yaml
id: product-manager
name: Product Manager
description: Owner of product direction and priorities

characteristics:
  role: Product Manager
  experience_level: mid-senior
  technical_depth: low-medium
  decision_authority: influencer

goals:
  - Ship features faster
  - Improve product quality
  - Understand user behavior
  - Reduce time to market

pain_points:
  - Engineering capacity constraints
  - Bugs delaying releases
  - Slow feedback loops
  - Difficulty prioritizing technical work

communication_preferences:
  tone: outcome-focused
  detail_level: moderate
  preferred_channels:
    - product docs
    - dashboards
    - email

value_messaging:
  frame_as: "Ship faster, ship better"
  emphasize: Velocity, quality, user impact
  avoid: Deep technical implementation
```

### Business Stakeholder
```yaml
id: business-stakeholder
name: Business Stakeholder
description: Non-technical decision maker or sponsor

characteristics:
  role: Business Executive / Sponsor
  experience_level: executive
  technical_depth: low
  decision_authority: buyer

goals:
  - Achieve business outcomes
  - Manage costs effectively
  - Reduce risk
  - Demonstrate ROI

pain_points:
  - Technical projects over budget/timeline
  - Difficulty understanding technical value
  - Risk of system failures
  - Compliance concerns

communication_preferences:
  tone: business/ROI-focused
  detail_level: high-level
  preferred_channels:
    - executive summaries
    - presentations
    - email

value_messaging:
  frame_as: "Protect and grow your investment"
  emphasize: Cost savings, risk reduction, business impact
  avoid: All technical jargon
```

---

## Persona Selection Guide

| Capability Type | Primary Personas | Secondary Personas |
|-----------------|------------------|-------------------|
| Developer tools | developer, senior-engineer | eng-manager |
| Automation | devops, developer | eng-manager, vp-eng |
| Observability | devops, senior-engineer | eng-manager |
| Quality/Testing | developer, senior-engineer | product-manager |
| Documentation | developer | product-manager, business |
| Platform | devops, senior-engineer | vp-eng |

## Messaging Matrix

| Persona | Lead With | Avoid | Proof Points |
|---------|-----------|-------|--------------|
| developer | Time savings | Management speak | "5 min to set up" |
| senior-engineer | Team impact | Oversimplification | "Reduced PRs by 40%" |
| devops | Reliability | Productivity metrics | "99.9% uptime" |
| eng-manager | Team velocity | Deep technical | "20% faster delivery" |
| vp-eng | Strategic value | Tactics | "Reclaimed 2 FTE capacity" |
| product-manager | Ship faster | Implementation | "2 weeks earlier launch" |
| business | ROI | Any jargon | "$500K annual savings" |
