"""
VSCode Extension feature tasks for Lead Contractor workflow.
"""

from ..runner import Feature

VSCODE_SCAFFOLDING_TASK = """
Create the VSCode extension project scaffolding for ContextCore.

## Goal
Set up a complete VSCode extension project structure with all necessary
configuration files, ready for TypeScript development.

## Context
- Extension will be at extensions/vscode/ within the ContextCore repo
- Extension name: contextcore-vscode
- Display name: ContextCore
- Publisher: contextcore (placeholder)
- Minimum VSCode version: 1.85.0

## Requirements

1. Create package.json with:
   - name: "contextcore-vscode"
   - displayName: "ContextCore"
   - description: "ProjectContext awareness in your editor"
   - version: "0.1.0"
   - engines.vscode: "^1.85.0"
   - categories: ["Other", "Visualization"]
   - activationEvents: ["workspaceContains:**/.contextcore", "workspaceContains:**/projectcontext.yaml"]
   - main: "./out/extension.js"
   - contributes:
     - configuration (contextcore.kubeconfig, contextcore.namespace, contextcore.showInlineHints, contextcore.refreshInterval)
     - viewsContainers.activitybar (contextcore icon)
     - views.contextcore (projectView, risksView, requirementsView)
     - commands (contextcore.refresh, contextcore.showImpact, contextcore.openDashboard, contextcore.showRisks)
   - scripts: compile, watch, package, lint, test
   - devDependencies: typescript, @types/vscode, @types/node, eslint, @typescript-eslint/parser, @typescript-eslint/eslint-plugin, vsce
   - dependencies: yaml, @kubernetes/client-node

2. Create tsconfig.json with:
   - target: ES2020
   - module: commonjs
   - lib: ["ES2020"]
   - outDir: "./out"
   - rootDir: "./src"
   - strict: true
   - esModuleInterop: true
   - skipLibCheck: true
   - forceConsistentCasingInFileNames: true

3. Create .vscodeignore with: .vscode, node_modules, src, .gitignore, tsconfig.json, *.map

4. Create .eslintrc.json with TypeScript rules

5. Create README.md documenting features, installation, and configuration

## Output Format
Provide complete file contents. Use proper JSON formatting for config files.
"""

VSCODE_CORE_TASK = """
Implement the core infrastructure for the ContextCore VSCode extension.

## Goal
Create the extension entry point and foundational utilities that all
other modules depend on.

## Context
- TypeScript extension for VSCode
- Located at extensions/vscode/src/
- Must handle activation and deactivation cleanly
- Should support multiple workspace folders

## Requirements

1. Create src/extension.ts:
   - import * as vscode from 'vscode'
   - export function activate(context: vscode.ExtensionContext): void
   - export function deactivate(): void
   - Initialize logger first
   - Log "ContextCore extension activated"
   - Register disposables with context.subscriptions

2. Create src/types.ts with TypeScript interfaces matching Python models:
   - ProjectContext { metadata: ProjectMetadata; spec: ProjectContextSpec }
   - ProjectMetadata { name: string; namespace: string }
   - ProjectContextSpec { project, business, requirements, risks, targets, design }
   - BusinessContext { criticality?: string; value?: string; owner?: string; costCenter?: string }
   - Requirements { availability?: string; latencyP99?: string; latencyP50?: string; throughput?: string; errorBudget?: string }
   - Risk { type: string; priority: string; description: string; scope?: string; mitigation?: string }
   - Target { kind: string; name: string; namespace?: string }
   - Design { adr?: string; doc?: string; apiContract?: string }

3. Create src/config.ts:
   - function getConfig<T>(key: string, defaultValue?: T): T
   - function onConfigChange(callback: () => void): vscode.Disposable
   - Export configuration keys as constants

4. Create src/logger.ts:
   - Create output channel named "ContextCore"
   - export function log(message: string, level?: 'info' | 'warn' | 'error'): void
   - export function showError(message: string): void (also shows notification)

## Output Format
Provide clean TypeScript with proper types, JSDoc comments, and ES module exports.
"""

VSCODE_CONTEXT_PROVIDER_TASK = """
Implement the context provider system for loading ProjectContext data.

## Goal
Create a provider system that loads ProjectContext from multiple sources
with caching and automatic refresh.

## Context
- TypeScript for VSCode extension
- Must support: local .contextcore files, CLI commands, K8s API
- Should gracefully degrade if sources unavailable
- Uses async/await for all I/O

## Requirements

1. Create src/providers/contextProvider.ts:
   - export class ContextProvider implements vscode.Disposable
   - constructor()
   - async getContext(workspaceFolder: vscode.WorkspaceFolder): Promise<ProjectContext | undefined>
   - async refresh(): Promise<void>
   - readonly onContextChange: vscode.Event<ProjectContext | undefined>
   - dispose(): void
   - Try sources in order: local file -> CLI -> K8s

2. Create src/providers/localConfigProvider.ts:
   - export async function loadLocalConfig(workspaceFolder: vscode.WorkspaceFolder): Promise<ProjectContext | undefined>
   - Look for .contextcore or .contextcore.yaml in workspace root
   - Parse YAML using 'yaml' package
   - Return undefined if file not found

3. Create src/providers/cliProvider.ts:
   - export async function loadFromCli(workspaceFolder: vscode.WorkspaceFolder): Promise<ProjectContext | undefined>
   - Execute: contextcore context show --format json
   - Use child_process.exec with Promise wrapper
   - Parse JSON output
   - Return undefined if command fails

4. Create src/providers/kubernetesProvider.ts:
   - export async function loadFromKubernetes(name: string, namespace: string): Promise<ProjectContext | undefined>
   - Use @kubernetes/client-node
   - Load kubeconfig from default location or config
   - Fetch ProjectContext CRD
   - Return undefined if not available (don't throw)

5. Create src/cache.ts:
   - export class Cache<T>
   - get(key: string): T | undefined
   - set(key: string, value: T, ttlMs?: number): void
   - invalidate(key: string): void
   - clear(): void
   - Default TTL from config (contextcore.refreshInterval * 1000)

## Output Format
Provide TypeScript with async/await, proper error handling, and vscode.Disposable pattern.
"""

VSCODE_CONTEXT_MAPPER_TASK = """
Implement file-to-context mapping for the VSCode extension.

## Goal
Map workspace files to their relevant ProjectContext based on configuration,
risk scopes, and target patterns.

## Context
- A workspace may have multiple ProjectContexts (multi-root)
- Files can match via: .contextcore config, risk.scope patterns
- Should efficiently handle large workspaces
- Cache mappings for performance

## Requirements

1. Create src/mapping/contextMapper.ts:
   - export class ContextMapper implements vscode.Disposable
   - constructor(contextProvider: ContextProvider)
   - async initialize(): Promise<void>
   - getContextForFile(uri: vscode.Uri): ProjectContext | undefined
   - getContextForDocument(document: vscode.TextDocument): ProjectContext | undefined
   - dispose(): void
   - Listen for workspace folder changes

2. Create src/mapping/patternMatcher.ts:
   - export function matchesPattern(filePath: string, pattern: string): boolean
   - Support glob patterns: * (single segment), ** (any depth), ? (single char)
   - Support negation with ! prefix
   - Normalize path separators

3. Create src/mapping/workspaceScanner.ts:
   - export async function findContextFiles(folder: vscode.WorkspaceFolder): Promise<vscode.Uri[]>
   - Use vscode.workspace.findFiles
   - Look for .contextcore, .contextcore.yaml, projectcontext.yaml

4. Mapping priority (implement in contextMapper):
   - Check if file path matches any risk.scope pattern
   - Check closest parent directory with .contextcore
   - Fall back to workspace root context

## Output Format
Provide TypeScript with efficient caching and proper VSCode API usage.
"""

VSCODE_STATUS_BAR_TASK = """
Implement the status bar component showing project criticality.

## Goal
Display current file's project context and criticality in the VSCode
status bar, with quick access to more details.

## Context
- Status bar items appear at bottom of VSCode window
- Should update when active editor changes
- Click should show quick pick menu

## Requirements

1. Create src/ui/statusBar.ts:
   - export class ContextStatusBar implements vscode.Disposable
   - constructor(contextMapper: ContextMapper)
   - private statusBarItem: vscode.StatusBarItem
   - update(editor: vscode.TextEditor | undefined): void
   - dispose(): void
   - Register for onDidChangeActiveTextEditor

2. Status bar display:
   - Icon based on criticality:
     - critical: $(flame)
     - high: $(warning)
     - medium: $(info)
     - low: $(check)
     - unknown: $(question)
   - Text: project ID (truncate if > 20 chars)
   - Background: statusBarItem.errorBackground for critical, warningBackground for high
   - Tooltip: MarkdownString with project details

3. Create src/ui/statusBarTooltip.ts:
   - export function buildTooltip(context: ProjectContext): vscode.MarkdownString
   - Include: project ID, criticality, owner, risk count, requirements summary
   - Use markdown formatting

4. Click action (command: contextcore.statusBarClick):
   - Show quick pick with options:
     - "$(eye) Show Full Context" -> reveal side panel
     - "$(graph) Show Impact Analysis" -> run showImpact command
     - "$(link-external) Open in Grafana" -> run openDashboard command
     - "$(warning) Show Risks" -> run showRisks command

## Output Format
Provide TypeScript using vscode.window.createStatusBarItem with StatusBarAlignment.Right.
"""

VSCODE_SIDE_PANEL_TASK = """
Implement the side panel tree view for full context display.

## Goal
Create an activity bar view that shows the complete ProjectContext
as an expandable tree with projects, risks, and requirements.

## Context
- Activity bar icon appears in left sidebar
- Tree view shows hierarchical data
- Should refresh when context changes

## Requirements

1. Create src/ui/sidePanel/projectTreeProvider.ts:
   - export class ProjectTreeProvider implements vscode.TreeDataProvider<ContextTreeItem>
   - constructor(contextMapper: ContextMapper)
   - getTreeItem(element: ContextTreeItem): vscode.TreeItem
   - getChildren(element?: ContextTreeItem): ContextTreeItem[]
   - refresh(): void
   - private _onDidChangeTreeData: vscode.EventEmitter<ContextTreeItem | undefined>
   - readonly onDidChangeTreeData: vscode.Event<ContextTreeItem | undefined>

2. Create src/ui/sidePanel/contextTreeItem.ts:
   - export class ContextTreeItem extends vscode.TreeItem
   - constructor(label: string, collapsibleState: vscode.TreeItemCollapsibleState, type: TreeItemType)
   - Export TreeItemType enum: Project, Section, Risk, Requirement, Target, Property
   - contextValue for context menu matching

3. Tree structure when expanded:
   - Project node (collapsible)
     - Business section (collapsible)
       - Criticality: <value>
       - Owner: <value>
       - Value: <value>
     - Risks section (collapsible) with count badge
       - Each risk with priority icon (P1 red, P2 orange, P3 yellow, P4 blue)
     - Requirements section (collapsible)
       - Availability: <value>
       - Latency P99: <value>
       - Throughput: <value>
     - Targets section (collapsible)
       - Each target with kind icon

4. Icons:
   - Project: $(package)
   - Business: $(organization)
   - Risks: $(warning)
   - Requirements: $(graph)
   - Targets: $(symbol-class)

## Output Format
Provide TypeScript using vscode.window.registerTreeDataProvider API.
"""

VSCODE_DECORATIONS_TASK = """
Implement editor decorations for inline SLO hints.

## Goal
Show SLO requirements as inline hints near relevant code patterns
(HTTP handlers, database queries, external calls).

## Context
- Decorations appear after line content
- Should be subtle (gray, italic)
- Can be toggled via contextcore.showInlineHints config

## Requirements

1. Create src/ui/decorations/decorationProvider.ts:
   - export class DecorationProvider implements vscode.Disposable
   - constructor(contextMapper: ContextMapper)
   - private sloDecorationType: vscode.TextEditorDecorationType
   - private riskDecorationType: vscode.TextEditorDecorationType
   - updateDecorations(editor: vscode.TextEditor): void
   - dispose(): void
   - Register for onDidChangeActiveTextEditor, onDidChangeTextEditorSelection

2. Create src/ui/decorations/sloDecorations.ts:
   - export function findHttpHandlers(document: vscode.TextDocument): vscode.Range[]
   - Patterns for Python: def get_, def post_, @app.route, async def handle
   - Patterns for TypeScript: app.get(, app.post(, router.get(, async function handle
   - Patterns for Go: func.*Handler, http.HandleFunc
   - export function buildSloDecoration(requirements: Requirements): vscode.DecorationOptions[]

3. SLO decoration style:
   - after.contentText: "// SLO: P99 < {latencyP99}"
   - after.color: new ThemeColor('editorCodeLens.foreground')
   - after.fontStyle: 'italic'
   - after.margin: '0 0 0 2em'

4. Create src/ui/decorations/riskDecorations.ts:
   - export function isFileInRiskScope(filePath: string, risks: Risk[]): Risk | undefined
   - Gutter decoration for files in risk scope
   - gutterIconPath based on priority (P1 red circle, P2 orange, P3 yellow)

5. Respect configuration:
   - Check contextcore.showInlineHints before applying decorations
   - Listen for config changes and update

## Output Format
Provide TypeScript using vscode.window.createTextEditorDecorationType API.
"""

VSCODE_COMMANDS_TASK = """
Implement extension commands and final integration.

## Goal
Create user-facing commands and wire everything together in the
main extension activation.

## Context
- Commands appear in command palette (Ctrl+Shift+P / Cmd+Shift+P)
- Should integrate with contextcore CLI where possible
- Provide quick access to common actions

## Requirements

1. Create src/commands/refreshContext.ts:
   - export function createRefreshCommand(contextProvider: ContextProvider): vscode.Disposable
   - Command ID: contextcore.refresh
   - Invalidate cache and reload all contexts
   - Show information message on completion

2. Create src/commands/showImpact.ts:
   - export function createShowImpactCommand(contextMapper: ContextMapper): vscode.Disposable
   - Command ID: contextcore.showImpact
   - Get current context, run: contextcore graph impact --project <id>
   - Display results in new webview panel or output channel
   - Show blast radius and affected projects

3. Create src/commands/openDashboard.ts:
   - export function createOpenDashboardCommand(contextMapper: ContextMapper): vscode.Disposable
   - Command ID: contextcore.openDashboard
   - Build Grafana URL: {grafanaUrl}/d/contextcore-project?var-project={projectId}
   - Get grafanaUrl from config (default: http://localhost:3000)
   - Open in external browser with vscode.env.openExternal

4. Create src/commands/showRisks.ts:
   - export function createShowRisksCommand(contextMapper: ContextMapper): vscode.Disposable
   - Command ID: contextcore.showRisks
   - Show quick pick with all risks for current context
   - Group by priority with icons
   - Select risk to show details in notification

5. Update src/extension.ts activate():
   - Create ContextProvider
   - Create ContextMapper with provider
   - Initialize mapper
   - Create and register ContextStatusBar
   - Register ProjectTreeProvider with vscode.window.registerTreeDataProvider
   - Create and register DecorationProvider
   - Register all commands
   - Register configuration change listener
   - Add all disposables to context.subscriptions
   - Log completion

## Output Format
Provide TypeScript with proper command registration, error handling, and disposable pattern.
"""

VSCODE_FEATURES = [
    Feature(
        task=VSCODE_SCAFFOLDING_TASK,
        name="VSCode_Scaffolding",
        is_typescript=True,
        output_subdir="vscode",
    ),
    Feature(
        task=VSCODE_CORE_TASK,
        name="VSCode_Core",
        is_typescript=True,
        output_subdir="vscode",
    ),
    Feature(
        task=VSCODE_CONTEXT_PROVIDER_TASK,
        name="VSCode_ContextProvider",
        is_typescript=True,
        output_subdir="vscode",
    ),
    Feature(
        task=VSCODE_CONTEXT_MAPPER_TASK,
        name="VSCode_ContextMapper",
        is_typescript=True,
        output_subdir="vscode",
    ),
    Feature(
        task=VSCODE_STATUS_BAR_TASK,
        name="VSCode_StatusBar",
        is_typescript=True,
        output_subdir="vscode",
    ),
    Feature(
        task=VSCODE_SIDE_PANEL_TASK,
        name="VSCode_SidePanel",
        is_typescript=True,
        output_subdir="vscode",
    ),
    Feature(
        task=VSCODE_DECORATIONS_TASK,
        name="VSCode_Decorations",
        is_typescript=True,
        output_subdir="vscode",
    ),
    Feature(
        task=VSCODE_COMMANDS_TASK,
        name="VSCode_Commands",
        is_typescript=True,
        output_subdir="vscode",
    ),
]
