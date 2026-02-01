/**
 * Core type definitions for the ContextCore VSCode extension.
 * These types match the ProjectContext CRD schema exactly.
 */

/**
 * Project criticality levels
 */
export type Criticality = 'critical' | 'high' | 'medium' | 'low';

/**
 * Risk priority levels
 */
export type Priority = 'P1' | 'P2' | 'P3' | 'P4';

/**
 * Project metadata information
 */
export interface ProjectMetadata {
  /** Project name */
  name: string;
  /** Kubernetes namespace */
  namespace: string;
}

/**
 * Basic project information
 */
export interface ProjectInfo {
  /** Unique project identifier */
  id: string;
  /** Associated epic (optional) */
  epic?: string;
  /** Human-readable project name (optional) */
  name?: string;
}

/**
 * Business context for the project
 */
export interface BusinessContext {
  /** Business criticality level */
  criticality?: Criticality;
  /** Business value description */
  value?: string;
  /** Project owner */
  owner?: string;
  /** Cost center identifier */
  costCenter?: string;
}

/**
 * Performance and reliability requirements
 */
export interface Requirements {
  /** Availability requirement (e.g., "99.9%") */
  availability?: string;
  /** 99th percentile latency requirement */
  latencyP99?: string;
  /** 50th percentile latency requirement */
  latencyP50?: string;
  /** Throughput requirement */
  throughput?: string;
  /** Error budget specification */
  errorBudget?: string;
  /** SLO targets */
  targets?: SloTarget[];
  /** Requirements description */
  description?: string;
}

/**
 * SLO target definition
 */
export interface SloTarget {
  /** Metric name */
  metric: string;
  /** Target threshold */
  threshold: string;
}

/**
 * Project risk definition
 */
export interface Risk {
  /** Risk ID */
  id?: string;
  /** Risk title */
  title?: string;
  /** Risk type/category */
  type: string;
  /** Risk priority level */
  priority: Priority;
  /** Risk description */
  description: string;
  /** Risk scope (optional) */
  scope?: string[];
  /** Risk severity */
  severity?: string;
  /** Affected component */
  component?: string;
  /** Mitigation strategy (optional) */
  mitigation?: string;
}

/**
 * Deployment or integration target
 */
export interface Target {
  /** Kubernetes resource kind */
  kind: string;
  /** Target name */
  name: string;
  /** Target namespace (optional) */
  namespace?: string;
}

/**
 * Design documentation references
 */
export interface Design {
  /** Architecture Decision Record reference */
  adr?: string;
  /** Design document reference */
  doc?: string;
  /** API contract reference */
  apiContract?: string;
}

/**
 * Project context specification
 */
export interface ProjectContextSpec {
  /** Project information */
  project?: ProjectInfo;
  /** Business context */
  business?: BusinessContext;
  /** Technical requirements */
  requirements?: Requirements;
  /** Associated risks */
  risks?: Risk[];
  /** Deployment targets */
  targets?: Target[];
  /** Design documentation */
  design?: Design;
}

/**
 * Complete project context matching the CRD schema
 */
export interface ProjectContext {
  /** Project metadata */
  metadata: ProjectMetadata;
  /** Project specification */
  spec: ProjectContextSpec;
  /** Flattened properties for easy access */
  projectId?: string;
  criticality?: string;
  owner?: string;
  risks?: Risk[];
  requirements?: Requirements;
  risk?: {
    scope?: string[];
  };
}

/**
 * Extension configuration interface
 */
export interface ContextCoreConfig {
  /** Cache refresh interval in milliseconds */
  refreshInterval: number;
  /** Kubernetes config file path (optional) */
  kubeconfig?: string;
  /** Kubernetes config file path (alias) */
  kubeconfigPath?: string;
  /** Default namespace */
  namespace: string;
  /** Show inline hints in editor */
  showInlineHints: boolean;
  /** Grafana dashboard URL */
  grafanaUrl: string;
}
