"""ContextCore CLI - PR Review commands."""

import json
import sys
from pathlib import Path
from typing import Optional

import click
import yaml


def _get_project_context_spec(project: str, namespace: str = "default") -> Optional[dict]:
    """Fetch ProjectContext spec from Kubernetes cluster or local file."""
    import subprocess

    # Check if it's a file path
    if Path(project).exists():
        with open(project) as f:
            data = yaml.safe_load(f)
        return data.get("spec", data)

    # Try Kubernetes
    if "/" in project:
        namespace, name = project.split("/", 1)
    else:
        name = project

    cmd = ["kubectl", "get", "projectcontext", name, "-n", namespace, "-o", "json"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None

    pc = json.loads(result.stdout)
    return pc.get("spec", {})


@click.group()
def review():
    """PR review guidance commands."""
    pass


@review.command("pr")
@click.option("--project", "-p", required=True, help="Project ID or path to ProjectContext YAML")
@click.option("--pr-number", required=True, type=int, help="PR number")
@click.option("--files", required=True, help="Comma-separated list of changed files")
@click.option("--output", "-o", type=click.Path(), help="Output markdown file")
@click.option("--json", "json_output", type=click.Path(), help="Output JSON metadata file")
@click.option("--namespace", "-n", default="default", help="Kubernetes namespace")
def review_pr_cmd(
    project: str,
    pr_number: int,
    files: str,
    output: Optional[str],
    json_output: Optional[str],
    namespace: str,
):
    """Generate review guidance for a PR based on ProjectContext risks.

    Analyzes changed files against ProjectContext risk definitions and generates
    a markdown report with:
    - Review priority based on highest-priority applicable risk
    - Risk-specific checklists
    - Suggested reviewers for P1/P2 risks
    - General checklist based on file types

    Example:
        contextcore review pr --project checkout-service --pr-number 123 \\
            --files "src/api/auth.py,src/models/user.py"
    """
    from contextcore.integrations.github_review import PRReviewAnalyzer

    spec = _get_project_context_spec(project, namespace)
    if not spec:
        click.echo(f"Error: ProjectContext '{project}' not found", err=True)
        sys.exit(1)

    # Parse file list
    changed_files = [f.strip() for f in files.split(",") if f.strip()]
    if not changed_files:
        click.echo("Error: No files specified", err=True)
        sys.exit(1)

    # Analyze PR
    analyzer = PRReviewAnalyzer()
    guidance = analyzer.analyze(pr_number, changed_files, spec)

    # Output markdown
    markdown = guidance.to_markdown()
    if output:
        with open(output, "w") as f:
            f.write(markdown)
        click.echo(f"Review guidance written to {output}")
    else:
        click.echo(markdown)

    # Output JSON metadata
    if json_output:
        metadata = {
            "pr_number": guidance.pr_number,
            "project_id": guidance.project_id,
            "overall_priority": guidance.overall_priority.value,
            "focus_areas": [
                {"area": f.area, "priority": f.priority.value}
                for f in guidance.focus_areas
            ],
            "warning_count": len(guidance.warnings),
            "checklist_count": len(guidance.auto_checklist),
        }
        with open(json_output, "w") as f:
            json.dump(metadata, f, indent=2)
        click.echo(f"Metadata written to {json_output}")
