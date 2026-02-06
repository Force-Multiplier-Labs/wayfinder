# Wayfinder Setup Script (Windows PowerShell)
# Equivalent of Makefile targets for Windows users.
#
# Usage:
#   .\setup.ps1 help        Show all available commands
#   .\setup.ps1 full-setup  Complete setup (up + wait + seed)
#   .\setup.ps1 up          Start the stack (runs doctor first)
#   .\setup.ps1 down        Stop (preserve data)
#   .\setup.ps1 destroy     Delete stack (auto-backup, confirm)
#   .\setup.ps1 health      Check component health
#   .\setup.ps1 smoke-test  Validate entire stack
#   .\setup.ps1 test [scope] Run tests (core, fox, rabbit, mole, all)
#   .\setup.ps1 logs <svc>  Follow container logs (tempo, mimir, loki, grafana)
#
# Requires: Docker Desktop with WSL2 backend for best performance.

param(
    [Parameter(Position = 0)]
    [string]$Command = "help",
    [switch]$Debug
)

$ErrorActionPreference = "Stop"

# Debug + progress helpers
$ScriptStart = Get-Date
$DebugMode = $Debug -or ($env:CONTEXTCORE_DEBUG -eq "1")

function Write-Phase([int]$Step, [int]$Total, [string]$Message) {
    $elapsed = [int]((Get-Date) - $ScriptStart).TotalSeconds
    Write-Host ("[{0}/{1}] {2} (elapsed {3}s)" -f $Step, $Total, $Message, $elapsed) -ForegroundColor Cyan
}

# Configuration
$ComposeFile = "docker-compose.yaml"
$DataDir = "data"
$GrafanaUrl = if ($env:GRAFANA_URL) { $env:GRAFANA_URL } else { "http://localhost:3000" }
$GrafanaUser = if ($env:GRAFANA_USER) { $env:GRAFANA_USER } else { "admin" }
$GrafanaPassword = if ($env:GRAFANA_PASSWORD) { $env:GRAFANA_PASSWORD } else { "admin" }
$RequiredPorts = @(3000, 3100, 3200, 9009, 4317, 4318)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

function Write-Status($icon, $message) {
    if ($icon -eq "pass") { Write-Host "  OK  $message" -ForegroundColor Green }
    elseif ($icon -eq "fail") { Write-Host "  FAIL  $message" -ForegroundColor Red }
    elseif ($icon -eq "warn") { Write-Host "  WARN  $message" -ForegroundColor Yellow }
    else { Write-Host "  $message" }
}

function Test-Port([int]$Port) {
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $tcp.Connect("127.0.0.1", $Port)
        $tcp.Close()
        return $true
    } catch {
        return $false
    }
}

function Test-Url([string]$Url) {
    try {
        $null = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
        return $true
    } catch {
        return $false
    }
}

# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

function Invoke-Doctor {
    Write-Host "`n=== Preflight Check ===" -ForegroundColor Cyan


    Write-Host "`nChecking required tools..."
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        Write-Status "pass" "docker"
    } else {
        Write-Status "fail" "docker not found"
    }
    try {
        docker compose version 2>&1 | Out-Null
        Write-Status "pass" "docker compose"
    } catch {
        Write-Status "fail" "docker compose not found"
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        Write-Status "pass" "python"
    } else {
        Write-Status "fail" "python not found (install from python.org or via winget)"
    }

    if (Get-Command contextcore -ErrorAction SilentlyContinue) {
        Write-Status "pass" "contextcore CLI"
    } else {
        Write-Status "warn" "contextcore CLI not found (is .venv activated?)"
    }

    Write-Host "`nChecking Docker daemon..."
    try {
        docker info 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Status "pass" "Docker is running"
        } else {
            Write-Status "fail" "Docker is not running — start Docker Desktop"
        }
    } catch {
        Write-Status "fail" "Docker is not running — start Docker Desktop"
    }

    Write-Host "`nChecking port availability..."
    foreach ($port in $RequiredPorts) {
        if (Test-Port $port) {
            Write-Status "fail" "Port $port is in use"
        } else {
            Write-Status "pass" "Port $port is available"
        }
    }

    Write-Host "`nChecking data directories..."
    foreach ($dir in @("tempo", "mimir", "loki", "grafana", "alertmanager")) {
        $path = Join-Path $DataDir $dir
        if (Test-Path $path) {
            Write-Status "pass" "$path exists"
        } else {
            Write-Status "warn" "$path will be created"
        }
    }

    Write-Host "`n=== Preflight Complete ===" -ForegroundColor Cyan
}

function Invoke-Up {
    Write-Phase 1 3 "Preflight checks"
    Invoke-Doctor

    Write-Host "`n=== Starting Wayfinder Stack ===" -ForegroundColor Cyan
    if ($DebugMode) {
        Write-Host "Compose file: $ComposeFile"
        Write-Host "Data dir: $DataDir"
    }


    # Create data directories
    foreach ($dir in @("tempo", "mimir", "loki", "grafana", "alertmanager")) {
        $path = Join-Path $DataDir $dir
        if (-not (Test-Path $path)) {
            New-Item -ItemType Directory -Path $path -Force | Out-Null
        }
    }

    if (Test-Path $ComposeFile) {
        docker compose -f $ComposeFile up -d
        if ($DebugMode) {
            docker compose -f $ComposeFile ps
        }
        Write-Host "Stack started. Run '.\setup.ps1 health' to verify." -ForegroundColor Green
    } else {
        Write-Host "No $ComposeFile found." -ForegroundColor Yellow
    }
}

function Invoke-Down {
    Write-Host "`n=== Stopping Wayfinder Stack ===" -ForegroundColor Cyan
    if (Test-Path $ComposeFile) {
        docker compose -f $ComposeFile down
        Write-Host "Stack stopped. Data preserved in $DataDir/." -ForegroundColor Green
        Write-Host "Run '.\setup.ps1 up' to restart."
    } else {
        Write-Host "No $ComposeFile found." -ForegroundColor Yellow
    }
}

function Invoke-Status {
    Write-Host "`n=== Container Status ===" -ForegroundColor Cyan
    if (Test-Path $ComposeFile) {
        docker compose -f $ComposeFile ps
    } else {
        docker ps --filter "name=tempo" --filter "name=mimir" --filter "name=loki" --filter "name=grafana" --filter "name=alloy"
    }
}

function Invoke-Health {
    Write-Host "`n=== Component Health ===" -ForegroundColor Cyan

    $checks = @(
        @{ Name = "Grafana";      Url = "http://localhost:3000/api/health" },
        @{ Name = "Tempo";        Url = "http://localhost:3200/ready" },
        @{ Name = "Mimir";        Url = "http://localhost:9009/ready" },
        @{ Name = "Loki";         Url = "http://localhost:3100/ready" },
        @{ Name = "Alloy";        Url = "http://localhost:12345/ready" }
    )

    foreach ($check in $checks) {
        $label = $check.Name.PadRight(12)
        if (Test-Url $check.Url) {
            Write-Host "  ${label} Ready" -ForegroundColor Green
        } else {
            Write-Host "  ${label} Not Ready" -ForegroundColor Red
        }
    }

    # OTLP port checks
    $otlpLabel = "OTLP (gRPC)".PadRight(12)
    if (Test-Port 4317) {
        Write-Host "  ${otlpLabel} Listening (Alloy)" -ForegroundColor Green
    } else {
        Write-Host "  ${otlpLabel} Not Listening" -ForegroundColor Red
    }
    $httpLabel = "OTLP (HTTP)".PadRight(12)
    if (Test-Port 4318) {
        Write-Host "  ${httpLabel} Listening (Alloy)" -ForegroundColor Green
    } else {
        Write-Host "  ${httpLabel} Not Listening" -ForegroundColor Red
    }
}

function Invoke-SmokeTest {
    Write-Host "`n=== Smoke Test ===" -ForegroundColor Cyan

    $passed = 0
    $total = 7

    # 1-5: Service health
    $services = @(
        @{ Num = 1; Name = "Grafana"; Url = "http://localhost:3000/api/health" },
        @{ Num = 2; Name = "Tempo";   Url = "http://localhost:3200/ready" },
        @{ Num = 3; Name = "Mimir";   Url = "http://localhost:9009/ready" },
        @{ Num = 4; Name = "Loki";    Url = "http://localhost:3100/ready" },
        @{ Num = 5; Name = "Alloy";   Url = "http://localhost:12345/ready" }
    )
    foreach ($svc in $services) {
        Write-Host "$($svc.Num). Checking $($svc.Name)..."
        if (Test-Url $svc.Url) {
            Write-Status "pass" "$($svc.Name) responding"
            $passed++
        } else {
            Write-Status "fail" "$($svc.Name) not accessible"
        }
    }

    # 6: Datasources
    Write-Host "6. Checking Grafana datasources..."
    try {
        $cred = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("${GrafanaUser}:${GrafanaPassword}"))
        $resp = Invoke-WebRequest -Uri "$GrafanaUrl/api/datasources" -Headers @{ Authorization = "Basic $cred" } -UseBasicParsing -TimeoutSec 5
        if ($resp.Content -match "tempo|mimir|loki") {
            Write-Status "pass" "Datasources configured"
            $passed++
        } else {
            Write-Status "warn" "Datasources may need provisioning"
        }
    } catch {
        Write-Status "warn" "Datasources may need provisioning"
    }

    # 7: CLI
    Write-Host "7. Checking Wayfinder CLI..."
    try {
        $env:PYTHONPATH = "./src"
        python -c "from contextcore import TaskTracker; print('ok')" 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Status "pass" "Wayfinder CLI available"
            $passed++
        } else {
            Write-Status "fail" "Wayfinder CLI not installed"
        }
    } catch {
        Write-Status "fail" "Wayfinder CLI not installed"
    }

    Write-Host "`n=== Smoke Test Complete: $passed/$total passed ===" -ForegroundColor Cyan
}

function Invoke-WaitReady {
    Write-Host "`n=== Waiting for Services ===" -ForegroundColor Cyan


    $timeout = 60
    $interval = 2
    $elapsed = 0

    while ($elapsed -lt $timeout) {
        $allReady = $true
        foreach ($url in @(
            "http://localhost:3000/api/health",
            "http://localhost:3200/ready",
            "http://localhost:9009/ready",
            "http://localhost:3100/ready",
            "http://localhost:12345/ready"
        )) {
            if (-not (Test-Url $url)) {
                $allReady = $false
                break
            }
        }
        if ($allReady) {
            Write-Host "All services ready!" -ForegroundColor Green
            return $true
        }
        Write-Host "  Waiting... ($elapsed/$timeout seconds)"
        Start-Sleep -Seconds $interval
        $elapsed += $interval
    }
    Write-Host "Timeout waiting for services" -ForegroundColor Red
    return $false
}

function Invoke-SeedMetrics {
    Write-Host "`n=== Seeding Installation Metrics ===" -ForegroundColor Cyan
    Write-Phase 3 3 "Seeding installation metrics"

    
    if (-not (Get-Command contextcore -ErrorAction SilentlyContinue)) {
        Write-Host "Error: contextcore CLI not found." -ForegroundColor Red
        Write-Host "Please activate your virtual environment:"
        Write-Host "  .venv\Scripts\Activate.ps1"
        return
    }

    Write-Host "Running installation verification with telemetry export..."

    $env:PYTHONPATH = "./src"
    contextcore install verify --endpoint localhost:4317

    Write-Host "`nMetrics exported to Mimir via localhost:4317" -ForegroundColor Green
    Write-Host "Dashboard: $GrafanaUrl/d/cc-core-installation-status"
}

function Invoke-FullSetup {
    Write-Host "`n=== Full Setup ===" -ForegroundColor Cyan


    Invoke-Up
    if (Invoke-WaitReady) {
        Write-Phase 2 3 "Services ready"
        Invoke-SeedMetrics
        Write-Host "`n=== Full Setup Complete ===" -ForegroundColor Green
        Write-Host "`nWayfinder observability stack is ready!"
        Write-Host "`nDashboards available at: $GrafanaUrl"
        Write-Host "  - Installation Status: $GrafanaUrl/d/cc-core-installation-status"
        Write-Host "  - Project Portfolio:   $GrafanaUrl/d/cc-core-portfolio-overview"
        Write-Host "`nQuick commands:"
        Write-Host "  .\setup.ps1 health       - Check component health"
        Write-Host "  .\setup.ps1 smoke-test   - Validate entire stack"
        Write-Host "  .\setup.ps1 seed-metrics - Re-export installation metrics"
    } else {
        Write-Host "Setup incomplete - services did not become ready" -ForegroundColor Red
    }
}

# ---------------------------------------------------------------------------
# Destroy & Backup
# ---------------------------------------------------------------------------

function Invoke-Destroy {
    Write-Host "`n=== DESTROY Wayfinder Stack ===" -ForegroundColor Red
    Write-Host ""
    Write-Host "WARNING: This will delete all Wayfinder data!" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "The following will be destroyed:"
    Write-Host "  - All spans in Tempo ($DataDir/tempo)"
    Write-Host "  - All metrics in Mimir ($DataDir/mimir)"
    Write-Host "  - All logs in Loki ($DataDir/loki)"
    Write-Host "  - Grafana dashboards and settings ($DataDir/grafana)"
    Write-Host ""
    Write-Host "Creating backup before destroy..."
    try { Invoke-Backup } catch { Write-Host "Note: Backup may be incomplete" -ForegroundColor Yellow }
    Write-Host ""
    $confirm = Read-Host "Are you sure? Type 'yes' to confirm"
    if ($confirm -ne "yes") {
        Write-Host "Aborted."
        return
    }
    if (Test-Path $ComposeFile) {
        docker compose -f $ComposeFile down -v
    }
    if (Test-Path $DataDir) {
        Remove-Item -Recurse -Force $DataDir
    }
    Write-Host "Stack destroyed. Run '.\setup.ps1 up' for fresh start." -ForegroundColor Green
}

function Invoke-Backup {
    Write-Host "`n=== Creating Backup ===" -ForegroundColor Cyan
    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $backupDir = "backups/$timestamp"
    New-Item -ItemType Directory -Path "$backupDir/dashboards" -Force | Out-Null
    New-Item -ItemType Directory -Path "$backupDir/datasources" -Force | Out-Null
    Write-Host "Backup directory: $backupDir"
    Write-Host ""

    # Export dashboards
    Write-Host "Exporting Grafana dashboards..."
    try {
        $cred = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("${GrafanaUser}:${GrafanaPassword}"))
        $headers = @{ Authorization = "Basic $cred" }
        $search = Invoke-WebRequest -Uri "$GrafanaUrl/api/search?type=dash-db" -Headers $headers -UseBasicParsing -TimeoutSec 5
        $dashboards = $search.Content | ConvertFrom-Json
        foreach ($dash in $dashboards) {
            $uid = $dash.uid
            $detail = Invoke-WebRequest -Uri "$GrafanaUrl/api/dashboards/uid/$uid" -Headers $headers -UseBasicParsing -TimeoutSec 5
            $detail.Content | Out-File -FilePath "$backupDir/dashboards/$uid.json" -Encoding utf8
        }
        Write-Status "pass" "$($dashboards.Count) dashboards exported"
    } catch {
        Write-Status "warn" "Grafana not accessible, skipping dashboard export"
    }

    # Export datasources
    Write-Host "Exporting Grafana datasources..."
    try {
        $ds = Invoke-WebRequest -Uri "$GrafanaUrl/api/datasources" -Headers $headers -UseBasicParsing -TimeoutSec 5
        $ds.Content | Out-File -FilePath "$backupDir/datasources/datasources.json" -Encoding utf8
        Write-Status "pass" "Datasources exported"
    } catch {
        Write-Status "warn" "Could not export datasources"
    }

    # Manifest
    @{ created_at = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ"); version = "1.0" } |
        ConvertTo-Json | Out-File -FilePath "$backupDir/manifest.json" -Encoding utf8

    Write-Host "`nBackup complete: $backupDir" -ForegroundColor Green
}

function Invoke-Restore {
    param([string]$BackupPath)
    if (-not $BackupPath) {
        Write-Host "Usage: .\setup.ps1 restore <backup-path>" -ForegroundColor Red
        Write-Host ""
        Write-Host "Available backups:"
        if (Test-Path "backups") {
            Get-ChildItem "backups" -Directory | ForEach-Object { Write-Host "  $($_.FullName)" }
        } else {
            Write-Host "  No backups found"
        }
        return
    }
    if (-not (Test-Path $BackupPath)) {
        Write-Host "Backup directory not found: $BackupPath" -ForegroundColor Red
        return
    }
    Write-Host "`n=== Restoring from $BackupPath ===" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Importing dashboards..."
    try {
        $cred = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("${GrafanaUser}:${GrafanaPassword}"))
        $headers = @{ Authorization = "Basic $cred"; "Content-Type" = "application/json" }
        foreach ($f in Get-ChildItem "$BackupPath/dashboards/*.json" -ErrorAction SilentlyContinue) {
            Write-Host "  Importing: $($f.Name)"
            $raw = Get-Content $f.FullName -Raw | ConvertFrom-Json
            $body = @{ dashboard = if ($raw.dashboard) { $raw.dashboard } else { $raw }; overwrite = $true } | ConvertTo-Json -Depth 20
            Invoke-WebRequest -Uri "$GrafanaUrl/api/dashboards/db" -Method Post -Headers $headers -Body $body -UseBasicParsing -TimeoutSec 10 | Out-Null
        }
        Write-Status "pass" "Dashboards imported"
    } catch {
        Write-Status "warn" "Could not import dashboards"
    }
    Write-Host "`nRestore complete" -ForegroundColor Green
    Write-Host "Run '.\setup.ps1 smoke-test' to verify"
}

# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

function Invoke-Verify {
    Write-Host "`n=== Quick Verification ===" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Data directories:"
    foreach ($dir in @("tempo", "mimir", "loki", "grafana", "alertmanager")) {
        $path = Join-Path $DataDir $dir
        if (Test-Path $path) {
            $size = "{0:N2} MB" -f ((Get-ChildItem $path -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum / 1MB)
            Write-Status "pass" "$path ($size)"
        } else {
            Write-Status "fail" "$path missing"
        }
    }
    Write-Host ""
    Write-Host "Containers:"
    $running = (docker ps --filter "name=tempo" --filter "name=mimir" --filter "name=loki" --filter "name=grafana" --filter "name=alloy" --format "{{.Names}}" 2>$null | Measure-Object -Line).Lines
    if ($running -gt 0) {
        Write-Status "pass" "$running container(s) running"
    } else {
        Write-Status "warn" "No observability containers running"
    }
}

function Invoke-StorageStatus {
    Write-Host "`n=== Storage Status ===" -ForegroundColor Cyan
    Write-Host ""
    if (Test-Path $DataDir) {
        Write-Host "Data directory: $DataDir"
        Write-Host ""
        foreach ($dir in Get-ChildItem $DataDir -Directory -ErrorAction SilentlyContinue) {
            $size = "{0:N2} MB" -f ((Get-ChildItem $dir.FullName -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum / 1MB)
            Write-Host "  $($dir.Name)  $size"
        }
        Write-Host ""
        $total = "{0:N2} MB" -f ((Get-ChildItem $DataDir -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum / 1MB)
        Write-Host "Total: $total"
    } else {
        Write-Host "Data directory does not exist yet." -ForegroundColor Yellow
        Write-Host "Run '.\setup.ps1 up' to create it."
    }
}

function Invoke-StorageClean {
    Write-Host "`n=== Storage Clean ===" -ForegroundColor Red
    Write-Host ""
    Write-Host "WARNING: This will delete all observability data!" -ForegroundColor Yellow
    Write-Host ""
    if (Test-Path $DataDir) {
        Invoke-StorageStatus
        Write-Host ""
    }
    $confirm = Read-Host "Delete all data in $DataDir/? Type 'yes' to confirm"
    if ($confirm -ne "yes") {
        Write-Host "Aborted."
        return
    }
    Remove-Item -Recurse -Force $DataDir
    Write-Host "Storage cleaned. Run '.\setup.ps1 up' to recreate." -ForegroundColor Green
}

# ---------------------------------------------------------------------------
# Logs
# ---------------------------------------------------------------------------

function Invoke-Logs {
    param([string]$Service)
    $container = docker ps --filter "name=$Service" --format "{{.Names}}" 2>$null | Select-Object -First 1
    if ($container) {
        docker logs -f $container
    } else {
        Write-Host "$Service container not running" -ForegroundColor Yellow
    }
}

# ---------------------------------------------------------------------------
# Development
# ---------------------------------------------------------------------------

function Invoke-Install {
    Write-Host "`n=== Installing Packages ===" -ForegroundColor Cyan
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        uv sync --all-packages --all-extras
    } else {
        Write-Host "uv not found. Install with: winget install astral-sh.uv" -ForegroundColor Red
    }
}

function Invoke-Test {
    param([string]$Scope = "core")
    switch ($Scope) {
        "core"   { uv run pytest tests/ -v }
        "fox"    { uv run pytest wayfinder-fox/tests/ -v }
        "rabbit" { uv run pytest contextcore-rabbit/tests/ -v }
        "mole"   { uv run pytest contextcore-mole/tests/ -v }
        "all"    {
            uv run pytest tests/ -v
            uv run pytest wayfinder-fox/tests/ -v
            uv run pytest contextcore-rabbit/tests/ -v
            uv run pytest contextcore-mole/tests/ -v
        }
        default  { Write-Host "Unknown test scope: $Scope. Use: core, fox, rabbit, mole, all" -ForegroundColor Red }
    }
}

function Invoke-Lint {
    Write-Host "`n=== Linting ===" -ForegroundColor Cyan
    uv run ruff check src/ wayfinder-fox/src/ contextcore-rabbit/src/ contextcore-mole/src/
}

function Invoke-Typecheck {
    Write-Host "`n=== Type Checking ===" -ForegroundColor Cyan
    uv run mypy src/contextcore
}

function Invoke-Build {
    Write-Host "`n=== Building ===" -ForegroundColor Cyan
    uv build
}

function Invoke-Clean {
    Write-Host "`n=== Cleaning Build Artifacts ===" -ForegroundColor Cyan
    foreach ($dir in @("build", "dist", "*.egg-info", "src/*.egg-info", ".venv")) {
        if (Test-Path $dir) {
            Remove-Item -Recurse -Force $dir
            Write-Host "  Removed $dir"
        }
    }
    Get-ChildItem -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
        ForEach-Object { Remove-Item -Recurse -Force $_.FullName }
    Write-Host "Clean complete." -ForegroundColor Green
}

# ---------------------------------------------------------------------------
# Dashboards
# ---------------------------------------------------------------------------

function Invoke-DashboardsProvision {
    Write-Host "`n=== Provisioning Dashboards ===" -ForegroundColor Cyan
    $env:PYTHONPATH = "./src"
    uv run python -m contextcore.cli dashboards provision
}

function Invoke-DashboardsList {
    Write-Host "`n=== Listing Dashboards ===" -ForegroundColor Cyan
    $env:PYTHONPATH = "./src"
    uv run python -m contextcore.cli dashboards list
}

# ---------------------------------------------------------------------------
# Kind Cluster
# ---------------------------------------------------------------------------

function Invoke-KindUp {
    Write-Host "`n=== Creating Kind Cluster ===" -ForegroundColor Cyan
    if (-not (Get-Command kind -ErrorAction SilentlyContinue)) {
        Write-Host "kind not found. Install with: winget install Kubernetes.kind" -ForegroundColor Red
        return
    }
    $clusterName = "wayfinder-dev"
    $existing = kind get clusters 2>&1
    if ($existing -contains $clusterName) {
        Write-Host "Kind cluster '$clusterName' already exists" -ForegroundColor Yellow
    } else {
        kind create cluster --name $clusterName
        Write-Host "Kind cluster '$clusterName' created" -ForegroundColor Green
    }
}

function Invoke-KindDown {
    Write-Host "`n=== Deleting Kind Cluster ===" -ForegroundColor Cyan
    if (-not (Get-Command kind -ErrorAction SilentlyContinue)) {
        Write-Host "kind not found." -ForegroundColor Red
        return
    }
    kind delete cluster --name "wayfinder-dev"
    Write-Host "Kind cluster deleted" -ForegroundColor Green
}

function Invoke-KindStatus {
    Write-Host "`n=== Kind Cluster Status ===" -ForegroundColor Cyan
    $clusterName = "wayfinder-dev"
    $existing = kind get clusters 2>&1
    if ($existing -contains $clusterName) {
        Write-Host "`nNodes:"
        kubectl get nodes --context "kind-$clusterName" 2>$null
        Write-Host "`nPods:"
        kubectl get pods -n observability --context "kind-$clusterName" 2>$null
    } else {
        Write-Host "Cluster '$clusterName' not found." -ForegroundColor Yellow
        Write-Host "Run '.\setup.ps1 kind-up' to create it."
    }
}

# ---------------------------------------------------------------------------
# Rules Validation
# ---------------------------------------------------------------------------

function Invoke-RulesValidate {
    Write-Host "`n=== Validating Recording Rules ===" -ForegroundColor Cyan
    Write-Host ""
    $passed = 0
    $total = 4
    $rules = @(
        @{ Label = "Loki recording rules"; Path = "loki/rules/fake/contextcore-rules.yaml" },
        @{ Label = "Loki alert rules";     Path = "loki/rules/fake/contextcore-alerts.yaml" },
        @{ Label = "Mimir recording rules"; Path = "mimir/rules/contextcore/rules.yaml" },
        @{ Label = "Mimir alert rules";     Path = "mimir/rules/contextcore/alerts.yaml" }
    )
    foreach ($rule in $rules) {
        Write-Host "$($rule.Label):"
        if (Test-Path $rule.Path) {
            try {
                $env:PYTHONPATH = "./src"
                python -c "import yaml; yaml.safe_load(open('$($rule.Path)'))" 2>&1 | Out-Null
                if ($LASTEXITCODE -eq 0) {
                    Write-Status "pass" "$($rule.Path) valid"
                    $passed++
                } else {
                    Write-Status "fail" "$($rule.Path) invalid YAML"
                }
            } catch {
                Write-Status "fail" "$($rule.Path) invalid YAML"
            }
        } else {
            Write-Status "fail" "$($rule.Path) not found"
        }
    }
    Write-Host "`n=== Rules Validation: $passed/$total passed ===" -ForegroundColor Cyan
}

# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------

function Invoke-Help {
    Write-Host @"

Wayfinder Setup (Windows)
=========================
Usage: .\setup.ps1 <command> [-Debug]

Quick Start:
  full-setup          Complete setup (up + wait-ready + seed-metrics)

Stack Management:
  up                  Start the stack (runs doctor first)
  down                Stop the stack (preserve data)
  destroy             Delete the stack (auto-backup first, requires confirmation)
  status              Show container status

Health & Validation:
  doctor              Run preflight checks
  health              Show component health
  smoke-test          Validate entire stack
  verify              Quick cluster health check (data dirs + containers)
  wait-ready          Wait for all services to be ready (60s timeout)
  seed-metrics        Run installation verification to populate dashboards

Backup & Restore:
  backup              Export Grafana dashboards/datasources to timestamped directory
  restore <path>      Restore from backup directory

Storage:
  storage-status      Show data directory sizes
  storage-clean       Delete all data (requires confirmation)

Logs:
  logs <service>      Follow container logs (tempo, mimir, loki, grafana, alloy)

Development:
  install             Install all workspace packages (uv sync)
  test [scope]        Run tests (core, fox, rabbit, mole, all)  [default: core]
  lint                Run ruff linting
  typecheck           Run mypy type checking
  build               Build package
  clean               Clean build artifacts

Dashboards:
  dashboards-provision  Provision Wayfinder dashboards to Grafana
  dashboards-list       List provisioned dashboards

Kind Cluster:
  kind-up             Create Kind dev cluster
  kind-down           Delete Kind dev cluster
  kind-status         Show Kind cluster pod status

Rules:
  rules-validate      Validate recording and alert rule YAML files

Info:
  help                Show this message

Environment Variables:
  GRAFANA_URL         Grafana URL       (default: http://localhost:3000)
  GRAFANA_USER        Grafana user      (default: admin)
  GRAFANA_PASSWORD    Grafana password  (default: admin)

Notes:
  - Docker Desktop with WSL2 backend is recommended.
  - For the full set of targets see the Makefile (requires WSL or Git Bash).
  - Use -Debug or CONTEXTCORE_DEBUG=1 for verbose output.
"@
}

# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

switch ($Command) {
    # Stack management
    "up"                  { Invoke-Up }
    "down"                { Invoke-Down }
    "destroy"             { Invoke-Destroy }
    "status"              { Invoke-Status }
    # Health & validation
    "doctor"              { Invoke-Doctor }
    "health"              { Invoke-Health }
    "smoke-test"          { Invoke-SmokeTest }
    "verify"              { Invoke-Verify }
    "wait-ready"          { Invoke-WaitReady }
    "seed-metrics"        { Invoke-SeedMetrics }
    "full-setup"          { Invoke-FullSetup }
    # Backup & restore
    "backup"              { Invoke-Backup }
    "restore"             { Invoke-Restore -BackupPath $args[0] }
    # Storage
    "storage-status"      { Invoke-StorageStatus }
    "storage-clean"       { Invoke-StorageClean }
    # Logs
    "logs"                { Invoke-Logs -Service $args[0] }
    # Development
    "install"             { Invoke-Install }
    "test"                { Invoke-Test -Scope $(if ($args[0]) { $args[0] } else { "core" }) }
    "lint"                { Invoke-Lint }
    "typecheck"           { Invoke-Typecheck }
    "build"               { Invoke-Build }
    "clean"               { Invoke-Clean }
    # Dashboards
    "dashboards-provision" { Invoke-DashboardsProvision }
    "dashboards-list"      { Invoke-DashboardsList }
    # Kind cluster
    "kind-up"             { Invoke-KindUp }
    "kind-down"           { Invoke-KindDown }
    "kind-status"         { Invoke-KindStatus }
    # Rules
    "rules-validate"      { Invoke-RulesValidate }
    # Help
    "help"                { Invoke-Help }
    default               { Write-Host "Unknown command: $Command. Run '.\setup.ps1 help' for usage." -ForegroundColor Red }
}
