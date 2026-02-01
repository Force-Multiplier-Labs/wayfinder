"""
VSCode Extension Assembly tasks for Lead Contractor workflow.

These tasks take the generated feature code and assemble it into
a complete, compilable VSCode extension.
"""

from ..runner import Feature

ASSEMBLY_PACKAGE_CONFIG_TASK = """
Create the complete VSCode extension configuration files.

## Goal
Generate production-ready package.json, tsconfig.json, and supporting config files
for the ContextCore VSCode extension.

## Requirements

1. Create package.json with:
   - name: "contextcore-vscode"
   - displayName: "ContextCore"
   - description: "ProjectContext awareness in your editor"
   - version: "0.1.0"
   - publisher: "contextcore"
   - engines.vscode: "^1.85.0"
   - categories: ["Other", "Visualization"]
   - activationEvents: ["workspaceContains:**/.contextcore", "workspaceContains:**/.contextcore.yaml", "workspaceContains:**/projectcontext.yaml"]
   - main: "./out/extension.js"
   - contributes:
     - configuration with properties:
       - contextcore.kubeconfig (string, default "", description: "Path to kubeconfig file")
       - contextcore.namespace (string, default "default", description: "Default Kubernetes namespace")
       - contextcore.showInlineHints (boolean, default true, description: "Show inline SLO hints")
       - contextcore.refreshInterval (number, default 30, min 5, max 300, description: "Auto-refresh interval in seconds")
       - contextcore.grafanaUrl (string, default "http://localhost:3000", description: "Grafana base URL")
     - viewsContainers.activitybar: [{ id: "contextcore", title: "ContextCore", icon: "resources/icons/contextcore.svg" }]
     - views.contextcore: [
         { id: "contextcore.projectView", name: "Projects" },
         { id: "contextcore.risksView", name: "Risks" },
         { id: "contextcore.requirementsView", name: "Requirements" }
       ]
     - commands: [
         { command: "contextcore.refresh", title: "Refresh Context", icon: "$(refresh)" },
         { command: "contextcore.showImpact", title: "Show Impact Analysis" },
         { command: "contextcore.openDashboard", title: "Open in Grafana", icon: "$(link-external)" },
         { command: "contextcore.showRisks", title: "Show Risks" }
       ]
     - menus.view/title: [{ command: "contextcore.refresh", when: "view == contextcore.projectView", group: "navigation" }]
   - scripts:
     - "vscode:prepublish": "npm run compile"
     - "compile": "tsc -p ./"
     - "watch": "tsc -watch -p ./"
     - "package": "vsce package"
     - "lint": "eslint src --ext ts"
   - devDependencies:
     - typescript: "^5.3.0"
     - @types/vscode: "^1.85.0"
     - @types/node: "^20.0.0"
     - @vscode/vsce: "^2.22.0"
     - eslint: "^8.56.0"
     - @typescript-eslint/parser: "^6.0.0"
     - @typescript-eslint/eslint-plugin: "^6.0.0"
   - dependencies:
     - yaml: "^2.3.0"
     - @kubernetes/client-node: "^0.20.0"

2. Create tsconfig.json with:
   - compilerOptions:
     - module: "commonjs"
     - target: "ES2020"
     - lib: ["ES2020"]
     - outDir: "out"
     - rootDir: "src"
     - strict: true
     - esModuleInterop: true
     - skipLibCheck: true
     - forceConsistentCasingInFileNames: true
     - declaration: true
     - sourceMap: true
   - exclude: ["node_modules", ".vscode-test"]

3. Create .vscodeignore with:
   - .vscode/**
   - .vscode-test/**
   - src/**
   - node_modules/**
   - .gitignore
   - tsconfig.json
   - **/*.map
   - **/*.ts
   - !out/**/*.d.ts

4. Create .eslintrc.json with TypeScript rules:
   - parser: "@typescript-eslint/parser"
   - parserOptions.ecmaVersion: 2020, sourceType: "module"
   - plugins: ["@typescript-eslint"]
   - extends: ["eslint:recommended", "plugin:@typescript-eslint/recommended"]
   - rules: semi, no-unused-vars off, @typescript-eslint/no-unused-vars warn, @typescript-eslint/no-explicit-any warn

## Output Format
Provide the complete JSON content for each file. Format JSON properly with 2-space indentation.
Label each file clearly with its filename.
"""

ASSEMBLY_CORE_MODULES_TASK = """
Assemble the core infrastructure modules for the ContextCore VSCode extension.

## Goal
Create production-ready core modules (types, config, logger, cache) with proper
imports, exports, and integration between modules.

## Requirements

1. Create src/types.ts:
   Export all TypeScript interfaces that match the ProjectContext CRD schema:

   - ProjectContext { metadata: ProjectMetadata; spec: ProjectContextSpec }
   - ProjectMetadata { name: string; namespace: string }
   - ProjectContextSpec { project?: ProjectInfo; business?: BusinessContext; requirements?: Requirements; risks?: Risk[]; targets?: Target[]; design?: Design }
   - ProjectInfo { id: string; epic?: string; name?: string }
   - BusinessContext { criticality?: 'critical' | 'high' | 'medium' | 'low'; value?: string; owner?: string; costCenter?: string }
   - Requirements { availability?: string; latencyP99?: string; latencyP50?: string; throughput?: string; errorBudget?: string }
   - Risk { type: string; priority: 'P1' | 'P2' | 'P3' | 'P4'; description: string; scope?: string; mitigation?: string }
   - Target { kind: string; name: string; namespace?: string }
   - Design { adr?: string; doc?: string; apiContract?: string }

   Also export:
   - ContextCoreConfig { refreshInterval: number; kubeconfig?: string; namespace: string; showInlineHints: boolean; grafanaUrl: string }

2. Create src/config.ts:
   - import * as vscode from 'vscode'
   - Export CONFIG_KEYS constant object with all config key strings
   - Export function getConfig<T>(key: string, defaultValue?: T): T
   - Export function onConfigChange(callback: () => void): vscode.Disposable
   - Export function getFullConfig(): ContextCoreConfig

3. Create src/logger.ts:
   - import * as vscode from 'vscode'
   - Private outputChannel variable
   - Export type LogLevel = 'info' | 'warn' | 'error'
   - Export function initialize(): void - creates output channel "ContextCore"
   - Export function log(message: string, level?: LogLevel): void - logs with timestamp
   - Export function showError(message: string): void - logs and shows notification
   - Export function dispose(): void - disposes output channel

4. Create src/cache.ts:
   - Export interface CacheEntry<T> { value: T; expiresAt: number }
   - Export class Cache<T>:
     - constructor(defaultTtlMs: number)
     - get(key: string): T | undefined
     - set(key: string, value: T, ttlMs?: number): void
     - invalidate(key: string): void
     - clear(): void
     - size(): number
     - Private cleanup() method to remove expired entries

## Output Format
Provide complete TypeScript files with proper imports, exports, and JSDoc comments.
Each file should be self-contained and ready to save directly.
Label each file clearly with its path (e.g., "// File: src/types.ts").
"""

ASSEMBLY_PROVIDERS_TASK = """
Assemble the context provider modules for the ContextCore VSCode extension.

## Goal
Create the provider layer that loads ProjectContext from multiple sources
(local files, CLI, Kubernetes) with caching and automatic refresh.

## Requirements

1. Create src/providers/index.ts:
   - Re-export ContextProvider from './contextProvider'
   - Re-export loadLocalConfig from './localConfigProvider'
   - Re-export loadFromCli from './cliProvider'
   - Re-export loadFromKubernetes from './kubernetesProvider'

2. Create src/providers/contextProvider.ts:
   - import * as vscode from 'vscode'
   - import { ProjectContext, ContextCoreConfig } from '../types'
   - import { Cache } from '../cache'
   - import { loadLocalConfig } from './localConfigProvider'
   - import { loadFromCli } from './cliProvider'
   - import { loadFromKubernetes } from './kubernetesProvider'
   - import { getFullConfig } from '../config'

   Export class ContextProvider implements vscode.Disposable:
   - private _onContextChange: EventEmitter<ProjectContext | undefined>
   - private cache: Cache<ProjectContext>
   - private refreshTimer?: NodeJS.Timeout
   - private disposables: Disposable[]

   - constructor() - initialize cache with config refreshInterval
   - async getContext(workspaceFolder: WorkspaceFolder): Promise<ProjectContext | undefined>
   - async refresh(): Promise<void> - invalidate cache and reload all
   - get onContextChange(): Event<ProjectContext | undefined>
   - private async loadFromSources(workspaceFolder): Promise<ProjectContext | undefined> - try local -> CLI -> K8s
   - private setupAutoRefresh(): void
   - dispose(): void

3. Create src/providers/localConfigProvider.ts:
   - import * as vscode from 'vscode'
   - import * as path from 'path'
   - import * as yaml from 'yaml'
   - import { ProjectContext } from '../types'

   Export async function loadLocalConfig(workspaceFolder: WorkspaceFolder): Promise<ProjectContext | undefined>
   - Look for .contextcore.yaml, .contextcore in workspace root
   - Parse YAML content
   - Return undefined if not found (don't throw)

4. Create src/providers/cliProvider.ts:
   - import * as child_process from 'child_process'
   - import * as vscode from 'vscode'
   - import { ProjectContext } from '../types'

   Export async function loadFromCli(workspaceFolder: WorkspaceFolder): Promise<ProjectContext | undefined>
   - Execute: contextcore context show --format json
   - Parse JSON output
   - Return undefined if command fails (don't throw)

5. Create src/providers/kubernetesProvider.ts:
   - import * as k8s from '@kubernetes/client-node'
   - import { ProjectContext } from '../types'
   - import { getConfig } from '../config'

   Export async function loadFromKubernetes(name: string, namespace?: string): Promise<ProjectContext | undefined>
   - Load kubeconfig from config or default location
   - Fetch ProjectContext CRD from cluster
   - Return undefined if not available (don't throw)

## Output Format
Provide complete TypeScript files with proper imports, async/await, and error handling.
Label each file with its path.
"""

ASSEMBLY_MAPPING_TASK = """
Assemble the file-to-context mapping modules for the ContextCore VSCode extension.

## Goal
Create the mapping layer that associates workspace files with their relevant
ProjectContext based on configuration, risk scopes, and directory structure.

## Requirements

1. Create src/mapping/index.ts:
   - Re-export ContextMapper from './contextMapper'
   - Re-export matchesPattern from './patternMatcher'
   - Re-export findContextFiles from './workspaceScanner'

2. Create src/mapping/contextMapper.ts:
   - import * as vscode from 'vscode'
   - import * as path from 'path'
   - import { ProjectContext } from '../types'
   - import { ContextProvider } from '../providers'
   - import { matchesPattern } from './patternMatcher'
   - import { findContextFiles } from './workspaceScanner'

   Export class ContextMapper implements vscode.Disposable:
   - private contextProvider: ContextProvider
   - private fileToContextCache: Map<string, ProjectContext | undefined>
   - private contextFilesCache: Map<string, vscode.Uri[]>
   - private disposables: Disposable[]
   - private isInitialized: boolean

   - constructor(contextProvider: ContextProvider)
   - async initialize(): Promise<void> - scan workspace folders
   - getContextForFile(uri: Uri): ProjectContext | undefined
   - getContextForDocument(document: TextDocument): ProjectContext | undefined
   - private findContextForFile(uri: Uri): ProjectContext | undefined
     - Priority 1: Check risk.scope patterns
     - Priority 2: Closest parent with .contextcore
     - Priority 3: Workspace root context
   - private setupWorkspaceChangeListener(): void
   - dispose(): void

3. Create src/mapping/patternMatcher.ts:
   Export function matchesPattern(filePath: string, pattern: string): boolean
   - Normalize path separators
   - Handle negation with ! prefix
   - Support glob patterns: * (single segment), ** (any depth), ? (single char)
   - Convert to regex and test

   Export function matchesAnyPattern(filePath: string, patterns: string[]): boolean

4. Create src/mapping/workspaceScanner.ts:
   - import * as vscode from 'vscode'

   Export async function findContextFiles(folder: WorkspaceFolder): Promise<Uri[]>
   - Use vscode.workspace.findFiles
   - Pattern: **/{.contextcore,.contextcore.yaml,.contextcore.yml,projectcontext.yaml,projectcontext.yml}
   - Exclude: **/node_modules/**
   - Sort by depth (closer to root first)

## Output Format
Provide complete TypeScript files with efficient caching and proper VSCode API usage.
Label each file with its path.
"""

ASSEMBLY_UI_TASK = """
Assemble the UI components for the ContextCore VSCode extension.

## Goal
Create status bar, side panel tree view, and editor decorations.

## Requirements

1. Create src/ui/statusBar.ts:
   - import * as vscode from 'vscode'
   - import { ContextMapper } from '../mapping'
   - import { ProjectContext } from '../types'
   - import { buildTooltip } from './statusBarTooltip'

   Export class ContextStatusBar implements vscode.Disposable:
   - private statusBarItem: StatusBarItem
   - private disposables: Disposable[]
   - constructor(contextMapper: ContextMapper)
   - update(editor: TextEditor | undefined): void
   - private getCriticalityStyle(criticality): { icon: string; backgroundColor?: ThemeColor }
     - critical: $(flame), errorBackground
     - high: $(warning), warningBackground
     - medium: $(info), undefined
     - low: $(check), undefined
     - unknown: $(question), undefined
   - private handleStatusBarClick(): Promise<void> - show quick pick menu
   - dispose(): void

2. Create src/ui/statusBarTooltip.ts:
   - import * as vscode from 'vscode'
   - import { ProjectContext } from '../types'

   Export function buildTooltip(context: ProjectContext): vscode.MarkdownString
   - Include: project ID, criticality, owner, risk count, requirements summary

3. Create src/ui/sidePanel/index.ts:
   - Re-export ProjectTreeProvider, ContextTreeItem, TreeItemType

4. Create src/ui/sidePanel/contextTreeItem.ts:
   - import * as vscode from 'vscode'

   Export enum TreeItemType { Project, Section, Risk, Requirement, Target, Property }

   Export class ContextTreeItem extends vscode.TreeItem:
   - constructor(label, collapsibleState, type, value?, priority?, count?)
   - private getIcon(): ThemeIcon - based on type and priority
   - contextValue for context menu matching

5. Create src/ui/sidePanel/projectTreeProvider.ts:
   - import * as vscode from 'vscode'
   - import { ContextTreeItem, TreeItemType } from './contextTreeItem'
   - import { ContextMapper } from '../../mapping'

   Export class ProjectTreeProvider implements TreeDataProvider<ContextTreeItem>:
   - private _onDidChangeTreeData: EventEmitter
   - readonly onDidChangeTreeData: Event
   - constructor(contextMapper: ContextMapper)
   - getTreeItem(element): TreeItem
   - getChildren(element?): ContextTreeItem[]
   - refresh(): void
   - dispose(): void

6. Create src/ui/decorations/index.ts:
   - Re-export DecorationProvider

7. Create src/ui/decorations/decorationProvider.ts:
   - import * as vscode from 'vscode'
   - import { ContextMapper } from '../../mapping'
   - import { findHttpHandlers, buildSloDecoration } from './sloDecorations'
   - import { isFileInRiskScope, buildRiskDecoration } from './riskDecorations'

   Export class DecorationProvider implements vscode.Disposable:
   - private sloDecorationType: TextEditorDecorationType
   - private riskDecorationType: TextEditorDecorationType
   - constructor(contextMapper: ContextMapper)
   - updateDecorations(editor: TextEditor): void
   - private isInlineHintsEnabled(): boolean - check config
   - dispose(): void

8. Create src/ui/decorations/sloDecorations.ts:
   Export function findHttpHandlers(document: TextDocument): Range[]
   Export function buildSloDecoration(ranges: Range[], requirements: Requirements): DecorationOptions[]

9. Create src/ui/decorations/riskDecorations.ts:
   Export function isFileInRiskScope(filePath: string, risks: Risk[]): Risk | undefined
   Export function buildRiskDecoration(risk: Risk): DecorationOptions[]

## Output Format
Provide complete TypeScript files ready to use. Label each file with its path.
"""

ASSEMBLY_COMMANDS_TASK = """
Assemble the commands and main extension entry point for the ContextCore VSCode extension.

## Goal
Create all commands and wire everything together in extension.ts.

## Requirements

1. Create src/commands/index.ts:
   - Re-export all command creators

2. Create src/commands/refreshContext.ts:
   - import * as vscode from 'vscode'
   - import { ContextProvider } from '../providers'

   Export function createRefreshCommand(contextProvider: ContextProvider): vscode.Disposable
   - Register command: contextcore.refresh
   - Invalidate cache, refresh, show info message

3. Create src/commands/showImpact.ts:
   - import * as vscode from 'vscode'
   - import { ContextMapper } from '../mapping'
   - import { runContextCoreCommand } from '../utils/cliRunner'

   Export function createShowImpactCommand(contextMapper: ContextMapper): vscode.Disposable
   - Register command: contextcore.showImpact
   - Get current project, run: contextcore graph impact --project <id>
   - Show results in output channel

4. Create src/commands/openDashboard.ts:
   - import * as vscode from 'vscode'
   - import { ContextMapper } from '../mapping'
   - import { getConfig } from '../config'

   Export function createOpenDashboardCommand(contextMapper: ContextMapper): vscode.Disposable
   - Register command: contextcore.openDashboard
   - Build URL: {grafanaUrl}/d/contextcore-project?var-project={projectId}
   - Open with vscode.env.openExternal

5. Create src/commands/showRisks.ts:
   - import * as vscode from 'vscode'
   - import { ContextMapper } from '../mapping'

   Export function createShowRisksCommand(contextMapper: ContextMapper): vscode.Disposable
   - Register command: contextcore.showRisks
   - Show quick pick with risks grouped by priority (P1, P2, P3, P4)

6. Create src/utils/cliRunner.ts:
   - import { exec } from 'child_process'
   - import { promisify } from 'util'

   Export async function runContextCoreCommand(command: string): Promise<string>

7. Create src/extension.ts (CRITICAL - main entry point):
   - import * as vscode from 'vscode'
   - import * as logger from './logger'
   - import { ContextProvider } from './providers'
   - import { ContextMapper } from './mapping'
   - import { ContextStatusBar } from './ui/statusBar'
   - import { ProjectTreeProvider } from './ui/sidePanel'
   - import { DecorationProvider } from './ui/decorations'
   - import { createRefreshCommand, createShowImpactCommand, createOpenDashboardCommand, createShowRisksCommand } from './commands'

   Export function activate(context: vscode.ExtensionContext): void
     1. Initialize logger
     2. Log "ContextCore extension activating..."
     3. Create ContextProvider
     4. Create ContextMapper(contextProvider)
     5. Initialize mapper: await contextMapper.initialize()
     6. Create ContextStatusBar(contextMapper)
     7. Create ProjectTreeProvider(contextMapper)
     8. Register tree: vscode.window.registerTreeDataProvider('contextcore.projectView', treeProvider)
     9. Create DecorationProvider(contextMapper)
     10. Register commands: refresh, showImpact, openDashboard, showRisks
     11. Add all disposables to context.subscriptions
     12. Log "ContextCore extension activated"

   Export function deactivate(): void
     - Logger cleanup handled by disposables

## Output Format
Provide complete TypeScript files. extension.ts must be fully integrated and working.
Label each file with its path.
"""

ASSEMBLY_RESOURCES_TASK = """
Create resource files and README for the ContextCore VSCode extension.

## Goal
Create SVG icons and documentation.

## Requirements

1. Create resources/icons/contextcore.svg:
   - 24x24 SVG icon for activity bar
   - Design: interconnected nodes representing project context
   - Use currentColor for theme compatibility

2. Create resources/icons/red-circle.svg:
   - 16x16 filled red circle (#dc2626) for P1 risks

3. Create resources/icons/orange-circle.svg:
   - 16x16 filled orange circle (#ea580c) for P2 risks

4. Create resources/icons/yellow-circle.svg:
   - 16x16 filled yellow circle (#ca8a04) for P3 risks

5. Create README.md:
   ## ContextCore for Visual Studio Code

   ### Features
   - **Status Bar**: Shows current project criticality at a glance
   - **Side Panel**: Full project context tree with business info, risks, requirements, targets
   - **Inline Hints**: SLO requirements shown near HTTP handlers (configurable)
   - **Risk Indicators**: Gutter icons for files in risk scope
   - **Commands**: Refresh, Impact Analysis, Open Grafana Dashboard, Show Risks

   ### Installation
   1. Install from VSIX: `code --install-extension contextcore-vscode-0.1.0.vsix`
   2. Or build from source (see Development section)

   ### Configuration
   | Setting | Type | Default | Description |
   |---------|------|---------|-------------|
   | `contextcore.kubeconfig` | string | "" | Path to kubeconfig |
   | `contextcore.namespace` | string | "default" | K8s namespace |
   | `contextcore.showInlineHints` | boolean | true | Show SLO hints |
   | `contextcore.refreshInterval` | number | 30 | Refresh interval (seconds) |
   | `contextcore.grafanaUrl` | string | "http://localhost:3000" | Grafana URL |

   ### Usage
   1. Open workspace with `.contextcore` or `projectcontext.yaml`
   2. Click ContextCore icon in Activity Bar
   3. Use Command Palette for actions

   ### Development
   ```bash
   npm install
   npm run compile
   # Press F5 to launch Extension Development Host
   npm run package  # Create VSIX
   ```

   ### Requirements
   - VSCode 1.85.0+
   - Node.js 18+ (for development)
   - Optional: Kubernetes cluster for live context

## Output Format
Provide complete SVG content and README markdown.
Label each file with its path.
"""


ASSEMBLY_FEATURES = [
    Feature(
        task=ASSEMBLY_PACKAGE_CONFIG_TASK,
        name="Assembly_PackageConfig",
        is_typescript=True,
        output_subdir="vscode_assembly",
    ),
    Feature(
        task=ASSEMBLY_CORE_MODULES_TASK,
        name="Assembly_CoreModules",
        is_typescript=True,
        output_subdir="vscode_assembly",
    ),
    Feature(
        task=ASSEMBLY_PROVIDERS_TASK,
        name="Assembly_Providers",
        is_typescript=True,
        output_subdir="vscode_assembly",
    ),
    Feature(
        task=ASSEMBLY_MAPPING_TASK,
        name="Assembly_Mapping",
        is_typescript=True,
        output_subdir="vscode_assembly",
    ),
    Feature(
        task=ASSEMBLY_UI_TASK,
        name="Assembly_UI",
        is_typescript=True,
        output_subdir="vscode_assembly",
    ),
    Feature(
        task=ASSEMBLY_COMMANDS_TASK,
        name="Assembly_Commands",
        is_typescript=True,
        output_subdir="vscode_assembly",
    ),
    Feature(
        task=ASSEMBLY_RESOURCES_TASK,
        name="Assembly_Resources",
        is_typescript=True,
        output_subdir="vscode_assembly",
    ),
]
