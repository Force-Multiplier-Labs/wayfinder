# Wayfinder Deployment Options

Choose the deployment method that fits your workflow. All options deploy the same
observability stack (Grafana, Tempo, Mimir, Loki, Alloy).

| Option | Best For | Command |
|--------|----------|---------|
| **Docker Compose** | Quick local development, no K8s needed | `make full-setup` |
| **Kind (dev)** | Kubernetes patterns, single-worker cluster | `make kind-up` |
| **Kind (test)** | Multi-node topology with criticality tiers | `make kind-up PROFILE=test` |
| **Helm** | Production / managed K8s clusters | `helm install` (scaffolded) |

## Docker Compose

Runs all components as containers on the host. Simplest path.

```bash
make full-setup       # Start stack, wait for ready, seed metrics
make health           # Check component health
make down             # Stop (preserve data)
```

See [docs/INSTALLATION.md](../docs/INSTALLATION.md) for full details.

## Kind Cluster

Runs a real Kubernetes cluster inside Docker via [Kind](https://kind.sigs.k8s.io/).

### Profiles

| Profile | Nodes | Topology |
|---------|-------|----------|
| `dev` (default) | 2 | control-plane + 1 combined worker |
| `test` | 3 | control-plane + platform worker (tainted) + workload worker |

### Quick Start

```bash
make kind-up                    # Create dev cluster (interactive — confirms defaults)
make kind-up PROFILE=test       # Create test cluster with criticality tiers
make kind-up YES=1              # Accept all defaults without prompting

make kind-status                # Show pod status
make kind-seed                  # Seed installation metrics
make kind-down                  # Delete cluster
```

### Direct Script Usage

```bash
deploy/kind/scripts/create-cluster.sh                    # Interactive setup
deploy/kind/scripts/create-cluster.sh --profile test     # Test profile
deploy/kind/scripts/create-cluster.sh --yes              # Accept defaults
deploy/kind/scripts/create-cluster.sh --verbose          # Detailed output
deploy/kind/scripts/create-cluster.sh --verbose-tutorial # Learning mode
deploy/kind/scripts/create-cluster.sh --delete           # Tear down
```

### Directory Layout

```
deploy/kind/
├── kind-dev.yaml.tmpl       # 2-node Kind config template
├── kind-test.yaml.tmpl      # 3-node Kind config template
├── namespaces.yaml          # observability + contextcore namespaces
└── scripts/
    └── create-cluster.sh    # Cluster lifecycle manager
```

Templates use `__WAYFINDER_ROOT__` placeholders that `create-cluster.sh` resolves
at runtime via `sed`. No hardcoded user paths.

## Helm (Scaffolded)

The Helm chart at `helm/contextcore/` is scaffolded but not yet complete.

## Port Reference

| Port | Service | Protocol |
|------|---------|----------|
| 3000 | Grafana | HTTP |
| 3100 | Loki | HTTP |
| 3200 | Tempo | HTTP |
| 4317 | Alloy (OTLP) | gRPC |
| 4318 | Alloy (OTLP) | HTTP |
| 9009 | Mimir | HTTP |
| 12345 | Alloy UI | HTTP |
