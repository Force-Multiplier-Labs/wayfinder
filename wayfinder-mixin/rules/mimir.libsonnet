// Mimir recording rules.
local helpers = import '../lib/rules.libsonnet';
local config = (import '../config.libsonnet')._config;

{
  groups: [
    {
      name: 'contextcore_mimir_precompute',
      interval: '1m',
      rules: [
        helpers.mimirRule(
          record=config.recordingRules.sprintPlannedPoints,
          expr='max by (project_id, sprint_id) (contextcore_sprint_planned_points)',
        ),
      ],
    },
  ],
}
