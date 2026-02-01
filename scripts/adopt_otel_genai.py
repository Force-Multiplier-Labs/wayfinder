#!/usr/bin/env python3
"""
Execute OTel GenAI adoption tasks via Lead Contractor Workflow.

Usage:
    python scripts/adopt_otel_genai.py              # Run all tasks
    PRIORITY=HIGH python scripts/adopt_otel_genai.py  # Run HIGH priority only
    TASK=1 python scripts/adopt_otel_genai.py       # Run specific task
"""

import os
import json
from pathlib import Path
from startd8.workflows.builtin import LeadContractorWorkflow

# Task definitions from plan
TASK_1 = {
    "task_description": """
    Analyze ContextCore's current semantic conventions against OTel GenAI conventions.

    INPUTS:
    - ContextCore conventions: docs/semantic-conventions.md, docs/agent-semantic-conventions.md
    - OTel GenAI spec: https://github.com/open-telemetry/semantic-conventions/blob/main/docs/gen-ai/gen-ai-spans.md

    OUTPUT: Gap analysis document with:
    1. Attribute-by-attribute comparison table
    2. Exact mapping recommendations (alias, migrate, add, preserve)
    3. Breaking change assessment
    4. Migration complexity score (1-5) per attribute
    5. Recommended adoption order
    """,
    "context": {
        "contextcore_conventions": "docs/semantic-conventions.md",
        "agent_conventions": "docs/agent-semantic-conventions.md",
        "otel_spec_url": "https://github.com/open-telemetry/semantic-conventions/blob/main/docs/gen-ai/gen-ai-spans.md"
    },
    "output_format": "Markdown document with tables",
    "integration_instructions": "Save as docs/OTEL_GENAI_GAP_ANALYSIS.md"
}

TASK_2 = {
    "task_description": """
    Implement a dual-emit compatibility layer for ContextCore that:

    1. Emits BOTH old (agent.*) and new (gen_ai.*) attributes during transition
    2. Is configurable via environment variable: CONTEXTCORE_EMIT_MODE=dual|legacy|otel
    3. Provides deprecation warnings when legacy attributes are queried
    4. Has zero performance overhead when mode=otel (future default)

    IMPLEMENTATION REQUIREMENTS:
    - Create src/contextcore/compat/otel_genai.py
    - Add attribute mapping registry
    - Hook into existing span emission code
    - Add unit tests for all three modes

    EXAMPLE:
    When emitting agent.id="claude-code", also emit gen_ai.agent.id="claude-code"
    """,
    "context": {
        "current_emitter": "src/contextcore/agent/insights.py",
        "tracker": "src/contextcore/tracker.py"
    },
    "output_format": "Python module with tests",
    "integration_instructions": "Integrate with InsightEmitter.emit() and TaskTracker.start_task()"
}

TASK_3 = {
    "task_description": """
    Add gen_ai.operation.name attribute to all ContextCore span types.

    OPERATION MAPPINGS:
    - Task spans: operation.name = "task.{action}" (task.start, task.update, task.complete)
    - Insight spans: operation.name = "insight.emit"
    - Handoff spans: operation.name = "handoff.{status}" (handoff.request, handoff.complete)
    - Verification spans: operation.name = "install.verify"

    IMPLEMENTATION:
    - Update TaskTracker to emit gen_ai.operation.name
    - Update InsightEmitter to emit gen_ai.operation.name
    - Update HandoffManager to emit gen_ai.operation.name
    - Update InstallationVerifier to emit gen_ai.operation.name

    Must work with dual-emit layer from Task 2.
    """,
    "context": {
        "tracker": "src/contextcore/tracker.py",
        "insights": "src/contextcore/agent/insights.py",
        "handoff": "src/contextcore/agent/handoff.py",
        "verifier": "src/contextcore/install/verifier.py"
    },
    "output_format": "Code changes with tests",
    "integration_instructions": "Update semantic-conventions.md with new attributes"
}

TASK_4 = {
    "task_description": """
    Add provider and model tracking to insight spans.

    When an agent emits an insight, capture:
    - gen_ai.provider.name: "anthropic", "openai", "google", etc.
    - gen_ai.request.model: "claude-opus-4-5-20251101", "gpt-4o", etc.

    IMPLEMENTATION:
    - Add optional provider/model params to InsightEmitter
    - Auto-detect from environment if not provided (OTEL_SERVICE_NAME pattern)
    - Store in span attributes

    This enables queries like:
    - "Show me all decisions made by Claude Opus"
    - "Compare insight confidence by model"
    """,
    "context": {
        "insights": "src/contextcore/agent/insights.py",
        "models": "src/contextcore/agent/models.py"
    },
    "output_format": "Code changes with tests",
    "integration_instructions": "Add to CLI: contextcore insight emit --provider anthropic --model claude-opus-4-5"
}

TASK_5 = {
    "task_description": """
    Map ContextCore handoff attributes to OTel gen_ai.tool.* conventions.

    CURRENT → NEW MAPPING:
    - handoff.capability_id → gen_ai.tool.name
    - handoff.inputs → gen_ai.tool.call.arguments (JSON)
    - handoff.expected_output → (keep, no OTel equivalent)
    - handoff.status → gen_ai.tool.call.result (on completion)
    - (new) gen_ai.tool.type = "agent_handoff"
    - (new) gen_ai.tool.call.id = handoff.id

    IMPLEMENTATION:
    - Update HandoffManager to emit both old and new attributes
    - Use dual-emit layer from Task 2
    - Update handoff completion to record result
    """,
    "context": {
        "handoff": "src/contextcore/agent/handoff.py",
        "conventions": "docs/agent-semantic-conventions.md"
    },
    "output_format": "Code changes with tests",
    "integration_instructions": "Document tool.type='agent_handoff' as ContextCore extension"
}

TASK_6 = {
    "task_description": """
    Replace agent.session_id with gen_ai.conversation.id per OTel conventions.

    MIGRATION:
    - agent.session_id → gen_ai.conversation.id
    - Keep agent.session_id as alias during transition (dual-emit)
    - Update all code references
    - Update CLI commands
    - Update documentation

    The conversation.id represents the session/thread that groups related
    agent interactions, aligning with OTel's concept.
    """,
    "context": {
        "insights": "src/contextcore/agent/insights.py",
        "cli": "src/contextcore/cli.py"
    },
    "output_format": "Code changes with tests",
    "integration_instructions": "Add migration note to CHANGELOG"
}

TASK_7 = {
    "task_description": """
    Update ContextCore semantic conventions documentation to reflect OTel GenAI alignment.

    DOCUMENTATION UPDATES:
    1. docs/semantic-conventions.md:
       - Add "OTel GenAI Alignment" section
       - Document all gen_ai.* attributes used
       - Show mapping from ContextCore-specific to OTel

    2. docs/agent-semantic-conventions.md:
       - Update attribute tables with OTel equivalents
       - Add migration guide section
       - Update query examples to use gen_ai.* attributes

    3. New: docs/OTEL_GENAI_MIGRATION_GUIDE.md:
       - Step-by-step migration for existing users
       - Query migration examples (old → new)
       - Timeline for deprecation of legacy attributes

    TONE: Position ContextCore as "OTel GenAI conventions + project management extensions"
    """,
    "context": {
        "semantic_conventions": "docs/semantic-conventions.md",
        "agent_conventions": "docs/agent-semantic-conventions.md"
    },
    "output_format": "Markdown documents",
    "integration_instructions": "Link from README.md"
}

TASKS = {
    1: {"priority": "HIGH", "name": "Gap Analysis", "config": TASK_1},
    2: {"priority": "HIGH", "name": "Dual-Emit Layer", "config": TASK_2},
    3: {"priority": "HIGH", "name": "Operation Name", "config": TASK_3},
    4: {"priority": "MEDIUM", "name": "Provider/Model", "config": TASK_4},
    5: {"priority": "MEDIUM", "name": "Tool Mapping", "config": TASK_5},
    6: {"priority": "MEDIUM", "name": "Conversation ID", "config": TASK_6},
    7: {"priority": "HIGH", "name": "Documentation", "config": TASK_7},
}

DEFAULT_CONFIG = {
    "lead_agent": "anthropic:claude-sonnet-4-20250514",
    "drafter_agent": "openai:gpt-4o-mini",
    "max_iterations": 3,
    "pass_threshold": 80,
}

def main():
    workflow = LeadContractorWorkflow()
    results_dir = Path("results/otel-genai-adoption")
    results_dir.mkdir(parents=True, exist_ok=True)

    priority_filter = os.environ.get("PRIORITY")
    task_filter = os.environ.get("TASK")

    for task_id, task in TASKS.items():
        # Apply filters
        if task_filter and str(task_id) != task_filter:
            continue
        if priority_filter and task["priority"] != priority_filter:
            continue

        print(f"\n{'='*60}")
        print(f"Task {task_id}: {task['name']} ({task['priority']})")
        print(f"{'='*60}")

        config = {**DEFAULT_CONFIG, **task["config"]}
        result = workflow.run(config=config)

        # Save result
        output_file = results_dir / f"task-{task_id}-{task['name'].lower().replace(' ', '-')}.json"
        with open(output_file, "w") as f:
            json.dump({
                "task_id": task_id,
                "name": task["name"],
                "priority": task["priority"],
                "success": result.success,
                "output": result.output,
                "metrics": {
                    "total_cost": result.metrics.get("total_cost"),
                    "iterations": result.metadata.get("iterations"),
                    "final_score": result.metadata.get("final_score"),
                }
            }, f, indent=2)

        status = "✅ PASSED" if result.success else "❌ FAILED"
        print(f"\nResult: {status}")
        print(f"Cost: ${result.metrics.get('total_cost', 0):.4f}")
        print(f"Output: {output_file}")

if __name__ == "__main__":
    main()
