"""Knowledge graph CLI commands.

This module provides CLI commands for building and querying the
ContextCore knowledge graph.
"""

__all__ = ["graph"]

import json
from typing import List, Dict, Any

import click


def list_all_project_contexts() -> List[Dict[str, Any]]:
    """Load all ProjectContexts from Kubernetes or local storage.

    Returns:
        List of ProjectContext dictionaries
    """
    contexts = []

    # Try Kubernetes first
    try:
        from kubernetes import client, config

        try:
            config.load_incluster_config()
        except Exception:
            config.load_kube_config()

        api = client.CustomObjectsApi()
        result = api.list_cluster_custom_object(
            group="contextcore.io",
            version="v1",
            plural="projectcontexts",
        )
        contexts = result.get("items", [])
    except Exception as e:
        click.echo(f"[graph] Could not load from Kubernetes: {e}", err=True)

    # Try local storage as fallback
    if not contexts:
        try:
            from contextcore.storage import get_storage

            storage = get_storage()
            contexts = storage.list_contexts()
        except Exception:
            pass

    if not contexts:
        click.echo(
            "[graph] No ProjectContexts found. Use 'contextcore sync' to load contexts.",
            err=True,
        )

    return contexts


@click.group()
def graph():
    """Knowledge graph commands."""
    pass


@graph.command("build")
@click.option(
    "--output", "-o", type=click.Path(), help="Output JSON file for graph export"
)
def graph_build_cmd(output: str):
    """Build knowledge graph from all ProjectContexts."""
    from contextcore.graph.builder import GraphBuilder

    contexts = list_all_project_contexts()
    if not contexts:
        return

    builder = GraphBuilder()
    g = builder.build_from_contexts(contexts)

    click.echo(f"Built graph with {len(g.nodes)} nodes and {len(g.edges)} edges")

    # Show summary by node type
    type_counts: Dict[str, int] = {}
    for node in g.nodes.values():
        type_counts[node.type.value] = type_counts.get(node.type.value, 0) + 1

    click.echo("\nNode types:")
    for node_type, count in sorted(type_counts.items()):
        click.echo(f"  {node_type}: {count}")

    if output:
        with open(output, "w") as f:
            json.dump(g.to_dict(), f, indent=2)
        click.echo(f"\nGraph exported to {output}")


@graph.command("impact")
@click.option("--project", "-p", required=True, help="Project ID to analyze")
@click.option("--depth", "-d", default=3, help="Max traversal depth")
def graph_impact_cmd(project: str, depth: int):
    """Analyze impact of changes to a project."""
    from contextcore.graph.builder import GraphBuilder
    from contextcore.graph.queries import GraphQueries

    contexts = list_all_project_contexts()
    if not contexts:
        return

    builder = GraphBuilder()
    g = builder.build_from_contexts(contexts)
    queries = GraphQueries(g)

    try:
        report = queries.impact_analysis(project, max_depth=depth)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        return

    click.echo(f"Impact Analysis: {project}")
    click.echo(f"  Affected Projects: {len(report.affected_projects)}")
    click.echo(f"  Critical Projects: {len(report.critical_projects)}")
    click.echo(f"  Affected Teams: {len(report.affected_teams)}")
    click.echo(f"  Blast Radius: {report.total_blast_radius}")

    if report.affected_projects:
        click.echo(f"\n  Projects: {', '.join(report.affected_projects)}")

    if report.affected_teams:
        click.echo(f"  Teams: {', '.join(report.affected_teams)}")

    if report.critical_projects:
        click.echo(
            f"\n  Warning: Critical projects affected: {', '.join(report.critical_projects)}"
        )


@graph.command("deps")
@click.option("--project", "-p", required=True, help="Project ID to query")
def graph_deps_cmd(project: str):
    """Show dependencies for a project."""
    from contextcore.graph.builder import GraphBuilder
    from contextcore.graph.queries import GraphQueries

    contexts = list_all_project_contexts()
    if not contexts:
        return

    builder = GraphBuilder()
    g = builder.build_from_contexts(contexts)
    queries = GraphQueries(g)

    deps = queries.get_dependencies(project)

    click.echo(f"Dependencies: {project}")
    click.echo(f"  Upstream (depends on): {', '.join(deps.upstream) or 'none'}")
    click.echo(f"  Downstream (depended by): {', '.join(deps.downstream) or 'none'}")
    click.echo(f"  Managed Resources: {', '.join(deps.shared_resources) or 'none'}")
    click.echo(f"  Implements ADRs: {', '.join(deps.shared_adrs) or 'none'}")


@graph.command("path")
@click.option("--from", "-f", "from_project", required=True, help="Source project ID")
@click.option("--to", "-t", "to_project", required=True, help="Target project ID")
def graph_path_cmd(from_project: str, to_project: str):
    """Find shortest path between two projects."""
    from contextcore.graph.builder import GraphBuilder
    from contextcore.graph.queries import GraphQueries

    contexts = list_all_project_contexts()
    if not contexts:
        return

    builder = GraphBuilder()
    g = builder.build_from_contexts(contexts)
    queries = GraphQueries(g)

    path = queries.find_path(from_project, to_project)

    if path:
        click.echo(f"Path from {from_project} to {to_project}:")
        click.echo(f"  {' -> '.join(path)}")
    else:
        click.echo(f"No path found between {from_project} and {to_project}")


@graph.command("risks")
@click.option("--team", "-t", required=True, help="Team name to analyze")
def graph_risks_cmd(team: str):
    """Show risk exposure for a team."""
    from contextcore.graph.builder import GraphBuilder
    from contextcore.graph.queries import GraphQueries

    contexts = list_all_project_contexts()
    if not contexts:
        return

    builder = GraphBuilder()
    g = builder.build_from_contexts(contexts)
    queries = GraphQueries(g)

    risks = queries.get_risk_exposure(team)
    projects = queries.get_projects_by_team(team)

    click.echo(f"Risk Exposure: {team}")
    click.echo(f"  Projects owned: {len(projects)}")
    if projects:
        click.echo(f"    {', '.join(projects)}")

    if risks:
        click.echo(f"\n  Risk types:")
        for risk_type, count in sorted(risks.items(), key=lambda x: -x[1]):
            click.echo(f"    {risk_type}: {count}")
    else:
        click.echo(f"\n  No risks found")


@graph.command("visualize")
@click.option("--output", "-o", required=True, type=click.Path(), help="Output JSON file")
@click.option("--format", "-f", "fmt", default="d3", help="Output format (d3, vis)")
def graph_visualize_cmd(output: str, fmt: str):
    """Export graph for visualization."""
    from contextcore.graph.builder import GraphBuilder
    from contextcore.graph.queries import GraphQueries

    contexts = list_all_project_contexts()
    if not contexts:
        return

    builder = GraphBuilder()
    g = builder.build_from_contexts(contexts)
    queries = GraphQueries(g)

    viz_data = queries.to_visualization_format()

    with open(output, "w") as f:
        json.dump(viz_data, f, indent=2)

    click.echo(f"Visualization data exported to {output}")
    click.echo(f"  Nodes: {len(viz_data['nodes'])}")
    click.echo(f"  Links: {len(viz_data['links'])}")
