import * as vscode from 'vscode';

/**
 * Supported log levels
 */
export type LogLevel = 'info' | 'warn' | 'error';

/**
 * Output channel for logging (private to this module)
 */
let outputChannel: vscode.OutputChannel | undefined;

/**
 * Initializes the logger and creates the output channel
 */
export function initialize(): void {
  if (!outputChannel) {
    outputChannel = vscode.window.createOutputChannel('ContextCore');
  }
}

/**
 * Logs a message with timestamp and level
 * @param message Message to log
 * @param level Log level (defaults to 'info')
 */
export function log(message: string, level: LogLevel = 'info'): void {
  // Ensure output channel is initialized
  if (!outputChannel) {
    initialize();
  }

  try {
    const timestamp = new Date().toISOString();
    const logEntry = `[${timestamp}] [${level.toUpperCase()}] ${message}`;
    outputChannel!.appendLine(logEntry);

    // Also log to console for debugging
    console.log(`ContextCore: ${logEntry}`);
  } catch (error) {
    console.error('Failed to write to output channel:', error);
  }
}

/**
 * Log info message
 */
export function info(message: string): void {
  log(message, 'info');
}

/**
 * Log warning message
 */
export function warn(message: string): void {
  log(message, 'warn');
}

/**
 * Log error message
 */
export function error(message: string, err?: unknown): void {
  let fullMessage = message;
  if (err) {
    fullMessage += `: ${err instanceof Error ? err.message : String(err)}`;
  }
  log(fullMessage, 'error');
}

/**
 * Shows an error notification to the user and logs the error
 * @param message Error message to display and log
 */
export function showError(message: string): void {
  log(message, 'error');

  // Show error notification without blocking
  vscode.window.showErrorMessage(`ContextCore: ${message}`).then(
    undefined, // Success handler not needed
    error => console.error('Failed to show error message:', error)
  );
}

/**
 * Disposes the output channel and cleans up resources
 */
export function dispose(): void {
  if (outputChannel) {
    try {
      outputChannel.dispose();
    } catch (error) {
      console.error('Error disposing output channel:', error);
    } finally {
      outputChannel = undefined;
    }
  }
}
