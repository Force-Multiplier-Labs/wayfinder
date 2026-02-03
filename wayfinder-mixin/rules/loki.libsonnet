// Loki recording rules.
local helpers = import '../lib/rules.libsonnet';
local config = (import '../config.libsonnet')._config;

{
  groups: [
    {
      name: 'contextcore_task_progress',
      interval: '1m',
      rules: [
        helpers.lokiRule(
          record=config.recordingRules.taskPercentComplete,
          expr=|||
            max by (project_id, task_id, task_type, sprint_id) (
              max_over_time(
                {service="contextcore"} | json
                | event = "task.progress_updated"
                | unwrap percent_complete [5m]
              )
            )
          |||,
        ),
        helpers.lokiRule(
          record=config.recordingRules.sprintProgress,
          expr=|||
            avg by (project_id, sprint_id) (
              %s{sprint_id!=""}
            )
          ||| % config.recordingRules.taskPercentComplete,
          source='derived',
        ),
        helpers.lokiRule(
          record=config.recordingRules.taskCompleted,
          expr=|||
            count by (project_id, sprint_id) (
              %s == 100
            )
          ||| % config.recordingRules.taskPercentComplete,
          source='derived',
        ),
        helpers.lokiRule(
          record=config.recordingRules.taskProgressRate,
          expr=|||
            sum by (project_id, task_id) (
              rate(
                {service="contextcore"} | json
                | event = "task.progress_updated"
                | unwrap percent_complete [1h]
              )
            )
          |||,
        ),
      ],
    },
    {
      name: 'contextcore_task_status',
      interval: '1m',
      rules: [
        helpers.lokiRule(
          record=config.recordingRules.taskCountByStatus,
          expr=|||
            count by (project_id, to_status) (
              last_over_time(
                {service="contextcore"} | json
                | event = "task.status_changed" [5m]
              )
            )
          |||,
        ),
      ],
    },
  ],
}
