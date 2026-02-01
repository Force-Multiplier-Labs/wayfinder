/**
 * Panel options for ContextCore Chat Panel
 */
export interface ChatPanelOptions {
  /** URL of the webhook server */
  webhookUrl: string;
  /** Maximum height for the response area in pixels */
  maxHeight: number;
  /** Whether to display response metrics (tokens, time) */
  showMetrics: boolean;
  /** Placeholder text for the input area */
  placeholder: string;
}

/**
 * Response from the webhook server
 */
export interface WebhookResponse {
  success: boolean;
  response: string;
  model?: string;
  metrics?: ResponseMetrics;
  error?: string;
}

/**
 * Metrics returned by the webhook server
 */
export interface ResponseMetrics {
  response_time_ms: number;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  sdk?: string;
}
