import * as vscode from 'vscode';
import { ContextCoreConfig } from './types';

/**
 * Configuration keys for the ContextCore extension
 */
export const CONFIG_KEYS = {
  refreshInterval: 'contextcore.refreshInterval',
  kubeconfig: 'contextcore.kubeconfig',
  namespace: 'contextcore.namespace',
  showInlineHints: 'contextcore.showInlineHints',
  grafanaUrl: 'contextcore.grafanaUrl'
} as const;

/**
 * Retrieves a configuration value with type safety
 * @param key Configuration key
 * @param defaultValue Default value if configuration is not set
 * @returns Configuration value or default
 */
export function getConfig<T>(key?: string, defaultValue?: T): T | ContextCoreConfig {
  try {
    const config = vscode.workspace.getConfiguration();

    // If no key provided, return full config
    if (!key) {
      return getFullConfig() as T | ContextCoreConfig;
    }

    const value = config.get<T>(key);
    return value !== undefined ? value : (defaultValue as T);
  } catch (error) {
    console.error(`Failed to get config for key ${key}:`, error);
    return defaultValue as T;
  }
}

/**
 * Registers a callback for configuration changes
 * @param callback Function to call when configuration changes
 * @returns Disposable to unregister the listener
 */
export function onConfigChange(callback: () => void): vscode.Disposable {
  return vscode.workspace.onDidChangeConfiguration(event => {
    // Only trigger callback if ContextCore configuration changed
    if (event.affectsConfiguration('contextcore')) {
      try {
        callback();
      } catch (error) {
        console.error('Configuration change callback failed:', error);
      }
    }
  });
}

/**
 * Gets the complete extension configuration
 * @returns Full configuration object with defaults applied
 */
export function getFullConfig(): ContextCoreConfig {
  const config = vscode.workspace.getConfiguration();
  const kubeconfig = config.get<string>(CONFIG_KEYS.kubeconfig);

  return {
    refreshInterval: config.get<number>(CONFIG_KEYS.refreshInterval, 30000),
    kubeconfig: kubeconfig,
    kubeconfigPath: kubeconfig,
    namespace: config.get<string>(CONFIG_KEYS.namespace, 'default'),
    showInlineHints: config.get<boolean>(CONFIG_KEYS.showInlineHints, true),
    grafanaUrl: config.get<string>(CONFIG_KEYS.grafanaUrl, '')
  };
}
