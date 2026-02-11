---
description: Review a markdown file and extract capabilities for the dev-tour-guide index system
arguments:
  - name: file
    description: Path to the markdown file to review
    required: true
---

# Index Review Command

Review the markdown file at `$ARGUMENTS.file` and extract capabilities that should be added to the dev-tour-guide capability index.

## Task

1. **Read the file** at `$ARGUMENTS.file`

2. **Extract these capability types:**

   | Type | Look For |
   |------|----------|
   | **Endpoints** | URLs, localhost:PORT, http(s)://, API references |
   | **Workflows** | Step-by-step processes, pipelines, numbered procedures |
   | **Tools** | Scripts, CLI commands, utilities, config files |
   | **Skills** | Claude skills, skill-like capabilities |
   | **Processes** | Standards, conventions, patterns, best practices |
   | **Projects** | Project references, paths, repositories |
   | **Credentials** | Environment variables, API key references (NOT values) |

3. **For each capability, determine the tier:**
   - **Personal** (`local-index/`): Private credentials, personal scripts
   - **Narrowly Shared** (`shared-index/`): Team-specific tools
   - **Widely Shared** (`Lessons_Learned/index/`): Cross-project, reusable
   - **Public** (in skill): General defaults

4. **Generate YAML entries** following this format:

```yaml
- id: "snake_case_id"
  name: "Human Readable Name"
  description: "What it does"
  # ... type-specific fields
  tags: [relevant, tags]
  tier_origin: "public|widely_shared|narrowly_shared|personal"
  added: "YYYY-MM-DD"
  added_by: "claude_code"
```

5. **Output a summary:**
   - Capabilities found by category
   - YAML entries ready to add
   - Which tier files to update
   - Any cross-references to existing capabilities

## Index Locations

```
Personal:        ~/Documents/craft/local-index/capabilities/
Narrowly Shared: ~/Documents/craft/shared-index/capabilities/
Widely Shared:   ~/Documents/craft/Lessons_Learned/index/capabilities/
Public:          ~/.claude/skills/dev-tour-guide/index/capabilities/
```

## Example Output

```markdown
## Extracted Capabilities

### Endpoints (2 found)
- `redis_local`: Redis cache at localhost:6379 → **widely_shared**
- `internal_api`: Team API at api.internal.co → **narrowly_shared**

### Add to: `widely_shared/capabilities/endpoints.yaml`
```yaml
- id: "redis_local"
  name: "Redis Cache"
  type: "database"
  url: "redis://localhost:6379"
  ...
```

Now review `$ARGUMENTS.file` and extract all indexable capabilities.
