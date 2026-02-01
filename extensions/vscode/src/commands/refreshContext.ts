import * as vscode from 'vscode';
import { ContextProvider } from '../providers';
import * as logger from '../logger';

/**
 * Creates and registers the refresh command for ContextCore
 * @param contextProvider - The context provider instance
 * @returns Disposable command registration
 */
export function createRefreshCommand(contextProvider: ContextProvider): vscode.Disposable {
  return vscode.commands.registerCommand('contextcore.refresh', async () => {
    try {
      logger.info('Refreshing ContextCore data...');
      contextProvider.invalidateCache();
      await contextProvider.refresh();
      vscode.window.showInformationMessage('ContextCore: Data refreshed successfully');
      logger.info('ContextCore data refreshed successfully');
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      logger.error('Failed to refresh ContextCore data', error);
      vscode.window.showErrorMessage(`ContextCore: Failed to refresh data - ${message}`);
    }
  });
}
