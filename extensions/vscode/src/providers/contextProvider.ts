import * as vscode from 'vscode';
import { ProjectContext } from '../types';
import { Cache } from '../cache';
import { loadLocalConfig } from './localConfigProvider';
import { loadFromCli } from './cliProvider';
import { loadFromKubernetes } from './kubernetesProvider';
import { getFullConfig } from '../config';

/**
 * Provider that loads ProjectContext from multiple sources with caching and automatic refresh.
 * Sources are checked in priority order: local files -> CLI -> Kubernetes.
 */
export class ContextProvider implements vscode.Disposable {
    private _onContextChange: vscode.EventEmitter<ProjectContext | undefined> = new vscode.EventEmitter();
    private cache: Cache<ProjectContext>;
    private contextsByPath: Map<string, ProjectContext> = new Map();
    private allContexts: ProjectContext[] = [];
    private refreshTimer?: ReturnType<typeof setInterval>;
    private disposables: vscode.Disposable[] = [];

    constructor() {
        const config = getFullConfig();
        this.cache = new Cache<ProjectContext>(config.refreshInterval);
        this.disposables.push(this._onContextChange);
    }

    /**
     * Initialize the context provider
     */
    async initialize(): Promise<void> {
        await this.loadAllContexts();
        this.setupAutoRefresh();
    }

    /**
     * Get project context for the given workspace folder.
     * Uses cache if available, otherwise loads from sources.
     */
    async getContext(workspaceFolder: vscode.WorkspaceFolder): Promise<ProjectContext | undefined> {
        const cacheKey = workspaceFolder.uri.toString();

        try {
            const cachedContext = this.cache.get(cacheKey);
            if (cachedContext) {
                return cachedContext;
            }

            const context = await this.loadFromSources(workspaceFolder);
            if (context) {
                this.cache.set(cacheKey, context);
                this._onContextChange.fire(context);
            }

            return context;
        } catch (error) {
            console.error(`Failed to get context for ${workspaceFolder.name}:`, error);
            return undefined;
        }
    }

    /**
     * Get context by file path
     */
    getContextByPath(path: string): ProjectContext | undefined {
        return this.contextsByPath.get(path);
    }

    /**
     * Get all loaded contexts
     */
    getAllContexts(): ProjectContext[] {
        return this.allContexts;
    }

    /**
     * Invalidate all cached contexts
     */
    invalidateCache(): void {
        this.cache.clear();
    }

    /**
     * Manually refresh all cached contexts by invalidating cache and reloading.
     */
    async refresh(): Promise<void> {
        try {
            this.cache.clear();
            await this.loadAllContexts();
            this._onContextChange.fire(undefined);
        } catch (error) {
            console.error('Failed to refresh contexts:', error);
        }
    }

    /**
     * Event fired when context changes.
     */
    get onContextChange(): vscode.Event<ProjectContext | undefined> {
        return this._onContextChange.event;
    }

    /**
     * Load all contexts from workspace folders
     */
    private async loadAllContexts(): Promise<void> {
        this.allContexts = [];
        this.contextsByPath.clear();

        const workspaceFolders = vscode.workspace.workspaceFolders || [];
        for (const folder of workspaceFolders) {
            const context = await this.loadFromSources(folder);
            if (context) {
                this.allContexts.push(context);
                const contextPath = vscode.Uri.joinPath(folder.uri, '.contextcore').fsPath;
                this.contextsByPath.set(contextPath, context);
            }
        }
    }

    /**
     * Load context from sources in priority order: local -> CLI -> Kubernetes.
     */
    private async loadFromSources(workspaceFolder: vscode.WorkspaceFolder): Promise<ProjectContext | undefined> {
        // Try local config first
        const localContext = await loadLocalConfig(workspaceFolder);
        if (localContext) {
            return localContext;
        }

        // Try CLI second
        const cliContext = await loadFromCli(workspaceFolder);
        if (cliContext) {
            return cliContext;
        }

        // Try Kubernetes last
        const kubernetesContext = await loadFromKubernetes(workspaceFolder.name);
        if (kubernetesContext) {
            return kubernetesContext;
        }

        return undefined;
    }

    /**
     * Set up automatic refresh timer based on configuration.
     */
    private setupAutoRefresh(): void {
        const config = getFullConfig();
        if (config.refreshInterval > 0) {
            this.refreshTimer = setInterval(() => {
                this.refresh();
            }, config.refreshInterval);
        }
    }

    dispose(): void {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
            this.refreshTimer = undefined;
        }

        this.disposables.forEach(disposable => {
            try {
                disposable.dispose();
            } catch (error) {
                console.error('Error disposing resource:', error);
            }
        });

        this.disposables = [];
    }
}
