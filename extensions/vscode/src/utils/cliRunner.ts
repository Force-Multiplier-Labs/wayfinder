import { exec } from 'child_process';
import { promisify } from 'util';
import * as logger from '../logger';

const execAsync = promisify(exec);

interface CliOptions {
  timeout?: number;
  maxBuffer?: number;
  cwd?: string;
}

/**
 * Executes a ContextCore CLI command
 * @param command - The command to execute (without 'contextcore' prefix)
 * @param options - Additional execution options
 * @returns Promise resolving to command output
 */
export async function runContextCoreCommand(
  command: string,
  options: CliOptions = {}
): Promise<string> {
  const {
    timeout = 30000,
    maxBuffer = 1024 * 1024 * 10, // 10MB
    cwd = process.cwd()
  } = options;

  const fullCommand = `contextcore ${command}`;

  try {
    logger.info(`Executing CLI command: ${fullCommand}`);
    const { stdout, stderr } = await execAsync(fullCommand, {
      timeout,
      maxBuffer,
      cwd,
      env: {
        ...process.env,
        CONTEXTCORE_OUTPUT_FORMAT: 'json'
      }
    });

    if (stderr && stderr.trim()) {
      logger.warn(`CLI command stderr: ${stderr}`);
    }

    const result = stdout.trim();
    logger.info(`CLI command completed successfully, output length: ${result.length}`);
    return result;
  } catch (error: unknown) {
    let errorMessage = 'Unknown error executing CLI command';

    if (error && typeof error === 'object') {
      const execError = error as { code?: string; stderr?: string };

      if (execError.code === 'ETIMEDOUT') {
        errorMessage = `Command timed out after ${timeout}ms`;
      } else if (execError.code === 'ENOENT') {
        errorMessage = 'ContextCore CLI not found. Please ensure it is installed and in PATH';
      } else if (execError.stderr) {
        errorMessage = `CLI error: ${execError.stderr.trim()}`;
      }
    }

    logger.error(`CLI command failed: ${errorMessage}`, error);
    throw new Error(errorMessage);
  }
}
