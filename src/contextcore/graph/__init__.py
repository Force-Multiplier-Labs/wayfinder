"""
Knowledge Graph module for ContextCore.

This module provides a knowledge graph representation of ProjectContext
relationships, enabling impact analysis, dependency visualization, and
cross-project intelligence.

Example:
    from contextcore.graph import GraphBuilder, GraphQueries

    # Build graph from ProjectContexts
    builder = GraphBuilder()
    graph = builder.build_from_contexts(contexts)

    # Query the graph
    queries = GraphQueries(graph)
    impact = queries.impact_analysis("my-project")
    print(f"Blast radius: {impact.total_blast_radius}")
"""

__all__ = [
    # Schema
    "NodeType",
    "EdgeType",
    "Node",
    "Edge",
    "Graph",
    # Builder
    "GraphBuilder",
    "GraphWatcher",
    # Queries
    "GraphQueries",
    "ImpactReport",
    "DependencyReport",
]


def __getattr__(name: str):
    """Lazy import for graph components."""
    if name in ("NodeType", "EdgeType", "Node", "Edge", "Graph"):
        from contextcore.graph.schema import NodeType, EdgeType, Node, Edge, Graph

        return {
            "NodeType": NodeType,
            "EdgeType": EdgeType,
            "Node": Node,
            "Edge": Edge,
            "Graph": Graph,
        }[name]

    if name in ("GraphBuilder", "GraphWatcher"):
        from contextcore.graph.builder import GraphBuilder, GraphWatcher

        return {"GraphBuilder": GraphBuilder, "GraphWatcher": GraphWatcher}[name]

    if name in ("GraphQueries", "ImpactReport", "DependencyReport"):
        from contextcore.graph.queries import GraphQueries, ImpactReport, DependencyReport

        return {
            "GraphQueries": GraphQueries,
            "ImpactReport": ImpactReport,
            "DependencyReport": DependencyReport,
        }[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
