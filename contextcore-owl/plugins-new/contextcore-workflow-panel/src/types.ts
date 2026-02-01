/**
 * Panel options for ContextCore Workflow Panel
 */
export interface WorkflowPanelOptions {
  /** Base URL of the Rabbit API */
  apiUrl: string;
  /** Project ID or template variable (e.g., $project) */
  projectId: string;
  /** Whether to show the Dry Run button */
  showDryRun: boolean;
  /** Whether to show the Execute button */
  showExecute: boolean;
  /** Auto-refresh interval in seconds (0 to disable) */
  refreshInterval: number;
  /** Whether to require confirmation before execution */
  confirmExecution: boolean;
}

/**
 * Workflow execution status
 */
export type WorkflowStatus = 'idle' | 'running' | 'completed' | 'failed';

/**
 * Response from workflow dry-run endpoint
 */
export interface DryRunResponse {
  status: 'success' | 'error';
  run_id: string;
  project_id: string;
  mode: 'dry_run';
  steps: DryRunStep[];
  error?: string;
}

/**
 * A step in the dry run preview
 */
export interface DryRunStep {
  name: string;
  status: 'would_execute' | 'would_skip' | 'error';
  reason?: string;
}

/**
 * Response from workflow execute endpoint
 */
export interface ExecuteResponse {
  status: 'started' | 'error';
  run_id: string;
  project_id: string;
  mode: 'execute';
  message?: string;
  error?: string;
}

/**
 * Response from workflow status endpoint
 */
export interface StatusResponse {
  run_id: string;
  status: 'running' | 'completed' | 'failed';
  started_at: string;
  completed_at?: string;
  duration_seconds?: number;
  steps_completed: number;
  steps_total: number;
  error?: string;
}
