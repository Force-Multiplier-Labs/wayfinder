// Project Portfolio Overview Dashboard
// Cross-project health overview using Loki logs and Mimir recording rules.
local config = (import '../../config.libsonnet')._config;
local dashboards = import '../../lib/dashboards.libsonnet';
local panels = import '../../lib/panels.libsonnet';

local lokiDs = { type: 'loki', uid: 'Loki' };
local mimirDs = { type: 'prometheus', uid: 'mimir' };

local withGrid(panel, h, w, x, y) = panel + { gridPos: { h: h, w: w, x: x, y: y } };

// Stat panel for KPI row
local kpiStat(id, title, datasource, expr, thresholds=[{ color: 'green', value: null }]) = {
  id: id,
  title: title,
  type: 'stat',
  datasource: datasource,
  fieldConfig: {
    defaults: {
      color: { mode: 'thresholds' },
      mappings: [],
      thresholds: {
        mode: 'absolute',
        steps: thresholds,
      },
    },
    overrides: [],
  },
  options: {
    colorMode: 'value',
    graphMode: 'area',
    justifyMode: 'auto',
    orientation: 'auto',
    reduceOptions: { calcs: ['lastNotNull'], fields: '', values: false },
    textMode: 'auto',
    wideLayout: true,
  },
  pluginVersion: '10.0.0',
  targets: [{ expr: expr, refId: 'A' }],
};

local baseDashboard = dashboards.dashboard(
  title='Project Portfolio Overview',
  uid='contextcore-portfolio',
  description='',
  tags=['contextcore', 'portfolio'],
);

baseDashboard {
  annotations: {
    list: [{
      builtIn: 1,
      datasource: { type: 'grafana', uid: '-- Grafana --' },
      enable: true,
      hide: true,
      iconColor: 'rgba(0, 211, 255, 1)',
      name: 'Annotations & Alerts',
      type: 'dashboard',
    }],
  },
  schemaVersion: 39,
  time: { from: 'now-7d', to: 'now' },
  timezone: 'browser',
  templating: {
    list: [
      {
        current: { text: 'All', value: '$__all' },
        datasource: mimirDs,
        definition: 'label_values(project:contextcore_task_percent_complete:max_over_time5m, project_id)',
        hide: 0,
        includeAll: true,
        multi: true,
        name: 'project',
        options: [],
        query: 'label_values(project:contextcore_task_percent_complete:max_over_time5m, project_id)',
        refresh: 1,
        regex: '',
        skipUrlSync: false,
        sort: 0,
        type: 'query',
      },
      {
        current: { text: 'All', value: '$__all' },
        datasource: mimirDs,
        definition: 'label_values(project_owner)',
        hide: 0,
        includeAll: true,
        multi: true,
        name: 'owner',
        options: [],
        query: 'label_values(project_owner)',
        refresh: 1,
        regex: '',
        skipUrlSync: false,
        sort: 0,
        type: 'query',
      },
      {
        current: { text: 'All', value: '$__all' },
        hide: 0,
        includeAll: true,
        multi: true,
        name: 'criticality',
        options: [
          { selected: true, text: 'All', value: '$__all' },
          { selected: false, text: 'critical', value: 'critical' },
          { selected: false, text: 'high', value: 'high' },
          { selected: false, text: 'medium', value: 'medium' },
          { selected: false, text: 'low', value: 'low' },
        ],
        query: 'critical,high,medium,low',
        skipUrlSync: false,
        type: 'custom',
      },
      {
        current: { text: 'All', value: '$__all' },
        datasource: mimirDs,
        definition: 'label_values(sprint_id)',
        hide: 0,
        includeAll: true,
        multi: true,
        name: 'sprint',
        options: [],
        query: 'label_values(sprint_id)',
        refresh: 1,
        regex: '',
        skipUrlSync: false,
        sort: 0,
        type: 'query',
      },
    ],
  },
  timepicker: {},
  weekStart: '',
  panels: [
    // === Row: KPI Stats ===
    withGrid(panels.row('KPI Stats'), h=1, w=24, x=0, y=0) + { id: 1 },

    // Active Projects (Loki)
    withGrid(kpiStat(
      id=2,
      title='Active Projects',
      datasource=lokiDs,
      expr='count(count by (project_id) ({service="contextcore"} | json | task_type =~ "epic|story|task" | __error__=""))',
    ), h=4, w=6, x=0, y=1),

    // On Track Projects (Mimir)
    withGrid(kpiStat(
      id=3,
      title='On Track Projects',
      datasource=mimirDs,
      expr='count(avg by (project_id) (project:contextcore_task_percent_complete:max_over_time5m{task_type=~"story|epic"}) > 60 unless count by (project_id) (project:contextcore_task_count:count_by_status{to_status="blocked"}) > 0)',
    ), h=4, w=6, x=6, y=1),

    // At Risk Projects (Mimir)
    withGrid(kpiStat(
      id=4,
      title='At Risk Projects',
      datasource=mimirDs,
      expr='count(avg by (project_id) (project:contextcore_task_percent_complete:max_over_time5m{task_type=~"story|epic"}) < 40 or count by (project_id) (project:contextcore_task_count:count_by_status{to_status="blocked"}) > 0)',
      thresholds=[
        { color: 'green', value: null },
        { color: '#EAB839', value: 1 },
      ],
    ), h=4, w=6, x=12, y=1),

    // Blocked Tasks (Loki)
    withGrid(kpiStat(
      id=5,
      title='Blocked Tasks (Total)',
      datasource=lokiDs,
      expr='count_over_time({service="contextcore"} | json | event="task.blocked" [$__range]) - count_over_time({service="contextcore"} | json | event="task.unblocked" [$__range])',
      thresholds=[
        { color: 'green', value: null },
        { color: '#EAB839', value: 1 },
        { color: 'red', value: 4 },
      ],
    ), h=4, w=6, x=18, y=1),

    // === Row: Project Health Overview ===
    withGrid(panels.row('Project Health Overview'), h=1, w=24, x=0, y=5) + { id: 6 },

    // Project Health Overview (Loki table)
    withGrid({
      id: 7,
      title: 'Project Health Overview',
      type: 'table',
      datasource: lokiDs,
      fieldConfig: {
        defaults: {
          custom: {
            align: 'auto',
            displayMode: 'auto',
            inspect: false,
          },
          mappings: [{
            options: {
              '0': { color: 'green', index: 2, text: '🟢' },
              '1': { color: 'yellow', index: 1, text: '🟡' },
              '2': { color: 'red', index: 0, text: '🔴' },
            },
            type: 'value',
          }],
          thresholds: {
            mode: 'absolute',
            steps: [{ color: 'green', value: null }],
          },
        },
        overrides: [
          {
            matcher: { id: 'byName', options: 'Status' },
            properties: [
              { id: 'custom.displayMode', value: 'color-text' },
            ],
          },
          {
            matcher: { id: 'byName', options: 'Progress' },
            properties: [
              { id: 'custom.displayMode', value: 'gradient-gauge' },
              { id: 'min', value: 0 },
              { id: 'max', value: 100 },
            ],
          },
          {
            matcher: { id: 'byName', options: 'Project' },
            properties: [{
              id: 'links',
              value: [{
                title: 'Project Details',
                url: '/d/contextcore-project-details?var-project=${__value.text}',
              }],
            }],
          },
        ],
      },
      options: {
        footer: {
          enablePagination: true,
          fields: '',
          reducer: ['sum'],
          show: false,
        },
        showHeader: true,
        sortBy: [],
      },
      pluginVersion: '10.0.0',
      targets: [{
        expr: '{service="contextcore"} | json | event="task.progress_updated" or event="task.status_changed"',
        refId: 'A',
      }],
      transformations: [
        {
          id: 'groupBy',
          options: {
            fields: {
              project_id: {
                aggregations: [],
                operation: 'groupby',
              },
              percent_complete: {
                aggregations: ['mean'],
                operation: 'aggregate',
              },
              to_status: {
                aggregations: [],
                operation: 'groupby',
              },
            },
          },
        },
        {
          id: 'organize',
          options: {
            renameByName: {
              project_id: 'Project',
              'percent_complete (mean)': 'Progress',
            },
          },
        },
      ],
    }, h=8, w=24, x=0, y=6),

    // === Row: Progress & Velocity ===
    withGrid(panels.row('Progress & Velocity'), h=1, w=24, x=0, y=14) + { id: 8 },

    // Portfolio Progress (gauge)
    withGrid({
      id: 9,
      title: 'Portfolio Progress',
      type: 'gauge',
      datasource: mimirDs,
      fieldConfig: {
        defaults: {
          color: { mode: 'thresholds' },
          mappings: [],
          max: 100,
          min: 0,
          thresholds: {
            mode: 'absolute',
            steps: [
              { color: 'red', value: null },
              { color: '#EAB839', value: 40 },
              { color: 'green', value: 70 },
            ],
          },
          unit: 'percent',
        },
        overrides: [],
      },
      options: {
        orientation: 'auto',
        reduceOptions: { calcs: ['lastNotNull'], fields: '', values: false },
        showThresholdLabels: false,
        showThresholdMarkers: true,
      },
      pluginVersion: '10.0.0',
      targets: [{
        expr: 'avg by (project_id) (project:contextcore_task_percent_complete:max_over_time5m{task_type=~"story|epic"})',
        legendFormat: '{{project_id}}',
        refId: 'A',
      }],
    }, h=8, w=12, x=0, y=15),

    // Velocity Trend (timeseries)
    withGrid({
      id: 10,
      title: 'Velocity Trend',
      type: 'timeseries',
      datasource: mimirDs,
      fieldConfig: {
        defaults: {
          color: { mode: 'palette-classic' },
          custom: {
            axisBorderShow: false,
            axisCenteredZero: false,
            axisColorMode: 'text',
            axisLabel: '',
            axisPlacement: 'auto',
            barAlignment: 0,
            drawStyle: 'line',
            fillOpacity: 0,
            gradientMode: 'none',
            hideFrom: { legend: false, tooltip: false, viz: false },
            insertNulls: false,
            lineInterpolation: 'linear',
            lineWidth: 2,
            pointSize: 5,
            scaleDistribution: { type: 'linear' },
            showPoints: 'auto',
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
        overrides: [{
          matcher: { id: 'byRegexp', options: 'Planned.*' },
          properties: [{
            id: 'custom.lineStyle',
            value: { dash: [10, 10], fill: 'dash' },
          }],
        }],
      },
      options: {
        legend: {
          calcs: [],
          displayMode: 'list',
          placement: 'bottom',
          showLegend: true,
        },
        tooltip: { mode: 'single', sort: 'none' },
      },
      pluginVersion: '10.0.0',
      targets: [
        {
          expr: 'sum by (sprint_id) (increase(task_story_points_completed_total[$__interval]))',
          legendFormat: 'Actual {{sprint_id}}',
          refId: 'A',
        },
        {
          expr: 'sum by (sprint_id) (sprint_planned_points)',
          legendFormat: 'Planned {{sprint_id}}',
          refId: 'B',
        },
      ],
    }, h=8, w=12, x=12, y=15),

    // === Row: Risk & Blockers ===
    withGrid(panels.row('Risk & Blockers'), h=1, w=24, x=0, y=23) + { id: 11 },

    // Blocked Tasks (Loki table)
    withGrid({
      id: 12,
      title: 'Blocked Tasks',
      type: 'table',
      datasource: lokiDs,
      fieldConfig: {
        defaults: {
          custom: {
            align: 'auto',
            displayMode: 'auto',
            inspect: false,
          },
          mappings: [],
          thresholds: {
            mode: 'absolute',
            steps: [{ color: 'green', value: null }],
          },
        },
        overrides: [],
      },
      options: {
        footer: {
          enablePagination: true,
          fields: '',
          reducer: ['sum'],
          show: false,
        },
        showHeader: true,
      },
      pluginVersion: '10.0.0',
      targets: [{
        expr: '{service="contextcore"} | json | event="task.blocked"',
        refId: 'A',
      }],
    }, h=8, w=12, x=0, y=24),

    // Tasks by Status (barchart)
    withGrid({
      id: 13,
      title: 'Tasks by Status',
      type: 'barchart',
      datasource: mimirDs,
      fieldConfig: {
        defaults: {
          color: { mode: 'palette-classic' },
          custom: {
            axisBorderShow: false,
            axisCenteredZero: false,
            axisColorMode: 'text',
            axisLabel: '',
            axisPlacement: 'auto',
            fillOpacity: 80,
            gradientMode: 'none',
            hideFrom: { legend: false, tooltip: false, viz: false },
            lineWidth: 1,
            scaleDistribution: { type: 'linear' },
            thresholdsStyle: { mode: 'off' },
          },
          mappings: [],
          thresholds: {
            mode: 'absolute',
            steps: [{ color: 'green', value: null }],
          },
        },
        overrides: [],
      },
      options: {
        barRadius: 0,
        barWidth: 0.97,
        fullHighlight: false,
        groupWidth: 0.7,
        legend: {
          calcs: [],
          displayMode: 'list',
          placement: 'bottom',
          showLegend: true,
        },
        orientation: 'horizontal',
        showValue: 'auto',
        stacking: 'normal',
        tooltip: { mode: 'single', sort: 'none' },
        xTickLabelRotation: 0,
        xTickLabelSpacing: 0,
      },
      pluginVersion: '10.0.0',
      targets: [{
        expr: 'sum by (project_id, status) (project:contextcore_task_count:count_by_status)',
        legendFormat: '{{status}}',
        refId: 'A',
      }],
    }, h=8, w=12, x=12, y=24),

    // === Row: Trends & Patterns ===
    withGrid(panels.row('Trends & Patterns'), h=1, w=24, x=0, y=32) + { id: 14 },

    // Lead Time Distribution (histogram)
    withGrid({
      id: 15,
      title: 'Lead Time Distribution',
      type: 'histogram',
      datasource: mimirDs,
      fieldConfig: {
        defaults: {
          color: { mode: 'palette-classic' },
          custom: {
            axisBorderShow: false,
            axisCenteredZero: false,
            axisColorMode: 'text',
            axisLabel: '',
            axisPlacement: 'auto',
            barAlignment: 0,
            drawStyle: 'line',
            fillOpacity: 0,
            gradientMode: 'none',
            hideFrom: { legend: false, tooltip: false, viz: false },
            insertNulls: false,
            lineInterpolation: 'linear',
            lineWidth: 1,
            pointSize: 5,
            scaleDistribution: { type: 'linear' },
            showPoints: 'auto',
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
        overrides: [],
      },
      options: {
        legend: {
          calcs: [],
          displayMode: 'list',
          placement: 'bottom',
          showLegend: true,
        },
        tooltip: { mode: 'single', sort: 'none' },
      },
      pluginVersion: '10.0.0',
      targets: [{
        expr: 'histogram_quantile(0.5, sum(rate(task_lead_time_bucket[$__rate_interval])) by (le))',
        legendFormat: 'Median Lead Time',
        refId: 'A',
      }],
    }, h=8, w=12, x=0, y=33),

    // Activity Heatmap
    withGrid({
      id: 16,
      title: 'Activity Heatmap',
      type: 'heatmap',
      datasource: lokiDs,
      options: {
        calculate: false,
        cellGap: 1,
        color: {
          exponent: 0.5,
          fill: '#F2F2F2',
          mode: 'scheme',
          reverse: false,
          scale: 'Spectral',
          scheme: 'Spectral',
          steps: 64,
        },
        exemplars: {
          color: 'rgba(255,0,255,0.7)',
        },
        filterValues: {
          le: 1e-9,
        },
        legend: {
          show: true,
        },
        tooltip: {
          show: true,
          yHistogram: false,
        },
        yAxis: {
          axisPlacement: 'left',
          reverse: false,
          unit: 'short',
        },
      },
      pluginVersion: '10.0.0',
      targets: [{
        expr: 'sum by (day_of_week, hour) (count_over_time({service="contextcore"} | json | event=~"task.created|task.completed|task.status_changed" [$__interval]))',
        refId: 'A',
      }],
    }, h=8, w=12, x=12, y=33),

    // === Row: Recent Activity Log ===
    withGrid(panels.row('Recent Activity Log'), h=1, w=24, x=0, y=41) + { id: 17 },

    // Recent Events (logs)
    withGrid({
      id: 18,
      title: 'Recent Events',
      type: 'logs',
      datasource: lokiDs,
      options: {
        dedupStrategy: 'none',
        enableInfiniteScrolling: false,
        enableLogDetails: true,
        prettifyLogMessage: false,
        showCommonLabels: false,
        showLabels: false,
        showTime: true,
        sortOrder: 'Descending',
        wrapLogMessage: true,
      },
      pluginVersion: '10.0.0',
      targets: [{
        expr: '{service="contextcore"} | json | event=~"task.created|task.completed|task.blocked|task.unblocked|task.status_changed" | line_format "{{.event}} {{.project_id}} {{.task_id}} {{if .to_status}}{{.from_status}}\u2192{{.to_status}}{{end}} {{if .reason}}\\"{{.reason}}\\"{{end}}"',
        refId: 'A',
      }],
    }, h=8, w=24, x=0, y=42),
  ],
}
