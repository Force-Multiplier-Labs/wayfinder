"""
Installation Tracking tasks for Lead Contractor workflow.

Implements the Installation Tracking & Resume Plan from docs/INSTALLATION_TRACKING_PLAN.md.

Features:
- Feature 1: State File Infrastructure - install-state.sh with state management functions
- Feature 2: Step Executor Framework - Idempotent step execution pattern
- Feature 3: CLI Entry Point - create-cluster.sh with --resume/--repair/--status/--reset
- Feature 4: Metric Emission - curl-based metric push to Mimir (Python-free)
- Feature 5: Repair Mode - Step verification and recovery logic
- Feature 6: Dashboard Enhancement - Add step progress visualization panels
"""

from ..runner import Feature

# =============================================================================
# Feature 1: State File Infrastructure
# =============================================================================

STATE_FILE_TASK = """
Create the state file management infrastructure for ContextCore installation.

## Goal
Create a bash library `install-state.sh` that provides functions for managing
installation state in a JSON file, enabling resume and repair capabilities.

## Context
- This is for the Wayfinder project (ContextCore reference implementation)
- The script should be placed at scripts/install-state.sh
- State file location: ~/.contextcore/install-state.json
- Must work with bash 4.0+ and require only jq as dependency

## State File Schema
```json
{
  "version": "1.0",
  "cluster_name": "wayfinder-dev",
  "started_at": "2024-01-22T15:30:00Z",
  "updated_at": "2024-01-22T15:35:00Z",
  "steps": {
    "preflight": {
      "status": "completed",
      "completed_at": "2024-01-22T15:30:05Z",
      "attempts": 1
    },
    "cluster_create": {
      "status": "in_progress",
      "started_at": "2024-01-22T15:31:00Z",
      "attempts": 2
    }
  }
}
```

## Required Functions

1. **init_state(cluster_name)**: Initialize state directory and file
   - Create ~/.contextcore/ if not exists
   - Create initial state file if not exists
   - Set cluster_name and started_at
   - Don't overwrite existing state (preserve for resume)

2. **get_step_status(step_id)**: Return status of a step
   - Returns: "pending", "in_progress", "completed", or "failed"
   - Returns "pending" if step doesn't exist

3. **set_step_status(step_id, status)**: Update step status
   - Valid statuses: pending, in_progress, completed, failed
   - Set appropriate timestamp (started_at, completed_at)
   - Increment attempts counter
   - Update file's updated_at

4. **get_step_attempts(step_id)**: Return number of attempts for a step
   - Returns 0 if step doesn't exist

5. **should_skip_step(step_id)**: Check if step should be skipped in resume mode
   - Returns 0 (true) if status is "completed" AND $RESUME_MODE is true
   - Returns 1 (false) otherwise

6. **get_last_completed_step()**: Return ID of the last completed step
   - Based on completed_at timestamps
   - Returns empty string if no steps completed

7. **reset_state()**: Delete state file for fresh start

8. **show_state_summary()**: Print human-readable state summary
   - Show each step with status, timestamps, attempts
   - Colorize output (green=completed, yellow=in_progress, red=failed)

9. **export_state_json()**: Output state as JSON for programmatic use

## Implementation Requirements

1. Use jq for all JSON manipulation (atomic updates via temp file)
2. All functions should be idempotent
3. Handle missing state file gracefully
4. Support both macOS and Linux date commands
5. No external dependencies beyond bash and jq
6. Include shebang: #!/bin/bash
7. Set -euo pipefail for safety
8. Include usage documentation in comments

## Step IDs (predefined constants)
```bash
INSTALL_STEPS=(
    "preflight"
    "cluster_create"
    "manifests_apply"
    "pods_ready"
    "services_verify"
    "metrics_seed"
)
```

## Output Format
Provide the complete install-state.sh script ready to be sourced by other scripts.
Include clear section comments and inline documentation.
"""

# =============================================================================
# Feature 2: Step Executor Framework
# =============================================================================

STEP_EXECUTOR_TASK = """
Create a step executor framework for idempotent installation steps.

## Goal
Create a bash library `step-executor.sh` that provides a pattern for running
installation steps with automatic state tracking, retries, and error handling.

## Context
- This is for the ContextCore project
- The script should be placed at scripts/step-executor.sh
- Must source install-state.sh for state management
- Integrates with metric emission (Feature 4)

## Required Functions

1. **run_step(step_id, step_fn, idempotency_check_fn)**: Execute a step
   ```bash
   run_step "cluster_create" create_kind_cluster check_cluster_exists
   ```
   - If RESUME_MODE and step completed, skip with message
   - Run idempotency_check_fn first - if passes, mark complete and skip
   - Set status to "in_progress"
   - Emit metric (if available)
   - Run step_fn
   - On success: set "completed", emit metric
   - On failure: set "failed", emit metric, handle based on CONTINUE_ON_ERROR

2. **run_step_with_retry(step_id, step_fn, max_retries, delay_seconds)**: Retry on failure
   - Call run_step with retry wrapper
   - Exponential backoff (delay * 2^attempt)
   - Max retries configurable

3. **skip_step(step_id, reason)**: Explicitly skip a step
   - Log reason
   - Don't change state

4. **wait_for_condition(check_fn, timeout_seconds, interval_seconds)**: Wait for condition
   - Poll check_fn at interval
   - Return 0 on success, 1 on timeout
   - Log progress dots

5. **check_dependency(dep_step_id)**: Verify dependency step is completed
   - Return 0 if dep completed, 1 otherwise
   - Log error if dependency missing

## Logging Functions

1. **step_log(level, message)**: Structured logging
   - Levels: INFO, WARN, ERROR, DEBUG
   - Include timestamp and step context
   - Color-coded output

2. **verbose(message)**: Log only if VERBOSE=true

## Step Definition Pattern

```bash
# Define idempotency check
check_cluster_exists() {
    kind get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}$"
}

# Define step logic
create_kind_cluster() {
    kind create cluster --name "$CLUSTER_NAME" --config "$KIND_CONFIG"
}

# Execute with framework
run_step "cluster_create" create_kind_cluster check_cluster_exists
```

## Environment Variables

```bash
RESUME_MODE=${RESUME_MODE:-false}      # Skip completed steps
REPAIR_MODE=${REPAIR_MODE:-false}      # Re-verify all steps
CONTINUE_ON_ERROR=${CONTINUE_ON_ERROR:-false}
VERBOSE=${VERBOSE:-false}
DRY_RUN=${DRY_RUN:-false}             # Log but don't execute
MAX_STEP_RETRIES=${MAX_STEP_RETRIES:-3}
```

## Implementation Requirements

1. Source install-state.sh at the top
2. Use local variables to avoid pollution
3. Capture both stdout and stderr from step functions
4. Support nested steps (substeps)
5. Return meaningful exit codes (0=success, 1=step failed, 2=dependency failed)
6. Include timing information (step duration)

## Output Format
Provide the complete step-executor.sh script with clear documentation.
"""

# =============================================================================
# Feature 3: CLI Entry Point (create-cluster.sh)
# =============================================================================

CLI_ENTRY_TASK = """
Create the main installation CLI script with resume/repair capabilities.

## Goal
Create `create-cluster.sh` - the main entry point for ContextCore Kind cluster
installation with full resume, repair, and status checking capabilities.

## Context
- This is for the ContextCore project
- The script should be placed at scripts/create-cluster.sh
- Sources install-state.sh and step-executor.sh
- Cluster name: wayfinder-dev
- K8s manifests: k8s/observability/

## CLI Interface

```bash
Usage: create-cluster.sh [OPTIONS]

Options:
  --resume        Continue from last completed step (skip completed)
  --repair        Re-verify all steps and fix failures
  --status        Show installation status and exit
  --reset         Clear state and start fresh
  --verbose, -v   Enable verbose output
  --dry-run       Show what would be done without doing it
  --help, -h      Show this help message

Environment:
  CLUSTER_NAME    Cluster name (default: wayfinder-dev)
  KUBECONFIG      kubectl config (default: ~/.kube/config)
```

## Installation Steps

1. **preflight**: Check prerequisites (Docker, kind, kubectl, jq)
   - Always run (fast checks)
   - Fail with actionable error messages

2. **cluster_create**: Create Kind cluster
   - Idempotency: kind get clusters | grep CLUSTER_NAME
   - Uses k8s/observability/kind-config.yaml if exists

3. **manifests_apply**: Apply Kubernetes manifests
   - kubectl apply -k k8s/observability/
   - Idempotency: check key ConfigMaps/Services exist

4. **pods_ready**: Wait for pods to be Running
   - timeout: 5 minutes
   - Check all pods in observability namespace

5. **services_verify**: Verify services are accessible
   - Grafana: localhost:3000
   - Tempo: localhost:3200
   - Mimir: localhost:9009
   - Loki: localhost:3100

6. **metrics_seed**: Run ContextCore verification
   - contextcore install verify --endpoint localhost:4317
   - Seeds installation dashboard with initial metrics

## Required Functions

1. **show_banner()**: Display ContextCore ASCII art banner

2. **show_status()**: Display formatted installation status
   - Show each step with status emoji (✅ ✓ ⏳ ❌)
   - Show timestamps and duration
   - Show overall progress (e.g., "4/6 steps completed")

3. **preflight_checks()**: Verify prerequisites
   - Docker daemon running
   - kind installed
   - kubectl installed
   - jq installed (for state management)

4. **create_cluster()**: Create Kind cluster
   - Generate port-forward config
   - Create cluster with config

5. **apply_manifests()**: Apply k8s manifests
   - Create observability namespace
   - Apply kustomization

6. **wait_for_pods()**: Wait for all pods ready
   - kubectl wait --for=condition=Ready
   - Show progress

7. **verify_services()**: Check service accessibility
   - curl health endpoints
   - Report status

8. **seed_metrics()**: Run contextcore verification
   - Activate venv if exists
   - Run contextcore install verify

## Error Handling

- On failure, show diagnostic information
- Suggest repair command
- Save logs to ~/.contextcore/install.log

## Output Format
Provide the complete create-cluster.sh script ready for execution.
Include comprehensive help text and error messages.
"""

# =============================================================================
# Feature 4: Metric Emission (Python-Free)
# =============================================================================

METRIC_EMISSION_TASK = """
Create Python-free metric emission for installation progress.

## Goal
Create a bash library `install-metrics.sh` that emits installation metrics
to Mimir using curl, without requiring Python or the contextcore package.

## Context
- This is for the ContextCore project
- The script should be placed at scripts/install-metrics.sh
- Metrics should be visible in Grafana installation dashboard
- Must work before Python venv is activated

## Metric Definitions

1. **contextcore_install_step_status**: Gauge
   - Labels: step, cluster, status
   - Values: 0=pending, 1=in_progress, 2=completed, 3=failed
   - One metric per step

2. **contextcore_install_progress_ratio**: Gauge
   - Labels: cluster
   - Value: completed_steps / total_steps (0.0 to 1.0)

3. **contextcore_install_step_duration_seconds**: Gauge
   - Labels: step, cluster
   - Value: duration of step in seconds (set on completion)

4. **contextcore_install_step_attempts_total**: Counter
   - Labels: step, cluster
   - Value: number of attempts for step

5. **contextcore_install_started_timestamp**: Gauge
   - Labels: cluster
   - Value: Unix timestamp of installation start

## Required Functions

1. **init_metrics()**: Check if Mimir is accessible
   - curl -sf http://localhost:9009/ready
   - Set METRICS_ENABLED=true/false
   - Log status

2. **emit_metric(name, labels, value)**: Generic metric emit
   - Format: name{label1="val1",...} value
   - POST to Mimir's Prometheus import endpoint
   - Best-effort (don't fail on network errors)

3. **emit_step_started(step_id)**: Emit step started
   - status=1 (in_progress)
   - Update progress ratio

4. **emit_step_completed(step_id, duration_seconds)**: Emit step completed
   - status=2 (completed)
   - Emit duration metric
   - Update progress ratio

5. **emit_step_failed(step_id)**: Emit step failed
   - status=3 (failed)
   - Update progress ratio

6. **emit_all_step_status()**: Emit status for all steps
   - Read from state file
   - Emit batch of metrics

## Mimir Integration

Endpoint: http://localhost:9009/api/v1/import/prometheus
Format: Prometheus text exposition format

```bash
emit_metric() {
    local name=$1
    local labels=$2
    local value=$3

    if [ "$METRICS_ENABLED" != "true" ]; then
        return 0
    fi

    curl -sf --max-time 2 -X POST \\
        "http://localhost:9009/api/v1/import/prometheus" \\
        --data-binary "${name}{${labels}} ${value}" \\
        >/dev/null 2>&1 || true
}
```

## Environment Variables

```bash
MIMIR_URL=${MIMIR_URL:-http://localhost:9009}
METRICS_ENABLED=${METRICS_ENABLED:-auto}  # auto, true, false
CLUSTER_NAME=${CLUSTER_NAME:-wayfinder-dev}
```

## Implementation Requirements

1. All network calls are best-effort (don't fail installation)
2. Timeout all curl calls (max 2 seconds)
3. Batch metrics where possible to reduce calls
4. Include timestamp in metrics if required
5. Handle Mimir not being available gracefully
6. Log metric emission in verbose mode only

## Output Format
Provide the complete install-metrics.sh script ready to be sourced.
"""

# =============================================================================
# Feature 5: Repair Mode Implementation
# =============================================================================

REPAIR_MODE_TASK = """
Create repair mode logic for installation recovery.

## Goal
Create a bash library `install-repair.sh` that provides functions to verify
installation health and repair broken components without full reinstall.

## Context
- This is for the ContextCore project
- The script should be placed at scripts/install-repair.sh
- Sources install-state.sh and step-executor.sh
- Called when --repair flag is used

## Repair Philosophy

1. **Verify First**: Check current state before attempting repair
2. **Minimal Intervention**: Only fix what's actually broken
3. **Idempotent Actions**: Safe to run multiple times
4. **Diagnostic Output**: Tell user what was found and fixed

## Required Functions

1. **run_repair()**: Main repair entry point
   - Run verify_all_steps()
   - Repair failed steps
   - Report summary

2. **verify_all_steps()**: Check health of all steps
   - Returns list of unhealthy steps
   - Doesn't modify anything

3. **verify_step(step_id)**: Check health of single step
   - Run idempotency check for step
   - Return 0 if healthy, 1 if needs repair

4. **repair_step(step_id)**: Repair a single step
   - Diagnosis → Action → Verify
   - Return 0 on success, 1 on failure

## Per-Step Repair Logic

```bash
repair_preflight() {
    # Just re-run checks - these can't be "repaired" 
    # but should identify what's missing
    preflight_checks
}

repair_cluster_create() {
    if ! kind get clusters | grep -q "^${CLUSTER_NAME}$"; then
        echo "Cluster missing, recreating..."
        create_cluster
    else
        echo "Cluster exists, checking health..."
        kubectl cluster-info --context "kind-${CLUSTER_NAME}"
    fi
}

repair_manifests_apply() {
    echo "Reapplying manifests (idempotent)..."
    kubectl apply -k k8s/observability/
}

repair_pods_ready() {
    # Find unhealthy pods
    local unhealthy=$(kubectl get pods -n observability --no-headers \\
        | grep -vE "Running|Completed" | awk '{print $1}')
    
    if [ -n "$unhealthy" ]; then
        echo "Restarting unhealthy pods: $unhealthy"
        echo "$unhealthy" | xargs kubectl delete pod -n observability
        wait_for_pods
    fi
}

repair_services_verify() {
    # Check each service, report issues
    for svc in grafana:3000 tempo:3200 mimir:9009 loki:3100; do
        local name=${svc%:*}
        local port=${svc#*:}
        if ! curl -sf "http://localhost:${port}/ready" >/dev/null 2>&1; then
            echo "WARNING: $name not accessible on port $port"
            # Suggest port-forward or check logs
            echo "  Check: kubectl logs -n observability deploy/$name"
        fi
    done
}

repair_metrics_seed() {
    echo "Re-running metrics seed..."
    contextcore install verify --endpoint localhost:4317
}
```

## Diagnostic Functions

1. **diagnose_cluster()**: Check cluster health
   - kubectl cluster-info
   - Node status
   - Resource usage

2. **diagnose_pods()**: Check pod health
   - List all pods with status
   - Show logs for non-running pods
   - Check resource constraints

3. **diagnose_networking()**: Check connectivity
   - Service endpoints
   - Port forwards
   - DNS resolution

4. **generate_diagnostic_report()**: Create full report
   - Save to ~/.contextcore/diagnostic-report.txt
   - Include all diagnostic output

## Environment Variables

```bash
REPAIR_MODE=${REPAIR_MODE:-false}
REPAIR_AGGRESSIVE=${REPAIR_AGGRESSIVE:-false}  # Delete and recreate if needed
DIAGNOSTIC_LEVEL=${DIAGNOSTIC_LEVEL:-normal}   # normal, verbose, full
```

## Output Format
Provide the complete install-repair.sh script with comprehensive repair logic.
"""

# =============================================================================
# Feature 6: Dashboard Enhancement
# =============================================================================

DASHBOARD_TASK = """
Update the Installation Status Grafana dashboard with step progress visualization.

## Goal
Enhance grafana/provisioning/dashboards/json/installation.json to display
real-time installation step progress from the new metric emission system.

## Context
- This is for the ContextCore project
- Modify existing: grafana/provisioning/dashboards/json/installation.json
- New metrics from install-metrics.sh:
  - contextcore_install_step_status{step="...",cluster="..."}
  - contextcore_install_progress_ratio{cluster="..."}
  - contextcore_install_step_duration_seconds{step="...",cluster="..."}

## New Panels to Add

### Row: Installation Progress

1. **Overall Progress** (Stat panel)
   - Position: x=0, y=0, w=6, h=4
   - Query: `contextcore_install_progress_ratio{cluster="$cluster"} * 100`
   - Unit: percent
   - Thresholds: 0=red, 50=yellow, 100=green
   - Title: "Installation Progress"

2. **Current Step** (Stat panel)
   - Position: x=6, y=0, w=6, h=4
   - Query: Extract step name where status=1
   - Use value mapping for step names
   - Title: "Current Step"

3. **Steps Completed** (Stat panel)
   - Position: x=12, y=0, w=4, h=4
   - Query: `count(contextcore_install_step_status{cluster="$cluster"} == 2)`
   - Format: "X / 6"
   - Title: "Steps Completed"

4. **Failed Steps** (Stat panel)
   - Position: x=16, y=0, w=4, h=4
   - Query: `count(contextcore_install_step_status{cluster="$cluster"} == 3)`
   - Thresholds: 0=green, 1=red
   - Title: "Failed Steps"

5. **Installation Duration** (Stat panel)
   - Position: x=20, y=0, w=4, h=4
   - Query: `time() - contextcore_install_started_timestamp{cluster="$cluster"}`
   - Unit: duration (seconds)
   - Title: "Duration"

### Row: Step Timeline

6. **Step Status Timeline** (State timeline panel)
   - Position: x=0, y=4, w=24, h=6
   - Query: `contextcore_install_step_status{cluster="$cluster"}`
   - Legend: Step name
   - Value mappings:
     - 0 → "Pending" (gray)
     - 1 → "In Progress" (blue)
     - 2 → "Completed" (green)
     - 3 → "Failed" (red)
   - Title: "Installation Step Timeline"

### Row: Step Details

7. **Step Duration** (Bar gauge panel)
   - Position: x=0, y=10, w=12, h=6
   - Query: `contextcore_install_step_duration_seconds{cluster="$cluster"}`
   - Unit: seconds
   - Orientation: horizontal
   - Title: "Step Duration"

8. **Step Attempts** (Table panel)
   - Position: x=12, y=10, w=12, h=6
   - Query: `contextcore_install_step_attempts_total{cluster="$cluster"}`
   - Columns: Step, Attempts
   - Title: "Step Attempts"

## Dashboard Variables

Add if not exists:
```json
{
  "name": "cluster",
  "type": "query",
  "query": "label_values(contextcore_install_step_status, cluster)",
  "current": {"text": "wayfinder-dev", "value": "wayfinder-dev"},
  "refresh": 2
}
```

## Panel JSON Structure

Follow existing panel structure in the dashboard. Example:
```json
{
  "type": "stat",
  "title": "Installation Progress",
  "gridPos": {"h": 4, "w": 6, "x": 0, "y": 0},
  "targets": [{
    "expr": "contextcore_install_progress_ratio{cluster=\\"$cluster\\"} * 100",
    "legendFormat": "Progress",
    "refId": "A"
  }],
  "fieldConfig": {
    "defaults": {
      "unit": "percent",
      "thresholds": {
        "mode": "absolute",
        "steps": [
          {"color": "red", "value": null},
          {"color": "yellow", "value": 50},
          {"color": "green", "value": 100}
        ]
      }
    }
  },
  "options": {"reduceOptions": {"calcs": ["lastNotNull"]}}
}
```

## Output Format
Provide the complete updated installation.json dashboard file.
Preserve all existing panels and settings.
Add new row at the top for installation progress.
"""

# =============================================================================
# Feature Definitions
# =============================================================================

INSTALL_TRACKING_FEATURES = [
    Feature(
        task=STATE_FILE_TASK,
        name="InstallTracking_StateFile",
        output_subdir="install_tracking",
    ),
    Feature(
        task=STEP_EXECUTOR_TASK,
        name="InstallTracking_StepExecutor",
        output_subdir="install_tracking",
    ),
    Feature(
        task=CLI_ENTRY_TASK,
        name="InstallTracking_CLI",
        output_subdir="install_tracking",
    ),
    Feature(
        task=METRIC_EMISSION_TASK,
        name="InstallTracking_Metrics",
        output_subdir="install_tracking",
    ),
    Feature(
        task=REPAIR_MODE_TASK,
        name="InstallTracking_Repair",
        output_subdir="install_tracking",
    ),
    Feature(
        task=DASHBOARD_TASK,
        name="InstallTracking_Dashboard",
        output_subdir="install_tracking",
    ),
]
