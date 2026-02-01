import { DataQuery, DataSourceJsonData } from '@grafana/data';

/**
 * Query model for ContextCore datasource
 */
export interface ContextCoreQuery extends DataQuery {
  /** The prompt text to send to Claude */
  queryText: string;
}

/**
 * Default query values
 */
export const DEFAULT_QUERY: Partial<ContextCoreQuery> = {
  queryText: '',
};

/**
 * Datasource configuration options
 */
export interface ContextCoreDataSourceOptions extends DataSourceJsonData {
  /** Base URL of the Rabbit API server */
  url?: string;
}

/**
 * Secure JSON data (not exposed to frontend)
 */
export interface ContextCoreSecureJsonData {
  /** Optional API key for authentication */
  apiKey?: string;
}

/**
 * Response from the Rabbit API invoke endpoint
 */
export interface WebhookResponse {
  success: boolean;
  response: string;
  model?: string;
  metrics?: {
    response_time_ms: number;
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
    sdk?: string;
  };
  error?: string;
}
