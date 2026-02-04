# Wayfinder Makefile
# Reference implementation of the ContextCore metadata standard
#
# Container engine agnostic — works with Docker or Podman.
# Override with: make up CONTAINER_ENGINE=podman
#
# Usage:
#   make help         Show available commands
#   make doctor       Preflight checks
#   make up           Start the stack (runs doctor first)
#   make down         Stop (preserve data)
#   make destroy      Delete (auto-backup, confirm)
#   make health       One-line status per component
#   make smoke-test   Validate entire stack
#   make backup       Export state to timestamped directory

.PHONY: help doctor up down destroy status health smoke-test verify backup restore \
        storage-status storage-clean logs-tempo logs-mimir logs-loki logs-grafana \
        test test-fox test-all lint typecheck build install install-core install-fox \
        clean dashboards-provision dashboards-list \
        seed-metrics full-setup wait-ready install-verify \
        kind-up kind-down kind-status kind-seed \
        rules-validate rules-status \
        jsonnet-generate jsonnet-test jsonnet-lint

# Container engine detection (Docker or Podman — override with CONTAINER_ENGINE=podman)
CONTAINER_ENGINE ?= $(shell which docker >/dev/null 2>&1 && echo docker || (which podman >/dev/null 2>&1 && echo podman || echo docker))
COMPOSE_CMD ?= $(shell \
	if [ "$(CONTAINER_ENGINE)" = "podman" ]; then \
		which podman-compose >/dev/null 2>&1 && echo "podman-compose" || echo "podman compose"; \
	else \
		docker compose version >/dev/null 2>&1 && echo "docker compose" || echo "docker-compose"; \
	fi)
ENGINE_LABEL := $(shell echo $(CONTAINER_ENGINE) | sed 's/.*/\u&/' 2>/dev/null || echo $(CONTAINER_ENGINE))

# Configuration
COMPOSE_FILE := docker-compose.yaml
REQUIRED_PORTS := 3000 3100 3200 9009 4317 4318
BACKUP_DIR := backups/$(shell date +%Y%m%d-%H%M%S)
DATA_DIR := data

# Environment configuration (can be overridden)
GRAFANA_URL ?= http://localhost:3000
GRAFANA_USER ?= admin
GRAFANA_PASSWORD ?= admin
OTLP_ENDPOINT ?= localhost:4317

# Colors for output
GREEN := \033[0;32m
RED := \033[0;31m
YELLOW := \033[0;33m
CYAN := \033[0;36m
NC := \033[0m # No Color

# === Preflight Checks ===

doctor: ## Check system readiness (ports, container engine, tools)
	@echo "$(CYAN)=== Preflight Check ===$(NC)"
	@echo ""
	@echo "Container engine: $(CONTAINER_ENGINE) (compose: $(COMPOSE_CMD))"
	@echo ""
	@echo "Checking required tools..."
	@which $(CONTAINER_ENGINE) >/dev/null 2>&1 && echo "$(GREEN)✅ $(CONTAINER_ENGINE)$(NC)" || echo "$(RED)❌ $(CONTAINER_ENGINE) not found$(NC)"
	@$(COMPOSE_CMD) version >/dev/null 2>&1 && echo "$(GREEN)✅ $(COMPOSE_CMD)$(NC)" || echo "$(RED)❌ $(COMPOSE_CMD) not found$(NC)"
	@which python3 >/dev/null 2>&1 && echo "$(GREEN)✅ python3$(NC)" || echo "$(RED)❌ python3 not found$(NC)"
	@echo ""
	@echo "Checking $(ENGINE_LABEL) daemon..."
	@$(CONTAINER_ENGINE) info >/dev/null 2>&1 && echo "$(GREEN)✅ $(ENGINE_LABEL) is running$(NC)" || echo "$(RED)❌ $(ENGINE_LABEL) is not running$(NC)"
	@echo ""
	@echo "Checking port availability..."
	@for port in $(REQUIRED_PORTS); do \
		if python3 -c "import socket; s=socket.socket(); s.settimeout(1); exit(0 if s.connect_ex(('127.0.0.1',$$port)) == 0 else 1)" 2>/dev/null; then \
			echo "$(RED)❌ Port $$port is in use$(NC)"; \
		else \
			echo "$(GREEN)✅ Port $$port is available$(NC)"; \
		fi; \
	done
	@echo ""
	@echo "Checking data directories..."
	@for dir in tempo mimir loki grafana; do \
		if [ -d "$(DATA_DIR)/$$dir" ]; then \
			echo "$(GREEN)✅ $(DATA_DIR)/$$dir exists$(NC)"; \
		else \
			echo "$(YELLOW)⚠️  $(DATA_DIR)/$$dir will be created$(NC)"; \
		fi; \
	done
	@echo ""
	@echo "$(CYAN)=== Preflight Complete ===$(NC)"

# === Stack Management ===

up: doctor ## Start the stack (runs doctor first, creates data dirs)
	@echo ""
	@echo "$(CYAN)=== Starting Wayfinder Stack ===$(NC)"
	@mkdir -p $(DATA_DIR)/tempo $(DATA_DIR)/mimir $(DATA_DIR)/loki $(DATA_DIR)/grafana
	@if [ -f "$(COMPOSE_FILE)" ]; then \
		$(COMPOSE_CMD) -f $(COMPOSE_FILE) up -d; \
		echo "$(GREEN)Stack started. Run 'make health' to verify.$(NC)"; \
	else \
		echo "$(YELLOW)No $(COMPOSE_FILE) found. Using CLI to verify OTLP endpoint...$(NC)"; \
		echo "Stack can be started with: $(COMPOSE_CMD) up -d"; \
	fi

down: ## Stop the stack (preserves data)
	@echo "$(CYAN)=== Stopping Wayfinder Stack ===$(NC)"
	@if [ -f "$(COMPOSE_FILE)" ]; then \
		$(COMPOSE_CMD) -f $(COMPOSE_FILE) down; \
		echo "$(GREEN)Stack stopped. Data preserved in $(DATA_DIR)/.$(NC)"; \
		echo "Run 'make up' to restart."; \
	else \
		echo "No $(COMPOSE_FILE) found."; \
	fi

destroy: ## Delete the stack (auto-backup first, requires confirmation)
	@echo "$(RED)=== DESTROY Wayfinder Stack ===$(NC)"
	@echo ""
	@echo "$(YELLOW)WARNING: This will delete all Wayfinder data!$(NC)"
	@echo ""
	@echo "The following will be destroyed:"
	@echo "  - All spans in Tempo ($(DATA_DIR)/tempo)"
	@echo "  - All metrics in Mimir ($(DATA_DIR)/mimir)"
	@echo "  - All logs in Loki ($(DATA_DIR)/loki)"
	@echo "  - Grafana dashboards and settings ($(DATA_DIR)/grafana)"
	@echo ""
	@echo "Creating backup before destroy..."
	@$(MAKE) backup 2>/dev/null || echo "$(YELLOW)Note: Backup may be incomplete$(NC)"
	@echo ""
	@read -p "Are you sure? Type 'yes' to confirm: " confirm && [ "$$confirm" = "yes" ] || (echo "Aborted." && exit 1)
	@if [ -f "$(COMPOSE_FILE)" ]; then \
		$(COMPOSE_CMD) -f $(COMPOSE_FILE) down -v; \
	fi
	@rm -rf $(DATA_DIR)
	@echo "$(GREEN)Stack destroyed. Run 'make up' for fresh start.$(NC)"

status: ## Show container status
	@echo "$(CYAN)=== Container Status ===$(NC)"
	@if [ -f "$(COMPOSE_FILE)" ]; then \
		$(COMPOSE_CMD) -f $(COMPOSE_FILE) ps; \
	else \
		$(CONTAINER_ENGINE) ps --filter "name=contextcore" --filter "name=tempo" --filter "name=mimir" --filter "name=loki" --filter "name=grafana" --filter "name=alloy"; \
	fi

# === Health & Validation ===

health: ## Show one-line health status per component
	@echo "$(CYAN)=== Component Health ===$(NC)"
	@printf "Grafana:     "; curl -sf http://localhost:3000/api/health >/dev/null 2>&1 && echo "$(GREEN)✅ Ready$(NC)" || echo "$(RED)❌ Not Ready$(NC)"
	@printf "Tempo:       "; curl -sf http://localhost:3200/ready >/dev/null 2>&1 && echo "$(GREEN)✅ Ready$(NC)" || echo "$(RED)❌ Not Ready$(NC)"
	@printf "Mimir:       "; curl -sf http://localhost:9009/ready >/dev/null 2>&1 && echo "$(GREEN)✅ Ready$(NC)" || echo "$(RED)❌ Not Ready$(NC)"
	@printf "Loki:        "; curl -sf http://localhost:3100/ready >/dev/null 2>&1 && echo "$(GREEN)✅ Ready$(NC)" || echo "$(RED)❌ Not Ready$(NC)"
	@printf "Alloy:       "; curl -sf http://localhost:12345/ready >/dev/null 2>&1 && echo "$(GREEN)✅ Ready$(NC)" || echo "$(RED)❌ Not Ready$(NC)"
	@printf "OTLP (gRPC): "; python3 -c "import socket; s=socket.socket(); s.settimeout(1); exit(0 if s.connect_ex(('127.0.0.1',4317))==0 else 1)" 2>/dev/null && echo "$(GREEN)✅ Listening (Alloy)$(NC)" || echo "$(RED)❌ Not Listening$(NC)"
	@printf "OTLP (HTTP): "; python3 -c "import socket; s=socket.socket(); s.settimeout(1); exit(0 if s.connect_ex(('127.0.0.1',4318))==0 else 1)" 2>/dev/null && echo "$(GREEN)✅ Listening (Alloy)$(NC)" || echo "$(RED)❌ Not Listening$(NC)"

smoke-test: ## Validate entire stack is working after deployment
	@echo "$(CYAN)=== Smoke Test ===$(NC)"
	@echo ""
	@PASSED=0; TOTAL=7; \
	echo "1. Checking Grafana..."; \
	curl -sf $(GRAFANA_URL)/api/health >/dev/null 2>&1 && { echo "$(GREEN)   ✅ Grafana responding$(NC)"; PASSED=$$((PASSED+1)); } || echo "$(RED)   ❌ Grafana not accessible$(NC)"; \
	echo "2. Checking Tempo..."; \
	curl -sf http://localhost:3200/ready >/dev/null 2>&1 && { echo "$(GREEN)   ✅ Tempo responding$(NC)"; PASSED=$$((PASSED+1)); } || echo "$(RED)   ❌ Tempo not accessible$(NC)"; \
	echo "3. Checking Mimir..."; \
	curl -sf http://localhost:9009/ready >/dev/null 2>&1 && { echo "$(GREEN)   ✅ Mimir responding$(NC)"; PASSED=$$((PASSED+1)); } || echo "$(RED)   ❌ Mimir not accessible$(NC)"; \
	echo "4. Checking Loki..."; \
	curl -sf http://localhost:3100/ready >/dev/null 2>&1 && { echo "$(GREEN)   ✅ Loki responding$(NC)"; PASSED=$$((PASSED+1)); } || echo "$(RED)   ❌ Loki not accessible$(NC)"; \
	echo "5. Checking Alloy (OTLP collector)..."; \
	curl -sf http://localhost:12345/ready >/dev/null 2>&1 && { echo "$(GREEN)   ✅ Alloy responding (OTLP on 4317/4318)$(NC)"; PASSED=$$((PASSED+1)); } || echo "$(RED)   ❌ Alloy not accessible$(NC)"; \
	echo "6. Checking Grafana datasources..."; \
	curl -sf $(GRAFANA_URL)/api/datasources -u $(GRAFANA_USER):$(GRAFANA_PASSWORD) 2>/dev/null | grep -q "tempo\|mimir\|loki" && { echo "$(GREEN)   ✅ Datasources configured$(NC)"; PASSED=$$((PASSED+1)); } || echo "$(YELLOW)   ⚠️  Datasources may need provisioning$(NC)"; \
	echo "7. Checking Wayfinder CLI..."; \
	PYTHONPATH=./src python3 -c "from contextcore import TaskTracker; print('ok')" >/dev/null 2>&1 && { echo "$(GREEN)   ✅ Wayfinder CLI available$(NC)"; PASSED=$$((PASSED+1)); } || echo "$(RED)   ❌ Wayfinder CLI not installed$(NC)"; \
	echo ""; \
	echo "$(CYAN)=== Smoke Test Complete: $$PASSED/$$TOTAL passed ===$(NC)"

verify: ## Quick cluster health check
	@echo "$(CYAN)=== Quick Verification ===$(NC)"
	@echo ""
	@echo "Data directories:"
	@for dir in tempo mimir loki grafana; do \
		if [ -d "$(DATA_DIR)/$$dir" ]; then \
			size=$$(du -sh "$(DATA_DIR)/$$dir" 2>/dev/null | cut -f1); \
			echo "$(GREEN)  ✅ $(DATA_DIR)/$$dir ($$size)$(NC)"; \
		else \
			echo "$(RED)  ❌ $(DATA_DIR)/$$dir missing$(NC)"; \
		fi; \
	done
	@echo ""
	@echo "Containers:"
	@running=$$($(CONTAINER_ENGINE) ps --filter "name=tempo" --filter "name=mimir" --filter "name=loki" --filter "name=grafana" --filter "name=alloy" --format "{{.Names}}" 2>/dev/null | wc -l | tr -d ' '); \
	if [ "$$running" -gt 0 ]; then \
		echo "$(GREEN)  ✅ $$running container(s) running$(NC)"; \
	else \
		echo "$(YELLOW)  ⚠️  No observability containers running$(NC)"; \
	fi

wait-ready: ## Wait for all services to be ready (timeout 60s)
	@echo "$(CYAN)=== Waiting for Services ===$(NC)"
	@echo ""
	@for i in $$(seq 1 30); do \
		ALL_READY=true; \
		curl -sf $(GRAFANA_URL)/api/health >/dev/null 2>&1 || ALL_READY=false; \
		curl -sf http://localhost:3200/ready >/dev/null 2>&1 || ALL_READY=false; \
		curl -sf http://localhost:9009/ready >/dev/null 2>&1 || ALL_READY=false; \
		curl -sf http://localhost:3100/ready >/dev/null 2>&1 || ALL_READY=false; \
		curl -sf http://localhost:12345/ready >/dev/null 2>&1 || ALL_READY=false; \
		if [ "$$ALL_READY" = "true" ]; then \
			echo "$(GREEN)All services ready!$(NC)"; \
			exit 0; \
		fi; \
		echo "  Waiting... ($$i/30)"; \
		sleep 2; \
	done; \
	echo "$(RED)Timeout waiting for services$(NC)"; \
	exit 1

seed-metrics: ## Run installation verification to populate dashboard metrics
	@echo "$(CYAN)=== Seeding Installation Metrics ===$(NC)"
	@echo ""
	@echo "Running installation verification with telemetry export..."
	@GRAFANA_URL=$(GRAFANA_URL) GRAFANA_USER=$(GRAFANA_USER) GRAFANA_PASSWORD=$(GRAFANA_PASSWORD) \
		PYTHONPATH=./src python3 -m contextcore.cli install verify --endpoint $(OTLP_ENDPOINT)
	@echo ""
	@echo "$(GREEN)Metrics exported to Mimir via $(OTLP_ENDPOINT)$(NC)"
	@echo "Dashboard data should now be available at: $(GRAFANA_URL)/d/cc-core-installation-status"

install-verify: install seed-metrics ## Install Wayfinder and populate dashboard metrics
	@echo ""
	@echo "$(GREEN)=== Installation Complete ===$(NC)"
	@echo ""
	@echo "Next steps:"
	@echo "  1. View Installation dashboard: $(GRAFANA_URL)/d/cc-core-installation-status"
	@echo "  2. Run 'make smoke-test' to validate stack"
	@echo "  3. Start tracking tasks with: contextcore task start --id TASK-1 --title 'My Task'"

full-setup: up wait-ready rules-validate seed-metrics ## Complete setup: start stack, wait for ready, validate rules, seed metrics
	@echo ""
	@echo "$(GREEN)=== Full Setup Complete ===$(NC)"
	@echo ""
	@echo "Wayfinder observability stack is ready!"
	@echo ""
	@echo "Dashboards available at: $(GRAFANA_URL)"
	@echo "  - Installation Status: $(GRAFANA_URL)/d/cc-core-installation-status"
	@echo "  - Project Portfolio:   $(GRAFANA_URL)/d/cc-core-portfolio-overview"
	@echo ""
	@echo "Quick commands:"
	@echo "  make health       - Check component health"
	@echo "  make smoke-test   - Validate entire stack"
	@echo "  make seed-metrics - Re-export installation metrics"

# === Backup & Restore ===

backup: ## Export state to timestamped backup directory
	@echo "$(CYAN)=== Creating Backup ===$(NC)"
	@mkdir -p $(BACKUP_DIR)/dashboards
	@mkdir -p $(BACKUP_DIR)/datasources
	@mkdir -p $(BACKUP_DIR)/state
	@echo "Backup directory: $(BACKUP_DIR)"
	@echo ""
	@echo "Exporting Grafana dashboards..."
	@curl -sf "$(GRAFANA_URL)/api/search?type=dash-db" -u $(GRAFANA_USER):$(GRAFANA_PASSWORD) 2>/dev/null | \
		python3 -c "import sys,json; [print(d['uid']) for d in json.load(sys.stdin)]" 2>/dev/null | \
		while read uid; do \
			curl -sf "$(GRAFANA_URL)/api/dashboards/uid/$$uid" -u $(GRAFANA_USER):$(GRAFANA_PASSWORD) > "$(BACKUP_DIR)/dashboards/$$uid.json" 2>/dev/null; \
		done || echo "$(YELLOW)  Note: Grafana not accessible, skipping dashboard export$(NC)"
	@echo "Exporting Grafana datasources..."
	@curl -sf "$(GRAFANA_URL)/api/datasources" -u $(GRAFANA_USER):$(GRAFANA_PASSWORD) > "$(BACKUP_DIR)/datasources/datasources.json" 2>/dev/null || echo "$(YELLOW)  Note: Could not export datasources$(NC)"
	@echo "Creating manifest..."
	@echo '{"created_at": "'$$(date -u +%Y-%m-%dT%H:%M:%SZ)'", "version": "1.0"}' > $(BACKUP_DIR)/manifest.json
	@echo ""
	@echo "$(GREEN)Backup complete: $(BACKUP_DIR)$(NC)"
	@ls -la $(BACKUP_DIR)/

restore: ## Restore from backup directory (usage: make restore BACKUP=backups/YYYYMMDD-HHMMSS)
	@if [ -z "$(BACKUP)" ]; then \
		echo "$(RED)Usage: make restore BACKUP=backups/YYYYMMDD-HHMMSS$(NC)"; \
		echo ""; \
		echo "Available backups:"; \
		ls -d backups/*/ 2>/dev/null || echo "  No backups found"; \
		exit 1; \
	fi
	@if [ ! -d "$(BACKUP)" ]; then \
		echo "$(RED)Backup directory not found: $(BACKUP)$(NC)"; \
		exit 1; \
	fi
	@echo "$(CYAN)=== Restoring from $(BACKUP) ===$(NC)"
	@echo ""
	@echo "Importing dashboards..."
	@for f in $(BACKUP)/dashboards/*.json; do \
		if [ -f "$$f" ]; then \
			echo "  Importing: $$f"; \
			cat "$$f" | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps({'dashboard':d.get('dashboard',d),'overwrite':True}))" | \
				curl -sf -X POST "$(GRAFANA_URL)/api/dashboards/db" -u $(GRAFANA_USER):$(GRAFANA_PASSWORD) -H "Content-Type: application/json" -d @- >/dev/null 2>&1; \
		fi; \
	done || echo "$(YELLOW)  Note: Could not import dashboards$(NC)"
	@echo ""
	@echo "$(GREEN)Restore complete$(NC)"
	@echo "Run 'make smoke-test' to verify"

# === Storage Management ===

storage-status: ## Show data directory sizes
	@echo "$(CYAN)=== Storage Status ===$(NC)"
	@echo ""
	@if [ -d "$(DATA_DIR)" ]; then \
		echo "Data directory: $(DATA_DIR)"; \
		echo ""; \
		du -sh $(DATA_DIR)/*/ 2>/dev/null || echo "  No data directories"; \
		echo ""; \
		echo "Total:"; \
		du -sh $(DATA_DIR) 2>/dev/null; \
	else \
		echo "$(YELLOW)Data directory does not exist yet.$(NC)"; \
		echo "Run 'make up' to create it."; \
	fi

storage-clean: ## Delete all data (WARNING: destructive, requires confirmation)
	@echo "$(RED)=== Storage Clean ===$(NC)"
	@echo ""
	@echo "$(YELLOW)WARNING: This will delete all observability data!$(NC)"
	@echo ""
	@if [ -d "$(DATA_DIR)" ]; then \
		du -sh $(DATA_DIR)/*/ 2>/dev/null; \
		echo ""; \
	fi
	@read -p "Delete all data in $(DATA_DIR)/? Type 'yes' to confirm: " confirm && [ "$$confirm" = "yes" ] || (echo "Aborted." && exit 1)
	@rm -rf $(DATA_DIR)
	@echo "$(GREEN)Storage cleaned. Run 'make up' to recreate.$(NC)"

# === Logs ===

logs-tempo: ## Follow Tempo logs
	@$(CONTAINER_ENGINE) logs -f $$($(CONTAINER_ENGINE) ps --filter "name=tempo" --format "{{.Names}}" | head -1) 2>/dev/null || echo "Tempo container not running"

logs-mimir: ## Follow Mimir logs
	@$(CONTAINER_ENGINE) logs -f $$($(CONTAINER_ENGINE) ps --filter "name=mimir" --format "{{.Names}}" | head -1) 2>/dev/null || echo "Mimir container not running"

logs-loki: ## Follow Loki logs
	@$(CONTAINER_ENGINE) logs -f $$($(CONTAINER_ENGINE) ps --filter "name=loki" --format "{{.Names}}" | head -1) 2>/dev/null || echo "Loki container not running"

logs-grafana: ## Follow Grafana logs
	@$(CONTAINER_ENGINE) logs -f $$($(CONTAINER_ENGINE) ps --filter "name=grafana" --format "{{.Names}}" | head -1) 2>/dev/null || echo "Grafana container not running"

# === Development ===

install: ## Install all workspace packages in development mode
	uv sync --all-packages --all-extras

install-core: ## Install core contextcore package only
	uv sync --package contextcore --all-extras

install-fox: ## Install wayfinder-fox package only
	uv sync --package wayfinder-fox --all-extras

test: ## Run core tests
	uv run pytest tests/ -v

test-fox: ## Run wayfinder-fox tests
	uv run pytest wayfinder-fox/tests/ -v

test-all: ## Run all workspace tests
	uv run pytest tests/ wayfinder-fox/tests/ -v

lint: ## Run linting across all packages
	uv run ruff check src/ wayfinder-fox/src/

typecheck: ## Run type checking
	uv run mypy src/contextcore

build: ## Build package
	uv build

clean: ## Clean build artifacts
	rm -rf build/ dist/ *.egg-info src/*.egg-info .venv
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# === Kind Cluster ===

# Kind profile: dev (2-node) or test (3-node with criticality tiers)
PROFILE ?= dev
KIND_CLUSTER_NAME ?= wayfinder-$(PROFILE)
KIND_SCRIPT := deploy/kind/scripts/create-cluster.sh

kind-up: ## Create Kind cluster (PROFILE=dev|test, YES=1 to skip prompts)
	@if [ "$(YES)" = "1" ]; then \
		$(KIND_SCRIPT) --profile $(PROFILE) --yes; \
	else \
		$(KIND_SCRIPT) --profile $(PROFILE); \
	fi

kind-down: ## Delete Kind cluster
	@$(KIND_SCRIPT) --delete

kind-status: ## Show Kind cluster pod status
	@echo "$(CYAN)=== Kind Cluster Status ===$(NC)"
	@echo ""
	@echo "Cluster: $(KIND_CLUSTER_NAME)"
	@echo ""
	@if kind get clusters 2>/dev/null | grep -q "^$(KIND_CLUSTER_NAME)$$"; then \
		echo "Nodes:"; \
		kubectl get nodes --context kind-$(KIND_CLUSTER_NAME) 2>/dev/null | sed 's/^/  /' || echo "  (kubectl not configured)"; \
		echo ""; \
		echo "Pods:"; \
		kubectl get pods -n observability --context kind-$(KIND_CLUSTER_NAME) 2>/dev/null | sed 's/^/  /' || echo "  (no pods)"; \
	else \
		echo -e "$(YELLOW)Cluster '$(KIND_CLUSTER_NAME)' not found.$(NC)"; \
		echo "Run 'make kind-up' to create it."; \
	fi

kind-seed: ## Seed installation metrics into Kind cluster
	@echo "$(CYAN)=== Seeding Kind Cluster Metrics ===$(NC)"
	@echo ""
	@GRAFANA_URL=$(GRAFANA_URL) GRAFANA_USER=$(GRAFANA_USER) GRAFANA_PASSWORD=$(GRAFANA_PASSWORD) \
		PYTHONPATH=./src python3 -m contextcore.cli install verify --endpoint $(OTLP_ENDPOINT)
	@echo ""
	@echo "$(GREEN)Metrics exported to Mimir via $(OTLP_ENDPOINT)$(NC)"
	@echo "Dashboard: $(GRAFANA_URL)/d/cc-core-installation-status"

# === Recording Rules ===

rules-validate: ## Validate recording and alert rule files exist and are well-formed YAML
	@echo "$(CYAN)=== Validating Recording Rules ===$(NC)"
	@echo ""
	@PASSED=0; TOTAL=4; \
	echo "Loki recording rules:"; \
	if [ -f "loki/rules/fake/contextcore-rules.yaml" ]; then \
		python3 -c "import yaml; yaml.safe_load(open('loki/rules/fake/contextcore-rules.yaml'))" 2>/dev/null && { echo "$(GREEN)  ✅ contextcore-rules.yaml valid$(NC)"; PASSED=$$((PASSED+1)); } || echo "$(RED)  ❌ contextcore-rules.yaml invalid YAML$(NC)"; \
	else \
		echo "$(RED)  ❌ contextcore-rules.yaml not found$(NC)"; \
	fi; \
	echo "Loki alert rules:"; \
	if [ -f "loki/rules/fake/contextcore-alerts.yaml" ]; then \
		python3 -c "import yaml; yaml.safe_load(open('loki/rules/fake/contextcore-alerts.yaml'))" 2>/dev/null && { echo "$(GREEN)  ✅ contextcore-alerts.yaml valid$(NC)"; PASSED=$$((PASSED+1)); } || echo "$(RED)  ❌ contextcore-alerts.yaml invalid YAML$(NC)"; \
	else \
		echo "$(RED)  ❌ contextcore-alerts.yaml not found$(NC)"; \
	fi; \
	echo "Mimir recording rules:"; \
	if [ -f "mimir/rules/contextcore/rules.yaml" ]; then \
		python3 -c "import yaml; yaml.safe_load(open('mimir/rules/contextcore/rules.yaml'))" 2>/dev/null && { echo "$(GREEN)  ✅ mimir rules.yaml valid$(NC)"; PASSED=$$((PASSED+1)); } || echo "$(RED)  ❌ mimir rules.yaml invalid YAML$(NC)"; \
	else \
		echo "$(RED)  ❌ mimir rules.yaml not found$(NC)"; \
	fi; \
	echo "Mimir alert rules:"; \
	if [ -f "mimir/rules/contextcore/alerts.yaml" ]; then \
		python3 -c "import yaml; yaml.safe_load(open('mimir/rules/contextcore/alerts.yaml'))" 2>/dev/null && { echo "$(GREEN)  ✅ mimir alerts.yaml valid$(NC)"; PASSED=$$((PASSED+1)); } || echo "$(RED)  ❌ mimir alerts.yaml invalid YAML$(NC)"; \
	else \
		echo "$(RED)  ❌ mimir alerts.yaml not found$(NC)"; \
	fi; \
	echo ""; \
	echo "$(CYAN)=== Rules Validation: $$PASSED/$$TOTAL passed ===$(NC)"

rules-status: ## Show status of active recording and alert rules
	@echo "$(CYAN)=== Recording Rules Status ===$(NC)"
	@echo ""
	@echo "Loki rules:"
	@curl -sf http://localhost:3100/loki/api/v1/rules 2>/dev/null | python3 -c "import sys,json; data=json.load(sys.stdin); [print(f'  {g[\"name\"]}: {len(g.get(\"rules\",[]))} rules') for g in data.get('data',{}).get('groups',[])]" 2>/dev/null || echo "  $(YELLOW)⚠️  Loki not accessible or no rules loaded$(NC)"
	@echo ""
	@echo "Mimir rules:"
	@curl -sf http://localhost:9009/prometheus/api/v1/rules 2>/dev/null | python3 -c "import sys,json; data=json.load(sys.stdin); [print(f'  {g[\"name\"]}: {len(g.get(\"rules\",[]))} rules') for g in data.get('data',{}).get('groups',[])]" 2>/dev/null || echo "  $(YELLOW)⚠️  Mimir not accessible or no rules loaded$(NC)"

# === Dashboards ===

dashboards-provision: ## Provision Wayfinder dashboards to Grafana
	@PYTHONPATH=./src python3 -m contextcore.cli dashboards provision

dashboards-list: ## List provisioned dashboards in Grafana
	@PYTHONPATH=./src python3 -m contextcore.cli dashboards list

# === Jsonnet Mixin ===

jsonnet-generate: ## Generate dashboards, rules, and alerts from Jsonnet
	$(MAKE) -C wayfinder-mixin generate
	@echo "Copying generated artifacts to deployment locations..."
	@cp wayfinder-mixin/generated/dashboards/*.json grafana/provisioning/dashboards/core/ 2>/dev/null || true
	@cp wayfinder-mixin/generated/rules/loki-rules.yaml loki/rules/fake/contextcore-rules.yaml 2>/dev/null || true
	@cp wayfinder-mixin/generated/rules/mimir-rules.yaml mimir/rules/contextcore/rules.yaml 2>/dev/null || true
	@echo "$(GREEN)Jsonnet artifacts deployed$(NC)"

jsonnet-test: ## Run Jsonnet mixin tests
	$(MAKE) -C wayfinder-mixin test

jsonnet-lint: ## Check Jsonnet formatting
	$(MAKE) -C wayfinder-mixin lint

# === Help ===

help: ## Show this help
	@echo "$(CYAN)Wayfinder Makefile$(NC)"
	@echo ""
	@echo "$(YELLOW)Quick Start:$(NC)"
	@grep -E '^full-setup:' $(MAKEFILE_LIST) | sed 's/:.*##/  →/' | sed 's/^/  make /'
	@echo ""
	@echo "$(YELLOW)Preflight:$(NC)"
	@grep -E '^doctor:' $(MAKEFILE_LIST) | sed 's/:.*##/  →/' | sed 's/^/  make /'
	@echo ""
	@echo "$(YELLOW)Stack Management:$(NC)"
	@grep -E '^(up|down|destroy|status):' $(MAKEFILE_LIST) | sed 's/:.*##/  →/' | sed 's/^/  make /'
	@echo ""
	@echo "$(YELLOW)Health & Validation:$(NC)"
	@grep -E '^(health|smoke-test|verify|wait-ready|seed-metrics):' $(MAKEFILE_LIST) | sed 's/:.*##/  →/' | sed 's/^/  make /'
	@echo ""
	@echo "$(YELLOW)Backup & Restore:$(NC)"
	@grep -E '^(backup|restore):' $(MAKEFILE_LIST) | sed 's/:.*##/  →/' | sed 's/^/  make /'
	@echo ""
	@echo "$(YELLOW)Storage:$(NC)"
	@grep -E '^storage-' $(MAKEFILE_LIST) | sed 's/:.*##/  →/' | sed 's/^/  make /'
	@echo ""
	@echo "$(YELLOW)Logs:$(NC)"
	@grep -E '^logs-' $(MAKEFILE_LIST) | sed 's/:.*##/  →/' | sed 's/^/  make /'
	@echo ""
	@echo "$(YELLOW)Development:$(NC)"
	@grep -E '^(install|install-core|install-fox|install-verify|test|test-fox|test-all|lint|typecheck|build|clean):' $(MAKEFILE_LIST) | sed 's/:.*##/  →/' | sed 's/^/  make /'
	@echo ""
	@echo "$(YELLOW)Kind Cluster:$(NC)"
	@grep -E '^kind-' $(MAKEFILE_LIST) | sed 's/:.*##/  →/' | sed 's/^/  make /'
	@echo ""
	@echo "$(YELLOW)Recording Rules:$(NC)"
	@grep -E '^rules-' $(MAKEFILE_LIST) | sed 's/:.*##/  →/' | sed 's/^/  make /'
	@echo ""
	@echo "$(YELLOW)Dashboards:$(NC)"
	@grep -E '^dashboards-' $(MAKEFILE_LIST) | sed 's/:.*##/  →/' | sed 's/^/  make /'
	@echo ""
	@echo "$(YELLOW)Jsonnet Mixin:$(NC)"
	@grep -E '^jsonnet-' $(MAKEFILE_LIST) | sed 's/:.*##/  →/' | sed 's/^/  make /'
	@echo ""
	@echo "$(YELLOW)Container Engine:$(NC)"
	@echo "  CONTAINER_ENGINE  Container runtime (default: auto-detect docker or podman)"
	@echo "  COMPOSE_CMD       Compose command (default: auto-detect)"
	@echo "  Current:          $(CONTAINER_ENGINE) / $(COMPOSE_CMD)"
	@echo ""
	@echo "$(YELLOW)Environment Variables:$(NC)"
	@echo "  GRAFANA_URL       Grafana URL (default: http://localhost:3000)"
	@echo "  GRAFANA_USER      Grafana user (default: admin)"
	@echo "  GRAFANA_PASSWORD  Grafana password (default: admin)"
	@echo "  OTLP_ENDPOINT     OTLP endpoint (default: localhost:4317)"

.DEFAULT_GOAL := help
