(import 'config.libsonnet') +
{
  grafanaDashboards+:: {
    // Core dashboards
    'installation.json': (import 'dashboards/core/installation.libsonnet'),
    'project-progress.json': (import 'dashboards/core/project_progress.libsonnet'),
    'sprint-metrics.json': (import 'dashboards/core/sprint_metrics.libsonnet'),
    // Additional dashboards to be migrated:
    // 'sprint-metrics.json': (import 'dashboards/core/sprint_metrics.libsonnet'),
    // 'project-operations.json': (import 'dashboards/core/project_operations.libsonnet'),
    // 'project-tasks.json': (import 'dashboards/core/project_tasks.libsonnet'),
    // 'workflow.json': (import 'dashboards/core/workflow.libsonnet'),
    // 'code-generation-health.json': (import 'dashboards/core/code_generation_health.libsonnet'),
    // Fox dashboards
    // 'fox-alert-automation.json': (import 'dashboards/fox/fox_alert_automation.libsonnet'),
    // Beaver dashboards
    // 'beaver-lead-contractor.json': (import 'dashboards/beaver/lead_contractor.libsonnet'),
    // Squirrel dashboards
    // 'skills-browser.json': (import 'dashboards/squirrel/skills_browser.libsonnet'),
    // 'value-capabilities.json': (import 'dashboards/squirrel/value_capabilities.libsonnet'),
    // External dashboards
    // 'agent-trigger.json': (import 'dashboards/external/agent_trigger.libsonnet'),
    // Portfolio (highest complexity, migrate last)
    // 'portfolio.json': (import 'dashboards/core/portfolio.libsonnet'),
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
