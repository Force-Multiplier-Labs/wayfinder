# Development Guide

Local development setup for ContextCore Grafana plugins.

## Prerequisites

- **Node.js** 20+ (with npm 10+)
- **Python** 3.9+ (for scaffold script)
- **Docker** (for development environment)
- **ANTHROPIC_API_KEY** (for scaffold script)

## Quick Start

```bash
# Navigate to contextcore-owl
cd /path/to/ContextCore/contextcore-owl

# Install dependencies for all plugins
npm install

# Build all plugins (outputs to grafana/plugins/)
npm run build

# Restart Grafana pod to load plugins
kubectl -n observability rollout restart deployment/grafana

# View Grafana at http://localhost:3000 (admin/admin)
open http://localhost:3000
```

## Kind Cluster Deployment

Plugins are deployed via Kind host mounts defined in `/Users/neilyashinsky/Documents/Deploy/kind-cluster.yaml`:

```yaml
extraMounts:
  - hostPath: .../contextcore-owl/grafana/plugins/contextcore-chat-panel
    containerPath: /plugins/contextcore/contextcore-chat-panel
  # ... other plugins
```

The Kubernetes Grafana deployment (`k8s/observability/deployments.yaml`) uses hostPath volumes
to mount these into `/var/lib/grafana/plugins/`.

If Kind cluster doesn't have the mounts yet, recreate it:
```bash
cd /Users/neilyashinsky/Documents/Deploy
./scripts/create-cluster.sh --delete && ./scripts/create-cluster.sh
```

## Project Structure

```
contextcore-owl/
├── package.json              # Monorepo root with npm workspaces
├── plugins/
│   ├── contextcore-chat-panel/
│   │   ├── src/
│   │   │   ├── module.ts       # Plugin entry point
│   │   │   ├── types.ts        # TypeScript interfaces
│   │   │   └── components/
│   │   │       └── ChatPanel.tsx
│   │   ├── plugin.json         # Plugin manifest
│   │   └── package.json        # Plugin dependencies
│   ├── contextcore-workflow-panel/
│   └── contextcore-datasource/
├── scripts/
│   └── scaffold_plugin.py      # Generate new plugins
├── docker/
│   ├── docker-compose.yml      # Dev environment
│   └── mock/expectations.json  # Mock Rabbit API
└── grafana/plugins/            # Built plugin output
```

## Development Workflow

### 1. Start Development Environment

```bash
# Start Grafana and mock API
npm run docker:up

# View logs
npm run docker:logs

# Stop environment
npm run docker:down
```

### 2. Build Plugins

```bash
# Build all plugins
npm run build

# Build specific plugin
cd plugins/contextcore-chat-panel
npm run build

# Watch mode (auto-rebuild on changes)
npm run dev
```

### 3. View in Grafana

1. Open http://localhost:3001
2. Login with `admin/admin`
3. Go to Configuration > Plugins
4. Search for "ContextCore"

### 4. Run Tests

```bash
# Run all tests
npm test

# Run specific plugin tests
cd plugins/contextcore-chat-panel
npm test
```

## Creating a New Plugin

### Option 1: Scaffold Script (Recommended)

```bash
# Generate panel plugin
python scripts/scaffold_plugin.py --plugin-type panel --name contextcore-my-panel

# Generate datasource plugin
python scripts/scaffold_plugin.py --plugin-type datasource --name contextcore-my-ds

# Generate app plugin
python scripts/scaffold_plugin.py --plugin-type app --name contextcore-my-app
```

### Option 2: Manual Creation

```bash
# Use Grafana's official scaffolder
cd plugins
npx @grafana/create-plugin@latest --plugin-type panel

# Follow prompts, then rename to contextcore-*
```

### Option 3: Copy Existing

```bash
cp -r plugins/contextcore-chat-panel plugins/contextcore-my-panel
# Update plugin.json, package.json, and source files
```

## Plugin Development

### Key Files

| File | Purpose |
|------|---------|
| `plugin.json` | Plugin metadata (id, name, type, version) |
| `package.json` | Dependencies and build scripts |
| `src/module.ts` | Plugin registration |
| `src/types.ts` | TypeScript interfaces |
| `src/components/*.tsx` | React components |

### Panel Plugin Pattern

```typescript
// module.ts
import { PanelPlugin } from '@grafana/data';
import { MyPanel } from './components/MyPanel';
import { MyPanelOptions } from './types';

export const plugin = new PanelPlugin<MyPanelOptions>(MyPanel)
  .setPanelOptions((builder) => {
    builder.addTextInput({
      path: 'apiUrl',
      name: 'API URL',
      defaultValue: 'http://localhost:8080',
    });
  });
```

### Using Template Variables

```typescript
import { getTemplateSrv } from '@grafana/runtime';

const templateSrv = getTemplateSrv();
const projectId = templateSrv.replace('${project}');
```

### Styling with Emotion

```typescript
import { css } from '@emotion/css';
import { useStyles2 } from '@grafana/ui';

const getStyles = () => ({
  container: css`
    display: flex;
    padding: 12px;
  `,
});

// In component
const styles = useStyles2(getStyles);
return <div className={styles.container}>...</div>;
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | - | Required for scaffold script |
| `CLAUDE_MODEL` | `claude-sonnet-4-20250514` | LLM model for scaffolding |

## Ports

| Service | Port | Description |
|---------|------|-------------|
| Grafana (dev) | 3001 | Plugin development |
| Rabbit Mock | 8080 | Mock Rabbit API |
| ContextCore Grafana | 3000 | Main stack (if running) |

## Common Issues

### Plugin Not Loading

1. Check console for errors: Developer Tools > Console
2. Verify plugin is in unsigned allowlist:
   ```
   GF_PLUGINS_ALLOW_LOADING_UNSIGNED_PLUGINS=contextcore-chat-panel,...
   ```
3. Rebuild plugin: `npm run build`
4. Restart Grafana: `docker compose restart grafana`

### Build Errors

1. Check Node version: `node --version` (should be 20+)
2. Clear node_modules: `npm run clean && npm install`
3. Check TypeScript errors: `npm run typecheck`

### CORS Errors

Panel plugins using direct `fetch()` need CORS on the API:
- Use the mock API (has CORS enabled)
- Or enable CORS on Rabbit API (GFP-006)
- Or use datasource plugin (route proxy avoids CORS)

## Useful Commands

```bash
# Lint code
npm run lint

# Fix lint issues
npm run lint:fix

# Type check
npm run typecheck

# Clean all builds
npm run clean

# View Grafana container logs
npm run docker:logs
```

## Related Documentation

- [Plugin Guide](PLUGIN_GUIDE.md) - Creating new plugins
- [Grafana Plugin Tools](https://grafana.com/developers/plugin-tools/)
- [@grafana/ui Components](https://developers.grafana.com/ui/latest/)
