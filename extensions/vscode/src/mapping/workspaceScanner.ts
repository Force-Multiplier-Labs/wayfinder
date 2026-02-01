import * as vscode from 'vscode';

/**
 * Find all context files in a workspace folder
 * Returns files sorted by depth (closer to root first)
 */
export async function findContextFiles(folder: vscode.WorkspaceFolder): Promise<vscode.Uri[]> {
  try {
    const patterns = [
      '.contextcore',
      '.contextcore.yaml',
      '.contextcore.yml',
      'projectcontext.yaml',
      'projectcontext.yml'
    ];

    const allFiles: vscode.Uri[] = [];

    for (const pattern of patterns) {
      const globPattern = new vscode.RelativePattern(folder, `**/${pattern}`);
      const files = await vscode.workspace.findFiles(
        globPattern,
        '**/node_modules/**'
      );
      allFiles.push(...files);
    }

    // Remove duplicates and sort by depth (closer to root first)
    const uniqueFiles = Array.from(new Set(allFiles.map(f => f.toString())))
      .map(str => vscode.Uri.parse(str));

    return uniqueFiles.sort((a, b) => {
      const aDepth = getPathDepth(a, folder);
      const bDepth = getPathDepth(b, folder);
      return aDepth - bDepth;
    });
  } catch (error) {
    console.error('Error finding context files:', error);
    return [];
  }
}

/**
 * Calculate the depth of a file path relative to the workspace folder
 */
function getPathDepth(uri: vscode.Uri, _workspaceFolder: vscode.WorkspaceFolder): number {
  const relativePath = vscode.workspace.asRelativePath(uri, false);
  return relativePath.split('/').length - 1;
}
