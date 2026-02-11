#!/bin/bash
# Auto-Fix Workflow Setup Script
# Deploys GitHub Actions workflow and Grafana alert rules
#
# Usage:
#   ./setup-auto-fix.sh [OPTIONS]
#
# Options:
#   --project-dir PATH    Target project directory (default: current directory)
#   --grafana-dir PATH    Grafana provisioning directory (default: /etc/grafana/provisioning/alerting)
#   --github-owner NAME   GitHub repository owner
#   --github-repo NAME    GitHub repository name
#   --skip-grafana        Skip Grafana alert rules deployment
#   --skip-github         Skip GitHub Actions workflow deployment
#   --dry-run             Show what would be done without making changes
#   -h, --help            Show this help message

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory (where templates are located)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Defaults
PROJECT_DIR="$(pwd)"
GRAFANA_DIR="/etc/grafana/provisioning/alerting"
GITHUB_OWNER=""
GITHUB_REPO=""
SKIP_GRAFANA=false
SKIP_GITHUB=false
DRY_RUN=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --project-dir)
            PROJECT_DIR="$2"
            shift 2
            ;;
        --grafana-dir)
            GRAFANA_DIR="$2"
            shift 2
            ;;
        --github-owner)
            GITHUB_OWNER="$2"
            shift 2
            ;;
        --github-repo)
            GITHUB_REPO="$2"
            shift 2
            ;;
        --skip-grafana)
            SKIP_GRAFANA=true
            shift
            ;;
        --skip-github)
            SKIP_GITHUB=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            head -25 "$0" | tail -20
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  Auto-Fix Workflow Setup${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Detect GitHub repo info from git remote if not provided
if [[ -z "$GITHUB_OWNER" || -z "$GITHUB_REPO" ]]; then
    if [[ -d "$PROJECT_DIR/.git" ]]; then
        REMOTE_URL=$(git -C "$PROJECT_DIR" remote get-url origin 2>/dev/null || echo "")
        if [[ -n "$REMOTE_URL" ]]; then
            # Parse GitHub URL (supports both HTTPS and SSH)
            if [[ "$REMOTE_URL" =~ github\.com[:/]([^/]+)/([^/.]+) ]]; then
                GITHUB_OWNER="${GITHUB_OWNER:-${BASH_REMATCH[1]}}"
                GITHUB_REPO="${GITHUB_REPO:-${BASH_REMATCH[2]}}"
                echo -e "${GREEN}✓ Detected GitHub repo: ${GITHUB_OWNER}/${GITHUB_REPO}${NC}"
            fi
        fi
    fi
fi

# Validate required info
if [[ "$SKIP_GRAFANA" == false && -z "$GITHUB_OWNER" ]]; then
    echo -e "${YELLOW}⚠ GitHub owner not detected. Grafana webhook URL will need manual configuration.${NC}"
fi

echo ""
echo -e "${BLUE}Configuration:${NC}"
echo "  Project directory: $PROJECT_DIR"
echo "  Grafana directory: $GRAFANA_DIR"
echo "  GitHub repo:       ${GITHUB_OWNER:-<not set>}/${GITHUB_REPO:-<not set>}"
echo "  Skip Grafana:      $SKIP_GRAFANA"
echo "  Skip GitHub:       $SKIP_GITHUB"
echo "  Dry run:           $DRY_RUN"
echo ""

# Function to run or simulate commands
run_cmd() {
    if [[ "$DRY_RUN" == true ]]; then
        echo -e "${YELLOW}[DRY-RUN]${NC} $*"
    else
        "$@"
    fi
}

# ============================================
# Deploy GitHub Actions Workflow
# ============================================
if [[ "$SKIP_GITHUB" == false ]]; then
    echo -e "${BLUE}--- Deploying GitHub Actions Workflow ---${NC}"

    WORKFLOW_DIR="$PROJECT_DIR/.github/workflows"
    WORKFLOW_FILE="$WORKFLOW_DIR/auto-fix.yml"

    # Create workflows directory
    if [[ ! -d "$WORKFLOW_DIR" ]]; then
        echo "Creating $WORKFLOW_DIR..."
        run_cmd mkdir -p "$WORKFLOW_DIR"
    fi

    # Copy workflow file
    if [[ -f "$WORKFLOW_FILE" ]]; then
        echo -e "${YELLOW}⚠ Workflow file already exists: $WORKFLOW_FILE${NC}"
        read -p "  Overwrite? [y/N] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "  Skipping workflow deployment."
        else
            run_cmd cp "$SCRIPT_DIR/auto-fix.yml" "$WORKFLOW_FILE"
            echo -e "${GREEN}✓ Deployed: $WORKFLOW_FILE${NC}"
        fi
    else
        run_cmd cp "$SCRIPT_DIR/auto-fix.yml" "$WORKFLOW_FILE"
        echo -e "${GREEN}✓ Deployed: $WORKFLOW_FILE${NC}"
    fi

    echo ""
    echo -e "${YELLOW}Required secrets (add in GitHub repo settings):${NC}"
    echo "  • ANTHROPIC_API_KEY - Your Claude API key"
    echo ""
fi

# ============================================
# Deploy Grafana Alert Rules
# ============================================
if [[ "$SKIP_GRAFANA" == false ]]; then
    echo -e "${BLUE}--- Deploying Grafana Alert Rules ---${NC}"

    ALERT_FILE="$GRAFANA_DIR/auto-fix-rules.yaml"
    TEMP_FILE=$(mktemp)

    # Process template with variable substitution
    cp "$SCRIPT_DIR/grafana-alert-rules.yaml" "$TEMP_FILE"

    # Substitute GitHub repo info if available
    if [[ -n "$GITHUB_OWNER" && -n "$GITHUB_REPO" ]]; then
        sed -i.bak "s|OWNER/REPO|${GITHUB_OWNER}/${GITHUB_REPO}|g" "$TEMP_FILE"
        rm -f "${TEMP_FILE}.bak"
        echo -e "${GREEN}✓ Configured webhook URL for ${GITHUB_OWNER}/${GITHUB_REPO}${NC}"
    fi

    # Check if Grafana directory exists
    if [[ ! -d "$GRAFANA_DIR" ]]; then
        echo -e "${YELLOW}⚠ Grafana provisioning directory not found: $GRAFANA_DIR${NC}"
        echo "  Options:"
        echo "    1. Create directory (requires sudo)"
        echo "    2. Copy to local file for manual import"
        echo "    3. Skip"
        read -p "  Choose [1/2/3]: " -n 1 -r
        echo

        case $REPLY in
            1)
                run_cmd sudo mkdir -p "$GRAFANA_DIR"
                run_cmd sudo cp "$TEMP_FILE" "$ALERT_FILE"
                run_cmd sudo chown grafana:grafana "$ALERT_FILE" 2>/dev/null || true
                echo -e "${GREEN}✓ Deployed: $ALERT_FILE${NC}"
                ;;
            2)
                LOCAL_FILE="$PROJECT_DIR/grafana-alert-rules.yaml"
                run_cmd cp "$TEMP_FILE" "$LOCAL_FILE"
                echo -e "${GREEN}✓ Saved to: $LOCAL_FILE${NC}"
                echo "  Import manually via Grafana UI: Alerting > Alert rules > Import"
                ;;
            *)
                echo "  Skipping Grafana deployment."
                ;;
        esac
    else
        # Directory exists, deploy directly
        if [[ -f "$ALERT_FILE" ]]; then
            echo -e "${YELLOW}⚠ Alert rules file already exists: $ALERT_FILE${NC}"
            read -p "  Overwrite? [y/N] " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                echo "  Skipping alert rules deployment."
            else
                if [[ -w "$GRAFANA_DIR" ]]; then
                    run_cmd cp "$TEMP_FILE" "$ALERT_FILE"
                else
                    run_cmd sudo cp "$TEMP_FILE" "$ALERT_FILE"
                fi
                echo -e "${GREEN}✓ Deployed: $ALERT_FILE${NC}"
            fi
        else
            if [[ -w "$GRAFANA_DIR" ]]; then
                run_cmd cp "$TEMP_FILE" "$ALERT_FILE"
            else
                run_cmd sudo cp "$TEMP_FILE" "$ALERT_FILE"
            fi
            echo -e "${GREEN}✓ Deployed: $ALERT_FILE${NC}"
        fi
    fi

    rm -f "$TEMP_FILE"

    echo ""
    echo -e "${YELLOW}Grafana configuration required:${NC}"
    echo "  1. Create Contact Point (webhook to GitHub Actions):"
    echo "     • Name: GitHub Auto-Fix Webhook"
    echo "     • Type: Webhook"
    echo "     • URL: https://api.github.com/repos/${GITHUB_OWNER:-OWNER}/${GITHUB_REPO:-REPO}/dispatches"
    echo "     • HTTP Headers:"
    echo "       - Authorization: Bearer <GITHUB_PAT>"
    echo "       - Accept: application/vnd.github.v3+json"
    echo ""
    echo "  2. Create Notification Policy:"
    echo "     • Matcher: auto_fix = true"
    echo "     • Contact Point: GitHub Auto-Fix Webhook"
    echo ""
    echo "  3. Restart Grafana to load provisioned rules:"
    echo "     sudo systemctl restart grafana-server"
    echo ""
fi

# ============================================
# Summary
# ============================================
echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  Setup Complete${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo -e "${GREEN}Deployed components:${NC}"
[[ "$SKIP_GITHUB" == false ]] && echo "  ✓ GitHub Actions workflow: .github/workflows/auto-fix.yml"
[[ "$SKIP_GRAFANA" == false ]] && echo "  ✓ Grafana alert rules"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Add ANTHROPIC_API_KEY secret to GitHub repository"
echo "  2. Create GitHub PAT with repo:dispatch permission"
echo "  3. Configure Grafana contact point with webhook URL"
echo "  4. Create notification policy routing auto_fix=true to webhook"
echo "  5. Test with: gh workflow run auto-fix.yml -f error_context='test error'"
echo ""
echo -e "${BLUE}Documentation:${NC}"
echo "  Skill: ~/.claude/skills/dev-tour-guide/SKILL.md"
echo "  Templates: ~/.claude/skills/dev-tour-guide/scripts/"
echo ""
