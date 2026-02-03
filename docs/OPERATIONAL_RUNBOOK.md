# Wayfinder Operational Runbook

Quick reference for operating the Wayfinder observability stack.

## Quick Reference

```bash
make doctor      # Preflight checks before starting
make up          # Start stack (runs doctor first)
make down        # Stop stack (preserves data)
make health      # One-line health status per component
make smoke-test  # Validate entire stack
make backup      # Create timestamped backup
make destroy     # Delete stack (auto-backup + confirmation)
```

## Environment Notice

All operations target the `observability` namespace. For Kind clusters, the default cluster name is `wayfinder-dev`.

## Daily Operations

### Starting the Stack

```bash
# Always run doctor first
make doctor

# Start all services with persistent storage
make up

# Verify everything is working
make health
make smoke-test
```

### Checking Health

```bash
# Quick status check
make health

# Detailed component status
contextcore ops health

# Full validation suite
make smoke-test
```

### Stopping Safely

```bash
# Stop but keep data (safe to restart later)
make down

# Check what data exists
make storage-status
```

## Component URLs

| Component | URL | Purpose |
|-----------|-----|---------|
| Grafana | http://localhost:3000 | Dashboards and visualization |
| Tempo | http://localhost:3200 | Trace backend |
| Mimir | http://localhost:9009 | Metrics backend |
| Loki | http://localhost:3100 | Log aggregation |
| OTLP gRPC | localhost:4317 | Telemetry ingestion (gRPC) |
| OTLP HTTP | localhost:4318 | Telemetry ingestion (HTTP) |

## Backup and Restore

### Creating Backups

```bash
# Create timestamped backup
make backup

# Or via CLI with custom location
contextcore ops backup --output ./my-backups
```

Backups include:
- Grafana dashboards
- Grafana datasources
- Wayfinder state

### Listing Backups

```bash
contextcore ops backups
```

### Restoring from Backup

```bash
# Restore specific backup
make restore BACKUP=backups/20260117-120000

# Or via CLI
contextcore ops restore backups/20260117-120000
```

## Alert Runbooks

These sections are referenced by alert `runbook_url` annotations. Each
alert links here via anchor (e.g., `#otlp-exporter-failure`).

### OTLP Exporter Failure

**Alert:** `ContextCoreExporterFailure` | **Severity:** critical

**Symptoms:**
- Dashboard data stops updating
- `contextcore` service logs contain OTLP export errors
- No new spans appearing in Tempo

**Diagnosis:**
```bash
# Check for export errors in logs
docker compose logs loki 2>&1 | grep -i "export.*fail\|otlp.*error"

# Verify OTLP endpoint is reachable
curl -s http://localhost:4317 || echo "OTLP endpoint unreachable"

# Check Alloy health (OTLP receiver)
curl -s http://localhost:12345/ready

# Verify Tempo is accepting traces
curl -s http://localhost:3200/ready
```

**Remediation:**
1. If Alloy is down: `docker compose restart alloy`
2. If Tempo is down: `docker compose restart tempo`
3. If network issue: check `docker network inspect contextcore`
4. If persistent: check `OTEL_EXPORTER_OTLP_ENDPOINT` env var

### Span State Loss

**Alert:** `ContextCoreSpanStateLoss` | **Severity:** critical

**Symptoms:**
- Tasks show incomplete data after controller restart
- In-flight spans missing from Tempo
- State persistence errors in logs

**Diagnosis:**
```bash
# Check for state persistence errors
docker compose logs 2>&1 | grep -i "state.*persist\|span.*state.*lost"

# Verify state file exists (if using file-based persistence)
ls -la data/contextcore/state/ 2>/dev/null || echo "No state directory"

# Check ConfigMap state (K8s)
kubectl get configmap contextcore-state -n observability -o yaml 2>/dev/null
```

**Remediation:**
1. If state file missing: restart ContextCore controller (it will recreate)
2. If ConfigMap missing: `kubectl create configmap contextcore-state -n observability`
3. If persistent: check disk space and permissions on state directory
4. After recovery: verify in-flight tasks with `contextcore task list --status in_progress`

### Insight Latency

**Alert:** `ContextCoreInsightLatencyHigh` | **Severity:** warning

**Symptoms:**
- Agent insight queries returning slowly (> 500ms P99)
- Dashboard panels for agent context loading slowly
- Tempo query latency increased

**Diagnosis:**
```bash
# Check Tempo query performance
curl -s http://localhost:3200/metrics | grep tempo_query_frontend

# Check Mimir for the metric
curl -s 'http://localhost:9009/prometheus/api/v1/query?query=histogram_quantile(0.99,sum(rate(contextcore_insight_query_duration_milliseconds_bucket[5m]))by(le))'

# Verify Tempo compactor is running
curl -s http://localhost:3200/ready
```

**Remediation:**
1. If Tempo is overloaded: check `data/tempo/` size, consider retention settings
2. If query is unoptimized: check TraceQL query for broad scans
3. If cache is cold: wait for cache warmup after restart
4. If persistent: consider increasing Tempo memory limits

### Task Stalled

**Alert:** `ContextCoreTaskStalled` | **Severity:** warning

**Symptoms:**
- Task has not had a status change in over 24 hours
- Sprint progress appears stuck
- Task appears in "in_progress" state without recent events

**Diagnosis:**
```bash
# Query for the stalled task in Tempo
# (replace TASK_ID with the task from alert labels)
curl -s 'http://localhost:3200/api/search?q={task.id="TASK_ID"}'

# Check recent task events in Loki
curl -s 'http://localhost:3100/loki/api/v1/query_range' \
  --data-urlencode 'query={service="contextcore"} | json | event="task.status_changed" | task_id="TASK_ID"' \
  --data-urlencode 'limit=10'

# List tasks by status
contextcore task list --status in_progress
```

**Remediation:**
1. If task is blocked: check for blockers with `contextcore task show TASK_ID`
2. If task is abandoned: update status to `cancelled` or reassign
3. If task is actively worked but not updated: remind assignee to update status
4. If false positive: task may be a long-running task — adjust threshold or add exception

---

## Troubleshooting

### Port Conflicts

If `make doctor` shows ports in use:

```bash
# Find what's using a port
lsof -i :3000

# Option 1: Stop the conflicting service
# Option 2: Modify docker-compose.yaml ports
```

### Container Won't Start

```bash
# Check container logs
make logs-grafana
make logs-tempo
make logs-mimir
make logs-loki

# Check Docker daemon
docker info

# Verify disk space
df -h
```

### Data Corruption

```bash
# Create backup of current state
make backup

# Stop stack
make down

# Clear corrupted data (specific component)
rm -rf data/tempo/*   # Traces
rm -rf data/mimir/*   # Metrics
rm -rf data/loki/*    # Logs
rm -rf data/grafana/* # Dashboards (restore from backup!)

# Restart
make up

# Restore dashboards
make restore BACKUP=backups/latest
```

### Health Check Failures

```bash
# Component-specific health endpoints
curl http://localhost:3000/api/health        # Grafana
curl http://localhost:3200/ready             # Tempo
curl http://localhost:9009/ready             # Mimir
curl http://localhost:3100/ready             # Loki

# Check container status
docker compose ps
```

## Recovery Procedures

### Complete Stack Recovery

```bash
# 1. Stop everything
make down

# 2. Clear all data (if needed)
make storage-clean

# 3. Start fresh
make up

# 4. Restore dashboards from backup
contextcore ops backups          # List available backups
make restore BACKUP=backups/xxx  # Restore latest
```

### Recovering from Accidental Deletion

If containers or data were accidentally deleted:

```bash
# 1. Check if data directory still exists
ls -la data/

# 2. If data exists, just restart
make up

# 3. If data is gone, restore from backup
make up
contextcore ops backups
make restore BACKUP=backups/latest
```

### Moving to New Machine

```bash
# On old machine
make backup
# Copy backups/ directory to new machine

# On new machine
git clone <repo>
make up
make restore BACKUP=backups/xxx
```

## Data Persistence

All data is stored in `./data/`:

```
data/
├── grafana/     # Dashboards, datasources, preferences
├── tempo/       # Trace data (spans)
├── mimir/       # Metrics data (time series)
└── loki/        # Log data
```

### Data Retention

| Component | Default Retention | Config Location |
|-----------|-------------------|-----------------|
| Tempo | 48 hours | tempo/tempo.yaml |
| Mimir | Unlimited (local) | mimir/mimir.yaml |
| Loki | 7 days | loki/loki.yaml |

### Checking Data Size

```bash
make storage-status
# Or
du -sh data/*
```

## Destructive Operations

### make destroy

This command:
1. Creates automatic backup
2. Prompts for confirmation (type "yes")
3. Stops containers
4. Removes volumes

```bash
make destroy
# Output:
# Creating backup before destroy...
# [backup output]
#
# WARNING: This will destroy all data!
# Type 'yes' to confirm: yes
# [destruction proceeds]
```

### Clearing Storage

```bash
# Show what will be deleted
make storage-status

# Clean (requires confirmation)
make storage-clean
```

## CLI Reference

### Doctor (Preflight)

```bash
contextcore ops doctor              # Full check
contextcore ops doctor --no-ports   # Skip port check
contextcore ops doctor --no-docker  # Skip Docker check
```

### Health

```bash
contextcore ops health              # All components
contextcore ops health --no-otlp    # Skip OTLP check
```

### Smoke Test

```bash
contextcore ops smoke-test          # Full suite
contextcore ops smoke-test --list   # Show available tests
```

### Backup/Restore

```bash
contextcore ops backup                        # Default location
contextcore ops backup --output ./backups     # Custom location
contextcore ops backups                       # List backups
contextcore ops restore ./backups/20260117    # Restore specific
```

## Environment Variables

```bash
# Telemetry export
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317

# Grafana authentication (if changed from defaults)
export GRAFANA_USER=admin
export GRAFANA_PASSWORD=admin
```

## Logs

### View Logs

```bash
# All services
docker compose logs -f

# Specific service
make logs-grafana
make logs-tempo
make logs-mimir
make logs-loki
```

### Common Log Issues

| Pattern | Cause | Fix |
|---------|-------|-----|
| `connection refused` | Service not ready | Wait or restart |
| `permission denied` | Volume permissions | `sudo chown -R $USER data/` |
| `disk full` | Storage exceeded | Clear old data or add disk |
| `port already in use` | Conflict | `make doctor` to identify |
