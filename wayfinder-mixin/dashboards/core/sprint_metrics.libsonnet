// Sprint Metrics Dashboard
// Tracks velocity, throughput, and sprint performance via Tempo.
local config = (import '../../config.libsonnet')._config;
local dashboards = import '../../lib/dashboards.libsonnet';
local panels = import '../../lib/panels.libsonnet';

local tempoDs = { type: 'tempo', uid: '${tempo_datasource}' };
local attr = config.taskAttributes;

local withGrid(panel, h, w, x, y) = panel + { gridPos: { h: h, w: w, x: x, y: y } };

local traceqlTarget(query, limit=1000) = {
  datasource: tempoDs,
  limit: limit,
  query: query,
  queryType: 'traceql',
  refId: 'A',
};

local baseDashboard = dashboards.dashboard(
  title='ContextCore: Sprint Metrics',
  uid='contextcore-sprint-metrics',
  description='ContextCore Sprint Metrics - Track velocity, throughput, and sprint performance',
  tags=['sprint-metrics', 'velocity'],
);

baseDashboard {
  schemaVersion: 38,
  refresh: '1m',
  time: { from: 'now-90d', to: 'now' },
  templating: {
    list: [
      {
        current: { selected: false, text: 'Tempo', value: 'tempo' },
        hide: 0,
        includeAll: false,
        label: 'Tempo Datasource',
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
    // === Row: Sprint Overview ===
    withGrid(panels.row('Sprint Overview'), h=1, w=24, x=0, y=0) + { id: 1 },

    // Total Sprints
    withGrid(
      panels.traceqlStat(
        title='Total Sprints',
        query='{name=~"sprint.*" && project.id="$project"}',
        datasource=tempoDs,
        limit=100,
      ),
      h=4, w=6, x=0, y=1,
    ) + { id: 2 },

    // Avg Planned Points
    withGrid(
      panels.traceqlStat(
        title='Avg Planned Points',
        query='{name=~"sprint.*" && project.id="$project"} | select(sprint.planned_points)',
        datasource=tempoDs,
        limit=100,
        calcs=['mean'],
        graphMode='area',
        unit='none',
        thresholds=[
          { color: 'red', value: null },
          { color: 'yellow', value: 20 },
          { color: 'green', value: 30 },
        ],
      ),
      h=4, w=6, x=6, y=1,
    ) + { id: 3 },

    // Total Story Points Completed
    withGrid(
      panels.traceqlStat(
        title='Total Story Points Completed',
        query='{%s="done" && project.id="$project"} | select(task.story_points)' % attr.status,
        datasource=tempoDs,
        calcs=['sum'],
        unit='none',
        thresholds=[{ color: 'green', value: null }],
      ),
      h=4, w=6, x=12, y=1,
    ) + { id: 4 },

    // Tasks Completed
    withGrid(
      panels.traceqlStat(
        title='Tasks Completed',
        query='{%s="done" && project.id="$project"}' % attr.status,
        datasource=tempoDs,
        unit='none',
        thresholds=[{ color: 'green', value: null }],
      ),
      h=4, w=6, x=18, y=1,
    ) + { id: 5 },

    // === Row: Velocity Trend ===
    withGrid(panels.row('Velocity Trend'), h=1, w=24, x=0, y=5) + { id: 6 },

    // Sprint Velocity Over Time
    withGrid(
      panels.traceqlTimeseries(
        title='Sprint Velocity Over Time',
        targets=[traceqlTarget('{name=~"sprint.*" && project.id="$project"} | select(sprint.planned_points, sprint.completed_points)', limit=100)],
        datasource=tempoDs,
        drawStyle='bars',
        fillOpacity=50,
        unit='none',
      ) + {
        fieldConfig+: {
          defaults+: {
            custom+: {
              axisLabel: 'Story Points',
            },
          },
          overrides: [
            {
              matcher: { id: 'byName', options: 'Planned' },
              properties: [{ id: 'color', value: { fixedColor: 'blue', mode: 'fixed' } }],
            },
            {
              matcher: { id: 'byName', options: 'Completed' },
              properties: [{ id: 'color', value: { fixedColor: 'green', mode: 'fixed' } }],
            },
          ],
        },
        options+: {
          legend+: { calcs: ['mean', 'sum'] },
        },
      },
      h=10, w=24, x=0, y=6,
    ) + { id: 7 },

    // === Row: Work In Progress ===
    withGrid(panels.row('Work In Progress'), h=1, w=24, x=0, y=16) + { id: 8 },

    // Current WIP (gauge)
    withGrid(
      panels.traceqlGauge(
        title='Current WIP',
        query='{%s="in_progress" && project.id="$project"}' % attr.status,
        datasource=tempoDs,
        min=0,
        max=20,
        thresholds=[
          { color: 'green', value: null },
          { color: 'yellow', value: 8 },
          { color: 'red', value: 12 },
        ],
      ),
      h=6, w=8, x=0, y=17,
    ) + { id: 9 },

    // WIP Over Time
    withGrid(
      panels.traceqlTimeseries(
        title='WIP Over Time',
        targets=[traceqlTarget('{%s="in_progress" && project.id="$project"}' % attr.status)],
        datasource=tempoDs,
        lineInterpolation='stepAfter',
        lineWidth=2,
        unit='none',
      ) + {
        fieldConfig+: {
          defaults+: {
            custom+: {
              showPoints: 'never',
              spanNulls: true,
              thresholdsStyle: { mode: 'line' },
            },
            thresholds: {
              mode: 'absolute',
              steps: [
                { color: 'green', value: null },
                { color: 'red', value: 10 },
              ],
            },
          },
        },
        options+: {
          legend+: { displayMode: 'list' },
          tooltip: { mode: 'single', sort: 'none' },
        },
      },
      h=6, w=16, x=8, y=17,
    ) + { id: 10 },

    // === Row: Cycle Time ===
    withGrid(panels.row('Cycle Time'), h=1, w=24, x=0, y=23) + { id: 11 },

    // Cycle Time Trend
    withGrid(
      panels.traceqlTimeseries(
        title='Cycle Time Trend (Hours)',
        targets=[traceqlTarget('{%s="done" && project.id="$project"} | select(duration)' % attr.status)],
        datasource=tempoDs,
        lineInterpolation='smooth',
        lineWidth=2,
        fillOpacity=0,
        unit='h',
      ) + {
        fieldConfig+: {
          defaults+: {
            custom+: {
              axisLabel: 'Hours',
            },
          },
        },
        options+: {
          legend+: { calcs: ['mean', 'min', 'max'] },
          tooltip: { mode: 'single', sort: 'none' },
        },
      },
      h=8, w=24, x=0, y=24,
    ) + { id: 12 },
  ],
}
