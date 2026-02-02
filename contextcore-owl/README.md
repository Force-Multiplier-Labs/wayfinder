# contextcore-owl (Gookooko'oo)

**Owl - Unified Grafana Plugin Package for the Wayfinder Suite**

| Field | Value |
|-------|-------|
| **Animal** | Owl |
| **Anishinaabe** | Gookooko'oo |
| **Pronunciation** | goo-koo-KOH-oh |
| **Status** | Planned |

## Why Owl?

The owl is renowned for its exceptional vision, watchful nature, and wisdom. In many traditions, the owl sees what others cannot, observing patterns in the darkness. Like the owl's vigilant watch, this package provides Grafana plugins for visualization and monitoring—workflow trigger panels, chat interfaces, and datasources that watch over systems and reveal insights through dashboards.

## Purpose

contextcore-owl consolidates all Wayfinder Grafana extensions into a single, well-maintained package:

- **Avoids recreating the wheel**: Reuses proven patterns from O11yBubo plugins
- **Consistent branding**: All plugins use ContextCore naming and conventions
- **Single source**: One place for all Grafana extensions
- **Monorepo structure**: Shared dependencies and build infrastructure

## Plugins

| Plugin ID | Type | Description | Status |
|-----------|------|-------------|--------|
| `contextcore-chat-panel` | Panel | Interactive chat with Claude via webhook | Planned |
| `contextcore-workflow-panel` | Panel | Trigger and monitor Rabbit workflow executions | Planned |
| `contextcore-datasource` | Datasource | Proxied access to Rabbit API (CORS-free) | Planned |

## Directory Structure

```
contextcore-owl/
├── README.md                    # This file
├── CLAUDE.md                    # Claude Code instructions
├── package.json                 # Monorepo root (npm workspaces)
├── pyproject.toml               # Python package for provisioning helpers
├── plugins/
│   ├── contextcore-chat-panel/      # Chat panel plugin
│   ├── contextcore-workflow-panel/  # Workflow trigger panel
│   └── contextcore-datasource/      # Datasource with route proxy
├── scripts/
│   └── scaffold_plugin.py       # Plugin generator (uses contextcore-beaver)
├── grafana/
│   └── plugins/                 # Built plugins for distribution
├── docker/
│   └── docker-compose.yml       # Development environment
└── docs/
    ├── DEVELOPMENT.md           # Local dev setup
    └── PLUGIN_GUIDE.md          # Creating new plugins
```

## Installation

### Wayfinder Stack (Automatic)

The Wayfinder observability stack automatically loads plugins when started:

```bash
cd /path/to/wayfinder

# Build plugins first
cd contextcore-owl && npm install && npm run build && cd ..

# Start the stack (plugins are mounted automatically)
docker compose up -d
```

Plugins are mounted via `docker-compose.yaml`:
- Volume: `./contextcore-owl/grafana/plugins:/var/lib/grafana/plugins:ro`
- Unsigned plugins allowed via `GF_PLUGINS_ALLOW_LOADING_UNSIGNED_PLUGINS`

### Docker Compose (Standalone)

Add to your `docker-compose.yaml`:

```yaml
grafana:
  image: grafana/grafana:latest
  volumes:
    - ./contextcore-owl/grafana/plugins:/var/lib/grafana/plugins
  environment:
    GF_PLUGINS_ALLOW_LOADING_UNSIGNED_PLUGINS: contextcore-chat-panel,contextcore-workflow-panel,contextcore-datasource
```

### Manual Installation

```bash
# Clone and build
git clone https://github.com/contextcore/contextcore-owl
cd contextcore-owl
npm install
npm run build

# Copy built plugins to Grafana
cp -r grafana/plugins/* /var/lib/grafana/plugins/

# Restart Grafana
systemctl restart grafana-server
```

### Grafana Configuration

Add to `grafana.ini`:

```ini
[plugins]
allow_loading_unsigned_plugins = contextcore-chat-panel,contextcore-workflow-panel,contextcore-datasource
```

## Development

### Prerequisites

- Node.js 18+
- npm 9+
- Python 3.9+ (for scaffold script)
- Docker (for development environment)

### Quick Start

```bash
# Install dependencies
npm install

# Start development server with Grafana
docker compose -f docker/docker-compose.yml up -d

# Build all plugins
npm run build

# Watch mode for development
npm run dev
```

### Creating a New Plugin

```bash
# Using the scaffold script (requires contextcore-beaver)
python scripts/scaffold_plugin.py --type panel --name my-custom-panel

# Or manually with @grafana/create-plugin
npx @grafana/create-plugin@latest --plugin-type panel
```

## Plugin Details

### contextcore-chat-panel

Interactive chat panel for communicating with Claude via webhook.

**Features**:
- Message input with send button
- Chat history display with markdown rendering
- Loading states and error handling
- Configurable webhook URL

**Options**:
- `webhookUrl`: URL to send chat requests
- `maxTokens`: Maximum response tokens
- `showMetrics`: Display response metrics

### contextcore-workflow-panel

Trigger and monitor Rabbit workflow executions from dashboards.

**Features**:
- Project selector (supports template variables)
- Dry Run button for preview
- Execute button with confirmation
- Status display (running/completed/failed)
- Last run timestamp

**Options**:
- `apiUrl`: Rabbit API base URL
- `projectId`: Project ID or `$project` template variable
- `showDryRun`: Show dry run button
- `showExecute`: Show execute button
- `refreshInterval`: Auto-refresh status (seconds)

### contextcore-datasource

Datasource plugin using Grafana's route proxy for CORS-free API calls.

**Features**:
- Route proxy configuration (no CORS issues)
- Health check endpoint
- Query endpoint for prompts
- Connection test in UI

**Routes**:
```json
{
  "routes": [
    {
      "path": "api/*",
      "url": "{{ .JsonData.apiUrl }}"
    }
  ]
}
```

## Relationship to O11yBubo

contextcore-owl consolidates and extends plugins originally developed in the O11yBubo project:

| O11yBubo | contextcore-owl | Changes |
|----------|---------------------|---------|
| `011ybubo-chat-panel` | `contextcore-chat-panel` | Branding, plugin ID |
| `011ybubo-datasource` | `contextcore-datasource` | Branding, plugin ID |
| `scaffold_plugin.py` | `scripts/scaffold_plugin.py` | Uses contextcore-beaver |
| — | `contextcore-workflow-panel` | New plugin |

## License

Equitable Use License v1.0

## Links

- [Wayfinder Documentation](https://github.com/contextcore/contextcore)
- [Grafana Plugin Development](https://grafana.com/developers/plugin-tools/)
- [Wayfinder Expansion Packs](../docs/EXPANSION_PACKS.md)
- [Naming Convention](https://github.com/Force-Multiplier-Labs/contextcore-spec/blob/main/docs/NAMING_CONVENTION.md)
