// Core ContextCore alerts.
local helpers = import '../lib/alerts.libsonnet';

{
  groups: [
    {
      name: 'contextcore_alerts',
      rules: [
        helpers.lokiAlert(
          name='ContextCoreExporterFailure',
          expr=|||
            count_over_time(
              {service="contextcore"} | json
              | severity_text = "ERROR"
              | body =~ ".*OTLP.*export.*fail.*|.*exporter.*error.*" [5m]
            ) > 0
          |||,
          forDuration='5m',
          severity='critical',
          summary='OTLP exporter failure detected',
          runbookUrl='docs/OPERATIONAL_RUNBOOK.md#otlp-exporter-failure',
          description='ContextCore OTLP export errors in last 5m. Health reporting impacted.',
        ),
        helpers.lokiAlert(
          name='ContextCoreSpanStateLoss',
          expr=|||
            count_over_time(
              {service="contextcore"} | json
              | severity_text = "ERROR"
              | body =~ ".*state.*persist.*fail.*|.*span.*state.*lost.*" [5m]
            ) > 0
          |||,
          forDuration='2m',
          severity='critical',
          summary='Span state persistence failure',
          runbookUrl='docs/OPERATIONAL_RUNBOOK.md#span-state-loss',
          description='In-flight spans may be lost on restart.',
        ),
      ],
    },
    {
      name: 'contextcore_task_alerts',
      rules: [
        helpers.lokiAlert(
          name='ContextCoreTaskStalled',
          expr=|||
            (time() - max by (project_id, task_id) (
              timestamp(count_over_time(
                {service="contextcore"} | json
                | event = "task.status_changed" [24h]
              ) > 0)
            )) > 86400
          |||,
          forDuration='1h',
          severity='warning',
          summary='Task {{ $labels.task_id }} stalled > 24h',
          runbookUrl='docs/OPERATIONAL_RUNBOOK.md#task-stalled',
        ),
      ],
    },
    {
      name: 'contextcore_mimir_alerts',
      rules: [
        helpers.mimirAlert(
          name='ContextCoreInsightLatencyHigh',
          expr=|||
            histogram_quantile(0.99,
              sum(rate(contextcore_insight_query_duration_milliseconds_bucket[5m])) by (le)
            ) > 500
          |||,
          forDuration='10m',
          severity='warning',
          summary='Insight query latency > 500ms P99',
          runbookUrl='docs/OPERATIONAL_RUNBOOK.md#insight-latency',
          description='Agent insight queries are exceeding the 500ms P99 latency budget.',
        ),
      ],
    },
  ],
}
