#!/bin/bash
# Wayfinder Kind Cluster Setup
# Creates a local Kubernetes cluster with the full observability stack
#
# Usage:
#   ./deploy/kind/scripts/create-cluster.sh                    # Interactive setup (confirms defaults)
#   ./deploy/kind/scripts/create-cluster.sh --yes              # Accept all defaults
#   ./deploy/kind/scripts/create-cluster.sh --profile test     # 3-node topology
#   ./deploy/kind/scripts/create-cluster.sh --verbose          # Show detailed progress
#   ./deploy/kind/scripts/create-cluster.sh --verbose-tutorial # Explain each step (learning mode)
#   ./deploy/kind/scripts/create-cluster.sh --skip-wait        # Skip waiting for pods
#   ./deploy/kind/scripts/create-cluster.sh --delete           # Delete cluster (with confirmation)
#
# Prerequisites:
#   - Docker running
#   - kind installed (brew install kind)
#   - kubectl installed (brew install kubectl)

set -e

# =============================================================================
# Resolve paths from script location (no hardcoded user paths)
# =============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KIND_DIR="$(dirname "$SCRIPT_DIR")"
DEPLOY_DIR="$(dirname "$KIND_DIR")"
DEFAULT_WAYFINDER_ROOT="$(dirname "$DEPLOY_DIR")"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
DIM='\033[2m'
BOLD='\033[1m'
NC='\033[0m'

# =============================================================================
# Parse arguments
# =============================================================================
SKIP_WAIT=false
DELETE_ONLY=false
VERBOSE=false
TUTORIAL=false
AUTO_ACCEPT=false
PROFILE="dev"

for arg in "$@"; do
    case $arg in
        --skip-wait)
            SKIP_WAIT=true
            ;;
        --delete)
            DELETE_ONLY=true
            ;;
        --verbose)
            VERBOSE=true
            ;;
        --verbose-tutorial)
            VERBOSE=true
            TUTORIAL=true
            ;;
        --yes|-y)
            AUTO_ACCEPT=true
            ;;
        --profile)
            # Next arg is the profile value — handled below
            ;;
        dev|test)
            PROFILE="$arg"
            ;;
    esac
done

# Handle --profile <value> (two-arg form)
while [[ $# -gt 0 ]]; do
    case $1 in
        --profile)
            PROFILE="${2:-dev}"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

# =============================================================================
# Helper functions
# =============================================================================
verbose() {
    if [ "$VERBOSE" = true ]; then
        echo -e "${DIM}   -> $1${NC}"
    fi
}

tutorial() {
    if [ "$TUTORIAL" = true ]; then
        echo ""
        echo -e "${BLUE}   +-- Why: ----------------------------------------------------------+${NC}"
        echo -e "${BLUE}   |${NC} $1"
        if [ -n "$2" ]; then
            echo -e "${BLUE}   |${NC} $2"
        fi
        if [ -n "$3" ]; then
            echo -e "${BLUE}   |${NC} $3"
        fi
        echo -e "${BLUE}   +------------------------------------------------------------------+${NC}"
        echo ""
    fi
}

# Prompt the user for a value, showing the default.
# If --yes was passed, auto-accept the default.
# Usage: prompt_value VARNAME "Description" "default_value"
prompt_value() {
    local varname=$1
    local description=$2
    local default=$3

    if [ "$AUTO_ACCEPT" = true ]; then
        eval "$varname=\"$default\""
        echo -e "  ${description}: ${GREEN}${default}${NC}"
        return
    fi

    echo -ne "  ${description} [${GREEN}${default}${NC}]: "
    read -r input
    if [ -z "$input" ]; then
        eval "$varname=\"$default\""
    else
        eval "$varname=\"$input\""
    fi
}

# Prompt for a choice between options.
# Usage: prompt_choice VARNAME "Description" "default" "option1|option2|..."
prompt_choice() {
    local varname=$1
    local description=$2
    local default=$3
    local options=$4

    if [ "$AUTO_ACCEPT" = true ]; then
        eval "$varname=\"$default\""
        echo -e "  ${description}: ${GREEN}${default}${NC}"
        return
    fi

    echo -ne "  ${description} (${options}) [${GREEN}${default}${NC}]: "
    read -r input
    if [ -z "$input" ]; then
        eval "$varname=\"$default\""
    else
        eval "$varname=\"$input\""
    fi
}

# =============================================================================
# Handle --delete flag (before interactive config)
# =============================================================================
if [ "$DELETE_ONLY" = true ]; then
    echo -e "${RED}=== DELETE Kind Cluster ===${NC}"
    echo ""

    # Find which clusters exist
    EXISTING=$(kind get clusters 2>/dev/null || true)
    WAYFINDER_CLUSTERS=$(echo "$EXISTING" | grep -E "^wayfinder-" || true)

    if [ -z "$WAYFINDER_CLUSTERS" ]; then
        echo -e "${YELLOW}No Wayfinder clusters found.${NC}"
        if [ -n "$EXISTING" ]; then
            echo ""
            echo "Other Kind clusters:"
            echo "$EXISTING" | sed 's/^/  /'
        fi
        exit 0
    fi

    echo "Wayfinder clusters:"
    echo "$WAYFINDER_CLUSTERS" | sed 's/^/  /'
    echo ""

    # If only one, target it; otherwise ask
    CLUSTER_COUNT=$(echo "$WAYFINDER_CLUSTERS" | wc -l | tr -d ' ')
    if [ "$CLUSTER_COUNT" -eq 1 ]; then
        TARGET_CLUSTER="$WAYFINDER_CLUSTERS"
    else
        read -p "Which cluster to delete? " TARGET_CLUSTER
    fi

    echo -e "${YELLOW}WARNING: This will delete the Kind cluster and all its data!${NC}"
    echo ""
    echo "The following will be destroyed:"
    echo "  - Kind cluster: $TARGET_CLUSTER"
    echo "  - All pods in observability namespace"
    echo "  - All stored traces, metrics, and logs"
    echo ""
    read -p "To confirm, type the cluster name ($TARGET_CLUSTER): " confirm
    if [ "$confirm" != "$TARGET_CLUSTER" ]; then
        echo -e "${RED}Cluster name did not match. Aborted.${NC}"
        exit 1
    fi

    echo ""
    echo "Deleting cluster..."
    kind delete cluster --name "$TARGET_CLUSTER"
    echo -e "${GREEN}Cluster '$TARGET_CLUSTER' deleted.${NC}"
    exit 0
fi

# =============================================================================
# Banner
# =============================================================================
echo -e "${CYAN}=== Wayfinder Kind Cluster Setup ===${NC}"
if [ "$TUTORIAL" = true ]; then
    echo -e "${BLUE}   Running in tutorial mode - explanations will be shown for each step${NC}"
fi
echo ""

# =============================================================================
# Interactive configuration — offer defaults, let user override
# =============================================================================
echo -e "${CYAN}Step 1: Configuration${NC}"
echo ""
echo "Review the defaults below. Press Enter to accept each, or type a new value."
if [ "$AUTO_ACCEPT" = true ]; then
    echo -e "${DIM}(--yes: accepting all defaults)${NC}"
fi
echo ""

# Profile
prompt_choice "PROFILE" "Cluster profile" "$PROFILE" "dev|test"

# Derive cluster name from profile
DEFAULT_CLUSTER_NAME="wayfinder-${PROFILE}"
prompt_value "CLUSTER_NAME" "Cluster name" "$DEFAULT_CLUSTER_NAME"

# Wayfinder root
prompt_value "WAYFINDER_ROOT" "Wayfinder root" "$DEFAULT_WAYFINDER_ROOT"

# K8s manifests
DEFAULT_K8S_MANIFESTS="${WAYFINDER_ROOT}/k8s/observability"
prompt_value "K8S_MANIFESTS" "K8s manifests" "$DEFAULT_K8S_MANIFESTS"

# Cluster config template
DEFAULT_CLUSTER_CONFIG="${KIND_DIR}/kind-${PROFILE}.yaml.tmpl"
prompt_value "CLUSTER_CONFIG" "Kind config template" "$DEFAULT_CLUSTER_CONFIG"

echo ""

# Confirm before proceeding
if [ "$AUTO_ACCEPT" != true ]; then
    echo -e "${CYAN}Summary:${NC}"
    echo "  Profile:    $PROFILE"
    echo "  Cluster:    $CLUSTER_NAME"
    echo "  Root:       $WAYFINDER_ROOT"
    echo "  Manifests:  $K8S_MANIFESTS"
    echo "  Template:   $CLUSTER_CONFIG"
    echo ""
    read -p "Proceed with these settings? (Y/n): " proceed
    if [[ "$proceed" =~ ^[Nn] ]]; then
        echo "Aborted."
        exit 0
    fi
fi

echo ""

# =============================================================================
# Step 2: Preflight checks
# =============================================================================
echo -e "${CYAN}Step 2: Preflight checks${NC}"

tutorial "Preflight checks ensure all required tools are installed before we start." \
         "This prevents partial failures mid-setup that are harder to debug."

verbose "Checking for Docker CLI..."
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: docker not found. Install with: brew install --cask docker${NC}"
    exit 1
fi
echo -e "${GREEN}  ✅ docker${NC}"

verbose "Checking Docker daemon is running..."
if ! docker info &> /dev/null; then
    echo -e "${RED}Error: Docker is not running. Start Docker Desktop first.${NC}"
    exit 1
fi
echo -e "${GREEN}  ✅ Docker daemon running${NC}"

tutorial "Kind (Kubernetes IN Docker) runs K8s clusters inside Docker containers." \
         "It's perfect for local development - no cloud account or VM needed."

verbose "Checking for kind CLI..."
if ! command -v kind &> /dev/null; then
    echo -e "${RED}Error: kind not found. Install with: brew install kind${NC}"
    exit 1
fi
echo -e "${GREEN}  ✅ kind${NC}"

verbose "Checking for kubectl CLI..."
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}Error: kubectl not found. Install with: brew install kubectl${NC}"
    exit 1
fi
echo -e "${GREEN}  ✅ kubectl${NC}"

verbose "Checking cluster config template at $CLUSTER_CONFIG..."
if [ ! -f "$CLUSTER_CONFIG" ]; then
    echo -e "${RED}Error: Cluster config template not found at: $CLUSTER_CONFIG${NC}"
    exit 1
fi
echo -e "${GREEN}  ✅ Cluster config: $CLUSTER_CONFIG${NC}"

tutorial "The cluster config template defines:" \
         "  - Port mappings: localhost:3000 -> Grafana, localhost:4317 -> OTLP, etc." \
         "  - Node topology: control-plane + worker nodes for realistic scheduling"

verbose "Checking K8s manifests exist at $K8S_MANIFESTS..."
if [ ! -d "$K8S_MANIFESTS" ]; then
    echo -e "${RED}Error: K8s manifests not found at: $K8S_MANIFESTS${NC}"
    exit 1
fi
echo -e "${GREEN}  ✅ K8s manifests: $K8S_MANIFESTS${NC}"

tutorial "The k8s/observability/ directory contains Kustomize manifests:" \
         "  - ConfigMaps for Tempo, Mimir, Loki, Alloy, Grafana" \
         "  - Deployments, Services, and dashboard JSON files"

echo ""

# =============================================================================
# Step 3: Render template
# =============================================================================
echo -e "${CYAN}Step 3: Rendering Kind config${NC}"

tutorial "Kind YAML doesn't support environment variables, so we ship .tmpl files" \
         "with __WAYFINDER_ROOT__ placeholders and render them with sed." \
         "The rendered file goes to a temp location and is cleaned up after use."

RENDERED_CONFIG=$(mktemp /tmp/wayfinder-kind-XXXXXX.yaml)
trap 'rm -f "$RENDERED_CONFIG"' EXIT

sed "s|__WAYFINDER_ROOT__|${WAYFINDER_ROOT}|g" "$CLUSTER_CONFIG" > "$RENDERED_CONFIG"

# Also override the cluster name in case user customized it
sed -i.bak "s|^name: wayfinder-.*|name: ${CLUSTER_NAME}|" "$RENDERED_CONFIG"
rm -f "${RENDERED_CONFIG}.bak"

verbose "Rendered config written to $RENDERED_CONFIG"
echo -e "${GREEN}  ✅ Template rendered (${PROFILE} profile)${NC}"

if [ "$VERBOSE" = true ]; then
    echo ""
    verbose "--- Rendered config preview (first 15 lines) ---"
    head -15 "$RENDERED_CONFIG" | sed 's/^/   /'
    echo -e "${DIM}   ...${NC}"
fi

echo ""

# =============================================================================
# Step 4: Check for existing cluster
# =============================================================================
echo -e "${CYAN}Step 4: Cluster management${NC}"

verbose "Checking if cluster '$CLUSTER_NAME' already exists..."

if kind get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}$"; then
    echo -e "${YELLOW}  Cluster '$CLUSTER_NAME' already exists.${NC}"
    read -p "  Delete and recreate? (y/N): " confirm
    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        verbose "Deleting existing cluster..."
        echo "  Deleting existing cluster..."
        kind delete cluster --name "$CLUSTER_NAME"
        echo -e "${GREEN}  ✅ Cluster deleted${NC}"
    else
        echo -e "${YELLOW}  Using existing cluster. Reapplying manifests.${NC}"

        tutorial "Reusing existing cluster - we'll just reapply manifests." \
                 "This is faster and preserves any existing data in the cluster."

        echo ""
        echo -e "${CYAN}Step 5: Applying manifests to existing cluster${NC}"

        verbose "Applying namespaces..."
        kubectl apply -f "${KIND_DIR}/namespaces.yaml"

        verbose "Running: kubectl apply -k $K8S_MANIFESTS"
        kubectl apply -k "$K8S_MANIFESTS"
        echo -e "${GREEN}  ✅ Manifests applied${NC}"

        if [ "$SKIP_WAIT" = false ]; then
            echo ""
            echo -e "${CYAN}Step 6: Waiting for pods${NC}"
            verbose "Running: kubectl wait --for=condition=ready pod --all -n observability"
            echo "  Waiting up to 180s for all pods to be ready..."
            if kubectl wait --for=condition=ready pod --all -n observability --timeout=180s; then
                echo -e "${GREEN}  ✅ All pods ready${NC}"
            else
                echo -e "${RED}  Some pods not ready. Check with: kubectl get pods -n observability${NC}"
            fi
        fi

        echo ""
        echo -e "${GREEN}=== Cluster Ready ===${NC}"
        kubectl get pods -n observability
        exit 0
    fi
else
    verbose "No existing cluster found. Will create new one."
fi

# =============================================================================
# Step 5: Create cluster
# =============================================================================
echo ""
echo -e "${CYAN}Step 5: Creating Kind cluster${NC}"

tutorial "Kind creates Docker containers that act as Kubernetes nodes." \
         "The control-plane runs the K8s API server, scheduler, and controllers." \
         "Worker nodes run your actual workloads (pods)."

verbose "Running: kind create cluster --config $RENDERED_CONFIG"
echo "  Creating '$CLUSTER_NAME' ($PROFILE profile)..."

kind create cluster --config "$RENDERED_CONFIG"

echo -e "${GREEN}  ✅ Cluster '$CLUSTER_NAME' created${NC}"

verbose "Cluster nodes:"
if [ "$VERBOSE" = true ]; then
    kubectl get nodes -o wide 2>/dev/null | sed 's/^/   /'
fi

echo ""

# =============================================================================
# Step 6: Apply namespaces and observability manifests
# =============================================================================
echo -e "${CYAN}Step 6: Deploying observability stack${NC}"

tutorial "The observability stack consists of:" \
         "  - Grafana: Dashboards and visualization (port 3000)" \
         "  - Tempo: Distributed tracing backend (port 3200)"

tutorial "  - Mimir: Prometheus-compatible metrics backend (port 9009)" \
         "  - Loki: Log aggregation (port 3100)" \
         "  - Alloy: OpenTelemetry collector - receives OTLP on port 4317"

verbose "Applying namespaces..."
kubectl apply -f "${KIND_DIR}/namespaces.yaml"

verbose "Running: kubectl apply -k $K8S_MANIFESTS"
kubectl apply -k "$K8S_MANIFESTS"

echo -e "${GREEN}  ✅ Observability manifests applied${NC}"

verbose "Resources created:"
if [ "$VERBOSE" = true ]; then
    kubectl get all -n observability 2>/dev/null | grep -E "^(NAME|pod/|service/|deployment)" | sed 's/^/   /'
fi

echo ""

# =============================================================================
# Step 7: Wait for pods
# =============================================================================
if [ "$SKIP_WAIT" = false ]; then
    echo -e "${CYAN}Step 7: Waiting for pods to be ready${NC}"

    tutorial "Pods need time to:" \
             "  - Pull container images from Docker Hub (first run only)" \
             "  - Initialize and pass health checks"

    verbose "Waiting for all pods in 'observability' namespace..."
    echo "  Waiting for images to pull and pods to start..."

    for i in {1..36}; do
        READY=$(kubectl get pods -n observability --no-headers 2>/dev/null | grep -c "Running" || echo "0")
        TOTAL=$(kubectl get pods -n observability --no-headers 2>/dev/null | wc -l | tr -d ' ')

        if [ "$VERBOSE" = true ]; then
            echo -ne "  Pods ready: $READY/$TOTAL (${i}0s elapsed)"
            PENDING=$(kubectl get pods -n observability --no-headers 2>/dev/null | grep -c "Pending" || echo "0")
            INIT=$(kubectl get pods -n observability --no-headers 2>/dev/null | grep -c "Init" || echo "0")
            if [ "$PENDING" -gt 0 ] || [ "$INIT" -gt 0 ]; then
                echo -ne " [Pending: $PENDING, Init: $INIT]"
            fi
            echo -ne "\r"
        else
            echo -ne "  Pods ready: $READY/$TOTAL (${i}0s elapsed)\r"
        fi

        if kubectl wait --for=condition=ready pod --all -n observability --timeout=10s &>/dev/null; then
            echo ""
            echo -e "${GREEN}  ✅ All pods ready${NC}"
            break
        fi

        if [ $i -eq 36 ]; then
            echo ""
            echo -e "${YELLOW}  Timeout waiting for pods. Some may still be starting.${NC}"
            verbose "Check status with: kubectl get pods -n observability"
            verbose "Check events with: kubectl get events -n observability --sort-by='.lastTimestamp'"
        fi
    done
else
    echo -e "${YELLOW}Step 7: Skipped (--skip-wait)${NC}"
    tutorial "Skipping wait - pods will continue starting in background." \
             "Use 'kubectl get pods -n observability -w' to watch progress."
fi

echo ""

# =============================================================================
# Step 8: Verify services
# =============================================================================
echo -e "${CYAN}Step 8: Verifying services${NC}"

tutorial "Services are exposed via NodePort -> Kind port mappings -> localhost." \
         "This lets you access Grafana at localhost:3000 from your browser," \
         "and send OTLP telemetry to localhost:4317 from your applications."

verbose "Waiting 2s for services to bind to ports..."
sleep 2

check_port() {
    local name=$1
    local port=$2
    local description=$3

    verbose "Checking $name on port $port..."
    if nc -z localhost "$port" 2>/dev/null; then
        echo -e "${GREEN}  ✅ $name (localhost:$port)${NC}"
        if [ "$TUTORIAL" = true ] && [ -n "$description" ]; then
            echo -e "${DIM}      $description${NC}"
        fi
        return 0
    else
        echo -e "${YELLOW}  -- $name (localhost:$port) - not ready yet${NC}"
        return 1
    fi
}

check_port "Grafana" 3000 "Dashboards UI - login with admin/admin"
check_port "Tempo" 3200 "Trace queries via HTTP API"
check_port "Mimir" 9009 "Prometheus-compatible metrics API"
check_port "Loki" 3100 "Log queries via HTTP API"
check_port "OTLP gRPC" 4317 "Send traces/metrics/logs here from your apps"
check_port "OTLP HTTP" 4318 "Alternative OTLP ingestion over HTTP"
check_port "Alloy UI" 12345 "Alloy debugging and pipeline status"

echo ""

# =============================================================================
# Summary
# =============================================================================
echo -e "${GREEN}=== Setup Complete ===${NC}"
echo ""
echo "Cluster:  $CLUSTER_NAME"
echo "Profile:  $PROFILE"
echo "Context:  kind-$CLUSTER_NAME"

if [ "$TUTORIAL" = true ]; then
    echo ""
    echo -e "${BLUE}+-- Architecture Overview -----------------------------------------------+${NC}"
    echo -e "${BLUE}|${NC}                                                                        ${BLUE}|${NC}"
    echo -e "${BLUE}|${NC}  Your App --OTLP--> Alloy (4317) --> Tempo (traces)                   ${BLUE}|${NC}"
    echo -e "${BLUE}|${NC}                         |          --> Mimir (metrics)                 ${BLUE}|${NC}"
    echo -e "${BLUE}|${NC}                         |          --> Loki (logs)                     ${BLUE}|${NC}"
    echo -e "${BLUE}|${NC}                         |                                              ${BLUE}|${NC}"
    echo -e "${BLUE}|${NC}  Browser <---------- Grafana (3000) <-- queries all three              ${BLUE}|${NC}"
    echo -e "${BLUE}|${NC}                                                                        ${BLUE}|${NC}"
    echo -e "${BLUE}+------------------------------------------------------------------------+${NC}"
fi

echo ""
echo -e "${CYAN}Pod Status:${NC}"
kubectl get pods -n observability
echo ""
echo -e "${CYAN}Access URLs:${NC}"
echo "  Grafana:    http://localhost:3000  (admin/admin)"
echo "  Tempo:      http://localhost:3200"
echo "  Mimir:      http://localhost:9009"
echo "  Loki:       http://localhost:3100"
echo "  OTLP gRPC:  localhost:4317"
echo "  OTLP HTTP:  localhost:4318"
echo "  Alloy UI:   http://localhost:12345"
echo ""
echo -e "${CYAN}Next Steps:${NC}"
echo "  1. Activate venv:    source ${WAYFINDER_ROOT}/.venv/bin/activate"
echo "  2. Seed metrics:     contextcore install verify --endpoint localhost:4317"
echo "  3. Open dashboard:   open http://localhost:3000/d/cc-core-installation-status"

if [ "$TUTORIAL" = true ]; then
    echo ""
    echo -e "${BLUE}+-- What 'contextcore install verify' does ------------------------------+${NC}"
    echo -e "${BLUE}|${NC} 1. Checks all infrastructure components are accessible                ${BLUE}|${NC}"
    echo -e "${BLUE}|${NC} 2. Emits metrics via OTLP to Alloy -> Mimir                           ${BLUE}|${NC}"
    echo -e "${BLUE}|${NC} 3. Populates the Installation Status dashboard with real data         ${BLUE}|${NC}"
    echo -e "${BLUE}+------------------------------------------------------------------------+${NC}"
fi

echo ""
echo -e "${CYAN}Useful Commands:${NC}"
echo "  make kind-status              # Check pod status"
echo "  make kind-seed                # Seed installation metrics"
echo "  make kind-down                # Delete cluster"
echo "  kubectl logs -n observability -l app=grafana   # View logs"
