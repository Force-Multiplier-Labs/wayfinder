# Wayfinder Setup Script (Windows PowerShell)
# Equivalent of Makefile targets for Windows users.
#
# Usage:
#   .\setup.ps1 up          Start the stack (runs doctor first)
#   .\setup.ps1 down        Stop (preserve data)
#   .\setup.ps1 health      Check component health
#   .\setup.ps1 smoke-test  Validate entire stack
#   .\setup.ps1 doctor      Preflight checks
#   .\setup.ps1 status      Show container status
#   .\setup.ps1 wait-ready  Wait for services to be ready
#   .\setup.ps1 seed-metrics Seed installation metrics
#   .\setup.ps1 full-setup  Complete setup (up + wait + seed)
#   .\setup.ps1 help        Show available commands
#
# Requires: Docker Desktop with WSL2 backend for best performance.

param(
    [Parameter(Position = 0)]
    [string]$Command = "help"
)

$ErrorActionPreference = "Stop"

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
    Invoke-Doctor

    Write-Host "`n=== Starting Wayfinder Stack ===" -ForegroundColor Cyan

    # Create data directories
    foreach ($dir in @("tempo", "mimir", "loki", "grafana", "alertmanager")) {
        $path = Join-Path $DataDir $dir
        if (-not (Test-Path $path)) {
            New-Item -ItemType Directory -Path $path -Force | Out-Null
        }
    }

    if (Test-Path $ComposeFile) {
        docker compose -f $ComposeFile up -d
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

function Invoke-Help {
    Write-Host @"

Wayfinder Setup (Windows)
=========================
Usage: .\setup.ps1 <command>

Quick Start:
  full-setup    Complete setup (up + wait-ready + seed-metrics)

Stack Management:
  up            Start the stack (runs doctor first)
  down          Stop the stack (preserve data)
  status        Show container status

Health & Validation:
  doctor        Run preflight checks
  health        Show component health
  smoke-test    Validate entire stack
  wait-ready    Wait for all services to be ready (60s timeout)
  seed-metrics  Run installation verification to populate dashboards

Info:
  help          Show this message

Environment Variables:
  GRAFANA_URL         Grafana URL       (default: http://localhost:3000)
  GRAFANA_USER        Grafana user      (default: admin)
  GRAFANA_PASSWORD    Grafana password  (default: admin)

Notes:
  - Docker Desktop with WSL2 backend is recommended.
  - For the full set of targets see the Makefile (requires WSL or Git Bash).
"@
}

# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

switch ($Command) {
    "up"           { Invoke-Up }
    "down"         { Invoke-Down }
    "status"       { Invoke-Status }
    "doctor"       { Invoke-Doctor }
    "health"       { Invoke-Health }
    "smoke-test"   { Invoke-SmokeTest }
    "wait-ready"   { Invoke-WaitReady }
    "seed-metrics" { Invoke-SeedMetrics }
    "full-setup"   { Invoke-FullSetup }
    "help"         { Invoke-Help }
    default        { Write-Host "Unknown command: $Command. Run '.\setup.ps1 help' for usage." -ForegroundColor Red }
}
