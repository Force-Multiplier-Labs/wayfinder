import * as vscode from 'vscode';
import * as yaml from 'yaml';
import { ProjectContext } from '../types';

/**
 * Load project context from local configuration files.
 * Looks for .contextcore.yaml or .contextcore in workspace root.
 */
export async function loadLocalConfig(workspaceFolder: vscode.WorkspaceFolder): Promise<ProjectContext | undefined> {
    const configFiles = ['.contextcore.yaml', '.contextcore'];

    for (const fileName of configFiles) {
        try {
            const configPath = vscode.Uri.joinPath(workspaceFolder.uri, fileName);
            const configData = await vscode.workspace.fs.readFile(configPath);
            const configText = Buffer.from(configData).toString('utf8');

            const context = yaml.parse(configText) as ProjectContext;
            return context;
        } catch {
            // File not found or parsing error - continue to next file
            continue;
        }
    }

    return undefined;
}
