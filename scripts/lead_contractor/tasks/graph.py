"""
Knowledge Graph feature tasks for Lead Contractor workflow.
"""

from ..runner import Feature

GRAPH_SCHEMA_TASK = """
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

GRAPH_BUILDER_TASK = """
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

GRAPH_QUERIES_TASK = """
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

GRAPH_CLI_TASK = """
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

GRAPH_FEATURES = [
    Feature(
        task=GRAPH_SCHEMA_TASK,
        name="Graph_Schema",
        output_subdir="graph",
    ),
    Feature(
        task=GRAPH_BUILDER_TASK,
        name="Graph_Builder",
        output_subdir="graph",
    ),
    Feature(
        task=GRAPH_QUERIES_TASK,
        name="Graph_Queries",
        output_subdir="graph",
    ),
    Feature(
        task=GRAPH_CLI_TASK,
        name="Graph_CLI",
        output_subdir="graph",
    ),
]
