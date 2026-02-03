// Fox (Waagosh) alerts.
local helpers = import '../lib/alerts.libsonnet';

{
  groups: [
    {
      name: 'fox_alerts',
      rules: [
        helpers.lokiAlert(
          name='FoxEnrichmentFailure',
          expr=|||
            count_over_time(
              {service_name=~".*fox.*"} | json
              | level = "error"
              | msg =~ ".*enrich.*fail.*" [5m]
            ) > 0
          |||,
          forDuration='5m',
          severity='warning',
          summary='Fox context enrichment failures detected',
          runbookUrl='docs/OPERATIONAL_RUNBOOK.md#fox-enrichment-failure',
        ),
      ],
    },
  ],
}
