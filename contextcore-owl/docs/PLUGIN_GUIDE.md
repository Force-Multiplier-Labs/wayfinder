# Plugin Creation Guide

How to create new ContextCore Grafana plugins.

## Plugin Types

| Type | Use Case | Key Components |
|------|----------|----------------|
| **Panel** | Custom visualizations, forms, controls | `module.ts`, `Panel.tsx` |
| **Datasource** | Connect to external data sources | `module.ts`, `datasource.ts`, editors |
| **App** | Full applications with multiple pages | `module.ts`, `pages/*.tsx` |

## Quick Start: Scaffold a Plugin

The fastest way to create a new plugin:

```bash
# Ensure you have the API key
export ANTHROPIC_API_KEY=your-key

# Generate a panel plugin
python scripts/scaffold_plugin.py --plugin-type panel --name contextcore-my-panel

# Generate a datasource plugin
python scripts/scaffold_plugin.py --plugin-type datasource --name contextcore-my-ds
```

The scaffold script:
1. Generates all required files using Claude
2. Copies webpack config from existing plugins
3. Creates a manifest of what was generated

## Manual Plugin Creation

### 1. Create Directory Structure

```bash
mkdir -p plugins/contextcore-my-panel/src/components
```

### 2. Create plugin.json

```json
{
  "type": "panel",
  "name": "My ContextCore Panel",
  "id": "contextcore-my-panel",
  "info": {
    "description": "Description of the panel",
    "author": {"name": "ContextCore"},
    "keywords": ["contextcore", "panel"],
    "version": "1.0.0",
    "updated": "2026-01-25"
  },
  "dependencies": {
    "grafanaDependency": ">=10.0.0",
    "plugins": []
  }
}
```

### 3. Create package.json

```json
{
  "name": "contextcore-my-panel",
  "version": "1.0.0",
  "scripts": {
    "dev": "webpack -w -c ./.config/webpack/webpack.config.js --env development",
    "build": "webpack -c ./.config/webpack/webpack.config.js --env production",
    "test": "jest --passWithNoTests",
    "clean": "rm -rf dist"
  },
  "dependencies": {
    "@emotion/css": "^11.11.0",
    "@grafana/data": "^11.0.0",
    "@grafana/runtime": "^11.0.0",
    "@grafana/ui": "^11.0.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "devDependencies": {
    "typescript": "^5.2.0",
    "webpack": "^5.88.0"
  }
}
```

### 4. Create types.ts

```typescript
export interface MyPanelOptions {
  apiUrl: string;
  showMetrics: boolean;
}
```

### 5. Create module.ts

```typescript
import { PanelPlugin } from '@grafana/data';
import { MyPanel } from './components/MyPanel';
import { MyPanelOptions } from './types';

export const plugin = new PanelPlugin<MyPanelOptions>(MyPanel)
  .setPanelOptions((builder) => {
    builder
      .addTextInput({
        path: 'apiUrl',
        name: 'API URL',
        defaultValue: 'http://localhost:8080',
      })
      .addBooleanSwitch({
        path: 'showMetrics',
        name: 'Show Metrics',
        defaultValue: true,
      });
  });
```

### 6. Create Panel Component

```typescript
// src/components/MyPanel.tsx
import React, { useState } from 'react';
import { PanelProps } from '@grafana/data';
import { Button, useStyles2 } from '@grafana/ui';
import { css } from '@emotion/css';
import { MyPanelOptions } from '../types';

interface Props extends PanelProps<MyPanelOptions> {}

export const MyPanel: React.FC<Props> = ({ options, width, height }) => {
  const [loading, setLoading] = useState(false);
  const styles = useStyles2(getStyles);

  return (
    <div className={styles.container} style={{ width, height }}>
      <Button onClick={() => setLoading(true)} disabled={loading}>
        {loading ? 'Loading...' : 'Click Me'}
      </Button>
    </div>
  );
};

const getStyles = () => ({
  container: css`
    display: flex;
    padding: 12px;
  `,
});
```

### 7. Copy Build Configuration

```bash
cp -r plugins/contextcore-chat-panel/.config plugins/contextcore-my-panel/
cp plugins/contextcore-chat-panel/{tsconfig.json,.eslintrc,.gitignore} plugins/contextcore-my-panel/
```

### 8. Build and Test

```bash
cd plugins/contextcore-my-panel
npm install
npm run build
```

## Panel Options

### Available Option Types

```typescript
.setPanelOptions((builder) => {
  builder
    // Text input
    .addTextInput({
      path: 'text',
      name: 'Text',
      defaultValue: '',
    })
    // Number input
    .addNumberInput({
      path: 'number',
      name: 'Number',
      defaultValue: 0,
    })
    // Boolean switch
    .addBooleanSwitch({
      path: 'enabled',
      name: 'Enabled',
      defaultValue: true,
    })
    // Select dropdown
    .addSelect({
      path: 'mode',
      name: 'Mode',
      defaultValue: 'auto',
      settings: {
        options: [
          { value: 'auto', label: 'Auto' },
          { value: 'manual', label: 'Manual' },
        ],
      },
    })
    // Color picker
    .addColorPicker({
      path: 'color',
      name: 'Color',
      defaultValue: 'green',
    });
})
```

### Categories

Group options into categories:

```typescript
.addTextInput({
  path: 'apiUrl',
  name: 'API URL',
  category: ['Connection'],
})
.addBooleanSwitch({
  path: 'showMetrics',
  name: 'Show Metrics',
  category: ['Display'],
})
```

## Datasource Plugins

### plugin.json with Routes

```json
{
  "type": "datasource",
  "name": "My Datasource",
  "id": "contextcore-my-ds",
  "routes": [
    {
      "path": "api/*",
      "url": "{{ .JsonData.url }}",
      "method": "*"
    }
  ]
}
```

### datasource.ts

```typescript
import { DataSourceApi, DataQueryRequest, DataQueryResponse } from '@grafana/data';
import { getBackendSrv } from '@grafana/runtime';

export class DataSource extends DataSourceApi<MyQuery, MyOptions> {
  async query(options: DataQueryRequest<MyQuery>): Promise<DataQueryResponse> {
    // Use getBackendSrv for route-proxied requests
    const response = await getBackendSrv().fetch({
      url: '/api/plugins/contextcore-my-ds/resources/api/endpoint',
      method: 'POST',
    }).toPromise();

    // Return as DataQueryResponse
    return { data: [...] };
  }

  async testDatasource() {
    return { status: 'success', message: 'Connected!' };
  }
}
```

## Best Practices

### Naming Convention

- Plugin ID: `contextcore-{name}-{type}` (e.g., `contextcore-chat-panel`)
- Package name: Same as plugin ID
- Display name: "ContextCore {Name}"

### Error Handling

```typescript
try {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
} catch (error) {
  setError(error instanceof Error ? error.message : 'Unknown error');
}
```

### Loading States

```typescript
const [loading, setLoading] = useState(false);

if (loading) {
  return <LoadingPlaceholder text="Loading..." />;
}
```

### Template Variables

```typescript
import { getTemplateSrv } from '@grafana/runtime';

const value = getTemplateSrv().replace('${variableName}');
```

## Testing

### Jest Configuration

```javascript
// jest.config.js
module.exports = {
  testEnvironment: 'jsdom',
  transform: { '^.+\\.(ts|tsx)$': '@swc/jest' },
  moduleNameMapper: {
    '\\.(css|scss)$': 'identity-obj-proxy',
  },
};
```

### Writing Tests

```typescript
import { render, screen } from '@testing-library/react';
import { MyPanel } from './MyPanel';

describe('MyPanel', () => {
  it('renders button', () => {
    render(<MyPanel options={{}} width={400} height={300} />);
    expect(screen.getByRole('button')).toBeInTheDocument();
  });
});
```

## Deployment

### Build for Production

```bash
npm run build
```

### Install in Grafana

1. Copy built plugin to Grafana plugins directory:
   ```bash
   cp -r dist /var/lib/grafana/plugins/contextcore-my-panel
   ```

2. Add to unsigned allowlist in `grafana.ini`:
   ```ini
   [plugins]
   allow_loading_unsigned_plugins = contextcore-my-panel
   ```

3. Restart Grafana

### Docker Deployment

```yaml
grafana:
  volumes:
    - ./contextcore-owl/grafana/plugins:/var/lib/grafana/plugins
  environment:
    GF_PLUGINS_ALLOW_LOADING_UNSIGNED_PLUGINS: contextcore-my-panel
```

## References

- [Grafana Plugin Tools](https://grafana.com/developers/plugin-tools/)
- [Build a Panel Plugin](https://grafana.com/developers/plugin-tools/tutorials/build-a-panel-plugin)
- [Build a Datasource Plugin](https://grafana.com/developers/plugin-tools/tutorials/build-a-data-source-plugin)
- [@grafana/ui Components](https://developers.grafana.com/ui/latest/)
