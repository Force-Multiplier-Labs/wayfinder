"""ContextCore CLI - SLO test generation commands."""

import json
import sys
from pathlib import Path
from typing import Optional, Tuple

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
def slo_tests():
    """SLO test generation commands."""
    pass


@slo_tests.command("generate")
@click.option("--project", "-p", required=True, help="Project ID or path to ProjectContext YAML")
@click.option("--output-dir", "-o", type=click.Path(), default="./generated-tests",
              help="Output directory for generated tests")
@click.option("--types", "-t", multiple=True,
              type=click.Choice(["load", "latency", "chaos", "availability"]),
              help="Test types to generate (default: all)")
@click.option("--namespace", "-n", default="default", help="Kubernetes namespace")
def generate_slo_tests_cmd(
    project: str,
    output_dir: str,
    types: Tuple[str, ...],
    namespace: str,
):
    """Generate SLO verification tests from ProjectContext requirements.

    Creates k6 load test scripts and chaos-mesh YAML experiments based on
    ProjectContext requirements. Generated tests include:

    - Latency tests: k6 scripts with thresholds from requirements.latencyP99/P50
    - Load tests: k6 scripts with throughput from requirements.throughput
    - Chaos tests: chaos-mesh YAMLs for availability from requirements.availability

    Example:
        contextcore slo-tests generate --project checkout-service

    Generate only chaos tests:
        contextcore slo-tests generate --project checkout-service -t chaos
    """
    from contextcore.generators.slo_tests import SLOTestGenerator, TestType, write_tests

    spec = _get_project_context_spec(project, namespace)
    if not spec:
        click.echo(f"Error: ProjectContext '{project}' not found", err=True)
        sys.exit(1)

    # Get project ID
    project_info = spec.get("project", {})
    if isinstance(project_info, dict):
        project_id = project_info.get("id", project)
    else:
        project_id = str(project_info) if project_info else project

    # Parse test types
    if types:
        test_types = [TestType(t) for t in types]
    else:
        test_types = None  # Generate all

    # Generate tests
    generator = SLOTestGenerator()
    tests = generator.generate(project_id, spec, test_types)

    if not tests:
        click.echo("No tests generated. Check that requirements are specified in ProjectContext:")
        click.echo("  - requirements.latencyP99 / latencyP50 for latency tests")
        click.echo("  - requirements.throughput for load tests")
        click.echo("  - requirements.availability for chaos tests")
        sys.exit(0)

    # Write tests
    output_path = Path(output_dir)
    written = write_tests(tests, output_path)

    click.echo(f"Generated {len(tests)} test(s):")
    for path in written:
        click.echo(f"  - {path}")

    # Provide usage hints
    k6_tests = [p for p in written if p.suffix == ".js"]
    chaos_tests = [p for p in written if p.suffix == ".yaml"]

    if k6_tests:
        click.echo(f"\nRun load tests:  k6 run {output_path}/*-slo-test.js")

    if chaos_tests:
        click.echo(f"Apply chaos:     kubectl apply -f {output_path}/*-chaos.yaml")
