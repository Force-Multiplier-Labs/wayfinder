# Review Markdown for Capability Index Integration

You are reviewing a markdown file to extract capabilities that should be indexed in the dev-tour-guide capability index system.

## Input

**File to review:** `{{file_path}}`

## Capability Index Structure

The index uses a 4-tier system with different sharing levels:

| Tier | Location | Use For |
|------|----------|---------|
| Personal | `~/Documents/craft/local-index/` | Private credentials, personal scripts |
| Narrowly Shared | `~/Documents/craft/shared-index/` | Team tools, internal workflows |
| Widely Shared | `~/Documents/craft/Lessons_Learned/index/` | Cross-project capabilities |
| Public | `~/.claude/skills/dev-tour-guide/index/` | Skill defaults |

## Capability Categories

Extract and categorize content into these types:

### 1. Endpoints
Infrastructure URLs, services, APIs.

```yaml
- id: "unique_id"
  name: "Human Readable Name"
  type: "service|api|database|queue|storage"
  url: "http://..."
  protocol: "http|https|grpc"
  authentication:
    type: "none|token|basic|oauth"
    credential_ref: "ENV_VAR_NAME"  # If auth required
  health_check: "http://..."  # Optional
  related_skills: ["skill_id"]
  tags: [tag1, tag2]
  tier_origin: "public|widely_shared|narrowly_shared|personal"
```

### 2. Workflows
Multi-step processes, pipelines, methodologies.

```yaml
- id: "unique_id"
  name: "Workflow Name"
  description: "What it does"
  type: "implementation|investigation|automation|methodology"
  steps:
    - order: 1
      name: "Step Name"
      description: "What happens"
      skill: "skill_id"  # If a skill is used
  related_skills: ["skill_id"]
  tags: [tag1, tag2]
  tier_origin: "..."
```

### 3. Tools
CLI tools, scripts, utilities, configurations.

```yaml
- id: "unique_id"
  name: "Tool Name"
  type: "cli|script|utility|config|alias"
  description: "What it does"
  location: "/path/to/tool"
  usage: |
    command examples
  tags: [tag1, tag2]
  tier_origin: "..."
```

### 4. Skills
Claude skills or skill-like capabilities.

```yaml
- id: "skill_id"
  name: "Skill Name"
  category: "observability|development|games|documents|ios|design|communication|data|specialized"
  description: "What it does"
  location: "~/.claude/skills/..."
  use_when:
    - "Scenario 1"
    - "Scenario 2"
  tags: [tag1, tag2]
  tier_origin: "..."
```

### 5. Processes
Standards, conventions, patterns, checklists.

```yaml
- id: "unique_id"
  name: "Process Name"
  type: "standard|convention|pattern|checklist|methodology"
  description: "What it establishes"
  rules:
    - "Rule 1"
    - "Rule 2"
  tags: [tag1, tag2]
  tier_origin: "..."
```

### 6. Projects
Project references and associations.

```yaml
- id: "project_id"
  name: "Project Name"
  description: "What it is"
  status: "active|complete|paused|archived"
  path: "/path/to/project"
  key_docs: ["CLAUDE.md", "README.md"]
  related_skills: ["skill_id"]
  tags: [tag1, tag2]
  tier_origin: "..."
```

### 7. Credentials (Personal Tier Only)
References to secrets (NEVER the actual secrets).

```yaml
- id: "credential_id"
  name: "Credential Name"
  type: "api_key|service_account|oauth|certificate"
  environment_variable: "ENV_VAR_NAME"
  storage_location: "~/.zshrc"
  format_hint: "sk-*"  # Pattern hint
  used_by:
    - endpoint: "endpoint_id"
    - skill: "skill_id"
  tier_origin: "personal"  # Always personal
```

## Review Instructions

1. **Read the markdown file** at `{{file_path}}`

2. **Extract capabilities** by looking for:
   - URLs and endpoints (http://, https://, localhost:)
   - Commands and scripts (bash, python, etc.)
   - Step-by-step processes or workflows
   - References to tools or utilities
   - Standards or conventions described
   - Project references
   - Environment variables or credential references

3. **Determine appropriate tier** for each capability:
   - Contains secrets/credentials → Personal
   - Team-specific/internal → Narrowly Shared
   - Cross-project/reusable → Widely Shared
   - General/skill-default → Public

4. **Generate YAML entries** for each extracted capability

5. **Suggest integration steps**:
   - Which tier file(s) to update
   - Any conflicts with existing entries
   - Related capabilities to cross-reference

## Output Format

```markdown
## Capabilities Found

### Endpoints (N found)
[YAML entries]

### Workflows (N found)
[YAML entries]

### Tools (N found)
[YAML entries]

### Skills (N found)
[YAML entries]

### Processes (N found)
[YAML entries]

### Projects (N found)
[YAML entries]

### Credentials (N found)
[YAML entries - references only]

## Integration Recommendations

### Files to Update
- `[tier]/capabilities/[category].yaml` - Add [entries]

### Cross-References
- Link [capability] to [related capability]

### Potential Conflicts
- [capability_id] may conflict with existing [entry]

### Tier Assignments
| Capability | Recommended Tier | Reason |
|------------|------------------|--------|
| ... | ... | ... |
```

## Now Review

Read the file at `{{file_path}}` and extract all indexable capabilities.
