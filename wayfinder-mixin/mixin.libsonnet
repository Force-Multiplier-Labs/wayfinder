(import 'config.libsonnet') +
{
  grafanaDashboards+:: {
    // Core dashboards
    'installation.json': (import 'dashboards/core/installation.libsonnet'),
    'project-progress.json': (import 'dashboards/core/project_progress.libsonnet'),
    'sprint-metrics.json': (import 'dashboards/core/sprint_metrics.libsonnet'),
    'project-operations.json': (import 'dashboards/core/project_operations.libsonnet'),
    'workflow.json': (import 'dashboards/core/workflow.libsonnet'),
    'portfolio.json': (import 'dashboards/core/portfolio.libsonnet'),
    // Beaver dashboards
    'beaver-lead-contractor.json': (import 'dashboards/beaver/lead_contractor.libsonnet'),
    // Squirrel dashboards
    'value-capabilities.json': (import 'dashboards/squirrel/value_capabilities.libsonnet'),
  },

  prometheusAlerts+:: {
    groups+: (import 'alerts/contextcore.libsonnet').groups
           + (import 'alerts/fox.libsonnet').groups,
  },

  lokiRules+:: {
    groups+: (import 'rules/loki.libsonnet').groups,
  },

  mimirRules+:: {
    groups+: (import 'rules/mimir.libsonnet').groups,
  },
}
