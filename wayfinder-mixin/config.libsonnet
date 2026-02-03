{
  _config+:: {
    // Datasource UIDs - override these to match your Grafana instance
    datasources: {
      tempo: { uid: 'tempo', type: 'tempo' },
      loki: { uid: 'loki', type: 'loki' },
      mimir: { uid: 'mimir', type: 'prometheus' },
    },

    // Dashboard defaults
    dashboardTags: ['contextcore'],
    dashboardRefresh: '30s',
    dashboardTimeFrom: 'now-24h',
    dashboardTimeTo: 'now',

    // ContextCore semantic convention attribute names
    taskAttributes: {
      id: 'task.id',
      type: 'task.type',
      status: 'task.status',
      title: 'task.title',
      priority: 'task.priority',
      percentComplete: 'task.percent_complete',
    },

    // Recording rule names (kubernetes-mixin convention)
    recordingRules: {
      taskPercentComplete: 'project:contextcore_task_percent_complete:max_over_time5m',
      sprintProgress: 'project_sprint:contextcore_task_percent_complete:avg',
      taskCompleted: 'project_sprint:contextcore_task_completed:count',
      taskProgressRate: 'project_task:contextcore_task_progress:rate1h',
      taskCountByStatus: 'project:contextcore_task_count:count_by_status',
      sprintPlannedPoints: 'project_sprint:contextcore_sprint_planned_points:last',
    },

    // Alert rule names
    alertRules: {
      exporterFailure: 'ContextCoreExporterFailure',
      spanStateLoss: 'ContextCoreSpanStateLoss',
      insightLatencyHigh: 'ContextCoreInsightLatencyHigh',
      taskStalled: 'ContextCoreTaskStalled',
    },

    // Fox configuration
    fox: {
      spanPrefix: 'fox.',
      alertAttributes: {
        name: 'alert.name',
        criticality: 'alert.criticality',
        source: 'alert.source',
      },
      enrichAttributes: {
        projectId: 'project.id',
        businessOwner: 'business.owner',
      },
      actionAttributes: {
        name: 'action.name',
      },
    },

    // Installation metrics
    installation: {
      completeness: 'contextcore_install_completeness_percent',
      criticalMet: 'contextcore_install_critical_met_ratio',
      criticalTotal: 'contextcore_install_critical_total_ratio',
      duration: 'contextcore_install_verification_duration_milliseconds',
      categoryCompleteness: 'contextcore_install_category_completeness_percent',
      requirementStatus: 'contextcore_install_requirement_status_ratio',
      installationId: 'contextcore',
    },
  },
}
