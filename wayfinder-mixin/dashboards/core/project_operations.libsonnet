// Project-to-Operations Dashboard
// Correlates project context with runtime telemetry.
local config = (import '../../config.libsonnet')._config;
local dashboards = import '../../lib/dashboards.libsonnet';
local panels = import '../../lib/panels.libsonnet';

local tempoDs = { type: 'tempo', uid: '${tempo_datasource}' };
local promDs = { type: 'prometheus', uid: '${prometheus_datasource}' };
local attr = config.taskAttributes;

local withGrid(panel, h, w, x, y) = panel + { gridPos: { h: h, w: w, x: x, y: y } };

local promTarget(expr, legendFormat='', format='', instant=false) = {
  datasource: promDs,
  editorMode: 'code',
  expr: expr,
  refId: 'A',
  [if legendFormat != '' then 'legendFormat']: legendFormat,
  [if format != '' then 'format']: format,
  [if instant then 'instant']: true,
  [if !instant then 'range']: true,
  [if instant then 'range']: false,
};

local traceqlTarget(query, limit=50) = {
  datasource: tempoDs,
  limit: limit,
  query: query,
  queryType: 'traceql',
  refId: 'A',
};

local baseDashboard = dashboards.dashboard(
  title='ContextCore: Project-to-Operations',
  uid='contextcore-project-operations',
  description='ContextCore Project-to-Operations - Correlate project context with runtime telemetry',
  tags=['project-operations', 'correlation'],
);

baseDashboard {
  schemaVersion: 38,
  time: { from: 'now-6h', to: 'now' },
  templating: {
    list: [
      {
        current: { selected: false, text: 'Prometheus', value: 'prometheus' },
        hide: 0,
        includeAll: false,
        label: 'Prometheus',
        multi: false,
        name: 'prometheus_datasource',
        options: [],
        query: 'prometheus',
        queryValue: '',
        refresh: 1,
        regex: '',
        skipUrlSync: false,
        type: 'datasource',
      },
      {
        current: { selected: false, text: 'Tempo', value: 'tempo' },
        hide: 0,
        includeAll: false,
        label: 'Tempo',
        multi: false,
        name: 'tempo_datasource',
        options: [],
        query: 'tempo',
        queryValue: '',
        refresh: 1,
        regex: '',
        skipUrlSync: false,
        type: 'datasource',
      },
      {
        current: { selected: true, text: 'contextcore', value: 'contextcore' },
        hide: 0,
        includeAll: false,
        label: 'Project',
        multi: false,
        name: 'project',
        options: [
          { selected: true, text: 'contextcore', value: 'contextcore' },
          { selected: false, text: 'online-boutique', value: 'online-boutique' },
        ],
        query: 'contextcore,online-boutique',
        skipUrlSync: false,
        type: 'custom',
      },
    ],
  },
  timepicker: {},
  timezone: '',
  weekStart: '',
  panels: [
    // === Row: Services by Business Criticality ===
    withGrid(panels.row('Services by Business Criticality'), h=1, w=24, x=0, y=0) + { id: 1 },

    // Critical Services (Error Rate)
    withGrid(
      panels.stat(
        title='Critical Services (Error Rate)',
        expr='sum(rate(http_server_requests_total{service=~"frontend|checkoutservice|cartservice|paymentservice", status=~"5.."}[5m])) / sum(rate(http_server_requests_total{service=~"frontend|checkoutservice|cartservice|paymentservice"}[5m]))',
        datasource=promDs,
        unit='percentunit',
        thresholds=[
          { color: 'green', value: null },
          { color: 'yellow', value: 0.01 },
          { color: 'red', value: 0.05 },
        ],
      ) + {
        targets: [promTarget(
          expr='sum(rate(http_server_requests_total{service=~"frontend|checkoutservice|cartservice|paymentservice", status=~"5.."}[5m])) / sum(rate(http_server_requests_total{service=~"frontend|checkoutservice|cartservice|paymentservice"}[5m]))',
          legendFormat='Critical Services Error Rate',
        )],
        options+: {
          colorMode: 'background',
          showPercentChange: false,
        },
      },
      h=6, w=8, x=0, y=1,
    ) + { id: 2, pluginVersion: '10.2.0' },

    // High Priority Services (Error Rate)
    withGrid(
      panels.stat(
        title='High Priority Services (Error Rate)',
        expr='sum(rate(http_server_requests_total{service=~"productcatalogservice|currencyservice|shippingservice", status=~"5.."}[5m])) / sum(rate(http_server_requests_total{service=~"productcatalogservice|currencyservice|shippingservice"}[5m]))',
        datasource=promDs,
        unit='percentunit',
        thresholds=[
          { color: 'green', value: null },
          { color: 'yellow', value: 0.02 },
          { color: 'red', value: 0.1 },
        ],
      ) + {
        targets: [promTarget(
          expr='sum(rate(http_server_requests_total{service=~"productcatalogservice|currencyservice|shippingservice", status=~"5.."}[5m])) / sum(rate(http_server_requests_total{service=~"productcatalogservice|currencyservice|shippingservice"}[5m]))',
          legendFormat='High Priority Services Error Rate',
        )],
        options+: {
          colorMode: 'background',
          showPercentChange: false,
        },
      },
      h=6, w=8, x=8, y=1,
    ) + { id: 3, pluginVersion: '10.2.0' },

    // Medium Priority Services (Error Rate)
    withGrid(
      panels.stat(
        title='Medium Priority Services (Error Rate)',
        expr='sum(rate(http_server_requests_total{service=~"emailservice|recommendationservice|adservice", status=~"5.."}[5m])) / sum(rate(http_server_requests_total{service=~"emailservice|recommendationservice|adservice"}[5m]))',
        datasource=promDs,
        unit='percentunit',
        thresholds=[
          { color: 'green', value: null },
          { color: 'yellow', value: 0.05 },
          { color: 'red', value: 0.5 },
        ],
      ) + {
        targets: [promTarget(
          expr='sum(rate(http_server_requests_total{service=~"emailservice|recommendationservice|adservice", status=~"5.."}[5m])) / sum(rate(http_server_requests_total{service=~"emailservice|recommendationservice|adservice"}[5m]))',
          legendFormat='Medium Priority Services Error Rate',
        )],
        options+: {
          colorMode: 'background',
          showPercentChange: false,
        },
      },
      h=6, w=8, x=16, y=1,
    ) + { id: 4, pluginVersion: '10.2.0' },

    // === Row: Service Health by Business Value ===
    withGrid(panels.row('Service Health by Business Value'), h=1, w=24, x=0, y=7) + { id: 5 },

    // Revenue-Primary Services (Request Rate)
    withGrid(
      panels.timeseries(
        title='Revenue-Primary Services (Request Rate)',
        expr='sum(rate(http_server_requests_total{service=~"frontend|checkoutservice|cartservice|productcatalogservice|paymentservice"}[5m])) by (service)',
        datasource=promDs,
        unit='reqps',
        legendFormat='{{service}} (revenue-primary)',
      ) + {
        targets: [promTarget(
          expr='sum(rate(http_server_requests_total{service=~"frontend|checkoutservice|cartservice|productcatalogservice|paymentservice"}[5m])) by (service)',
          legendFormat='{{service}} (revenue-primary)',
        )],
        fieldConfig+: {
          defaults+: {
            custom+: {
              axisBorderShow: false,
              axisCenteredZero: false,
              axisColorMode: 'text',
              axisLabel: '',
              axisPlacement: 'auto',
              barAlignment: 0,
              gradientMode: 'none',
              hideFrom: { legend: false, tooltip: false, viz: false },
              insertNulls: false,
              scaleDistribution: { type: 'linear' },
              showPoints: 'never',
              spanNulls: false,
              stacking: { group: 'A', mode: 'none' },
              thresholdsStyle: { mode: 'off' },
            },
            mappings: [],
            thresholds: {
              mode: 'absolute',
              steps: [{ color: 'green', value: null }],
            },
          },
        },
        options: {
          legend: {
            calcs: ['mean', 'max'],
            displayMode: 'table',
            placement: 'bottom',
            showLegend: true,
          },
          tooltip: { mode: 'multi', sort: 'desc' },
        },
      },
      h=8, w=12, x=0, y=8,
    ) + { id: 6, pluginVersion: '10.2.0' },

    // Revenue-Primary Services (P99 Latency)
    withGrid(
      panels.timeseries(
        title='Revenue-Primary Services (P99 Latency)',
        expr='histogram_quantile(0.99, sum(rate(http_server_request_duration_seconds_bucket{service=~"frontend|checkoutservice|cartservice|productcatalogservice|paymentservice"}[5m])) by (le, service))',
        datasource=promDs,
        unit='s',
        legendFormat='{{service}} P99',
      ) + {
        targets: [promTarget(
          expr='histogram_quantile(0.99, sum(rate(http_server_request_duration_seconds_bucket{service=~"frontend|checkoutservice|cartservice|productcatalogservice|paymentservice"}[5m])) by (le, service))',
          legendFormat='{{service}} P99',
        )],
        fieldConfig+: {
          defaults+: {
            custom+: {
              axisBorderShow: false,
              axisCenteredZero: false,
              axisColorMode: 'text',
              axisLabel: '',
              axisPlacement: 'auto',
              barAlignment: 0,
              gradientMode: 'none',
              hideFrom: { legend: false, tooltip: false, viz: false },
              insertNulls: false,
              scaleDistribution: { type: 'linear' },
              showPoints: 'never',
              spanNulls: false,
              stacking: { group: 'A', mode: 'none' },
              thresholdsStyle: { mode: 'off' },
            },
            mappings: [],
            thresholds: {
              mode: 'absolute',
              steps: [{ color: 'green', value: null }],
            },
          },
        },
        options: {
          legend: {
            calcs: ['mean', 'max'],
            displayMode: 'table',
            placement: 'bottom',
            showLegend: true,
          },
          tooltip: { mode: 'multi', sort: 'desc' },
        },
      },
      h=8, w=12, x=12, y=8,
    ) + { id: 7, pluginVersion: '10.2.0' },

    // === Row: Context-Enriched Alerts ===
    withGrid(panels.row('Context-Enriched Alerts'), h=1, w=24, x=0, y=16) + { id: 8 },

    // Active Alerts with Project Context
    withGrid({
      title: 'Active Alerts with Project Context',
      type: 'table',
      datasource: promDs,
      targets: [promTarget(
        expr='ALERTS{alertstate="firing"}',
        legendFormat='__auto',
        format='table',
        instant=true,
      )],
      fieldConfig: {
        defaults: {
          color: { mode: 'thresholds' },
          custom: {
            align: 'auto',
            cellOptions: { type: 'auto' },
            inspect: false,
          },
          mappings: [],
          thresholds: {
            mode: 'absolute',
            steps: [
              { color: 'green', value: null },
              { color: 'red', value: 80 },
            ],
          },
        },
        overrides: [
          {
            matcher: { id: 'byName', options: 'Criticality' },
            properties: [
              {
                id: 'custom.cellOptions',
                value: { mode: 'basic', type: 'color-background' },
              },
              {
                id: 'mappings',
                value: [{
                  options: {
                    critical: { color: 'red', index: 0 },
                    high: { color: 'orange', index: 1 },
                    medium: { color: 'yellow', index: 2 },
                  },
                  type: 'value',
                }],
              },
            ],
          },
        ],
      },
      options: {
        cellHeight: 'sm',
        footer: {
          countRows: false,
          fields: '',
          reducer: ['sum'],
          show: false,
        },
        showHeader: true,
        sortBy: [{ desc: true, displayName: 'Criticality' }],
      },
      transformations: [{
        id: 'organize',
        options: {
          excludeByName: {
            Time: true,
            Value: true,
            __name__: true,
            alertstate: true,
          },
          includeByName: {},
          indexByName: {
            alertname: 0,
            business_criticality: 1,
            design_doc: 3,
            owner: 2,
            service: 4,
          },
          renameByName: {
            alertname: 'Alert',
            business_criticality: 'Criticality',
            design_doc: 'Design Doc',
            owner: 'Owner',
            service: 'Service',
          },
        },
      }],
      pluginVersion: '10.2.0',
    }, h=8, w=24, x=0, y=17) + { id: 9 },

    // === Row: Project Task Correlation ===
    withGrid(panels.row('Project Task Correlation'), h=1, w=24, x=0, y=25) + { id: 10 },

    // Active Project Tasks (In Progress or Blocked)
    withGrid(
      panels.traceqlTable(
        title='Active Project Tasks (In Progress or Blocked)',
        query='{%s=~"in_progress|blocked" && project.id="$project"} | select(%s, %s, %s, task.assignee, %s)' % [attr.status, attr.id, attr.title, attr.status, attr.type],
        datasource=tempoDs,
        limit=50,
      ) + {
        fieldConfig+: {
          overrides: [
            {
              matcher: { id: 'byName', options: 'Status' },
              properties: [
                {
                  id: 'custom.cellOptions',
                  value: { mode: 'basic', type: 'color-background' },
                },
                {
                  id: 'mappings',
                  value: [{
                    options: {
                      blocked: { color: 'red', index: 0 },
                      done: { color: 'green', index: 2 },
                      in_progress: { color: 'blue', index: 1 },
                    },
                    type: 'value',
                  }],
                },
              ],
            },
          ],
        },
        transformations: [{
          id: 'organize',
          options: {
            renameByName: {
              'task.assignee': 'Assignee',
              'task.id': 'Task ID',
              'task.status': 'Status',
              'task.title': 'Title',
              'task.type': 'Type',
            },
          },
        }],
      },
      h=8, w=24, x=0, y=26,
    ) + { id: 11 },

    // === Row: Service Dependencies ===
    withGrid(panels.row('Service Dependencies'), h=1, w=24, x=0, y=34) + { id: 12 },

    // Service Map (from Runtime Traces)
    withGrid({
      title: 'Service Map (from Runtime Traces)',
      type: 'nodeGraph',
      datasource: tempoDs,
      targets: [{
        datasource: tempoDs,
        limit: 1000,
        query: '{resource.service.name=~".*service"}',
        queryType: 'traceql',
        refId: 'A',
        serviceMapQuery: '{resource.service.namespace="online-boutique"}',
      }],
      options: {
        nodes: {},
      },
      pluginVersion: '10.2.0',
    }, h=8, w=24, x=0, y=35) + { id: 13 },
  ],
}
