#!/usr/bin/env python3
"""
Environment-Specific Install Guide Generator

Detects the deployment environment and generates a customized reinstall guide.

Usage:
    python scripts/generate-install-guide.py [--output FILE] [--format md|txt]

    # Or make executable and run directly
    ./scripts/generate-install-guide.py

    # Output to specific file
    ./scripts/generate-install-guide.py --output docs/MY_REINSTALL_GUIDE.md

    # Run against a specific deployment directory
    ./scripts/generate-install-guide.py --project-root /path/to/Deploy
"""

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


# =============================================================================
# Environment Detection
# =============================================================================

@dataclass
class EnvironmentInfo:
    """Detected environment information."""

    # Stack type
    stack_type: str = "unknown"  # kind, docker-compose, k8s-external, hybrid

    # Paths
    project_root: Path = field(default_factory=Path.cwd)

    # Kind-specific
    kind_cluster_name: Optional[str] = None
    kind_config_file: Optional[Path] = None
    kind_cluster_running: bool = False
    kind_node_count: int = 0

    # Docker Compose-specific
    docker_compose_file: Optional[Path] = None
    docker_compose_running: bool = False

    # Kubernetes-specific
    kubectl_context: Optional[str] = None
    kubectl_available: bool = False

    # Components detected
    has_observability: bool = False
    has_contextcore: bool = False
    has_011ybubo: bool = False

    # Observability components
    observability_components: list = field(default_factory=list)

    # Port configuration
    ports: dict = field(default_factory=dict)

    # Credentials
    grafana_password: str = "admin"

    # Scripts available
    has_makefile: bool = False
    has_setup_script: bool = False
    has_teardown_script: bool = False

    # Virtual environment
    venv_path: Optional[Path] = None
    contextcore_installed: bool = False

    # Extra mounts (for Kind)
    extra_mounts: list = field(default_factory=list)


def run_command(cmd: list[str], capture: bool = True) -> tuple[int, str, str]:
    """Run a shell command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture,
            text=True,
            timeout=10
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return 1, "", str(e)


def detect_environment(project_root: Path) -> EnvironmentInfo:
    """Detect the deployment environment."""
    env = EnvironmentInfo(project_root=project_root)

    # --- Detect available tools ---
    rc, _, _ = run_command(["kubectl", "version", "--client", "--short"])
    env.kubectl_available = rc == 0

    # --- Detect Kind cluster ---
    kind_configs = list(project_root.glob("kind-cluster*.yaml"))
    if kind_configs:
        env.kind_config_file = kind_configs[0]
        # Parse cluster name from config
        try:
            import yaml
            with open(env.kind_config_file) as f:
                config = yaml.safe_load(f)
                env.kind_cluster_name = config.get("name", "kind")
                nodes = config.get("nodes", [])
                env.kind_node_count = len(nodes)
                # Extract extra mounts
                for node in nodes:
                    mounts = node.get("extraMounts", [])
                    for mount in mounts:
                        env.extra_mounts.append({
                            "host": mount.get("hostPath", ""),
                            "container": mount.get("containerPath", ""),
                        })
                # Extract port mappings
                for node in nodes:
                    for mapping in node.get("extraPortMappings", []):
                        host_port = mapping.get("hostPort")
                        container_port = mapping.get("containerPort")
                        if host_port:
                            env.ports[host_port] = container_port
        except Exception:
            env.kind_cluster_name = "wayfinder-dev"  # Default

    # Check if Kind cluster is running
    if env.kind_cluster_name:
        rc, stdout, _ = run_command(["kind", "get", "clusters"])
        if rc == 0 and env.kind_cluster_name in stdout.split():
            env.kind_cluster_running = True

    # --- Detect Docker Compose ---
    compose_files = [
        project_root / "docker-compose.yaml",
        project_root / "docker-compose.yml",
    ]
    for cf in compose_files:
        if cf.exists():
            env.docker_compose_file = cf
            break

    # Check if compose stack is running
    if env.docker_compose_file:
        rc, stdout, _ = run_command(["docker", "compose", "ps", "-q"])
        env.docker_compose_running = rc == 0 and bool(stdout)

    # --- Determine stack type ---
    if env.kind_config_file and not env.docker_compose_file:
        env.stack_type = "kind"
    elif env.docker_compose_file and not env.kind_config_file:
        env.stack_type = "docker-compose"
    elif env.kind_config_file and env.docker_compose_file:
        env.stack_type = "hybrid"
    elif env.kubectl_available:
        env.stack_type = "k8s-external"

    # --- Detect kubectl context ---
    if env.kubectl_available:
        rc, stdout, _ = run_command(["kubectl", "config", "current-context"])
        if rc == 0:
            env.kubectl_context = stdout

    # --- Detect components ---
    env.has_observability = (project_root / "observability").is_dir()
    env.has_contextcore = (project_root / "contextcore").is_dir()
    env.has_011ybubo = (project_root / "011ybubo").is_dir()

    # Detect observability components
    obs_dir = project_root / "observability"
    if obs_dir.is_dir():
        for component in ["grafana", "tempo", "loki", "mimir", "alloy", "pyroscope"]:
            if (obs_dir / component).is_dir() or list(obs_dir.glob(f"*{component}*")):
                env.observability_components.append(component)

    # --- Detect scripts ---
    env.has_makefile = (project_root / "Makefile").exists()
    env.has_setup_script = (project_root / "setup.sh").exists()
    env.has_teardown_script = (project_root / "teardown.sh").exists()

    # --- Detect virtual environment ---
    venv_candidates = [
        project_root / "contextcore-venv",
        project_root / "venv",
        project_root / ".venv",
    ]
    for venv in venv_candidates:
        if venv.is_dir() and (venv / "bin" / "python").exists():
            env.venv_path = venv
            # Check if contextcore is installed
            rc, stdout, _ = run_command([
                str(venv / "bin" / "pip"), "show", "contextcore"
            ])
            env.contextcore_installed = rc == 0
            break

    # --- Detect credentials from env or files ---
    env.grafana_password = os.environ.get("GRAFANA_PASSWORD", "adminadminadmin")

    # --- Set default ports if not detected ---
    if not env.ports:
        env.ports = {
            3000: 30000,   # Grafana
            3100: 30100,   # Loki
            3200: 30200,   # Tempo
            4317: 30317,   # OTLP gRPC
            4318: 30318,   # OTLP HTTP
            9009: 30009,   # Mimir
        }

    return env


# =============================================================================
# Guide Generation
# =============================================================================

def generate_guide(env: EnvironmentInfo) -> str:
    """Generate the install guide based on detected environment."""

    lines = []

    def add(text: str = ""):
        lines.append(text)

    def add_section(title: str):
        add()
        add(f"## {title}")
        add()

    # Header
    add(f"# {env.project_root.name} Reinstall Guide")
    add()
    add(f"> Auto-generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    add(f"> Stack type: **{env.stack_type}**")
    add(f"> Project root: `{env.project_root}`")
    add()

    # Prerequisites
    add_section("Prerequisites")
    add("Ensure the following are installed and running:")
    add()
    add("```bash")
    add("# Verify prerequisites")
    if env.stack_type in ("kind", "hybrid"):
        add("which kind      # Kind (Kubernetes in Docker)")
    add("which kubectl   # Kubernetes CLI")
    add("which docker    # Docker")
    add("docker info     # Verify Docker is running")
    add("```")

    # Current State
    add_section("Current State")
    add("| Component | Status |")
    add("|-----------|--------|")
    if env.stack_type == "kind":
        status = "Running" if env.kind_cluster_running else "Not running"
        add(f"| Kind cluster `{env.kind_cluster_name}` | {status} |")
    elif env.stack_type == "docker-compose":
        status = "Running" if env.docker_compose_running else "Not running"
        add(f"| Docker Compose stack | {status} |")
    add(f"| kubectl context | `{env.kubectl_context or 'Not set'}` |")
    add(f"| Observability | {'Configured' if env.has_observability else 'Not found'} |")
    add(f"| ContextCore | {'Configured' if env.has_contextcore else 'Not found'} |")
    add(f"| 011yBubo | {'Configured' if env.has_011ybubo else 'Not found'} |")
    add(f"| Python venv | {'Found' if env.venv_path else 'Not found'} |")
    add(f"| contextcore CLI | {'Installed' if env.contextcore_installed else 'Not installed'} |")

    # Phase 1: Teardown
    add_section("Phase 1: Teardown")
    add("**Stop and remove existing deployment.**")
    add()

    if env.stack_type == "kind":
        add("### Kind Cluster Teardown")
        add()
        if env.has_makefile:
            add("```bash")
            add(f"cd {env.project_root}")
            add()
            add("# Option A: Using Makefile (recommended)")
            add("make down      # Stop cluster (preserves data)")
            add("make destroy   # Delete cluster completely (type 'yes' to confirm)")
            add()
            add("# Option B: Direct Kind command")
            add(f"kind delete cluster --name {env.kind_cluster_name}")
            add("```")
        else:
            add("```bash")
            add(f"kind delete cluster --name {env.kind_cluster_name}")
            add("```")

    elif env.stack_type == "docker-compose":
        add("### Docker Compose Teardown")
        add()
        if env.has_makefile:
            add("```bash")
            add(f"cd {env.project_root}")
            add()
            add("# Option A: Using Makefile")
            add("make down      # Stop containers")
            add("make destroy   # Remove containers and volumes")
            add()
            add("# Option B: Direct Docker Compose")
            add("docker compose down -v")
            add("```")
        else:
            add("```bash")
            add(f"cd {env.project_root}")
            add("docker compose down -v")
            add("```")

    add()
    add("### Verify Teardown")
    add()
    add("```bash")
    if env.stack_type == "kind":
        add(f"# Cluster should be gone")
        add("kind get clusters")
        add(f"# Should NOT show: {env.kind_cluster_name}")
    add()
    add("# Ports should be free")
    port_list = " -i :".join(str(p) for p in sorted(env.ports.keys())[:6])
    add(f"lsof -i :{port_list}")
    add("# Should return nothing")
    add("```")

    # Phase 2: Fresh Install
    add_section("Phase 2: Fresh Installation")
    add()

    if env.stack_type == "kind":
        add("### Create Kind Cluster and Deploy")
        add()
        if env.has_makefile:
            add("```bash")
            add(f"cd {env.project_root}")
            add()
            add("# One-command setup")
            add("make up")
            add("```")
            add()
            add("**What `make up` does:**")
            add(f"1. Creates Kind cluster `{env.kind_cluster_name}` ({env.kind_node_count} nodes)")
            add("2. Installs local-path-provisioner for storage")
            add("3. Creates namespaces")
            if env.has_observability:
                add(f"4. Deploys observability stack ({', '.join(env.observability_components)})")
            if env.has_contextcore:
                add("5. Deploys ContextCore CRDs and operator")
            if env.has_011ybubo:
                add("6. Deploys 011yBubo")
        else:
            add("```bash")
            add(f"cd {env.project_root}")
            add()
            if env.has_setup_script:
                add("# Run setup script")
                add("./setup.sh")
            else:
                add("# Manual setup")
                add(f"kind create cluster --config {env.kind_config_file} --wait 5m")
                add(f"kubectl config use-context kind-{env.kind_cluster_name}")
                if env.has_observability:
                    add("kubectl apply -k observability/")
                if env.has_contextcore:
                    add("kubectl apply -f vendor/contextcore-spec/crds/")
                    add("kubectl apply -k contextcore/")
            add("```")

    elif env.stack_type == "docker-compose":
        add("### Start Docker Compose Stack")
        add()
        if env.has_makefile:
            add("```bash")
            add(f"cd {env.project_root}")
            add()
            add("# Using Makefile")
            add("make up")
            add("# Or with full setup including verification")
            add("make full-setup")
            add("```")
        else:
            add("```bash")
            add(f"cd {env.project_root}")
            add("docker compose up -d")
            add("```")

    # Phase 3: Verification
    add_section("Phase 3: Verification")
    add()

    if env.has_makefile:
        add("### Quick Verification")
        add()
        add("```bash")
        add("make health      # Component health check")
        add("make status      # Pod/container status")
        add("make smoke-test  # Full verification suite")
        add("```")
        add()

    add("### Component Checks")
    add()
    add("| Component | Command | Expected |")
    add("|-----------|---------|----------|")

    if env.stack_type == "kind":
        add(f"| Cluster | `kind get clusters` | `{env.kind_cluster_name}` |")
        add("| Pods | `kubectl get pods -A` | All Running |")

    if 3000 in env.ports:
        add("| Grafana | `curl -s http://localhost:3000/api/health` | `{\"database\":\"ok\"}` |")
    if 3200 in env.ports:
        add("| Tempo | `curl -s http://localhost:3200/ready` | `ready` |")
    if 3100 in env.ports:
        add("| Loki | `curl -s http://localhost:3100/ready` | `ready` |")
    if 9009 in env.ports:
        add("| Mimir | `curl -s http://localhost:9009/ready` | `ready` |")
    if 4317 in env.ports:
        add("| OTLP gRPC | `nc -zv localhost 4317` | `succeeded` |")

    if env.has_contextcore:
        add("| CRD | `kubectl get crd projectcontexts.contextcore.io` | CRD exists |")

    # Phase 4: Python Package
    if env.venv_path:
        add_section("Phase 4: Python Package Installation")
        add()
        add("```bash")
        add(f"# Activate virtual environment")
        add(f"source {env.venv_path}/bin/activate")
        add()
        add("# Install contextcore (adjust path as needed)")
        add("pip install -e \"/path/to/ContextCore[all]\"")
        add()
        add("# Verify CLI")
        add("contextcore --help")
        add("```")

    # Quick Reference
    add_section("Quick Reference")
    add()
    add("### URLs")
    add()
    add("| Service | URL | Credentials |")
    add("|---------|-----|-------------|")
    if 3000 in env.ports:
        add(f"| Grafana | http://localhost:3000 | admin / {env.grafana_password} |")
    if 3200 in env.ports:
        add("| Tempo | http://localhost:3200 | - |")
    if 3100 in env.ports:
        add("| Loki | http://localhost:3100 | - |")
    if 9009 in env.ports:
        add("| Mimir | http://localhost:9009 | - |")
    if 4317 in env.ports:
        add("| OTLP gRPC | localhost:4317 | - |")
    if 4318 in env.ports:
        add("| OTLP HTTP | http://localhost:4318 | - |")

    # Makefile commands
    if env.has_makefile:
        add()
        add("### Makefile Commands")
        add()
        add("| Command | Description |")
        add("|---------|-------------|")
        add("| `make doctor` | Preflight checks |")
        add("| `make up` | Start everything |")
        add("| `make down` | Stop (preserve data) |")
        add("| `make destroy` | Delete completely |")
        add("| `make status` | Show status |")
        add("| `make health` | Health checks |")
        add("| `make logs-grafana` | Follow Grafana logs |")

    # Copy-paste sequence
    add_section("Complete Reinstall Sequence")
    add()
    add("Copy-paste ready:")
    add()
    add("```bash")
    add(f"cd {env.project_root}")
    add()
    add("# Teardown")
    if env.stack_type == "kind":
        if env.has_makefile:
            add("make destroy")
        else:
            add(f"kind delete cluster --name {env.kind_cluster_name}")
    elif env.stack_type == "docker-compose":
        if env.has_makefile:
            add("make destroy")
        else:
            add("docker compose down -v")
    add()
    add("# Fresh install")
    if env.has_makefile:
        add("make up")
    elif env.has_setup_script:
        add("./setup.sh")
    elif env.stack_type == "kind":
        add(f"kind create cluster --config {env.kind_config_file}")
    else:
        add("docker compose up -d")
    add()
    add("# Verify")
    if env.has_makefile:
        add("make health")
    add("```")

    # Troubleshooting
    add_section("Troubleshooting")
    add()
    add("### Ports Still In Use")
    add()
    add("```bash")
    add("# Check what's using ports")
    add(f"lsof -i :{port_list}")
    add()
    add("# Force stop all Docker containers")
    add("docker stop $(docker ps -q)")
    add("```")
    add()

    if env.stack_type == "kind":
        add("### Pods Not Starting")
        add()
        add("```bash")
        add("# Check pod status")
        add("kubectl get pods -A")
        add()
        add("# Describe failing pod")
        add("kubectl describe pod <pod-name> -n <namespace>")
        add()
        add("# Check logs")
        add("kubectl logs <pod-name> -n <namespace>")
        add("```")

    return "\n".join(lines)


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Generate environment-specific install guide"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        help="Output file path (default: stdout)"
    )
    parser.add_argument(
        "--project-root", "-p",
        type=Path,
        default=Path.cwd(),
        help="Project root directory (default: current directory)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output detected environment as JSON instead of guide"
    )

    args = parser.parse_args()

    # Detect environment
    env = detect_environment(args.project_root)

    if args.json:
        # Output environment info as JSON
        import dataclasses
        env_dict = dataclasses.asdict(env)
        # Convert Path objects to strings
        for key, value in env_dict.items():
            if isinstance(value, Path):
                env_dict[key] = str(value)
            elif value is None:
                env_dict[key] = None
        output = json.dumps(env_dict, indent=2, default=str)
    else:
        # Generate guide
        output = generate_guide(env)

    # Output
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output)
        print(f"Guide written to: {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
