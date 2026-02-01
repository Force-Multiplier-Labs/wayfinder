import * as vscode from 'vscode';
import { ContextMapper } from '../mapping';
import { getFullConfig } from '../config';
import * as logger from '../logger';

/**
 * Creates and registers the open dashboard command for ContextCore
 * @param contextMapper - The context mapper instance
 * @returns Disposable command registration
 */
export function createOpenDashboardCommand(contextMapper: ContextMapper): vscode.Disposable {
  return vscode.commands.registerCommand('contextcore.openDashboard', async () => {
    try {
      logger.info('Opening ContextCore dashboard...');
      const currentProject = await contextMapper.getCurrentProject();
      if (!currentProject) {
        vscode.window.showWarningMessage('ContextCore: No active project found');
        return;
      }

      const config = getFullConfig();
      const grafanaUrl = config.grafanaUrl;
      if (!grafanaUrl) {
        vscode.window.showErrorMessage('ContextCore: Grafana URL not configured');
        return;
      }

      const projectId = encodeURIComponent(currentProject.id);
      const dashboardUrl = `${grafanaUrl}/d/contextcore-project?var-project=${projectId}`;

      await vscode.env.openExternal(vscode.Uri.parse(dashboardUrl));
      logger.info(`Dashboard opened for project: ${currentProject.id}`);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      logger.error('Failed to open dashboard', error);
      vscode.window.showErrorMessage(`ContextCore: Failed to open dashboard - ${message}`);
    }
  });
}
