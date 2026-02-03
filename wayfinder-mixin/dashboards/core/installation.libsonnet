// Installation Verification Dashboard
// Proof-of-concept: first dashboard migrated to Jsonnet.
local config = (import '../../config.libsonnet')._config;
local dashboards = import '../../lib/dashboards.libsonnet';
local panels = import '../../lib/panels.libsonnet';
local variables = import '../../lib/variables.libsonnet';

local ds = { type: 'prometheus', uid: '${datasource}' };
local tempoDs = { type: 'tempo', uid: '${tempo}' };
local installId = config.installation.installationId;
local m = config.installation;

local withGrid(panel, h, w, x, y) = panel + { gridPos: { h: h, w: w, x: x, y: y } };

local baseDashboard = dashboards.dashboard(
  title='[CORE] Wayfinder Installation Status',
  uid='cc-core-installation-status',
  description='Wayfinder Installation Verification - Self-monitoring dashboard showing installation completeness and requirement status. Run \'contextcore install verify --endpoint localhost:4317\' to populate data.',
  tags=['installation'],
);

baseDashboard {
  templating: {
    list: [
      variables.prometheusDatasource(),
      variables.tempoDatasource(),
    ],
  },
  panels: [
    // Row 1: KPI gauges
    withGrid(
      panels.gauge(
        title='Installation Completeness',
        expr='last_over_time(%s{installation_id="%s"}[1h])' % [m.completeness, installId],
        datasource=ds,
      ),
      h=8, w=8, x=0, y=0,
    ) + { id: 1, pluginVersion: '11.4.0' },

    withGrid(
      panels.stat(
        title='Critical Requirements Met',
        expr='last_over_time(%s{installation_id="%s"}[1h])' % [m.criticalMet, installId],
        datasource=ds,
        thresholds=[
          { color: 'red', value: null },
          { color: 'green', value: 1 },
        ],
      ),
      h=8, w=8, x=8, y=0,
    ) + { id: 2 },

    withGrid(
      panels.stat(
        title='Critical Requirements Total',
        expr='last_over_time(%s{installation_id="%s"}[1h])' % [m.criticalTotal, installId],
        datasource=ds,
      ),
      h=8, w=8, x=16, y=0,
    ) + { id: 3 },

    // Row 2: Duration and category breakdown
    withGrid(
      panels.stat(
        title='Verification Duration (avg)',
        expr='last_over_time(%s_sum{installation_id="%s"}[1h]) / last_over_time(%s_count{installation_id="%s"}[1h])' % [m.duration, installId, m.duration, installId],
        datasource=ds,
        unit='ms',
      ),
      h=8, w=8, x=0, y=8,
    ) + { id: 4 },

    withGrid(
      panels.barGauge(
        title='Completeness by Category',
        expr='last_over_time(%s{installation_id="%s"}[1h])' % [m.categoryCompleteness, installId],
        datasource=ds,
      ),
      h=8, w=16, x=8, y=8,
    ) + { id: 5 },

    // Row 3: Requirement status table
    withGrid(
      panels.table(
        title='Requirement Status',
        expr='last_over_time(%s[1h])' % m.requirementStatus,
        datasource=ds,
      ),
      h=10, w=24, x=0, y=16,
    ) + { id: 6 },

    // Row 4: Time series
    withGrid(
      panels.timeseries(
        title='Completeness Over Time',
        expr='%s{installation_id="%s"}' % [m.completeness, installId],
        datasource=ds,
        unit='percent',
      ),
      h=8, w=24, x=0, y=26,
    ) + { id: 7 },

    // Row 5: Tempo trace panels
    withGrid({
      title: 'Recent Verification Traces',
      type: 'table',
      datasource: tempoDs,
      targets: [{
        queryType: 'traceqlSearch',
        query: '{ resource.service.name = "contextcore" && name = "installation.verify" }',
        refId: 'A',
      }],
      fieldConfig: { defaults: {}, overrides: [] },
      options: { showHeader: true },
    }, h=8, w=12, x=0, y=34) + { id: 8 },

    withGrid({
      title: 'Failed Requirements (Traces)',
      type: 'table',
      datasource: tempoDs,
      targets: [{
        queryType: 'traceqlSearch',
        query: '{ resource.service.name = "contextcore" && name = "installation.requirement" && span.requirement.status = "fail" }',
        refId: 'A',
      }],
      fieldConfig: { defaults: {}, overrides: [] },
      options: { showHeader: true },
    }, h=8, w=12, x=12, y=34) + { id: 9 },
  ],
}
