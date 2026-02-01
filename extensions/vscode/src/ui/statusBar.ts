import * as vscode from 'vscode';
import { ContextMapper } from '../mapping';
import { buildTooltip } from './statusBarTooltip';

/**
 * Manages the status bar item for displaying project context information
 */
export class ContextStatusBar implements vscode.Disposable {
    private statusBarItem: vscode.StatusBarItem;
    private disposables: vscode.Disposable[] = [];

    constructor(private contextMapper: ContextMapper) {
        this.statusBarItem = vscode.window.createStatusBarItem(
            vscode.StatusBarAlignment.Left,
            100
        );
        this.statusBarItem.command = 'contextCore.showQuickPick';

        // Register click handler
        this.disposables.push(
            vscode.commands.registerCommand('contextCore.showQuickPick', () => {
                this.handleStatusBarClick().catch(error => {
                    console.error('Error handling status bar click:', error);
                });
            })
        );

        // Listen for active editor changes
        this.disposables.push(
            vscode.window.onDidChangeActiveTextEditor((editor) => {
                this.update(editor);
            })
        );

        // Initial update
        this.update(vscode.window.activeTextEditor);
        this.statusBarItem.show();
    }

    /**
     * Updates the status bar based on the current active editor
     */
    public update(editor: vscode.TextEditor | undefined): void {
        try {
            if (!editor) {
                this.statusBarItem.hide();
                return;
            }

            const context = this.contextMapper.getContextForFile(editor.document.uri.fsPath);
            if (!context) {
                this.statusBarItem.hide();
                return;
            }

            const style = this.getCriticalityStyle(context.criticality);
            this.statusBarItem.text = `${style.icon} Context`;
            this.statusBarItem.tooltip = buildTooltip(context);

            if (style.backgroundColor) {
                this.statusBarItem.backgroundColor = new vscode.ThemeColor(style.backgroundColor);
            } else {
                this.statusBarItem.backgroundColor = undefined;
            }

            this.statusBarItem.show();
        } catch (error) {
            console.error('Error updating status bar:', error);
            this.statusBarItem.hide();
        }
    }

    /**
     * Gets icon and background color based on criticality level
     */
    private getCriticalityStyle(criticality: string): { icon: string; backgroundColor?: string } {
        switch (criticality.toLowerCase()) {
            case 'critical':
                return { icon: '$(flame)', backgroundColor: 'statusBarItem.errorBackground' };
            case 'high':
                return { icon: '$(warning)', backgroundColor: 'statusBarItem.warningBackground' };
            case 'medium':
                return { icon: '$(info)' };
            case 'low':
                return { icon: '$(check)' };
            default:
                return { icon: '$(question)' };
        }
    }

    /**
     * Handles status bar click to show context menu
     */
    private async handleStatusBarClick(): Promise<void> {
        try {
            const activeEditor = vscode.window.activeTextEditor;
            if (!activeEditor) {
                return;
            }

            const context = this.contextMapper.getContextForFile(activeEditor.document.uri.fsPath);
            if (!context) {
                return;
            }

            const items: vscode.QuickPickItem[] = [
                {
                    label: '$(eye) View Context Details',
                    description: 'Show detailed context information'
                },
                {
                    label: '$(refresh) Refresh Context',
                    description: 'Reload context mapping'
                },
                {
                    label: '$(settings-gear) Configure Context',
                    description: 'Open context configuration'
                }
            ];

            const selected = await vscode.window.showQuickPick(items, {
                placeHolder: 'Choose a context action'
            });

            if (selected?.label.includes('View Context Details')) {
                await vscode.commands.executeCommand('contextCore.showContextDetails');
            } else if (selected?.label.includes('Refresh Context')) {
                await vscode.commands.executeCommand('contextcore.refresh');
            } else if (selected?.label.includes('Configure Context')) {
                await vscode.commands.executeCommand('workbench.action.openSettings', 'contextCore');
            }
        } catch (error) {
            vscode.window.showErrorMessage(`Context action failed: ${error}`);
        }
    }

    public dispose(): void {
        this.statusBarItem.dispose();
        this.disposables.forEach(d => d.dispose());
    }
}
