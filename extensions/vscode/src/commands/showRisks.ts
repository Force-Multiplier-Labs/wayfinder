import * as vscode from 'vscode';
import { ContextMapper, Risk } from '../mapping';
import * as logger from '../logger';

interface RiskItem extends vscode.QuickPickItem {
  priority: string;
  component: string;
  risk: Risk | null;
}

/**
 * Creates and registers the show risks command for ContextCore
 * @param contextMapper - The context mapper instance
 * @returns Disposable command registration
 */
export function createShowRisksCommand(contextMapper: ContextMapper): vscode.Disposable {
  return vscode.commands.registerCommand('contextcore.showRisks', async () => {
    try {
      logger.info('Loading project risks...');
      const currentProject = await contextMapper.getCurrentProject();
      if (!currentProject) {
        vscode.window.showWarningMessage('ContextCore: No active project found');
        return;
      }

      const risks = await contextMapper.getProjectRisks(currentProject.id);
      if (!risks || risks.length === 0) {
        vscode.window.showInformationMessage('ContextCore: No risks found for current project');
        return;
      }

      const priorityOrder = ['P1', 'P2', 'P3', 'P4'];
      const groupedItems: RiskItem[] = [];

      for (const priority of priorityOrder) {
        const priorityRisks = risks.filter(risk => risk.priority === priority);
        if (priorityRisks.length > 0) {
          // Add separator for priority group
          groupedItems.push({
            label: `${priority} Risks (${priorityRisks.length})`,
            kind: vscode.QuickPickItemKind.Separator,
            priority,
            component: '',
            risk: null
          });

          // Add individual risks
          priorityRisks.forEach(risk => {
            groupedItems.push({
              label: `$(warning) ${risk.title || risk.description}`,
              description: risk.component,
              detail: risk.description,
              priority: risk.priority,
              component: risk.component || '',
              risk
            });
          });
        }
      }

      const selected = await vscode.window.showQuickPick(groupedItems, {
        placeHolder: 'Select a risk to view details',
        matchOnDescription: true,
        matchOnDetail: true
      });

      if (selected?.risk) {
        const risk = selected.risk;
        const message = `Risk: ${risk.title || risk.description}\n\nComponent: ${risk.component || 'N/A'}\nPriority: ${risk.priority}\n\nDescription: ${risk.description}\n\nMitigation: ${risk.mitigation || 'Not specified'}`;

        const action = await vscode.window.showInformationMessage(
          message,
          { modal: true },
          'View in Dashboard',
          'Close'
        );

        if (action === 'View in Dashboard') {
          await vscode.commands.executeCommand('contextcore.openDashboard');
        }
      }

      logger.info(`Displayed ${risks.length} risks for project: ${currentProject.id}`);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      logger.error('Failed to show risks', error);
      vscode.window.showErrorMessage(`ContextCore: Failed to load risks - ${message}`);
    }
  });
}
