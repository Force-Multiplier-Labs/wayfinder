---
name: dev-tour-guide
description: Onboarding guide for Claude and other agents about local development infrastructure, processes, and capabilities. Use this skill at session start to understand existing assets and avoid reinventing wheels. Informs agents about local observability stack, skills, lessons learned library, prompt engineering framework, and integrated workflows. Establishes default behaviors that leverage existing infrastructure.
---

# Dev Tour Guide

This skill provides orientation to local development infrastructure. **Default behavior: Use existing tools and processes before building new ones.**

---

## Agent-to-Agent Communication (Machine-Readable)

**For agents:** This skill provides machine-readable files optimized for agent-to-agent communication. Use these instead of parsing this markdown document.

### Entry Point (Start Here)

```bash
# Primary entry point (~100 tokens)
cat MANIFEST.yaml
```

### Progressive Disclosure Pattern

| Level | File | Token Cost | Purpose |
|-------|------|------------|---------|
| 0 | `MANIFEST.yaml` | ~100 | Quick actions, capabilities summary |
| 1 | `agent/_index.yaml` | ~200 | Capability routing table |
| 2 | `agent/capabilities/*.yaml` | ~300-500 each | Full typed schemas |
| 3 | `agent/protocols/*.yaml` | ~150-250 each | Communication standards |

**Typical usage: ~300 tokens** (Load Level 0 + selective Level 1)

### Quick Actions (No Schema Lookup Needed)

```yaml
# From MANIFEST.yaml
quick_actions:
  debug_error: delegate_to → o11y
  create_dashboard: delegate_to → grafana-dashboards
  check_infra: read → ~/.claude/harbor-manifest.yaml
  find_skill: read → agent/_index.yaml
```

### Agent Directory Structure

```
agent/
├── _index.yaml              # Capability routing (~200 tokens)
├── capabilities/
│   ├── observability.yaml   # o11y, grafana-dashboards (~400 tokens)
│   ├── skills.yaml          # All skills with typed I/O (~500 tokens)
│   ├── workflows.yaml       # Multi-step workflows (~300 tokens)
│   ├── infrastructure.yaml  # Protected services (~250 tokens)
│   └── knowledge.yaml       # Lessons learned, indexes (~200 tokens)
├── protocols/
│   ├── discovery.yaml       # How to find capabilities
│   ├── invocation.yaml      # How to invoke capabilities
│   └── handoff.yaml         # Agent-to-agent delegation format
└── actions/
    ├── debug-error.yaml     # Pre-packaged debug workflow
    ├── check-infrastructure.yaml
    └── create-dashboard.yaml
```

### Handoff Message Format (Agent-to-Agent)

```yaml
# Standard format for delegating to another agent
handoff_message:
  from_agent: "orchestrator"
  to_agent: "o11y"
  capability_id: "investigate_error"
  task: "Find root cause of checkout failures"
  inputs:
    error_context: "HTTP 500 errors in checkout-service"
    time_range: "2h"
  expected_output:
    type: "analysis_report"
    fields: ["root_cause", "evidence", "recommended_fix"]
  constraints:
    timeout_ms: 300000
    priority: "high"
```

### Protocols Reference

| Protocol | File | Purpose |
|----------|------|---------|
| Discovery | `agent/protocols/discovery.yaml` | Find capabilities by task type |
| Invocation | `agent/protocols/invocation.yaml` | Standard invocation patterns |
| Handoff | `agent/protocols/handoff.yaml` | Agent-to-agent delegation |

---

## Human-Readable Documentation (Below)

The rest of this document provides human-readable documentation. Agents should prefer the structured files above.

## ⚓ Harbor Manifest (CRITICAL - Read First!)

**BEFORE adding ANY infrastructure (docker, brew install, new services):**

```bash
# Check what already exists
cat ~/.claude/harbor-manifest.yaml
docker ps
```

**Harbor Manifest Location:** `~/.claude/harbor-manifest.yaml`

This file is the single source of truth for all local infrastructure. The `infra-guard-hook` will **BLOCK** commands that attempt to create duplicate services.

### Anti-Pattern: Duplicate Infrastructure
Creating a second instance of existing infrastructure (e.g., another Grafana on port 3002 when one exists on 3000) causes:
- Port conflicts
- Wasted resources
- Confusion about which instance to use
- Data fragmentation

### Pre-Flight Checklist (Before Adding Infrastructure)
1. ✅ Check `harbor-manifest.yaml` for existing service
2. ✅ Check `service_equivalents` section for alternatives
3. ✅ Run `docker ps` to see running containers
4. ✅ If service exists, USE IT instead of creating new
5. ✅ If truly needed, update harbor-manifest.yaml after adding

### Protected Services (Will Be Blocked)
- Grafana (use localhost:3000)
- Prometheus (use localhost:9090)
- Loki (use localhost:3100)
- Tempo (use localhost:3200)
- Pyroscope (use localhost:4040)
- Mimir (use localhost:9009)
- Pushgateway (use Mimir at localhost:9009)
- InfluxDB (use Mimir)
- Elasticsearch (use Loki)
- Jaeger (use Tempo)

---

## Local Observability Stack

### Grafana Ecosystem (port 3000)
```
http://localhost:3000   # Grafana UI
http://localhost:9090   # Prometheus (metrics)
http://localhost:9009   # Mimir (long-term metrics storage)
http://localhost:3100   # Loki (logs)
http://localhost:3200   # Tempo (traces)
http://localhost:4040   # Pyroscope (profiling)
```

**For any error investigation, debugging, or performance issue:**
1. Use the `o11y` skill - AI-powered root cause analysis
2. Use the `grafana-dashboards` skill - create/manage dashboards

### When to Use o11y Skill
- Production issues
- Error spike analysis
- Latency debugging
- System behavior investigation
- Correlating metrics, logs, traces, and profiles with source code

```bash
# Environment setup for o11y
export PROMETHEUS_URL=http://localhost:9090
export LOKI_URL=http://localhost:3100
export TEMPO_URL=http://localhost:3200
export PYROSCOPE_URL=http://localhost:4040
```

### ContextCore Skill Capabilities in Tempo

Skills can be stored as OTel spans in Tempo for token-efficient agent discovery via TraceQL.

**SDK Location:** `$HOME/Documents/dev/ContextCore/src/contextcore/skill/`

**CLI Commands:**
```bash
cd $HOME/Documents/dev/ContextCore
source .venv/bin/activate

# Emit skill to Tempo
contextcore skill emit --path /path/to/skill

# Query capabilities by trigger
contextcore skill query --trigger "format"

# Query by category and budget
contextcore skill query --category transform --budget 500

# Get routing table
contextcore skill routing --skill-id llm-formatter
```

**Token Efficiency:** Summary+evidence pattern compresses ~400 token capabilities to ~50 tokens (87% reduction).

**TraceQL Queries:**
```traceql
# Find capabilities by trigger
{ capability.triggers =~ ".*format.*" }

# Find high-confidence, agent-optimized capabilities
{ capability.audience = "agent" && capability.confidence >= 0.9 }

# Find capabilities by project
{ capability.project_refs =~ ".*checkout.*" }
```

**Use `llm-formatter` skill** to transform docs and emit to Tempo.

## 011yBubo: Dashboard Agent & Alert Automation

**Location:** `$HOME/Documents/dev/011yBubo/`

011yBubo enables AI agent interaction from Grafana dashboards and automated alert responses.

### Core Components

| Component | Purpose |
|-----------|---------|
| `webhook_server.py` | Zero-dependency Python server (stdlib only) |
| `/invoke` endpoint | Human-initiated Claude queries from Grafana button |
| `/webhook/grafana` endpoint | Automated alert handling via Hermes module |
| Hermes module (`hermes/`) | Alert-driven automation framework |

### Quick Start

```bash
# Start webhook server
cd $HOME/Documents/dev/011yBubo
ANTHROPIC_API_KEY=$("$HOME/.claude/scripts/secrets.sh" get ANTHROPIC_API_KEY) python3 webhook_server.py

# Test Hermes alert endpoint
curl -X POST http://localhost:8080/webhook/grafana \
  -H "Content-Type: application/json" \
  -d '{"receiver": "hermes", "status": "firing", "alerts": [{"status": "firing", "labels": {"alertname": "TestAlert"}}]}'
```

### Hermes Action Types

| Type | Description |
|------|-------------|
| `log` | Log alert to Loki |
| `notify` | macOS native notification (osascript) |
| `claude` | Send to Claude for analysis |
| `script` | Execute shell script in `actions/` |

### Grafana Integration

- **Contact Point:** "Hermes" webhook → `http://host.docker.internal:8080/webhook/grafana`
- **Notification Policy:** Routes `severity=~"critical|warning"` to Hermes
- **Test Alert:** Use `__expr__` datasource with `1 > 0` for instant-fire test

### Related Skills
- Use `o11y` skill to investigate alerts that Hermes receives
- Use `grafana-dashboards` skill to create dashboards with agent buttons

---

## GitHub Actions Auto-Fix Workflow

Automated error detection and fix workflow triggered by log entries.

### Architecture
```
Loki (logs) → Grafana Alert → Webhook → GitHub Actions → Claude Agent → PR
```

### Flow
1. **Error Detection**: Loki receives error logs from applications
2. **Alert Trigger**: Grafana alerting rules fire on error patterns
3. **Webhook**: Alert sends payload to GitHub Actions webhook
4. **Agent Dispatch**: GitHub Action triggers Claude agent with error context
5. **Auto-Fix**: Agent investigates using o11y skill, proposes fix
6. **PR Creation**: Fix submitted as PR for review

### Quick Setup

**One-command deployment:** [scripts/setup-auto-fix.sh](scripts/setup-auto-fix.sh)

```bash
# Deploy to current project (auto-detects GitHub repo from git remote)
~/.claude/skills/dev-tour-guide/scripts/setup-auto-fix.sh

# Deploy to specific project
~/.claude/skills/dev-tour-guide/scripts/setup-auto-fix.sh --project-dir /path/to/project

# Dry run to preview changes
~/.claude/skills/dev-tour-guide/scripts/setup-auto-fix.sh --dry-run

# Skip Grafana (GitHub workflow only)
~/.claude/skills/dev-tour-guide/scripts/setup-auto-fix.sh --skip-grafana
```

**Options:**
| Flag | Description |
|------|-------------|
| `--project-dir PATH` | Target project directory |
| `--grafana-dir PATH` | Grafana provisioning path |
| `--github-owner NAME` | GitHub repo owner |
| `--github-repo NAME` | GitHub repo name |
| `--skip-grafana` | Skip Grafana deployment |
| `--skip-github` | Skip GitHub workflow |
| `--dry-run` | Preview without changes |

### Grafana Alert Rules

**Template:** [scripts/grafana-alert-rules.yaml](scripts/grafana-alert-rules.yaml)

Provision via: `/etc/grafana/provisioning/alerting/` or import in Grafana UI.

**Included alert rules:**
| Rule | Trigger | Severity |
|------|---------|----------|
| Application Error | `level="error"` in logs | warning |
| Exception/Panic | `exception`, `panic`, `fatal` patterns | critical |
| HTTP 5xx Spike | >5% error rate | warning |
| Latency Spike | P99 >2s | warning |
| Memory Issues | OOM patterns in logs | critical |
| DB Connection Errors | Connection failures | critical |

All rules include `auto_fix="true"` label for routing to webhook.

### GitHub Actions Workflow

**Template:** [scripts/auto-fix.yml](scripts/auto-fix.yml)

Copy to your project: `.github/workflows/auto-fix.yml`

The template includes:
- Repository dispatch trigger (for Grafana webhooks)
- Manual workflow dispatch (for testing)
- Claude Code integration for investigation
- Automatic PR creation for code fixes
- Issue creation when no auto-fix is possible
- Investigation report artifact upload

**Quick setup:**
```bash
mkdir -p .github/workflows
cp ~/.claude/skills/dev-tour-guide/scripts/auto-fix.yml .github/workflows/
```

**Required secrets:**
- `ANTHROPIC_API_KEY` - Claude API key
- `GITHUB_TOKEN` - Automatic (for PR creation)

### Webhook Configuration (Grafana)
```
Contact Point: GitHub Actions Webhook
URL: https://api.github.com/repos/OWNER/REPO/dispatches
Authorization: Bearer $GITHUB_TOKEN
Body:
{
  "event_type": "error-detected",
  "client_payload": {
    "error_context": "{{ .CommonAnnotations.log_query }}",
    "error_summary": "{{ .CommonAnnotations.summary }}",
    "app": "{{ .CommonLabels.app }}"
  }
}
```

### When to Use
- Recurring errors with known fix patterns
- Infrastructure issues (restarts, scaling)
- Configuration drift
- Dependency updates

### When NOT to Use
- Security vulnerabilities (require human review)
- Business logic changes
- Database migrations
- Breaking changes

## StartD8 SDK for Async Agent Development

**Location:** `$HOME/Documents/dev/startd8-sdk/`
**Documentation:** See `docs/` directory for detailed guides

The StartD8 SDK provides a unified interface for multi-LLM agent workflows with async support.

### Quick Start

```python
# Install with all providers
pip install startd8[all]

# Or specific providers
pip install startd8[anthropic,openai,gemini]
```

### Async Agent Usage

All agents support both sync and async interfaces:

```python
import asyncio
from startd8.agents import ClaudeAgent, GPT4Agent, GeminiAgent

async def main():
    # Create agents (default max_tokens: 16384)
    claude = ClaudeAgent(name="claude", model="claude-sonnet-4-20250514")
    gpt4 = GPT4Agent(name="gpt4", model="gpt-4o")

    # Async generation
    response_text, response_time_ms, token_usage = await claude.agenerate("Your prompt")

    # Or create full AgentResponse object
    response = await claude.acreate_response(
        prompt_id="prompt-123",
        prompt="Your prompt",
        metadata={"project": "my-project"}
    )

    # Check for truncation
    if response.token_usage and response.token_usage.was_truncated:
        print(f"Warning: Response was truncated (finish_reason: {response.token_usage.finish_reason})")

    # Sync wrappers also available
    response_text, response_time_ms, token_usage = claude.generate("Your prompt")

asyncio.run(main())
```

### Parallel Agent Execution

Run multiple agents concurrently:

```python
import asyncio
from startd8.agents import ClaudeAgent, GPT4Agent, GeminiAgent

async def benchmark_agents(prompt: str):
    agents = [
        ClaudeAgent(name="claude"),
        GPT4Agent(name="gpt4"),
        GeminiAgent(name="gemini"),
    ]

    # Run all agents in parallel
    tasks = [agent.agenerate(prompt) for agent in agents]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for agent, result in zip(agents, results):
        if isinstance(result, Exception):
            print(f"{agent.name}: Error - {result}")
        else:
            text, time_ms, usage = result
            print(f"{agent.name}: {time_ms}ms, {usage.output} tokens")

    return results

asyncio.run(benchmark_agents("Explain quantum computing"))
```

### Connection Pooling for Multi-Agent Workloads

For high-throughput scenarios, enable connection pooling:

```python
from startd8.agents import ClaudeAgent, GPT4Agent

# Enable connection pooling - shares HTTP clients across agents
claude1 = ClaudeAgent(name="claude-1", use_connection_pool=True)
claude2 = ClaudeAgent(name="claude-2", use_connection_pool=True)
gpt1 = GPT4Agent(name="gpt-1", use_connection_pool=True)

# All agents now share underlying HTTP connections
# Reduces connection overhead for parallel requests
```

### Retry Configuration

Built-in retry with exponential backoff:

```python
from startd8.agents import ClaudeAgent
from startd8.utils.retry import RetryConfig

# Use default retry config
agent = ClaudeAgent(name="claude", enable_retry=True)

# Or customize retry behavior
custom_config = RetryConfig(
    max_attempts=5,
    base_delay=2.0,
    max_delay=120.0,
    retryable_status_codes=(429, 500, 502, 503, 504, 529),  # 529 = Anthropic overloaded
)
agent = ClaudeAgent(name="claude", retry_config=custom_config)
```

### Cost Tracking Integration

Track costs across all agent calls:

```python
from startd8.costs import CostTracker, BudgetManager
from startd8.agents import ClaudeAgent

# Initialize tracking
tracker = CostTracker()
budget = BudgetManager(daily_budget=10.0)

# Agents with cost tracking
agent = ClaudeAgent(
    name="claude",
    cost_tracker=tracker,
    budget_manager=budget
)

# Use normally - costs are tracked automatically
response = await agent.acreate_response(
    prompt_id="p1",
    prompt="Hello",
    project="my-project",
    tags=["experiment-1"]
)

# Query costs
summary = tracker.get_summary(project="my-project")
print(f"Total cost: ${summary.total_cost:.4f}")
```

### Truncation Detection

The SDK automatically detects truncated responses:

```python
from startd8.agents import ClaudeAgent
import warnings
from startd8.exceptions import TruncationWarning

# Catch truncation warnings
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")

    response = await agent.acreate_response(prompt_id="p1", prompt="...")

    # Check for truncation warnings
    truncation_warnings = [x for x in w if issubclass(x.category, TruncationWarning)]
    if truncation_warnings:
        print(f"Response may be truncated: {truncation_warnings[0].message}")

# Or check via token_usage
if response.token_usage and response.token_usage.was_truncated:
    print(f"Truncated! finish_reason: {response.token_usage.finish_reason}")

# Or check metadata
if response.metadata.get('truncation_detected'):
    print(f"Indicators: {response.metadata.get('truncation_indicators')}")
```

### Provider Registry

Discover and use providers dynamically:

```python
from startd8.providers import ProviderRegistry

# Discover all installed providers
ProviderRegistry.discover()

# List available providers
providers = ProviderRegistry.list_providers()
print(providers)  # ['anthropic', 'openai', 'gemini', 'mock']

# Get provider and create agent
provider = ProviderRegistry.get_provider("anthropic")
provider.validate_config({})  # Check API key etc.
agent = provider.create_agent("claude-sonnet-4-20250514")
```

### Key Agent Classes

| Agent | Provider | Default Model | Import |
|-------|----------|---------------|--------|
| `ClaudeAgent` | Anthropic | claude-sonnet-4-20250514 | `from startd8.agents import ClaudeAgent` |
| `GPT4Agent` | OpenAI | gpt-4o | `from startd8.agents import GPT4Agent` |
| `GeminiAgent` | Google | gemini-2.0-flash | `from startd8.agents import GeminiAgent` |
| `OpenAICompatibleAgent` | Any OpenAI-compatible | custom | `from startd8.agents import OpenAICompatibleAgent` |
| `MockAgent` | Testing | mock-model | `from startd8.agents import MockAgent` |

### Environment Variables

```bash
ANTHROPIC_API_KEY    # For Claude models
OPENAI_API_KEY       # For GPT models
GOOGLE_API_KEY       # For Gemini models
OLLAMA_HOST          # Ollama server URL (optional, default: http://localhost:11434)
```

### Session Tracking with Prometheus

Monitor active sessions and context capacity with built-in Prometheus metrics:

```python
from startd8 import AgentFramework

# Enable session tracking with Prometheus export
framework = AgentFramework(
    enable_session_tracking=True,
    prometheus_port=9091  # Metrics at http://localhost:9091/metrics
)

# Start a tracked session
session_id = framework.start_session(
    agent_name="claude",
    model="claude-sonnet-4-20250514"
)

# Get session summary
summary = framework.get_session_summary()
print(f"Active sessions: {summary['active_sessions']}")
print(f"Context usage: {summary['average_context_usage']:.1%}")
print(f"Total cost: ${summary['total_cost']:.4f}")

# End session when done
framework.end_session(session_id)
```

**Prometheus Metrics Exported:**
| Metric | Type | Description |
|--------|------|-------------|
| `startd8_active_sessions` | Gauge | Active sessions by agent/model |
| `startd8_requests_total` | Counter | Requests by status |
| `startd8_tokens_total` | Counter | Token consumption |
| `startd8_response_time_ms` | Histogram | Response time distribution |
| `startd8_context_usage_ratio` | Gauge | Context window usage |
| `startd8_truncations_total` | Counter | Truncation events |
| `startd8_cost_total` | Counter | Cost in USD |

### Grafana Dashboard

Pre-built dashboard for SDK metrics visualization:

**Dashboard:** `dashboards/startd8-metrics.json`
**Live URL:** http://localhost:3000/d/startd8-sdk-metrics

**Panels include:**
- Overview KPIs (sessions, requests, tokens, cost, truncations)
- Session trends by agent/model
- Token consumption and cost over time
- Response time percentiles (P50/P90/P99)
- Context usage per session with capacity warnings

**Import dashboard:**
```bash
curl -X POST "http://localhost:3000/api/dashboards/db" \
  -H "Authorization: Bearer $GRAFANA_SA_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"dashboard\": $(cat dashboards/startd8-metrics.json), \"overwrite\": true}"
```

### Related Documentation

- `docs/SDK_ARCHITECTURE_v1.md` - Full architecture overview
- `docs/API_REFERENCE_v1.md` - Complete API reference
- `docs/COST_TRACKING_USER_GUIDE.md` - Cost tracking guide
- `docs/TUI_USER_GUIDE_v1.md` - TUI usage guide
- `docs/developer-portal.html` - Interactive developer portal
- `dashboards/startd8-metrics.json` - Grafana dashboard
- Lessons Learned: `$HOME/Documents/craft/Lessons_Learned/sdk/SDK_developer_LESSONS_LEARNED.md`

### StartD8 TUI (Interactive Terminal UI)

Launch with `startd8 tui` for a full interactive experience. Built on questionary + Rich.

```bash
# Launch TUI
startd8 tui

# Or with custom storage directory
startd8 tui --dir /path/to/.startd8
```

#### TUI Main Menu Sections

| Section | Options |
|---------|---------|
| **WORKFLOW** | Create Prompt, Prompt Builder, Enhance Prompt File, Document Updater, Document Enhancement Chain, Design Pipeline, Design Polish Pipeline, Critical Review Workflow, Iterative Dev Workflow, Job Queue, Distribute to Agents, View Results |
| **MANAGE** | List All Prompts, Compare Prompt Responses, View Statistics |
| **AGENTS** | Chat with Agent, Test Agent Connections, Fix Agent Config Issues, Manage Agents, Manage API Keys |
| **EXTERNAL USAGE** | Log External Usage, Compare SDK vs External, Manage External Tools |
| **SYSTEM** | Test All Agents Readiness, Self-Diagnostics, Resilience Settings, Analyze Last Error, Analyze Agent Config Errors, Manage Output Folders, Tour Guide, Help |

#### Key TUI Features

**1. Prompt Builder Wizard**
Interactive template-based prompt generation with:
- Category-organized templates (builtin + user)
- Step-by-step variable filling
- Project context auto-detection
- Preview before generation
- Directory browser for path inputs

**2. Multi-Agent Workflows**
- **Document Enhancement Chain**: Sequential multi-agent document refinement
- **Design Pipeline**: Draft → Review → Polish
- **Design Polish Pipeline**: Polish → Suggest Updates → Final Polish
- **Critical Review Workflow**: Multi-agent analysis
- **Iterative Dev Workflow**: Dev → Review → Fix cycles

**3. Agent Management**
- API key management with secure storage (encrypted export/import)
- Custom agent configurations (Claude, GPT-4, Gemini, Ollama, OpenAI-compatible)
- Connection testing with detailed diagnostics
- Support for OpenAI-compatible providers (Cursor, Groq, Together AI, OpenRouter)

**4. Job Queue**
- File-based job processing
- Watch folder for automatic processing
- Priority-based queue management
- Archive completed jobs option

**5. External Usage Tracking**
- Log usage from Claude Code, Cursor, etc.
- Compare SDK costs vs external tool costs
- Manage external tool configurations

**6. Help System**
- YAML-configurable help topics (`help_content/*.yaml`)
- Contextual help for each screen
- Related topics linking
- Workflow-specific guidance

#### TUI Module Structure

```
src/startd8/
├── tui_improved.py       # Main TUI with all menus and workflows
├── tui_help_system.py    # Help topic management
├── tui_workflow_help.py  # Workflow-specific help
├── tui_advanced_help.py  # Advanced feature help
├── tui_prompt_builder.py # Prompt builder wizard
└── help_content/         # YAML help configurations
    ├── help_topics.yaml
    └── contextual_help.yaml
```

#### Common TUI Workflows

**Quick Benchmark:**
1. TUI → Create New Prompt → Enter content
2. Distribute Prompt to Agents → Select agents
3. View Results → Compare responses

**Document Enhancement:**
1. TUI → Document Enhancement Chain
2. Select source document
3. Choose agents (order matters)
4. Set enhancement instructions
5. Run chain → View results

**Prompt from Template:**
1. TUI → Prompt Builder
2. Select template by category
3. Fill variables (auto-suggests from project)
4. Preview and generate

## StartD8 Workflow System (Agent-Accessible)

**Location:** `$HOME/Documents/dev/startd8-sdk/.startd8/workflows/`

The StartD8 SDK provides a unified workflow system that external AI agents can discover and execute. This follows Anthropic's "progressive disclosure" pattern for token-efficient agent interaction.

### Why Filesystem-Based Discovery?

Traditional MCP tool schemas load all definitions upfront (~600+ tokens). The filesystem approach:
- **Index file**: ~30 tokens (lightweight listing)
- **Full schema**: Loaded only when needed
- **~95% token reduction** when agents just need to list workflows

### Workflow Files Location

```
$HOME/Documents/dev/startd8-sdk/.startd8/workflows/
├── _index.yaml          # Lightweight index (read first!)
├── pipeline.yaml        # Sequential multi-agent pipeline
├── doc-enhancement.yaml # Document enhancement chain
├── iterative-dev.yaml   # Dev-review-fix loop
├── design-polish.yaml   # 3-stage document polish
└── critical-review.yaml # Multi-agent document review
```

### How Agents Should Use Workflows

**Step 1: Read the index (minimal tokens)**
```bash
cat $HOME/Documents/dev/startd8-sdk/.startd8/workflows/_index.yaml
```

Returns lightweight listing:
```yaml
workflows:
- workflow_id: pipeline
  name: Pipeline Workflow
  description: Sequential multi-agent pipeline...
  capabilities: [sequential, multi-agent, transform]
  file: pipeline.yaml
- workflow_id: design-polish
  name: Design Polish Workflow
  description: 3-stage design document refinement...
  capabilities: [document-polish, multi-agent, design-refinement]
  file: design-polish.yaml
# ... (5 workflows total)
```

**Step 2: Load full schema only when needed**
```bash
cat $HOME/Documents/dev/startd8-sdk/.startd8/workflows/pipeline.yaml
```

Returns complete schema with:
- Input definitions and JSON Schema
- Agent requirements
- MCP invocation example

**Step 3: Execute via MCP or CLI**
```bash
# Via CLI
startd8 workflow run pipeline --config config.json

# Via MCP (for AI agents)
# Use startd8_workflow tool with action="run"
```

### Available Workflows

| Workflow | Purpose | Agents Required |
|----------|---------|-----------------|
| `pipeline` | Sequential multi-agent processing | 1+ (configurable) |
| `doc-enhancement` | Document refinement chain | 2+ agents |
| `iterative-dev` | Dev → Review → Fix cycles | Exactly 2 (dev + reviewer) |
| `design-polish` | 3-stage document refinement: Polish → Suggest → Final | Exactly 3 agents |
| `critical-review` | Multi-agent document review with analysis reports | 1+ agents |

### Python API for Agents

```python
from startd8.workflows import WorkflowRegistry

# Option 1: Traditional discovery (loads all schemas)
WorkflowRegistry.discover()
result = WorkflowRegistry.run_workflow("pipeline", config={...})

# Option 2: Filesystem discovery (token-efficient)
workflows = WorkflowRegistry.discover_from_filesystem()  # Lightweight
schema = WorkflowRegistry.get_workflow_from_filesystem("pipeline")  # On-demand
```

### MCP Integration

External AI agents can use the `startd8_workflow` MCP tool:

```json
{
  "tool": "startd8_workflow",
  "input": {
    "action": "list"  // or "describe", "run"
  }
}
```

Actions:
- `list` - Returns all workflow metadata
- `describe` - Returns full schema for one workflow
- `run` - Executes workflow with config

### Exporting/Updating Workflow Files

When workflows change, re-export:
```bash
cd $HOME/Documents/dev/startd8-sdk
startd8 workflow export
```

### When to Use Workflows vs Direct Agents

| Use Case | Approach |
|----------|----------|
| Single prompt to single agent | Direct agent call |
| Multi-step processing | Pipeline workflow |
| Document refinement | Doc-enhancement workflow |
| Code with review cycles | Iterative-dev workflow |
| Design document polish | Design-polish workflow |
| Multi-agent document review | Critical-review workflow |
| Custom orchestration | Write code using workflow primitives |

### Integration with Other Skills

- Use `o11y` skill to debug workflow execution issues
- Use `grafana-dashboards` to visualize workflow metrics
- Workflows integrate with StartD8's cost tracking automatically

## Lessons Learned Library

**Location:** `$HOME/Documents/craft/Lessons_Learned/`

Domain-specific knowledge captured from development sessions:

| Domain | Lessons File | Agent Update Prompt |
|--------|--------------|---------------------|
| **Infrastructure** | `infrastructure/Infrastructure_LESSONS_LEARNED.md` | - |
| Interactive Text Games | `Interactive_text_game/Interactive_Text_Game_LESSONS_LEARNED.md` | `Interactive_Text_Game_AGENT_UPDATE_PROMPT.md` |
| MCP Server | `mcp/MCP_developer_LESSONS_LEARNED.md` | `MCP_DEV_LESSONS_LEARNED_AGENT_UPDATE_PROMPT.md` |
| SDK Development | `sdk/SDK_developer_LESSONS_LEARNED.md` | `SDK_DEV_LESSONS_LEARNED_AGENT_UPDATE_PROMPT.md` |
| GUI Games | `GUI_Game/GUI_Game_Developer_LESSONS_LEARNED.md` | `GUI_Game_AGENT_UPDATE_PROMPT.md` |
| Knowledge Management | `knowledge_management/knowledge_mgmt_LESSONS_LEARNED.md` | `knowledge_mgmt_AGENT_UPDATE_PROMPT.MD` |
| TTRPG Games | `ttrpg/TTRPG_Games_LESSONS_LEARNED.md` | `TTRPG_Games_AGENT_UPDATE_PROMPT.md` |

**Before starting work in a domain:** Read the relevant lessons learned file to apply proven patterns and avoid known anti-patterns.

**Lesson Format:**
- **Context:** What were you trying to do?
- **Problem:** What obstacle did you encounter?
- **Solution:** How did you resolve it?
- **Reusable:** Heuristic/Pattern/Checklist/Anti-pattern

## Prompt Engineering Framework

**Location:** `$HOME/Documents/craft/Prompt_Engineering/`

### Key Components

| Resource | Location | Purpose |
|----------|----------|---------|
| Prompt Library | `Prompt_Library/` | Reusable prompts by category |
| Prompt Templates | `prompt_template.md`, `feature_implementation_template.md` | Standard formats |
| Implementation Prompts | `prompts/*.md` | Feature implementation workflows |
| Prompt Archive | `Prompt_Raw_Archive/` | Session history and raw prompts |
| Template Generator | `template_generator.py` | Generate prompts from templates |
| TUI Workflow | `run_tui.py` | Interactive prompt workflow interface |

### Implementation Cycle (7 Steps)
Each feature follows: Create Tests → Implement → Test & Fix → Code Review → Fix Critical → Fix Remaining → Prepare Commit

## Session Management

### /end-session Command
Encapsulates the end-of-session workflow:
1. Identifies development domain from project path
2. Captures session learnings (patterns, problems solved, anti-patterns)
3. Updates lessons learned file for the domain
4. Updates project index at `$HOME/Documents/pers/persOS/index/`
5. Optionally exports prompts to archive

**Always run `/end-session` before closing to preserve knowledge.**

## Available Skills

Reference these skills instead of building from scratch:

| Skill | Use Case |
|-------|----------|
| `o11y` | Error investigation, root cause analysis |
| `grafana-dashboards` | Create/manage visualization dashboards |
| `grafana-plugin-dev` | Build Grafana plugins (panels, datasources, apps) |
| `code-review` | Comprehensive code reviews |
| `mcp-builder` | Build MCP servers |
| `webapp-testing` | Test web apps with Playwright |
| `skill-creator` | Create new skills |
| `frontend-design` | Production-grade UI development |
| `skill-html_game_dev` | HTML5 canvas games |
| `ttrpg-games` | TTRPG character/game systems |
| `database-administrator` | Supabase/PostgreSQL |
| `ios` | iOS development (Swift/SwiftUI) |
| `docx`, `pdf`, `xlsx`, `pptx` | Document manipulation |
| `sdk-developer` | StartD8 SDK development (see SDK section above) |
| `llm-formatter` | Transform docs to agent-optimized format, emit skills to Tempo |

**StartD8 TUI:** Run `startd8 tui` for interactive multi-agent workflows, benchmarking, and prompt management.

**Full catalog with descriptions:** See [references/skills-catalog.md](references/skills-catalog.md)

## Secure Secrets Management

API keys and secrets are managed through the **Secrets Manager** (`~/.claude/scripts/secrets.sh`).

### Why Not Environment Variables?

Environment variables have security issues for agents:
- Visible to child processes (can be dumped)
- Not inherited by background processes spawned by Claude
- Can appear in logs or process listings
- Persist in shell history if set inline

### Storage Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Secrets Manager                               │
│                ~/.claude/scripts/secrets.sh                      │
├─────────────────────────────────────────────────────────────────┤
│  Primary: macOS Keychain          │  Fallback: File Storage     │
│  - OS-level encryption            │  - ~/.claude/secrets/       │
│  - Per-user isolation             │  - 600 permissions          │
│  - Survives reboots               │  - Owner read/write only    │
└─────────────────────────────────────────────────────────────────┘
```

### Quick Start

```bash
# Store a secret (prompts securely - value never in command line)
~/.claude/scripts/secrets.sh set ANTHROPIC_API_KEY

# Use inline (secret never stored in environment)
ANTHROPIC_API_KEY=$("$HOME/.claude/scripts/secrets.sh" get ANTHROPIC_API_KEY) python3 server.py

# List stored secrets
~/.claude/scripts/secrets.sh list

# Health check
~/.claude/scripts/secrets.sh check
```

### Available Commands

| Command | Description |
|---------|-------------|
| `secrets.sh get <KEY>` | Retrieve secret to stdout |
| `secrets.sh set <KEY>` | Store secret (prompts for value) |
| `secrets.sh set <KEY> --stdin` | Store from stdin (for piping) |
| `secrets.sh delete <KEY>` | Remove secret from storage |
| `secrets.sh list` | List all stored secret names |
| `secrets.sh export <KEY>` | Output `export KEY=value` for eval |
| `secrets.sh check` | Verify storage health |

### Agent Usage Patterns

**Pattern 1: Inline Usage (Most Secure)**
```bash
# Secret retrieved at runtime, never stored in env
ANTHROPIC_API_KEY=$("$HOME/.claude/scripts/secrets.sh" get ANTHROPIC_API_KEY) python3 webhook_server.py
```

**Pattern 2: Export for Session**
```bash
# Export to current shell (less secure but convenient)
eval $("$HOME/.claude/scripts/secrets.sh" export ANTHROPIC_API_KEY)
python3 webhook_server.py
```

**Pattern 3: In Scripts**
```bash
#!/bin/bash
# my-script.sh
SECRETS="$HOME/.claude/scripts/secrets.sh"
API_KEY=$("$SECRETS" get ANTHROPIC_API_KEY)

# Use the key
curl -H "x-api-key: $API_KEY" https://api.anthropic.com/...
```

### Registered Secrets

| Key Name | Purpose | Required By |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | Claude API access | webhook_server.py, Claude agents |
| `GRAFANA_TOKEN` | Grafana API access | grafana-dashboards skill |
| `GITHUB_TOKEN` | GitHub API access | auto-fix workflow |

### Security Properties

1. **Values never in command line** - Can't be seen via `ps aux`
2. **Not in shell history** - `set` command prompts for value
3. **Encrypted at rest** - Keychain uses macOS encryption
4. **Per-user isolation** - Only your user can access
5. **Permission enforcement** - File fallback uses 600 permissions
6. **Full audit trail** - All operations logged with context

### Audit Trail

Every API key operation is logged to `~/.claude/secrets.audit.log` (JSON lines format).

**What's logged:**
- Timestamp (UTC)
- Operation (GET, SET, DELETE, EXPORT, LIST, CHECK)
- Key name (never the value!)
- Status (success/failure/warning)
- Details (source, input method, value length)
- Context (user, TTY, parent process, PID, Claude session)

**View audit log:**
```bash
# Last 50 entries (formatted table)
~/.claude/scripts/secrets.sh audit

# Last 100 entries
~/.claude/scripts/secrets.sh audit 100

# Filter by key
~/.claude/scripts/secrets.sh audit --key ANTHROPIC_API_KEY

# Filter by operation
~/.claude/scripts/secrets.sh audit --op GET

# Raw JSON output (for processing)
~/.claude/scripts/secrets.sh audit --json
```

**Example audit entry:**
```json
{
  "timestamp": "2026-01-12T18:10:43Z",
  "operation": "GET",
  "key": "ANTHROPIC_API_KEY",
  "status": "success",
  "details": "source=keychain",
  "context": {
    "user": "neilyashinsky",
    "tty": "/dev/ttys001",
    "parent_process": "python3",
    "pid": 12345,
    "claude_session": null
  }
}
```

### First-Time Setup

```bash
# 1. Verify the script is available
~/.claude/scripts/secrets.sh check

# 2. Store your Anthropic API key
~/.claude/scripts/secrets.sh set ANTHROPIC_API_KEY
# (prompts for value - paste your key)

# 3. Verify it's stored
~/.claude/scripts/secrets.sh list

# 4. Test retrieval
~/.claude/scripts/secrets.sh get ANTHROPIC_API_KEY
```

### Troubleshooting

**"Secret not found" error:**
```bash
# Check if it's stored
~/.claude/scripts/secrets.sh list

# Re-store if needed
~/.claude/scripts/secrets.sh set ANTHROPIC_API_KEY
```

**Keychain access denied:**
```bash
# macOS may prompt for password on first access
# Grant "Always Allow" for claude-code access
```

**Background process can't access secrets:**
```bash
# Use inline pattern - retrieves at spawn time
ANTHROPIC_API_KEY=$("$HOME/.claude/scripts/secrets.sh" get ANTHROPIC_API_KEY) python3 server.py &
```

## Default Behaviors

When starting any task:

1. **🚢 Check harbor manifest FIRST** - Before adding ANY infrastructure, check `~/.claude/harbor-manifest.yaml`
2. **Check existing skills** - Use skill catalog before building new capabilities
3. **Read lessons learned** - Apply domain patterns, avoid known anti-patterns
4. **Use o11y for debugging** - Don't manually grep logs; use the observability stack
5. **Use prompt templates** - Don't write prompts from scratch
6. **Run /end-session** - Always capture learnings at session end

## Active Hooks & Guards

The following hooks are active and will intercept commands:

| Hook | Trigger | Purpose |
|------|---------|---------|
| `session-init.sh` | Session start | Initialize session context |
| `infra-guard-hook.sh` | Bash commands | Block duplicate infrastructure |

### Infrastructure Guard
The `infra-guard-hook` automatically blocks:
- `docker run` with infrastructure images (grafana, prometheus, loki, etc.)
- `brew install` of infrastructure packages
- Commands that would create port conflicts

If blocked, check `~/.claude/harbor-manifest.yaml` for existing services.

## Quick Reference

```
Harbor Manifest:   ~/.claude/harbor-manifest.yaml (CHECK FIRST!)
Secrets Manager:   ~/.claude/scripts/secrets.sh
Secrets Audit:     ~/.claude/secrets.audit.log
Observability:     http://localhost:3000 (Grafana)
Lessons Learned:   $HOME/Documents/craft/Lessons_Learned/
Prompt Framework:  $HOME/Documents/craft/Prompt_Engineering/
Skills Directory:  ~/.claude/skills/
Project Index:     $HOME/Documents/pers/persOS/index/
Hooks Directory:   ~/.claude/hooks/
Scripts Directory: ~/.claude/scripts/
StartD8 SDK:       $HOME/Documents/dev/startd8-sdk/
StartD8 Workflows: $HOME/Documents/dev/startd8-sdk/.startd8/workflows/
StartD8 TUI:       startd8 tui (interactive terminal UI)
StartD8 Portal:    docs/developer-portal.html (open in browser)
```
