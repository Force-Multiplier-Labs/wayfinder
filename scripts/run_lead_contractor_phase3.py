#!/usr/bin/env python3
"""
Run Lead Contractor Workflow for ContextCore Phase 3 Implementation.

This script uses the startd8 SDK's Lead Contractor workflow to implement
the Phase 3 strategic features from PHASE3_STRATEGIC.md.

Features:
- Feature 3.1: Project Knowledge Graph (Python)
- Feature 3.2: VSCode Extension (TypeScript) - Optional IDE integration
- Feature 3.3: Agent Learning Loop (Python)

Usage:
  python3 run_lead_contractor_phase3.py           # Run all features
  python3 run_lead_contractor_phase3.py 1-8       # Run Python features only
  python3 run_lead_contractor_phase3.py 9-16      # Run TypeScript features only
  python3 run_lead_contractor_phase3.py 9         # Run specific feature
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

# Add startd8 SDK to path (install startd8-sdk or set STARTD8_SDK_PATH)
_sdk_path = os.environ.get("STARTD8_SDK_PATH", os.path.expanduser("~/Documents/dev/startd8-sdk/src"))
sys.path.insert(0, _sdk_path)

from startd8.workflows.builtin.lead_contractor_workflow import LeadContractorWorkflow

# Feature 3.1: Project Knowledge Graph - Schema
FEATURE_3_1A_TASK = """
Implement the Knowledge Graph Schema module for ContextCore.

## Goal
Define the data models for a knowledge graph that represents ProjectContext relationships,
enabling impact analysis and cross-project intelligence.

## Context
- This is for the Wayfinder project (ContextCore reference implementation)
- The module should be placed at src/contextcore/graph/schema.py
- ContextCore uses Pydantic v2 for models, Python 3.9+
- ProjectContext CRD has: project (id, epic), business (criticality, value, owner, costCenter),
  targets (kind, name, namespace), design (adr, doc, apiContract), risks (type, priority, description)

## Requirements
1. Create NodeType enum with values: PROJECT, RESOURCE, TEAM, ADR, CONTRACT, RISK, REQUIREMENT, INSIGHT

2. Create EdgeType enum with values:
   - MANAGES: Project -> Resource
   - DEPENDS_ON: Project -> Project (inferred from targets)
   - OWNED_BY: Project -> Team
   - IMPLEMENTS: Project -> ADR
   - EXPOSES: Project -> Contract
   - HAS_RISK: Project -> Risk
   - HAS_REQUIREMENT: Project -> Requirement
   - GENERATED: Project -> Insight
   - CALLS: Resource -> Resource (from traces)

3. Create Node dataclass with:
   - id: str (unique identifier)
   - type: NodeType
   - name: str (display name)
   - attributes: Dict[str, Any] (arbitrary metadata)
   - created_at: datetime
   - updated_at: datetime
   - to_dict() method returning serializable dict

4. Create Edge dataclass with:
   - source_id: str
   - target_id: str
   - type: EdgeType
   - attributes: Dict[str, Any]
   - weight: float (default 1.0 for weighted algorithms)
   - to_dict() method

5. Create Graph dataclass with:
   - nodes: Dict[str, Node] (id -> Node mapping)
   - edges: List[Edge]
   - add_node(node: Node) -> None
   - add_edge(edge: Edge) -> None
   - get_node(node_id: str) -> Optional[Node]
   - get_edges_from(node_id: str) -> List[Edge]
   - get_edges_to(node_id: str) -> List[Edge]
   - to_dict() method returning {"nodes": [...], "edges": [...]}

## Output Format
Provide clean, production-ready Python code with:
- Proper type hints
- Docstrings for all classes and methods
- Standard library imports only (dataclasses, enum, typing, datetime)
- __all__ export list at the top
"""

# Feature 3.1: Project Knowledge Graph - Builder
FEATURE_3_1B_TASK = """
Implement the Knowledge Graph Builder module for ContextCore.

## Goal
Build a knowledge graph from ProjectContext CRDs, extracting nodes and edges
from the structured metadata.

## Context
- This is for the ContextCore project
- The module should be placed at src/contextcore/graph/builder.py
- It imports from contextcore.graph.schema: Graph, Node, Edge, NodeType, EdgeType
- ProjectContext structure:
  - metadata: {name, namespace}
  - spec.project: {id, epic} or string
  - spec.business: {criticality, value, owner, costCenter}
  - spec.targets: [{kind, name, namespace}]
  - spec.design: {adr, doc, apiContract}
  - spec.risks: [{type, priority, description, scope}]
  - spec.requirements: {availability, latencyP99, latencyP50, throughput}

## Requirements
1. Create GraphBuilder class with:
   - __init__(self): Initialize empty graph and resource-to-project mapping dict
   - graph: Graph instance
   - _resource_to_project: Dict[str, List[str]] for dependency inference

2. Implement build_from_contexts(contexts: List[Dict]) -> Graph:
   - Reset graph and mappings
   - Process each context
   - Infer dependencies after all contexts processed
   - Return the completed graph

3. Implement _process_context(ctx: Dict) -> None:
   - Extract metadata (name, namespace) and spec
   - Create PROJECT node with attributes (namespace, criticality, value, epic)
   - Create TEAM node from business.owner, add OWNED_BY edge
   - Create RESOURCE nodes for each target, add MANAGES edges
   - Track resource -> project mapping for dependency inference
   - Create ADR node from design.adr, add IMPLEMENTS edge
   - Create CONTRACT node from design.apiContract, add EXPOSES edge
   - Create RISK nodes for each risk, add HAS_RISK edges with priority-based weights

4. Helper methods:
   - _get_project_id(spec: Dict, default: str) -> str: Extract project ID from spec
   - _make_resource_id(target: Dict, default_ns: str) -> str: Create "resource:{ns}/{kind}/{name}"
   - _hash_url(url: str) -> str: MD5 hash first 12 chars for contract IDs
   - _risk_weight(priority: Optional[str]) -> float: P1=4.0, P2=3.0, P3=2.0, P4=1.0

5. Implement _infer_dependencies() -> None:
   - Find Service resources
   - (Placeholder for future trace-based inference)

6. Create GraphWatcher class (stub implementation):
   - __init__(builder: GraphBuilder)
   - start() -> None: Watch for CRD changes (placeholder using kubernetes client)
   - stop() -> None: Stop watching
   - _remove_context(ctx: Dict) -> None: Remove project from graph

## Output Format
Provide clean, production-ready Python code with:
- Proper type hints and docstrings
- Import hashlib for MD5 hashing
- Minimal kubernetes imports (just client, config, watch for stub)
- __all__ export list
"""

# Feature 3.1: Project Knowledge Graph - Queries
FEATURE_3_1C_TASK = """
Implement the Knowledge Graph Queries module for ContextCore.

## Goal
Provide query operations on the knowledge graph for impact analysis,
dependency discovery, and path finding.

## Context
- This is for the ContextCore project
- The module should be placed at src/contextcore/graph/queries.py
- It imports from contextcore.graph.schema: Graph, Node, Edge, NodeType, EdgeType
- Uses BFS traversal for graph queries

## Requirements
1. Create ImpactReport dataclass:
   - source_project: str
   - affected_projects: List[str]
   - affected_teams: List[str]
   - critical_projects: List[str] (criticality == "critical")
   - total_blast_radius: int
   - dependency_paths: List[List[str]] (paths showing impact propagation)

2. Create DependencyReport dataclass:
   - project_id: str
   - upstream: List[str] (projects this depends on)
   - downstream: List[str] (projects that depend on this)
   - shared_resources: List[str]
   - shared_adrs: List[str]

3. Create GraphQueries class with:
   - __init__(graph: Graph)
   - graph: Graph instance

4. Implement impact_analysis(project_id: str, max_depth: int = 5) -> ImpactReport:
   - Use BFS to find all reachable nodes through DEPENDS_ON and MANAGES edges
   - Track affected projects, teams, and critical projects
   - Record paths for visualization
   - Raise ValueError if project not found

5. Implement get_dependencies(project_id: str) -> DependencyReport:
   - Find upstream (DEPENDS_ON edges from this project)
   - Find downstream (DEPENDS_ON edges to this project)
   - Find shared resources (MANAGES edges)
   - Find shared ADRs (IMPLEMENTS edges)

6. Implement find_path(from_project: str, to_project: str) -> Optional[List[str]]:
   - Use BFS to find shortest path between two projects
   - Return None if no path exists or project not found

7. Implement get_risk_exposure(team: str) -> Dict[str, int]:
   - Find all projects owned by team (OWNED_BY edges to team)
   - Aggregate risk counts by type
   - Return {risk_type: count} dict

8. Implement to_visualization_format() -> Dict:
   - Return {"nodes": [...], "links": [...]} format for D3.js/vis.js
   - Nodes: {id, label, group, ...attributes}
   - Links: {source, target, type, value (weight)}

## Output Format
Provide clean, production-ready Python code with:
- Proper type hints and docstrings
- Use collections.deque for BFS queues
- __all__ export list
"""

# Feature 3.1: Knowledge Graph CLI
FEATURE_3_1D_TASK = """
Implement the Knowledge Graph CLI commands for ContextCore.

## Goal
Add CLI commands for building and querying the knowledge graph.

## Context
- This is for the ContextCore project
- The module should be placed at src/contextcore/cli/graph.py
- Uses Click for CLI, follows existing CLI patterns
- Imports from contextcore.graph.builder and contextcore.graph.queries

## Requirements
1. Create a Click group called "graph" with help text "Knowledge graph commands."

2. Implement "build" command:
   - @graph.command("build")
   - Option: --output/-o (optional file path for JSON export)
   - Load all ProjectContexts (use list_all_project_contexts helper or mock)
   - Build graph using GraphBuilder
   - Print summary: "Built graph with X nodes and Y edges"
   - If output specified, export graph to JSON file

3. Implement "impact" command:
   - @graph.command("impact")
   - Option: --project/-p (required, project ID to analyze)
   - Option: --depth/-d (default 3, max traversal depth)
   - Build graph from contexts
   - Run impact_analysis
   - Print formatted report:
     - Impact Analysis: {project}
     - Affected Projects: {count}
     - Critical Projects: {count}
     - Affected Teams: {count}
     - Blast Radius: {total}
     - Warning line for critical projects if any

4. Implement "deps" command:
   - @graph.command("deps")
   - Option: --project/-p (required, project ID)
   - Build graph from contexts
   - Run get_dependencies
   - Print formatted report:
     - Dependencies: {project}
     - Upstream (depends on): {list or 'none'}
     - Downstream (depended by): {list or 'none'}
     - Shared Resources: {list or 'none'}
     - Shared ADRs: {list or 'none'}

5. Implement "path" command:
   - @graph.command("path")
   - Option: --from/-f (required, source project)
   - Option: --to/-t (required, target project)
   - Build graph and run find_path
   - Print path or "No path found"

6. Helper: list_all_project_contexts() -> List[Dict]
   - Try to load from Kubernetes if available
   - Fall back to empty list with warning message

## Output Format
Provide clean, production-ready Python code with:
- Proper Click decorators and options
- import click at top
- __all__ export list
- Error handling with click.echo for user feedback
"""

# Feature 3.3: Agent Learning Loop - Models
FEATURE_3_3A_TASK = """
Implement the Agent Learning Models module for ContextCore.

## Goal
Define data models for the agent learning system that stores and retrieves
lessons learned during agent work sessions.

## Context
- This is for the ContextCore project
- The module should be placed at src/contextcore/learning/models.py
- Uses dataclasses and enums, Python 3.9+
- Lessons are stored as OpenTelemetry spans in Tempo

## Requirements
1. Create LessonCategory enum with values:
   - ARCHITECTURE, TESTING, DEBUGGING, PERFORMANCE, SECURITY
   - DEPLOYMENT, DOCUMENTATION, REFACTORING, ERROR_HANDLING, INTEGRATION

2. Create LessonSource enum with values:
   - BLOCKER_RESOLVED: Learned from fixing a blocker
   - ERROR_FIXED: Learned from fixing an error
   - PATTERN_DISCOVERED: Discovered a reusable pattern
   - REVIEW_FEEDBACK: Learned from code review
   - HUMAN_GUIDANCE: Human provided the lesson
   - DOCUMENTATION: Extracted from documentation

3. Create Lesson dataclass with:
   - id: str (unique identifier)
   - summary: str (1-2 sentence description)
   - category: LessonCategory
   - source: LessonSource
   - applies_to: List[str] (file patterns like "src/auth/**", "*.test.py")
   - project_id: Optional[str] (None for global lessons)
   - confidence: float (0.0-1.0)
   - validated_by_human: bool (default False)
   - success_count: int (times applied successfully, default 0)
   - failure_count: int (times didn't help, default 0)
   - context: str (extended description, default "")
   - code_example: Optional[str]
   - anti_pattern: Optional[str] (what NOT to do)
   - agent_id: str (default "")
   - trace_id: str (default "")
   - created_at: datetime
   - expires_at: Optional[datetime]
   - @property effectiveness_score: float (success_count / total * confidence, or just confidence if no usage)

4. Create LessonQuery dataclass with:
   - project_id: Optional[str]
   - file_pattern: Optional[str]
   - category: Optional[LessonCategory]
   - min_confidence: float (default 0.5)
   - include_global: bool (default True)
   - max_results: int (default 10)
   - time_range: str (default "30d", e.g., "1h", "7d", "30d")

5. Create LessonApplication dataclass with:
   - lesson_id: str
   - applied_at: datetime
   - context: str (where/how applied)
   - success: bool
   - feedback: Optional[str]

## Output Format
Provide clean, production-ready Python code with:
- Proper type hints and docstrings
- Default values using field(default_factory=...) for mutable defaults
- __all__ export list
"""

# Feature 3.3: Agent Learning Loop - Emitter
FEATURE_3_3B_TASK = """
Implement the Lesson Emitter module for ContextCore.

## Goal
Emit lessons as OpenTelemetry spans for storage in Tempo, enabling
persistent learning across agent sessions.

## Context
- This is for the ContextCore project
- The module should be placed at src/contextcore/learning/emitter.py
- Uses OpenTelemetry SDK for span creation
- Imports models from contextcore.learning.models

## Requirements
1. Create LessonEmitter class with:
   - __init__(project_id: str, agent_id: str, session_id: Optional[str] = None)
   - project_id, agent_id, session_id attributes
   - _tracer from trace.get_tracer("contextcore.learning")

2. Implement emit_lesson() method:
   - Parameters: summary, category (LessonCategory), source (LessonSource),
     applies_to (List[str]), confidence (float), context (str),
     code_example (Optional[str]), anti_pattern (Optional[str]),
     global_lesson (bool)
   - Create span with name "lesson.emit", kind=SpanKind.INTERNAL
   - Set span attributes:
     - insight.type = "lesson"
     - lesson.id, lesson.summary, lesson.category, lesson.source
     - lesson.applies_to (as list), lesson.is_global
     - lesson.confidence, lesson.context, lesson.code_example, lesson.anti_pattern
     - project.id (if not global), agent.id, agent.session_id
   - Add event "lesson_created"
   - Return Lesson object

3. Implement convenience methods:
   - emit_blocker_resolution(blocker_summary, resolution, applies_to, confidence=0.9) -> Lesson
   - emit_pattern_discovery(pattern_name, description, applies_to, code_example, anti_pattern) -> Lesson

4. Implement record_application(lesson_id, success, context, feedback) -> None:
   - Create span "lesson.applied"
   - Set attributes: lesson.id, lesson.applied, lesson.success, lesson.application_context, lesson.feedback

## Output Format
Provide clean, production-ready Python code with:
- from opentelemetry import trace
- from opentelemetry.trace import SpanKind
- Proper type hints and docstrings
- __all__ export list
"""

# Feature 3.3: Agent Learning Loop - Retriever
FEATURE_3_3C_TASK = """
Implement the Lesson Retriever module for ContextCore.

## Goal
Query lessons from Tempo using TraceQL for agent work sessions,
enabling continuous learning from past experiences.

## Context
- This is for the ContextCore project
- The module should be placed at src/contextcore/learning/retriever.py
- Uses HTTP requests to Tempo's API
- Imports models from contextcore.learning.models

## Requirements
1. Create LessonRetriever class with:
   - __init__(tempo_url: str = "http://localhost:3200")
   - tempo_url attribute (strip trailing slash)

2. Implement retrieve(query: LessonQuery) -> List[Lesson]:
   - Build TraceQL query from LessonQuery
   - Execute query against Tempo
   - Parse results into Lesson objects
   - Filter by min_confidence
   - Sort by effectiveness_score descending
   - Return top max_results

3. Implement convenience methods:
   - get_lessons_for_file(file_path, project_id, category) -> List[Lesson]
   - get_lessons_for_task(task_type, project_id) -> List[Lesson]
     (Map task types to categories: testing->TESTING, debugging->DEBUGGING, etc.)
   - get_global_lessons(category, min_confidence=0.9) -> List[Lesson]

4. Implement _build_traceql(query: LessonQuery) -> str:
   - Start with: span.insight.type = "lesson"
   - Add project.id condition if specified (or include global)
   - Add category condition if specified
   - Add file pattern regex matching for applies_to
   - Return "{ condition1 && condition2 && ... }"

5. Implement _query_tempo(traceql: str, time_range: str) -> List[dict]:
   - Parse time_range to start/end timestamps
   - Make GET request to {tempo_url}/api/search with q, start, end params
   - Return traces list from response

6. Implement _parse_results(raw_results: List[dict]) -> List[Lesson]:
   - Extract spans from traces
   - Parse attributes into Lesson objects
   - Handle applies_to as JSON string

7. Implement _parse_time_range(time_range: str) -> timedelta:
   - Parse "1h", "7d", "30d", "1m" (m=30 days)
   - Default to 7 days

## Output Format
Provide clean, production-ready Python code with:
- Use urllib.request for HTTP (standard library)
- import json for parsing
- Proper error handling with try/except
- __all__ export list
"""

# Feature 3.3: Agent Learning Loop - Integration
FEATURE_3_3D_TASK = """
Implement the Learning Loop Integration module for ContextCore.

## Goal
Provide a high-level integration class that agents use for the complete
learning loop: query lessons before tasks, emit lessons after tasks.

## Context
- This is for the ContextCore project
- The module should be placed at src/contextcore/learning/loop.py
- Imports from contextcore.learning.emitter and contextcore.learning.retriever
- Designed for easy integration into agent workflows

## Requirements
1. Create LearningLoop class with:
   - __init__(project_id: str, agent_id: str, tempo_url: str = "http://localhost:3200")
   - project_id attribute
   - emitter: LessonEmitter instance
   - retriever: LessonRetriever instance

2. Implement before_task(task_type: str, files: Optional[List[str]], custom_query: Optional[Callable]) -> List[Lesson]:
   - Get task-type lessons
   - Get file-specific lessons for each file
   - Get high-confidence global lessons
   - Deduplicate by lesson.id
   - Sort by effectiveness_score descending
   - Return top 10 lessons

3. Implement after_task methods:
   - after_task_blocker(blocker: str, resolution: str, affected_files: List[str], confidence=0.9) -> Lesson
   - after_task_discovery(pattern_name: str, description: str, affected_files: List[str], code_example: str, anti_pattern: Optional[str]) -> Lesson
   - after_task_general(summary: str, category: LessonCategory, affected_files: List[str], context: str, is_global: bool) -> Lesson

4. Implement feedback methods:
   - record_lesson_success(lesson_id: str, context: str) -> None
   - record_lesson_failure(lesson_id: str, context: str, feedback: str) -> None

5. Include docstring with usage example:
   ```
   loop = LearningLoop(project_id="my-project", agent_id="claude-code")

   # Before starting work
   lessons = loop.before_task(task_type="testing", files=["src/auth/oauth.py"])
   for lesson in lessons:
       print(f"Tip: {lesson.summary}")

   # After completing work
   if encountered_blocker:
       loop.after_task_blocker(
           blocker="OAuth token refresh failed in tests",
           resolution="Mock the token refresh endpoint in conftest.py",
           affected_files=["tests/conftest.py", "src/auth/oauth.py"]
       )
   ```

## Output Format
Provide clean, production-ready Python code with:
- Proper type hints and docstrings
- Clear usage documentation
- __all__ export list
"""

# =============================================================================
# Feature 3.2: VSCode Extension (TypeScript)
# =============================================================================

FEATURE_3_2A_TASK = """
Create the VSCode extension project scaffolding for ContextCore.

## Goal
Set up a complete VSCode extension project structure with all necessary
configuration files, ready for TypeScript development.

## Context
- Extension will be at extensions/vscode/ within the ContextCore repo
- Extension name: contextcore-vscode
- Display name: ContextCore
- Publisher: contextcore (placeholder)
- Minimum VSCode version: 1.85.0

## Requirements

1. Create package.json with:
   - name: "contextcore-vscode"
   - displayName: "ContextCore"
   - description: "ProjectContext awareness in your editor"
   - version: "0.1.0"
   - engines.vscode: "^1.85.0"
   - categories: ["Other", "Visualization"]
   - activationEvents: ["workspaceContains:**/.contextcore", "workspaceContains:**/projectcontext.yaml"]
   - main: "./out/extension.js"
   - contributes:
     - configuration (contextcore.kubeconfig, contextcore.namespace, contextcore.showInlineHints, contextcore.refreshInterval)
     - viewsContainers.activitybar (contextcore icon)
     - views.contextcore (projectView, risksView, requirementsView)
     - commands (contextcore.refresh, contextcore.showImpact, contextcore.openDashboard, contextcore.showRisks)
   - scripts: compile, watch, package, lint, test
   - devDependencies: typescript, @types/vscode, @types/node, eslint, @typescript-eslint/parser, @typescript-eslint/eslint-plugin, vsce
   - dependencies: yaml, @kubernetes/client-node

2. Create tsconfig.json with:
   - target: ES2020
   - module: commonjs
   - lib: ["ES2020"]
   - outDir: "./out"
   - rootDir: "./src"
   - strict: true
   - esModuleInterop: true
   - skipLibCheck: true
   - forceConsistentCasingInFileNames: true

3. Create .vscodeignore with: .vscode, node_modules, src, .gitignore, tsconfig.json, *.map

4. Create .eslintrc.json with TypeScript rules

5. Create README.md documenting features, installation, and configuration

## Output Format
Provide complete file contents. Use proper JSON formatting for config files.
"""

FEATURE_3_2B_TASK = """
Implement the core infrastructure for the ContextCore VSCode extension.

## Goal
Create the extension entry point and foundational utilities that all
other modules depend on.

## Context
- TypeScript extension for VSCode
- Located at extensions/vscode/src/
- Must handle activation and deactivation cleanly
- Should support multiple workspace folders

## Requirements

1. Create src/extension.ts:
   - import * as vscode from 'vscode'
   - export function activate(context: vscode.ExtensionContext): void
   - export function deactivate(): void
   - Initialize logger first
   - Log "ContextCore extension activated"
   - Register disposables with context.subscriptions

2. Create src/types.ts with TypeScript interfaces matching Python models:
   - ProjectContext { metadata: ProjectMetadata; spec: ProjectContextSpec }
   - ProjectMetadata { name: string; namespace: string }
   - ProjectContextSpec { project, business, requirements, risks, targets, design }
   - BusinessContext { criticality?: string; value?: string; owner?: string; costCenter?: string }
   - Requirements { availability?: string; latencyP99?: string; latencyP50?: string; throughput?: string; errorBudget?: string }
   - Risk { type: string; priority: string; description: string; scope?: string; mitigation?: string }
   - Target { kind: string; name: string; namespace?: string }
   - Design { adr?: string; doc?: string; apiContract?: string }

3. Create src/config.ts:
   - function getConfig<T>(key: string, defaultValue?: T): T
   - function onConfigChange(callback: () => void): vscode.Disposable
   - Export configuration keys as constants

4. Create src/logger.ts:
   - Create output channel named "ContextCore"
   - export function log(message: string, level?: 'info' | 'warn' | 'error'): void
   - export function showError(message: string): void (also shows notification)

## Output Format
Provide clean TypeScript with proper types, JSDoc comments, and ES module exports.
"""

FEATURE_3_2C_TASK = """
Implement the context provider system for loading ProjectContext data.

## Goal
Create a provider system that loads ProjectContext from multiple sources
with caching and automatic refresh.

## Context
- TypeScript for VSCode extension
- Must support: local .contextcore files, CLI commands, K8s API
- Should gracefully degrade if sources unavailable
- Uses async/await for all I/O

## Requirements

1. Create src/providers/contextProvider.ts:
   - export class ContextProvider implements vscode.Disposable
   - constructor()
   - async getContext(workspaceFolder: vscode.WorkspaceFolder): Promise<ProjectContext | undefined>
   - async refresh(): Promise<void>
   - readonly onContextChange: vscode.Event<ProjectContext | undefined>
   - dispose(): void
   - Try sources in order: local file -> CLI -> K8s

2. Create src/providers/localConfigProvider.ts:
   - export async function loadLocalConfig(workspaceFolder: vscode.WorkspaceFolder): Promise<ProjectContext | undefined>
   - Look for .contextcore or .contextcore.yaml in workspace root
   - Parse YAML using 'yaml' package
   - Return undefined if file not found

3. Create src/providers/cliProvider.ts:
   - export async function loadFromCli(workspaceFolder: vscode.WorkspaceFolder): Promise<ProjectContext | undefined>
   - Execute: contextcore context show --format json
   - Use child_process.exec with Promise wrapper
   - Parse JSON output
   - Return undefined if command fails

4. Create src/providers/kubernetesProvider.ts:
   - export async function loadFromKubernetes(name: string, namespace: string): Promise<ProjectContext | undefined>
   - Use @kubernetes/client-node
   - Load kubeconfig from default location or config
   - Fetch ProjectContext CRD
   - Return undefined if not available (don't throw)

5. Create src/cache.ts:
   - export class Cache<T>
   - get(key: string): T | undefined
   - set(key: string, value: T, ttlMs?: number): void
   - invalidate(key: string): void
   - clear(): void
   - Default TTL from config (contextcore.refreshInterval * 1000)

## Output Format
Provide TypeScript with async/await, proper error handling, and vscode.Disposable pattern.
"""

FEATURE_3_2D_TASK = """
Implement file-to-context mapping for the VSCode extension.

## Goal
Map workspace files to their relevant ProjectContext based on configuration,
risk scopes, and target patterns.

## Context
- A workspace may have multiple ProjectContexts (multi-root)
- Files can match via: .contextcore config, risk.scope patterns
- Should efficiently handle large workspaces
- Cache mappings for performance

## Requirements

1. Create src/mapping/contextMapper.ts:
   - export class ContextMapper implements vscode.Disposable
   - constructor(contextProvider: ContextProvider)
   - async initialize(): Promise<void>
   - getContextForFile(uri: vscode.Uri): ProjectContext | undefined
   - getContextForDocument(document: vscode.TextDocument): ProjectContext | undefined
   - dispose(): void
   - Listen for workspace folder changes

2. Create src/mapping/patternMatcher.ts:
   - export function matchesPattern(filePath: string, pattern: string): boolean
   - Support glob patterns: * (single segment), ** (any depth), ? (single char)
   - Support negation with ! prefix
   - Normalize path separators

3. Create src/mapping/workspaceScanner.ts:
   - export async function findContextFiles(folder: vscode.WorkspaceFolder): Promise<vscode.Uri[]>
   - Use vscode.workspace.findFiles
   - Look for .contextcore, .contextcore.yaml, projectcontext.yaml

4. Mapping priority (implement in contextMapper):
   - Check if file path matches any risk.scope pattern
   - Check closest parent directory with .contextcore
   - Fall back to workspace root context

## Output Format
Provide TypeScript with efficient caching and proper VSCode API usage.
"""

FEATURE_3_2E_TASK = """
Implement the status bar component showing project criticality.

## Goal
Display current file's project context and criticality in the VSCode
status bar, with quick access to more details.

## Context
- Status bar items appear at bottom of VSCode window
- Should update when active editor changes
- Click should show quick pick menu

## Requirements

1. Create src/ui/statusBar.ts:
   - export class ContextStatusBar implements vscode.Disposable
   - constructor(contextMapper: ContextMapper)
   - private statusBarItem: vscode.StatusBarItem
   - update(editor: vscode.TextEditor | undefined): void
   - dispose(): void
   - Register for onDidChangeActiveTextEditor

2. Status bar display:
   - Icon based on criticality:
     - critical: $(flame)
     - high: $(warning)
     - medium: $(info)
     - low: $(check)
     - unknown: $(question)
   - Text: project ID (truncate if > 20 chars)
   - Background: statusBarItem.errorBackground for critical, warningBackground for high
   - Tooltip: MarkdownString with project details

3. Create src/ui/statusBarTooltip.ts:
   - export function buildTooltip(context: ProjectContext): vscode.MarkdownString
   - Include: project ID, criticality, owner, risk count, requirements summary
   - Use markdown formatting

4. Click action (command: contextcore.statusBarClick):
   - Show quick pick with options:
     - "$(eye) Show Full Context" -> reveal side panel
     - "$(graph) Show Impact Analysis" -> run showImpact command
     - "$(link-external) Open in Grafana" -> run openDashboard command
     - "$(warning) Show Risks" -> run showRisks command

## Output Format
Provide TypeScript using vscode.window.createStatusBarItem with StatusBarAlignment.Right.
"""

FEATURE_3_2F_TASK = """
Implement the side panel tree view for full context display.

## Goal
Create an activity bar view that shows the complete ProjectContext
as an expandable tree with projects, risks, and requirements.

## Context
- Activity bar icon appears in left sidebar
- Tree view shows hierarchical data
- Should refresh when context changes

## Requirements

1. Create src/ui/sidePanel/projectTreeProvider.ts:
   - export class ProjectTreeProvider implements vscode.TreeDataProvider<ContextTreeItem>
   - constructor(contextMapper: ContextMapper)
   - getTreeItem(element: ContextTreeItem): vscode.TreeItem
   - getChildren(element?: ContextTreeItem): ContextTreeItem[]
   - refresh(): void
   - private _onDidChangeTreeData: vscode.EventEmitter<ContextTreeItem | undefined>
   - readonly onDidChangeTreeData: vscode.Event<ContextTreeItem | undefined>

2. Create src/ui/sidePanel/contextTreeItem.ts:
   - export class ContextTreeItem extends vscode.TreeItem
   - constructor(label: string, collapsibleState: vscode.TreeItemCollapsibleState, type: TreeItemType)
   - Export TreeItemType enum: Project, Section, Risk, Requirement, Target, Property
   - contextValue for context menu matching

3. Tree structure when expanded:
   - Project node (collapsible)
     - Business section (collapsible)
       - Criticality: <value>
       - Owner: <value>
       - Value: <value>
     - Risks section (collapsible) with count badge
       - Each risk with priority icon (P1 red, P2 orange, P3 yellow, P4 blue)
     - Requirements section (collapsible)
       - Availability: <value>
       - Latency P99: <value>
       - Throughput: <value>
     - Targets section (collapsible)
       - Each target with kind icon

4. Icons:
   - Project: $(package)
   - Business: $(organization)
   - Risks: $(warning)
   - Requirements: $(graph)
   - Targets: $(symbol-class)

## Output Format
Provide TypeScript using vscode.window.registerTreeDataProvider API.
"""

FEATURE_3_2G_TASK = """
Implement editor decorations for inline SLO hints.

## Goal
Show SLO requirements as inline hints near relevant code patterns
(HTTP handlers, database queries, external calls).

## Context
- Decorations appear after line content
- Should be subtle (gray, italic)
- Can be toggled via contextcore.showInlineHints config

## Requirements

1. Create src/ui/decorations/decorationProvider.ts:
   - export class DecorationProvider implements vscode.Disposable
   - constructor(contextMapper: ContextMapper)
   - private sloDecorationType: vscode.TextEditorDecorationType
   - private riskDecorationType: vscode.TextEditorDecorationType
   - updateDecorations(editor: vscode.TextEditor): void
   - dispose(): void
   - Register for onDidChangeActiveTextEditor, onDidChangeTextEditorSelection

2. Create src/ui/decorations/sloDecorations.ts:
   - export function findHttpHandlers(document: vscode.TextDocument): vscode.Range[]
   - Patterns for Python: def get_, def post_, @app.route, async def handle
   - Patterns for TypeScript: app.get(, app.post(, router.get(, async function handle
   - Patterns for Go: func.*Handler, http.HandleFunc
   - export function buildSloDecoration(requirements: Requirements): vscode.DecorationOptions[]

3. SLO decoration style:
   - after.contentText: "// SLO: P99 < {latencyP99}"
   - after.color: new ThemeColor('editorCodeLens.foreground')
   - after.fontStyle: 'italic'
   - after.margin: '0 0 0 2em'

4. Create src/ui/decorations/riskDecorations.ts:
   - export function isFileInRiskScope(filePath: string, risks: Risk[]): Risk | undefined
   - Gutter decoration for files in risk scope
   - gutterIconPath based on priority (P1 red circle, P2 orange, P3 yellow)

5. Respect configuration:
   - Check contextcore.showInlineHints before applying decorations
   - Listen for config changes and update

## Output Format
Provide TypeScript using vscode.window.createTextEditorDecorationType API.
"""

FEATURE_3_2H_TASK = """
Implement extension commands and final integration.

## Goal
Create user-facing commands and wire everything together in the
main extension activation.

## Context
- Commands appear in command palette (Ctrl+Shift+P / Cmd+Shift+P)
- Should integrate with contextcore CLI where possible
- Provide quick access to common actions

## Requirements

1. Create src/commands/refreshContext.ts:
   - export function createRefreshCommand(contextProvider: ContextProvider): vscode.Disposable
   - Command ID: contextcore.refresh
   - Invalidate cache and reload all contexts
   - Show information message on completion

2. Create src/commands/showImpact.ts:
   - export function createShowImpactCommand(contextMapper: ContextMapper): vscode.Disposable
   - Command ID: contextcore.showImpact
   - Get current context, run: contextcore graph impact --project <id>
   - Display results in new webview panel or output channel
   - Show blast radius and affected projects

3. Create src/commands/openDashboard.ts:
   - export function createOpenDashboardCommand(contextMapper: ContextMapper): vscode.Disposable
   - Command ID: contextcore.openDashboard
   - Build Grafana URL: {grafanaUrl}/d/contextcore-project?var-project={projectId}
   - Get grafanaUrl from config (default: http://localhost:3000)
   - Open in external browser with vscode.env.openExternal

4. Create src/commands/showRisks.ts:
   - export function createShowRisksCommand(contextMapper: ContextMapper): vscode.Disposable
   - Command ID: contextcore.showRisks
   - Show quick pick with all risks for current context
   - Group by priority with icons
   - Select risk to show details in notification

5. Update src/extension.ts activate():
   - Create ContextProvider
   - Create ContextMapper with provider
   - Initialize mapper
   - Create and register ContextStatusBar
   - Register ProjectTreeProvider with vscode.window.registerTreeDataProvider
   - Create and register DecorationProvider
   - Register all commands
   - Register configuration change listener
   - Add all disposables to context.subscriptions
   - Log completion

## Output Format
Provide TypeScript with proper command registration, error handling, and disposable pattern.
"""


# =============================================================================
# Workflow Functions
# =============================================================================

TYPESCRIPT_CONTEXT = {
    "language": "TypeScript 5.0+",
    "framework": "VSCode Extension API",
    "project": "ContextCore VSCode Extension",
    "style": "ESLint, strict TypeScript, JSDoc comments"
}

PYTHON_CONTEXT = {
    "language": "Python 3.9+",
    "framework": "Click CLI, Pydantic v2, OpenTelemetry SDK",
    "project": "ContextCore",
    "style": "PEP 8, type hints, docstrings, dataclasses"
}


def run_workflow(task_description: str, feature_name: str, context: dict = None) -> dict:
    """Run Lead Contractor workflow for a feature."""
    print(f"\n{'='*60}")
    print(f"Running Lead Contractor for: {feature_name}")
    print(f"{'='*60}\n")

    workflow = LeadContractorWorkflow()

    config = {
        "task_description": task_description,
        "context": context or {
            "language": "Python 3.9+",
            "framework": "Click CLI, Pydantic v2, OpenTelemetry SDK",
            "project": "ContextCore",
            "style": "PEP 8, type hints, docstrings, dataclasses"
        },
        "lead_agent": "anthropic:claude-sonnet-4-20250514",
        "drafter_agent": "openai:gpt-4o-mini",
        "max_iterations": 3,
        "pass_threshold": 80,
        "integration_instructions": """
        Finalize the code for production use:
        1. Ensure all imports are at the top
        2. Add proper __all__ export list
        3. Verify type hints are complete
        4. Add inline comments for complex logic
        5. Ensure the code is self-contained and can be dropped into the project
        6. Use only standard library imports unless specified otherwise
        """
    }

    result = workflow.run(config=config)

    return {
        "feature": feature_name,
        "success": result.success,
        "final_implementation": result.output.get("final_implementation", ""),
        "summary": result.output.get("summary", {}),
        "error": result.error,
        "total_cost": result.metrics.total_cost if result.metrics else 0,
        "total_iterations": result.metadata.get("total_iterations", 0),
    }


def extract_code_blocks(text: str, language: str = "python") -> str:
    """Extract code from markdown code blocks."""
    import re

    # Try language-specific code blocks first
    pattern = rf'```{language}\n(.*?)```'
    matches = re.findall(pattern, text, re.DOTALL)
    if matches:
        return "\n\n".join(matches)

    # Try typescript/ts variants
    if language in ("typescript", "ts"):
        for lang in ("typescript", "ts"):
            pattern = rf'```{lang}\n(.*?)```'
            matches = re.findall(pattern, text, re.DOTALL)
            if matches:
                return "\n\n".join(matches)

    # Try json for config files
    if language == "json":
        pattern = r'```json\n(.*?)```'
        matches = re.findall(pattern, text, re.DOTALL)
        if matches:
            return "\n\n".join(matches)

    # Try generic code blocks
    pattern = r'```\n(.*?)```'
    matches = re.findall(pattern, text, re.DOTALL)
    if matches:
        return "\n\n".join(matches)

    return text


def save_result(result: dict, output_dir: Path, is_typescript: bool = False):
    """Save workflow result to files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    feature_slug = result['feature'].replace(' ', '_').lower()

    # Save full result as JSON
    result_file = output_dir / f"{feature_slug}_result.json"
    with open(result_file, 'w') as f:
        json.dump({
            "feature": result["feature"],
            "success": result["success"],
            "summary": result["summary"],
            "error": result["error"],
            "total_cost": result["total_cost"],
            "total_iterations": result["total_iterations"],
        }, f, indent=2)

    # Save implementation code with appropriate extension
    if is_typescript:
        code_file = output_dir / f"{feature_slug}_code.ts"
        code = extract_code_blocks(result["final_implementation"], "typescript")
    else:
        code_file = output_dir / f"{feature_slug}_code.py"
        code = extract_code_blocks(result["final_implementation"], "python")

    with open(code_file, 'w') as f:
        f.write(code)

    print(f"Saved result to: {result_file}")
    print(f"Saved code to: {code_file}")


def main():
    """Run Lead Contractor workflow for Phase 3 features."""
    output_dir = Path(__file__).resolve().parent.parent / "generated" / "phase3"

    # Each feature tuple: (task, name, context, is_typescript)
    features = [
        # Feature 3.1: Knowledge Graph (Python)
        (FEATURE_3_1A_TASK, "Feature_3_1A_Graph_Schema", PYTHON_CONTEXT, False),
        (FEATURE_3_1B_TASK, "Feature_3_1B_Graph_Builder", PYTHON_CONTEXT, False),
        (FEATURE_3_1C_TASK, "Feature_3_1C_Graph_Queries", PYTHON_CONTEXT, False),
        (FEATURE_3_1D_TASK, "Feature_3_1D_Graph_CLI", PYTHON_CONTEXT, False),
        # Feature 3.3: Agent Learning Loop (Python)
        (FEATURE_3_3A_TASK, "Feature_3_3A_Learning_Models", PYTHON_CONTEXT, False),
        (FEATURE_3_3B_TASK, "Feature_3_3B_Learning_Emitter", PYTHON_CONTEXT, False),
        (FEATURE_3_3C_TASK, "Feature_3_3C_Learning_Retriever", PYTHON_CONTEXT, False),
        (FEATURE_3_3D_TASK, "Feature_3_3D_Learning_Loop", PYTHON_CONTEXT, False),
        # Feature 3.2: VSCode Extension (TypeScript)
        (FEATURE_3_2A_TASK, "Feature_3_2A_VSCode_Scaffolding", TYPESCRIPT_CONTEXT, True),
        (FEATURE_3_2B_TASK, "Feature_3_2B_VSCode_Core", TYPESCRIPT_CONTEXT, True),
        (FEATURE_3_2C_TASK, "Feature_3_2C_VSCode_ContextProvider", TYPESCRIPT_CONTEXT, True),
        (FEATURE_3_2D_TASK, "Feature_3_2D_VSCode_ContextMapper", TYPESCRIPT_CONTEXT, True),
        (FEATURE_3_2E_TASK, "Feature_3_2E_VSCode_StatusBar", TYPESCRIPT_CONTEXT, True),
        (FEATURE_3_2F_TASK, "Feature_3_2F_VSCode_SidePanel", TYPESCRIPT_CONTEXT, True),
        (FEATURE_3_2G_TASK, "Feature_3_2G_VSCode_Decorations", TYPESCRIPT_CONTEXT, True),
        (FEATURE_3_2H_TASK, "Feature_3_2H_VSCode_Commands", TYPESCRIPT_CONTEXT, True),
    ]

    # Check which feature to run (can pass index as argument)
    if len(sys.argv) > 1:
        try:
            arg = sys.argv[1]

            # Support running ranges like "1-8" for Python features
            if "-" in arg:
                start, end = arg.split("-")
                start_idx = int(start) - 1
                end_idx = int(end)
                if 0 <= start_idx < len(features) and end_idx <= len(features):
                    features = features[start_idx:end_idx]
                else:
                    print(f"Invalid range. Use 1-{len(features)}")
                    sys.exit(1)
            else:
                idx = int(arg) - 1
                if 0 <= idx < len(features):
                    features = [features[idx]]
                else:
                    print(f"Invalid feature index. Use 1-{len(features)}")
                    sys.exit(1)
        except ValueError:
            print("Usage: python3 run_lead_contractor_phase3.py [feature_number|range]")
            print("\nExamples:")
            print("  python3 run_lead_contractor_phase3.py 1      # Run feature 1")
            print("  python3 run_lead_contractor_phase3.py 1-8    # Run Python features")
            print("  python3 run_lead_contractor_phase3.py 9-16   # Run TypeScript features")
            print("\nFeatures:")
            print("\n  Python (Core SDK):")
            for i, (_, name, _, is_ts) in enumerate(features, 1):
                if not is_ts:
                    print(f"    {i}. {name}")
            print("\n  TypeScript (VSCode Extension):")
            for i, (_, name, _, is_ts) in enumerate(features, 1):
                if is_ts:
                    print(f"    {i}. {name}")
            sys.exit(1)

    results = []
    for task, name, context, is_typescript in features:
        try:
            result = run_workflow(task, name, context)
            results.append(result)
            save_result(result, output_dir, is_typescript)

            print(f"\n{name} Result:")
            print(f"  Success: {result['success']}")
            print(f"  Iterations: {result['total_iterations']}")
            print(f"  Cost: ${result['total_cost']:.4f}")
            if result['error']:
                print(f"  Error: {result['error']}")
        except Exception as e:
            print(f"Error running {name}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'='*60}")
    print("All workflows complete")
    print(f"{'='*60}")

    total_cost = sum(r['total_cost'] for r in results)
    print(f"Total cost: ${total_cost:.4f}")


if __name__ == "__main__":
    main()
