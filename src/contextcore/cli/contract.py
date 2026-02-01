"""ContextCore CLI - Contract drift detection commands."""

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


def _derive_service_url(targets: list) -> Optional[str]:
    """Derive service URL from ProjectContext targets."""
    for target in targets:
        if target.get("kind") == "Service":
            ns = target.get("namespace", "default")
            name = target.get("name", "service")
            port = target.get("port", 80)
            return f"http://{name}.{ns}.svc.cluster.local:{port}"

    # Fallback to first target
    if targets:
        name = targets[0].get("name", "service")
        ns = targets[0].get("namespace", "default")
        return f"http://{name}.{ns}.svc.cluster.local"

    return None


@click.group()
def contract():
    """API contract commands."""
    pass


@contract.command("check")
@click.option("--project", "-p", required=True, help="Project ID or path to ProjectContext YAML")
@click.option("--service-url", "-s", help="Service URL (auto-detect from targets if not provided)")
@click.option("--contract-url", "-c", help="OpenAPI spec URL/path (auto-detect from design.apiContract if not provided)")
@click.option("--output", "-o", type=click.Path(), help="Output report file")
@click.option("--fail-on-drift", is_flag=True, help="Exit with error if drift detected")
@click.option("--namespace", "-n", default="default", help="Kubernetes namespace")
def contract_check_cmd(
    project: str,
    service_url: Optional[str],
    contract_url: Optional[str],
    output: Optional[str],
    fail_on_drift: bool,
    namespace: str,
):
    """Check for API contract drift.

    Compares OpenAPI specification against live service responses to detect
    contract drift. Reports:
    - Missing endpoints (critical)
    - Schema mismatches (warning)
    - Unexpected properties (info)

    Example:
        contextcore contract check --project checkout-service \\
            --service-url http://localhost:8080 \\
            --contract-url ./openapi.yaml

    Or auto-detect from ProjectContext:
        contextcore contract check --project checkout-service
    """
    from contextcore.integrations.contract_drift import ContractDriftDetector

    spec = _get_project_context_spec(project, namespace)
    if not spec:
        click.echo(f"Error: ProjectContext '{project}' not found", err=True)
        sys.exit(1)

    # Get contract URL
    if not contract_url:
        design = spec.get("design", {})
        contract_url = design.get("apiContract")
        if not contract_url:
            click.echo("Error: No apiContract specified. Use --contract-url or set design.apiContract in ProjectContext", err=True)
            sys.exit(1)

    # Get service URL
    if not service_url:
        service_url = _derive_service_url(spec.get("targets", []))
        if not service_url:
            click.echo("Error: Could not derive service URL. Use --service-url or specify targets in ProjectContext", err=True)
            sys.exit(1)

    # Get project ID
    project_info = spec.get("project", {})
    if isinstance(project_info, dict):
        project_id = project_info.get("id", project)
    else:
        project_id = str(project_info) if project_info else project

    # Run drift detection
    click.echo(f"Checking contract drift...")
    click.echo(f"  Contract: {contract_url}")
    click.echo(f"  Service:  {service_url}")

    detector = ContractDriftDetector()
    report = detector.detect(project_id, contract_url, service_url)

    # Output report
    markdown = report.to_markdown()
    if output:
        with open(output, "w") as f:
            f.write(markdown)
        click.echo(f"\nReport written to {output}")
    else:
        click.echo("\n" + markdown)

    # Summary
    click.echo(f"\nEndpoints checked: {report.endpoints_checked}")
    click.echo(f"Endpoints passed:  {report.endpoints_passed}")
    click.echo(f"Issues found:      {len(report.issues)}")

    if report.critical_issues:
        click.echo(f"Critical issues:   {len(report.critical_issues)}")

    if fail_on_drift and report.has_drift:
        sys.exit(1)
