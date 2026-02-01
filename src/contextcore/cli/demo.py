"""ContextCore CLI - Demo data generation commands."""

import os
import sys
from typing import Optional

import click


@click.group()
def demo():
    """Generate and load demo data using Google's microservices-demo."""
    pass


@demo.command("generate")
@click.option("--project", "-p", default="online-boutique", help="Project identifier")
@click.option("--output", "-o", default="./demo_output", help="Output directory for spans")
@click.option("--months", "-m", type=int, default=3, help="Duration of project history (months)")
@click.option("--seed", type=int, help="Random seed for reproducibility")
@click.option("--format", "output_format", type=click.Choice(["json", "otlp"]), default="json", help="Output format")
@click.option("--endpoint", envvar="OTEL_EXPORTER_OTLP_ENDPOINT", help="OTLP endpoint (for otlp format)")
def demo_generate(project: str, output: str, months: int, seed: Optional[int], output_format: str, endpoint: Optional[str]):
    """Generate demo project history for microservices-demo."""
    from contextcore.demo import generate_demo_data

    click.echo(f"Generating {months}-month project history for {project}")
    click.echo(f"  Output: {output}")
    if seed:
        click.echo(f"  Seed: {seed}")

    stats = generate_demo_data(
        project=project,
        output_dir=output if output_format == "json" else None,
        duration_months=months,
        seed=seed,
    )

    click.echo()
    click.echo("Generation complete!")
    click.echo(f"  Services: {stats['services']}")
    click.echo(f"  Epics: {stats['epics']}")
    click.echo(f"  Stories: {stats['stories']}")
    click.echo(f"  Tasks: {stats['tasks']}")
    click.echo(f"  Blockers: {stats['blockers']}")
    click.echo(f"  Sprints: {stats['sprints']}")
    click.echo(f"  Total spans: {stats['total_spans']}")

    if output_format == "json" and "output_file" in stats:
        click.echo()
        click.echo(f"Spans saved to: {stats['output_file']}")

    if output_format == "otlp":
        if not endpoint:
            click.echo("Error: --endpoint required for otlp format", err=True)
            sys.exit(1)
        click.echo("(Direct OTLP export not yet implemented)")


@demo.command("load")
@click.option("--file", "-f", "spans_file", required=True, type=click.Path(exists=True), help="JSON spans file")
@click.option("--endpoint", "-e", envvar="OTEL_EXPORTER_OTLP_ENDPOINT", default="localhost:4317", help="OTLP endpoint")
@click.option("--insecure/--secure", default=True, help="Use insecure connection")
def demo_load(spans_file: str, endpoint: str, insecure: bool):
    """Load generated spans to Tempo via OTLP."""
    from contextcore.demo import load_to_tempo

    click.echo(f"Loading spans from {spans_file}")
    click.echo(f"  Endpoint: {endpoint}")

    result = load_to_tempo(endpoint=endpoint, spans_file=spans_file, insecure=insecure)

    if result["success"]:
        click.echo(f"Successfully loaded {result['spans_exported']} spans to {endpoint}")
    else:
        click.echo("Failed to load spans", err=True)
        sys.exit(1)


@demo.command("setup")
@click.option("--cluster-name", default="contextcore-demo", help="Kind cluster name")
@click.option("--skip-cluster", is_flag=True, help="Skip cluster creation")
@click.option("--skip-observability", is_flag=True, help="Skip observability stack deployment")
@click.option("--skip-demo", is_flag=True, help="Skip microservices-demo deployment")
def demo_setup(cluster_name: str, skip_cluster: bool, skip_observability: bool, skip_demo: bool):
    """Set up local kind cluster with observability stack."""
    import subprocess
    import shutil

    missing = []
    for cmd in ["kind", "kubectl", "helm"]:
        if not shutil.which(cmd):
            missing.append(cmd)

    if missing:
        click.echo(f"Missing required tools: {', '.join(missing)}", err=True)
        sys.exit(1)

    click.echo("ContextCore Demo Setup")
    click.echo("=" * 40)

    if not skip_cluster:
        click.echo("\n[1/4] Creating kind cluster...")
        result = subprocess.run(["kind", "get", "clusters"], capture_output=True, text=True)
        if cluster_name in result.stdout.split():
            click.echo(f"  Cluster '{cluster_name}' already exists")
        else:
            result = subprocess.run(["kind", "create", "cluster", "--name", cluster_name], capture_output=True, text=True)
            if result.returncode != 0:
                click.echo(f"Error creating cluster: {result.stderr}", err=True)
                sys.exit(1)
            click.echo(f"  Created cluster: {cluster_name}")
    else:
        click.echo("\n[1/4] Skipping cluster creation")

    if not skip_observability:
        click.echo("\n[2/4] Deploying observability stack...")
        click.echo("  (Manual Helm install required)")
    else:
        click.echo("\n[2/4] Skipping observability deployment")

    click.echo("\n[3/4] Applying ContextCore CRD...")
    crd_path = os.path.join(os.path.dirname(__file__), "..", "..", "crds", "projectcontext.yaml")
    if os.path.exists(crd_path):
        result = subprocess.run(["kubectl", "apply", "-f", crd_path], capture_output=True, text=True)
        if result.returncode == 0:
            click.echo("  Applied ProjectContext CRD")
        else:
            click.echo(f"  Warning: {result.stderr}")
    else:
        click.echo("  CRD file not found - skipping")

    if not skip_demo:
        click.echo("\n[4/4] Deploying microservices-demo...")
        click.echo("  (Not yet implemented)")
    else:
        click.echo("\n[4/4] Skipping microservices-demo deployment")

    click.echo("\n" + "=" * 40)
    click.echo("Setup complete!")


@demo.command("services")
def demo_services():
    """List all 11 microservices from Online Boutique."""
    from contextcore.demo import SERVICE_CONFIGS

    click.echo("Online Boutique Microservices")
    click.echo("=" * 60)
    click.echo()
    click.echo(f"{'Service':<25} {'Language':<10} {'Criticality':<10} {'Business Value'}")
    click.echo("-" * 60)

    for name, config in SERVICE_CONFIGS.items():
        click.echo(f"{name:<25} {config.language:<10} {config.criticality:<10} {config.business_value}")

    click.echo()
    click.echo(f"Total: {len(SERVICE_CONFIGS)} services")
