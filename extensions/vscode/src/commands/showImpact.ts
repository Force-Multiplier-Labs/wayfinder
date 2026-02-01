import * as vscode from 'vscode';
import { ContextMapper } from '../mapping';
import { runContextCoreCommand } from '../utils/cliRunner';
import * as logger from '../logger';

/**
 * Creates and registers the show impact command for ContextCore
 * @param contextMapper - The context mapper instance
 * @returns Disposable command registration
 */
export function createShowImpactCommand(contextMapper: ContextMapper): vscode.Disposable {
  return vscode.commands.registerCommand('contextcore.showImpact', async () => {
    try {
      logger.info('Analyzing project impact...');
      const currentProject = await contextMapper.getCurrentProject();
      if (!currentProject) {
        vscode.window.showWarningMessage('ContextCore: No active project found');
        return;
      }

      const command = `graph impact --project ${currentProject.id}`;
      const result = await runContextCoreCommand(command);

      const outputChannel = vscode.window.createOutputChannel('ContextCore Impact');
      outputChannel.clear();
      outputChannel.appendLine(`Impact Analysis for Project: ${currentProject.name}`);
      outputChannel.appendLine('='.repeat(50));
      outputChannel.appendLine(result);
      outputChannel.show();

      logger.info(`Impact analysis completed for project: ${currentProject.id}`);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      logger.error('Failed to analyze impact', error);
      vscode.window.showErrorMessage(`ContextCore: Failed to analyze impact - ${message}`);
    }
  });
}
