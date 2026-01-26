# Session Log: Tempo Task Loading & Grafana Debugging

**Date:** 2026-01-26
**Author:** Claude Code (agent:claude-code)
**Related Project:** ContextCore, contextcore-mole
**Session Duration:** ~2 hours

---

## Executive Summary

This session documented the end-to-end process of loading task data into Tempo (where contextcore-mole recovers data from) and debugging why Grafana dashboards showed "No data." The findings are directly relevant to contextcore-mole's mission of recovering task data from Tempo exports.

**Key Outcomes:**
1. Successfully loaded 63 task spans into Tempo (11 beaver-lead-contractor + 52 dashboard-persistence)
2. Identified and fixed Grafana datasource UID mismatch causing silent "No data" failures
3. Discovered Tempo search API requires explicit time range for historical data
4. Documented 3 new lessons in Observability Lessons Learned

---

## Context: How This Relates to contextcore-mole

contextcore-mole recovers tasks from Tempo trace exports. This session explored:

1. **How tasks are stored in Tempo** - Understanding the span structure, attributes, and query patterns
2. **Why Tempo might return empty results** - Critical for debugging when mole's source data appears missing
3. **TraceQL query requirements** - Same queries mole would use to find task spans

**Data Flow:**
```
Task JSON files (plans/*.json)
    ↓
load_tasks_to_tempo.py (OTLP export)
    ↓
Tempo (stores as spans)
    ↓
Grafana dashboards / TraceQL queries / mole scan
    ↓
Task recovery
```

---

## What Was Done

### 1. Task Data Loading

**Source Files:**
- `plans/beaver-lead-contractor-tasks.json` - 11 tasks
- `plans/dashboard-persistence-tasks.json` - 52 tasks

**Loader Script:** `scripts/load_tasks_to_tempo.py`

**Command Used:**
```bash
python3 scripts/load_tasks_to_tempo.py --all --endpoint localhost:4317
```

**Output:**
```
Loading 2 task file(s) to localhost:4317
  Created 52 spans for project 'dashboard-persistence'
  Created 11 spans for project 'beaver-lead-contractor'
Total spans created: 63
```

**Key Insight for mole:** The task spans have these attributes:
- `resource.project.id` - Project identifier
- `span.task.id` - Task ID (e.g., "BLC-001")
- `span.task.title` - Task title
- `span.task.status` - Status (pending, backlog, done, cancelled)
- `span.task.type` - Type (story, task, epic)

### 2. Debugging "No Data" in Grafana Dashboards

**Problem:** Grafana Project Tasks dashboard showed empty panels despite 63 spans in Tempo.

**Investigation Steps:**

1. **Verified data in Tempo directly:**
   ```bash
   # Without time range - returned 0!
   curl -s "http://localhost:3200/api/search?limit=10"
   # Output: {"traces":[]}

   # With explicit time range - returned data!
   START=$(date -u -v-7d +%s)
   END=$(date -u +%s)
   curl -s "http://localhost:3200/api/search?start=${START}&end=${END}&limit=10"
   # Output: {"traces":[...10 traces...]}
   ```

2. **Checked Grafana datasource configuration:**
   ```bash
   curl -s -u admin:adminadminadmin 'http://localhost:3000/api/datasources'
   # Found: Tempo uid was "P214B5B846CF3925F" (auto-generated)
   # Dashboard expected: uid "tempo" (hardcoded)
   ```

3. **Identified root causes:**
   - Grafana provisioning auto-generates random UIDs unless explicitly set
   - Dashboard JSON used `"uid": "tempo"` but datasource had `"uid": "P214B5B846CF3925F"`
   - Tempo search API returns empty without explicit time range

### 3. Fixes Applied

#### Fix 1: Explicit Datasource UIDs in Provisioning

**File:** `k8s/observability/configs.yaml`

**Before (implicit UIDs):**
```yaml
datasources:
  - name: Tempo
    type: tempo
    url: http://tempo:3200
    # No uid specified - Grafana generates random one
```

**After (explicit UIDs):**
```yaml
datasources:
  - name: Loki
    uid: loki              # Explicit UID
    type: loki
    url: http://loki:3100

  - name: Mimir
    uid: mimir             # Explicit UID
    type: prometheus
    url: http://mimir:9009/prometheus

  - name: Tempo
    uid: tempo             # Explicit UID - matches dashboard JSON
    type: tempo
    url: http://tempo:3200
    jsonData:
      tracesToLogsV2:
        datasourceUid: loki   # Cross-reference uses explicit UID
      tracesToMetrics:
        datasourceUid: mimir  # Cross-reference uses explicit UID
```

#### Fix 2: Reset Grafana Database State

Grafana's SQLite database had stale datasource references causing "data source not found" during provisioning.

```bash
# Scale down, delete PVC, recreate, scale up
kubectl scale deployment grafana -n observability --replicas=0
kubectl delete pvc grafana-pvc -n observability
kubectl apply -f - <<EOF
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: grafana-pvc
  namespace: observability
spec:
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 1Gi
EOF
kubectl scale deployment grafana -n observability --replicas=1
```

#### Fix 3: Update Dashboard Datasource References

**Files Updated:**
- `grafana/provisioning/dashboards/squirrel/skills-browser.json`
- `grafana/provisioning/dashboards/squirrel/value-capabilities.json`
- `grafana/provisioning/dashboards/external/agent-trigger.json`

**Pattern Applied:**
```bash
# Replace auto-generated UIDs with explicit ones
sed -i '' 's/P214B5B846CF3925F/tempo/g' <file>.json  # Tempo
sed -i '' 's/P8E80F9AEF21F6940/loki/g' <file>.json   # Loki
sed -i '' 's/PAE45454D0EDB9216/mimir/g' <file>.json  # Mimir
```

### 4. Verification

**Data accessible via Grafana proxy:**
```bash
START=$(date -u -v-7d +%s)
END=$(date -u +%s)
curl -s -u admin:adminadminadmin \
  "http://localhost:3000/api/datasources/proxy/uid/tempo/api/search?start=${START}&end=${END}&limit=5"
# Output: {"traces":[...5 traces with task data...]}
```

**Dashboard URL:** `http://localhost:3000/d/contextcore-tasks?var-project=beaver-lead-contractor`

---

## Lessons Learned (Persisted)

Three lessons were added to `craft/Lessons_Learned/observability/`:

### Leg 3 #19: Provisioned Datasource UID Consistency
- Always set explicit `uid:` in Grafana datasource provisioning YAML
- Auto-generated UIDs like `P214B5B846CF3925F` don't match dashboard expectations

### Leg 3 #20: Grafana Database State vs Provisioning Conflicts
- Manually created datasources in SQLite conflict with provisioning changes
- Solution: Delete Grafana PVC to reset for clean provisioning

### Leg 5 #16: Tempo Search API Requires Explicit Time Range
- `/api/search` returns empty without `start` and `end` parameters
- Use Unix seconds: `start=${START}&end=${END}`
- This is the #2 cause of "No data" after missing `span.` prefix

---

## Relevance to contextcore-mole

### Task Span Schema Confirmed

The loaded tasks follow the schema documented in `CLAUDE.md`:

```json
{
  "name": "task:BLC-001",
  "attributes": [
    {"key": "task.id", "value": {"stringValue": "BLC-001"}},
    {"key": "task.title", "value": {"stringValue": "Add workflow run endpoint"}},
    {"key": "task.status", "value": {"stringValue": "pending"}},
    {"key": "task.type", "value": {"stringValue": "task"}},
    {"key": "project.id", "value": {"stringValue": "beaver-lead-contractor"}}
  ]
}
```

### Query Patterns for mole

When `mole scan` queries Tempo exports (or live Tempo), it should:

1. **Always include time range** when using Tempo API:
   ```python
   import time
   start = int(time.time() - 7 * 24 * 3600)  # 7 days ago
   end = int(time.time())
   params = {"start": start, "end": end, "limit": 1000}
   ```

2. **Use `span.` prefix** for dotted attributes in TraceQL:
   ```
   {span.task.status = "cancelled"} | select(span.task.id, span.task.title)
   ```

3. **Handle both export formats:**
   - Tempo JSON export (batches → scopeSpans → spans)
   - TraceQL API response (traces → spanSets → spans)

### Projects with Recoverable Tasks

| Project ID | Tasks | Status |
|------------|-------|--------|
| beaver-lead-contractor | 11 | All pending |
| dashboard-persistence | 52 | All backlog |

---

## Infrastructure State After Session

### Running Services

| Service | URL | Status |
|---------|-----|--------|
| Grafana | http://localhost:3000 | Running (admin/adminadminadmin) |
| Tempo | http://localhost:3200 | Ready |
| Loki | http://localhost:3100 | Ready |
| Mimir | http://localhost:9009 | Ready |
| Rabbit | http://localhost:8082 | Running |

### Datasource UIDs (Standardized)

| Datasource | UID | Type |
|------------|-----|------|
| Tempo | `tempo` | tempo |
| Loki | `loki` | loki |
| Mimir | `mimir` | prometheus |

### Kubernetes Context

```bash
kubectl config current-context
# Output: kind-o11y-dev
```

---

## Commands Reference

### Load Tasks to Tempo
```bash
python3 scripts/load_tasks_to_tempo.py --all --endpoint localhost:4317
```

### Query Tempo Directly
```bash
# With time range
START=$(date -u -v-7d +%s)
END=$(date -u +%s)
curl -s "http://localhost:3200/api/search?start=${START}&end=${END}&limit=10"

# With TraceQL filter
curl -s -G "http://localhost:3200/api/search" \
  --data-urlencode 'q={resource.project.id = "beaver-lead-contractor"}' \
  --data-urlencode "start=${START}" \
  --data-urlencode "end=${END}"
```

### Query via Grafana Proxy
```bash
curl -s -u admin:adminadminadmin \
  "http://localhost:3000/api/datasources/proxy/uid/tempo/api/search?start=${START}&end=${END}&limit=5"
```

### Check Grafana Datasources
```bash
curl -s -u admin:adminadminadmin 'http://localhost:3000/api/datasources' | jq '.[].uid'
```

### Reset Grafana State
```bash
kubectl scale deployment grafana -n observability --replicas=0
kubectl delete pvc grafana-pvc -n observability
# ... recreate PVC ...
kubectl scale deployment grafana -n observability --replicas=1
```

---

## Files Modified

| File | Change |
|------|--------|
| `k8s/observability/configs.yaml` | Added explicit UIDs to datasources |
| `grafana/provisioning/dashboards/squirrel/skills-browser.json` | Updated datasource UIDs |
| `grafana/provisioning/dashboards/squirrel/value-capabilities.json` | Updated datasource UIDs |
| `grafana/provisioning/dashboards/external/agent-trigger.json` | Updated datasource UIDs |
| `grafana/provisioning/dashboards/core/project-tasks.json` | Updated Rabbit API URL to 8082 |

---

## Next Steps for contextcore-mole

Based on this session's findings:

1. **Implement time range handling** in `parser.py`:
   - When scanning Tempo exports, don't assume recent data
   - Support `--since` and `--until` CLI flags

2. **Add TraceQL query builder** for live Tempo queries:
   - Include `span.` prefix automatically for task attributes
   - Always pass time range parameters

3. **Handle datasource UID variations** in export files:
   - Tempo exports may contain different UID formats
   - Normalize during parsing

4. **Test with the loaded data**:
   - Use `beaver-lead-contractor` project as test fixture (11 tasks)
   - Use `dashboard-persistence` project for larger scale testing (52 tasks)

---

*Session log generated by Claude Code as part of ContextCore development workflow.*
