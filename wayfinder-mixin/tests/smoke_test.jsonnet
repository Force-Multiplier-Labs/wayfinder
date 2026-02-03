// Smoke test: verify all mixin outputs compile without error.
local mixin = import '../mixin.libsonnet';

{
  // Verify dashboards compile
  dashboards: std.length(std.objectFields(mixin.grafanaDashboards)),

  // Verify alerts compile
  alertGroups: std.length(mixin.prometheusAlerts.groups),

  // Verify rules compile
  lokiRuleGroups: std.length(mixin.lokiRules.groups),
  mimirRuleGroups: std.length(mixin.mimirRules.groups),

  // Verify specific dashboard has expected fields
  installationHasUid: std.objectHas(mixin.grafanaDashboards['installation.json'], 'uid'),
  installationHasPanels: std.length(mixin.grafanaDashboards['installation.json'].panels) > 0,

  // Summary
  summary: 'Compiled %d dashboards, %d alert groups, %d loki rule groups, %d mimir rule groups' % [
    self.dashboards,
    self.alertGroups,
    self.lokiRuleGroups,
    self.mimirRuleGroups,
  ],
}
