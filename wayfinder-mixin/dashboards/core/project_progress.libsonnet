// Project Progress Dashboard
// Tracks epics, stories, and tasks as OpenTelemetry spans via Tempo.
local config = (import '../../config.libsonnet')._config;
local dashboards = import '../../lib/dashboards.libsonnet';
local panels = import '../../lib/panels.libsonnet';
local variables = import '../../lib/variables.libsonnet';

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
  title='[CORE] Wayfinder: Project Progress',
  uid='cc-core-project-progress',
  description='Wayfinder Project Progress - Track epics, stories, and tasks as OpenTelemetry spans',
  tags=['project-management', 'tasks-as-spans'],
);

baseDashboard {
  schemaVersion: 38,
  time: { from: 'now-90d', to: 'now' },
  links: [{
    asDropdown: false,
    icon: 'external link',
    includeVars: false,
    keepTime: false,
    tags: [],
    targetBlank: true,
    title: 'Wayfinder Docs',
    tooltip: '',
    type: 'link',
    url: 'https://github.com/contextcore/contextcore',
  }],
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
    // === Row: Project Overview ===
    withGrid(panels.row('Project Overview'), h=1, w=24, x=0, y=0) + { id: 1 },

    // Epics count
    withGrid(
      panels.traceqlStat(
        title='Epics',
        query='{%s="epic" && project.id="$project"}' % attr.type,
        datasource=tempoDs,
      ),
      h=4, w=6, x=0, y=1,
    ) + { id: 2 },

    // Stories count
    withGrid(
      panels.traceqlStat(
        title='Stories',
        query='{%s="story" && project.id="$project"}' % attr.type,
        datasource=tempoDs,
      ),
      h=4, w=6, x=6, y=1,
    ) + { id: 3 },

    // Tasks count
    withGrid(
      panels.traceqlStat(
        title='Tasks',
        query='{%s="task" && project.id="$project"}' % attr.type,
        datasource=tempoDs,
      ),
      h=4, w=6, x=12, y=1,
    ) + { id: 4 },

    // Blocked count (with thresholds)
    withGrid(
      panels.traceqlStat(
        title='Blocked',
        query='{%s="blocked" && project.id="$project"}' % attr.status,
        datasource=tempoDs,
        thresholds=[
          { color: 'green', value: null },
          { color: 'yellow', value: 1 },
          { color: 'red', value: 3 },
        ],
      ),
      h=4, w=6, x=18, y=1,
    ) + { id: 5 },

    // === Row: Task Status Distribution ===
    withGrid(panels.row('Task Status Distribution'), h=1, w=24, x=0, y=5) + { id: 6 },

    // Tasks by Status (pie chart)
    withGrid(
      panels.piechart(
        title='Tasks by Status',
        targets=[traceqlTarget('{project.id="$project"} | select(%s)' % attr.status)],
        datasource=tempoDs,
      ),
      h=8, w=12, x=0, y=6,
    ) + { id: 7, pluginVersion: '10.2.0' },

    // Tasks by Type (pie chart)
    withGrid(
      panels.piechart(
        title='Tasks by Type',
        targets=[traceqlTarget('{project.id="$project"} | select(%s)' % attr.type)],
        datasource=tempoDs,
      ),
      h=8, w=12, x=12, y=6,
    ) + { id: 8, pluginVersion: '10.2.0' },

    // === Row: Blocked Tasks ===
    withGrid(panels.row('Blocked Tasks'), h=1, w=24, x=0, y=14) + { id: 9 },

    // Blocked tasks table
    withGrid(
      panels.traceqlTable(
        title='Currently Blocked Tasks',
        query='{%s="blocked" && project.id="$project"} | select(%s, %s, %s, task.blocked_by)' % [attr.status, attr.id, attr.title, 'task.assignee'],
        datasource=tempoDs,
      ),
      h=8, w=24, x=0, y=15,
    ) + { id: 10 },

    // === Row: Lead Time Analysis ===
    withGrid(panels.row('Lead Time Analysis'), h=1, w=24, x=0, y=23) + { id: 11 },

    // Lead time histogram
    withGrid(
      panels.histogram(
        title='Task Lead Time Distribution (seconds)',
        targets=[traceqlTarget('{%s="done" && project.id="$project"} | select(duration)' % attr.status)],
        datasource=tempoDs,
        unit='s',
      ),
      h=8, w=24, x=0, y=24,
    ) + { id: 12, pluginVersion: '10.2.0' },
  ],
}
