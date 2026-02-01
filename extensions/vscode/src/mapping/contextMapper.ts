import * as vscode from 'vscode';
import * as path from 'path';
import { ProjectContext, Risk } from '../types';
import { ContextProvider } from '../providers';
import { matchesPattern } from './patternMatcher';
import { findContextFiles } from './workspaceScanner';

/**
 * Flattened context for UI display
 */
interface FlattenedContext {
  projectId: string;
  criticality: string;
  owner?: string;
  risks?: Risk[];
  requirements?: {
    targets?: { metric: string; threshold: string }[];
    description?: string;
  };
}

/**
 * Project info for commands
 */
interface CurrentProject {
  id: string;
  name: string;
}

/**
 * Maps workspace files to their relevant ProjectContext based on configuration,
 * risk scopes, and directory structure.
 */
export class ContextMapper implements vscode.Disposable {
  private contextProvider: ContextProvider;
  private fileToContextCache: Map<string, ProjectContext | undefined>;
  private contextFilesCache: Map<string, vscode.Uri[]>;
  private disposables: vscode.Disposable[];
  private isInitialized: boolean;

  constructor(contextProvider: ContextProvider) {
    this.contextProvider = contextProvider;
    this.fileToContextCache = new Map();
    this.contextFilesCache = new Map();
    this.disposables = [];
    this.isInitialized = false;
  }

  /**
   * Initialize the context mapper by scanning workspace folders
   */
  async initialize(): Promise<void> {
    try {
      const workspaceFolders = vscode.workspace.workspaceFolders || [];

      for (const folder of workspaceFolders) {
        const contextFiles = await findContextFiles(folder);
        this.contextFilesCache.set(folder.uri.toString(), contextFiles);
      }

      this.setupWorkspaceChangeListener();
      this.isInitialized = true;
    } catch (error) {
      console.error('Failed to initialize ContextMapper:', error);
      throw error;
    }
  }

  /**
   * Get the ProjectContext for a given file path
   */
  getContextForFile(filePath: string): FlattenedContext | undefined {
    if (!this.isInitialized) {
      console.warn('ContextMapper not initialized');
      return undefined;
    }

    const uri = vscode.Uri.file(filePath);
    const cacheKey = uri.fsPath;
    if (this.fileToContextCache.has(cacheKey)) {
      const context = this.fileToContextCache.get(cacheKey);
      return context ? this.flattenContext(context) : undefined;
    }

    const context = this.findContextForFile(uri);
    this.fileToContextCache.set(cacheKey, context);
    return context ? this.flattenContext(context) : undefined;
  }

  /**
   * Get the ProjectContext for a given document
   */
  getContextForDocument(document: vscode.TextDocument): FlattenedContext | undefined {
    return this.getContextForFile(document.uri.fsPath);
  }

  /**
   * Get the current active project
   */
  async getCurrentProject(): Promise<CurrentProject | undefined> {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
      return undefined;
    }

    const context = this.getContextForFile(editor.document.uri.fsPath);
    if (!context) {
      return undefined;
    }

    return {
      id: context.projectId,
      name: context.projectId
    };
  }

  /**
   * Get risks for a project
   */
  async getProjectRisks(projectId: string): Promise<Risk[]> {
    const contexts = this.contextProvider.getAllContexts();
    for (const context of contexts) {
      const flat = this.flattenContext(context);
      if (flat.projectId === projectId && flat.risks) {
        return flat.risks;
      }
    }
    return [];
  }

  /**
   * Flatten a ProjectContext for easy UI access
   */
  private flattenContext(context: ProjectContext): FlattenedContext {
    return {
      projectId: context.projectId || context.spec?.project?.id || context.metadata?.name || 'unknown',
      criticality: context.criticality || context.spec?.business?.criticality || 'medium',
      owner: context.owner || context.spec?.business?.owner,
      risks: context.risks || context.spec?.risks,
      requirements: context.requirements || context.spec?.requirements
    };
  }

  /**
   * Find context for file using priority system:
   * 1. Risk scope patterns
   * 2. Closest parent with .contextcore
   * 3. Workspace root context
   */
  private findContextForFile(uri: vscode.Uri): ProjectContext | undefined {
    try {
      // Priority 1: Check risk scope patterns
      const riskScopeContext = this.findRiskScopeContext(uri);
      if (riskScopeContext) {
        return riskScopeContext;
      }

      // Priority 2: Closest parent with .contextcore
      const parentContext = this.findParentDirectoryContext(uri);
      if (parentContext) {
        return parentContext;
      }

      // Priority 3: Workspace root context
      return this.findWorkspaceRootContext(uri);
    } catch (error) {
      console.error('Error finding context for file:', uri.fsPath, error);
      return undefined;
    }
  }

  private findRiskScopeContext(uri: vscode.Uri): ProjectContext | undefined {
    const contexts = this.contextProvider.getAllContexts();
    const relativePath = this.getRelativePath(uri);

    for (const context of contexts) {
      if (context.risk?.scope) {
        for (const pattern of context.risk.scope) {
          if (matchesPattern(relativePath, pattern)) {
            return context;
          }
        }
      }
    }
    return undefined;
  }

  private findParentDirectoryContext(uri: vscode.Uri): ProjectContext | undefined {
    let currentDir = path.dirname(uri.fsPath);
    const workspaceRoot = this.getWorkspaceRoot(uri);

    while (currentDir && currentDir !== workspaceRoot && currentDir !== path.dirname(currentDir)) {
      const contextFile = path.join(currentDir, '.contextcore');
      const context = this.contextProvider.getContextByPath(contextFile);
      if (context) {
        return context;
      }
      currentDir = path.dirname(currentDir);
    }
    return undefined;
  }

  private findWorkspaceRootContext(uri: vscode.Uri): ProjectContext | undefined {
    const workspaceFolder = vscode.workspace.getWorkspaceFolder(uri);
    if (!workspaceFolder) {
      return undefined;
    }

    const rootContextFile = path.join(workspaceFolder.uri.fsPath, '.contextcore');
    return this.contextProvider.getContextByPath(rootContextFile);
  }

  private getRelativePath(uri: vscode.Uri): string {
    const workspaceFolder = vscode.workspace.getWorkspaceFolder(uri);
    if (!workspaceFolder) {
      return uri.fsPath;
    }
    return path.relative(workspaceFolder.uri.fsPath, uri.fsPath);
  }

  private getWorkspaceRoot(uri: vscode.Uri): string | undefined {
    const workspaceFolder = vscode.workspace.getWorkspaceFolder(uri);
    return workspaceFolder?.uri.fsPath;
  }

  /**
   * Set up file system watchers for context files
   */
  private setupWorkspaceChangeListener(): void {
    const patterns = [
      '**/.contextcore',
      '**/.contextcore.yaml',
      '**/.contextcore.yml',
      '**/projectcontext.yaml',
      '**/projectcontext.yml'
    ];

    for (const pattern of patterns) {
      const watcher = vscode.workspace.createFileSystemWatcher(pattern);

      watcher.onDidCreate((uri) => this.handleContextFileChange(uri));
      watcher.onDidChange((uri) => this.handleContextFileChange(uri));
      watcher.onDidDelete((uri) => this.handleContextFileChange(uri));

      this.disposables.push(watcher);
    }

    // Listen for file changes to invalidate cache
    const fileWatcher = vscode.workspace.onDidChangeTextDocument((event) => {
      this.fileToContextCache.delete(event.document.uri.fsPath);
    });

    this.disposables.push(fileWatcher);
  }

  private handleContextFileChange(uri: vscode.Uri): void {
    // Invalidate relevant cache entries
    this.fileToContextCache.clear();

    // Update context files cache
    const workspaceFolder = vscode.workspace.getWorkspaceFolder(uri);
    if (workspaceFolder) {
      findContextFiles(workspaceFolder).then(contextFiles => {
        this.contextFilesCache.set(workspaceFolder.uri.toString(), contextFiles);
      }).catch(error => {
        console.error('Error updating context files cache:', error);
      });
    }
  }

  /**
   * Dispose of all resources
   */
  dispose(): void {
    this.disposables.forEach(disposable => {
      try {
        disposable.dispose();
      } catch (error) {
        console.error('Error disposing resource:', error);
      }
    });
    this.disposables = [];
    this.fileToContextCache.clear();
    this.contextFilesCache.clear();
  }
}
