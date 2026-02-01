import * as vscode from 'vscode';

/**
 * Flattened context interface for tooltip building
 */
interface FlattenedContext {
  projectId: string;
  criticality: string;
  owner?: string;
  risks?: { description?: string }[];
  requirements?: {
    targets?: { metric: string; threshold: string }[];
    description?: string;
  };
}

/**
 * Builds a formatted tooltip for the status bar item
 */
export function buildTooltip(context: FlattenedContext): vscode.MarkdownString {
  const tooltip = new vscode.MarkdownString();
  tooltip.supportHtml = true;
  tooltip.isTrusted = true;

  tooltip.appendMarkdown(`**Project Context**\n\n`);
  tooltip.appendMarkdown(`**Project ID:** ${context.projectId}\n`);
  tooltip.appendMarkdown(`**Criticality:** ${context.criticality}\n`);

  if (context.owner) {
    tooltip.appendMarkdown(`**Owner:** ${context.owner}\n`);
  }

  if (context.risks?.length) {
    tooltip.appendMarkdown(`**Risks:** ${context.risks.length} identified\n`);
  }

  if (context.requirements?.targets?.length) {
    const targetCount = context.requirements.targets.length;
    tooltip.appendMarkdown(`**SLO Targets:** ${targetCount} defined\n`);
  }

  if (context.requirements?.description) {
    const summary = context.requirements.description.length > 100
      ? context.requirements.description.substring(0, 100) + '...'
      : context.requirements.description;
    tooltip.appendMarkdown(`\n**Requirements:** ${summary}\n`);
  }

  return tooltip;
}
