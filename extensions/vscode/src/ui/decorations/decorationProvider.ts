import * as vscode from 'vscode';
import { ContextMapper } from '../../mapping';
import { getFullConfig } from '../../config';

/**
 * Provides inline decorations for files with project context
 */
export class DecorationProvider implements vscode.Disposable {
  private decorationType: vscode.TextEditorDecorationType;
  private disposables: vscode.Disposable[] = [];

  constructor(private contextMapper: ContextMapper) {
    this.decorationType = vscode.window.createTextEditorDecorationType({
      after: {
        margin: '0 0 0 1em',
        fontStyle: 'italic',
        color: new vscode.ThemeColor('editorCodeLens.foreground')
      }
    });

    // Listen for active editor changes
    this.disposables.push(
      vscode.window.onDidChangeActiveTextEditor((editor) => {
        if (editor) {
          this.updateDecorations(editor);
        }
      })
    );

    // Listen for document changes
    this.disposables.push(
      vscode.workspace.onDidChangeTextDocument((event) => {
        const editor = vscode.window.activeTextEditor;
        if (editor && event.document === editor.document) {
          this.updateDecorations(editor);
        }
      })
    );

    // Initial update
    if (vscode.window.activeTextEditor) {
      this.updateDecorations(vscode.window.activeTextEditor);
    }
  }

  /**
   * Update decorations for the given editor
   */
  private updateDecorations(editor: vscode.TextEditor): void {
    const config = getFullConfig();
    if (!config.showInlineHints) {
      editor.setDecorations(this.decorationType, []);
      return;
    }

    const context = this.contextMapper.getContextForFile(editor.document.uri.fsPath);
    if (!context) {
      editor.setDecorations(this.decorationType, []);
      return;
    }

    // Only show decoration on first line
    const firstLine = editor.document.lineAt(0);
    const decoration: vscode.DecorationOptions = {
      range: new vscode.Range(firstLine.range.end, firstLine.range.end),
      renderOptions: {
        after: {
          contentText: `[${context.projectId}] ${context.criticality}`,
          color: this.getCriticalityColor(context.criticality)
        }
      }
    };

    editor.setDecorations(this.decorationType, [decoration]);
  }

  /**
   * Get color based on criticality level
   */
  private getCriticalityColor(criticality: string): string {
    switch (criticality.toLowerCase()) {
      case 'critical':
        return '#ff6b6b';
      case 'high':
        return '#ffd93d';
      case 'medium':
        return '#6bcb77';
      case 'low':
        return '#4d96ff';
      default:
        return '#888888';
    }
  }

  public dispose(): void {
    this.decorationType.dispose();
    this.disposables.forEach(d => d.dispose());
  }
}
