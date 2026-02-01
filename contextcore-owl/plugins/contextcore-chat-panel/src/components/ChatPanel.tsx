import React, { useState, useCallback } from 'react';
import { PanelProps } from '@grafana/data';
import { Button, TextArea, useStyles2, Alert, LoadingPlaceholder } from '@grafana/ui';
import { css } from '@emotion/css';
import ReactMarkdown from 'react-markdown';
import { ChatPanelOptions, WebhookResponse, ResponseMetrics } from '../types';

interface Props extends PanelProps<ChatPanelOptions> {}

export const ChatPanel: React.FC<Props> = ({ options, width, height }) => {
  const [prompt, setPrompt] = useState('');
  const [response, setResponse] = useState<string | null>(null);
  const [metrics, setMetrics] = useState<ResponseMetrics | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const styles = useStyles2(getStyles);

  const handleSubmit = useCallback(async () => {
    if (!prompt.trim()) {
      return;
    }

    setLoading(true);
    setError(null);
    setResponse(null);
    setMetrics(null);

    try {
      const res = await fetch(options.webhookUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: prompt.trim() }),
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      }

      const data: WebhookResponse = await res.json();

      if (data.success) {
        setResponse(data.response);
        if (data.metrics) {
          setMetrics(data.metrics);
        }
      } else {
        setError(data.error || 'Unknown error occurred');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to connect to webhook server');
    } finally {
      setLoading(false);
    }
  }, [prompt, options.webhookUrl]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit]
  );

  const handleClear = useCallback(() => {
    setPrompt('');
    setResponse(null);
    setMetrics(null);
    setError(null);
  }, []);

  const responseMaxHeight = options.maxHeight > 0 ? options.maxHeight : undefined;

  return (
    <div className={styles.container} style={{ width, height }}>
      <div className={styles.inputSection}>
        <TextArea
          value={prompt}
          onChange={(e) => setPrompt(e.currentTarget.value)}
          onKeyDown={handleKeyDown}
          placeholder={options.placeholder}
          rows={3}
          disabled={loading}
          className={styles.textarea}
        />
        <div className={styles.buttonRow}>
          <Button onClick={handleSubmit} disabled={loading || !prompt.trim()} variant="primary">
            {loading ? 'Sending...' : 'Ask Claude'}
          </Button>
          <Button onClick={handleClear} variant="secondary" disabled={loading}>
            Clear
          </Button>
          <span className={styles.hint}>Cmd/Ctrl+Enter to submit</span>
        </div>
      </div>

      {loading && (
        <div className={styles.loadingSection}>
          <LoadingPlaceholder text="Waiting for response..." />
        </div>
      )}

      {error && (
        <Alert severity="error" title="Error">
          {error}
        </Alert>
      )}

      {response && (
        <div className={styles.responseSection}>
          <div
            className={styles.responseContent}
            style={{ maxHeight: responseMaxHeight }}
          >
            <ReactMarkdown>{response}</ReactMarkdown>
          </div>

          {options.showMetrics && metrics && (
            <div className={styles.metricsBar}>
              <span className={styles.metric}>
                <strong>{metrics.total_tokens}</strong> tokens
              </span>
              <span className={styles.metric}>
                <strong>{metrics.response_time_ms}</strong>ms
              </span>
              {metrics.sdk && (
                <span className={styles.metric}>
                  via <strong>{metrics.sdk}</strong>
                </span>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const getStyles = () => ({
  container: css`
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 12px;
    height: 100%;
    overflow: hidden;
  `,
  inputSection: css`
    display: flex;
    flex-direction: column;
    gap: 8px;
    flex-shrink: 0;
  `,
  textarea: css`
    resize: vertical;
    min-height: 60px;
  `,
  buttonRow: css`
    display: flex;
    gap: 8px;
    align-items: center;
  `,
  hint: css`
    font-size: 11px;
    color: var(--text-secondary);
    margin-left: auto;
  `,
  loadingSection: css`
    display: flex;
    justify-content: center;
    padding: 20px;
  `,
  responseSection: css`
    display: flex;
    flex-direction: column;
    gap: 8px;
    flex: 1;
    min-height: 0;
    overflow: hidden;
  `,
  responseContent: css`
    padding: 12px;
    background: var(--background-secondary);
    border-radius: 4px;
    overflow: auto;
    flex: 1;

    p {
      margin: 0 0 8px 0;
    }

    p:last-child {
      margin-bottom: 0;
    }

    pre {
      background: var(--background-primary);
      padding: 8px;
      border-radius: 4px;
      overflow-x: auto;
    }

    code {
      font-family: monospace;
      font-size: 13px;
    }

    ul,
    ol {
      margin: 8px 0;
      padding-left: 20px;
    }
  `,
  metricsBar: css`
    display: flex;
    gap: 16px;
    padding: 8px 12px;
    background: var(--background-secondary);
    border-radius: 4px;
    font-size: 12px;
    color: var(--text-secondary);
    flex-shrink: 0;
  `,
  metric: css`
    strong {
      color: var(--text-primary);
    }
  `,
});
