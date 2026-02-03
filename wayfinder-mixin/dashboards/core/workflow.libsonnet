// Workflow Manager Dashboard
// View project tasks and workflow executions from Tempo traces.
local config = (import '../../config.libsonnet')._config;
local dashboards = import '../../lib/dashboards.libsonnet';
local panels = import '../../lib/panels.libsonnet';

local tempoDs = { type: 'tempo', uid: 'tempo' };

local withGrid(panel, h, w, x, y) = panel + { gridPos: { h: h, w: w, x: x, y: y } };

local traceqlTarget(query, limit=50) = {
  datasource: tempoDs,
  limit: limit,
  query: query,
  queryType: 'traceql',
  refId: 'A',
};

local baseDashboard = dashboards.dashboard(
  title='[RABBIT] ContextCore Workflow Manager',
  uid='contextcore-workflow',
  description='View project tasks and workflow executions from Tempo traces',
  tags=['contextcore', 'rabbit', 'workflow'],
);

baseDashboard {
  annotations: { list: [] },
  schemaVersion: 39,
  time: { from: 'now-7d', to: 'now' },
  templating: {
    list: [
      {
        name: 'project',
        label: 'Project',
        type: 'custom',
        current: { text: 'beaver-lead-contractor', value: 'beaver-lead-contractor' },
        options: [
          { text: 'beaver-lead-contractor', value: 'beaver-lead-contractor', selected: true },
          { text: 'dashboard-persistence', value: 'dashboard-persistence' },
          { text: 'ajidamoo-squirrel', value: 'ajidamoo-squirrel' },
          { text: 'asabikeshiinh-localization', value: 'asabikeshiinh-localization' },
          { text: 'contextcore-tui-fixes', value: 'contextcore-tui-fixes' },
          { text: 'demo-project', value: 'demo-project' },
          { text: 'contextcore', value: 'contextcore' },
        ],
        query: 'beaver-lead-contractor,dashboard-persistence,ajidamoo-squirrel,asabikeshiinh-localization,contextcore-tui-fixes,demo-project,contextcore',
      },
    ],
  },
  timepicker: {},
  timezone: '',
  weekStart: '',
  panels: [
    // === Row: Project Overview ===
    withGrid(panels.row('Project Overview'), h=1, w=24, x=0, y=0) + { id: 100 },

    // Projects with Activity
    withGrid({
      id: 1,
      title: 'Projects with Activity',
      type: 'table',
      datasource: tempoDs,
      fieldConfig: {
        defaults: {
          custom: {
            align: 'auto',
            cellOptions: { type: 'auto' },
          },
        },
      },
      options: {
        cellHeight: 'sm',
        showHeader: true,
      },
      targets: [traceqlTarget('{resource.project.id != ""} | select(resource.project.id)', limit=100)],
    }, h=8, w=12, x=0, y=1),

    // Tasks - $project
    withGrid({
      id: 2,
      title: 'Tasks - ${project}',
      type: 'table',
      datasource: tempoDs,
      fieldConfig: {
        defaults: {
          custom: {
            align: 'auto',
            cellOptions: { type: 'auto' },
          },
        },
        overrides: [
          {
            matcher: { id: 'byName', options: 'task.status' },
            properties: [
              {
                id: 'custom.cellOptions',
                value: { type: 'color-background', mode: 'basic' },
              },
              {
                id: 'mappings',
                value: [
                  { type: 'value', options: { pending: { color: 'yellow', text: 'PENDING' } } },
                  { type: 'value', options: { in_progress: { color: 'blue', text: 'IN PROGRESS' } } },
                  { type: 'value', options: { done: { color: 'green', text: 'DONE' } } },
                  { type: 'value', options: { blocked: { color: 'red', text: 'BLOCKED' } } },
                ],
              },
            ],
          },
        ],
      },
      options: {
        cellHeight: 'sm',
        showHeader: true,
      },
      targets: [traceqlTarget('{resource.project.id = "$project"} | select(span.task.id, span.task.title, span.task.status, span.task.type)')],
    }, h=8, w=12, x=12, y=1),

    // === Row: Workflow Runs ===
    withGrid(panels.row('Workflow Runs'), h=1, w=24, x=0, y=9) + { id: 101 },

    // Workflow Executions
    withGrid({
      id: 3,
      title: 'Workflow Executions',
      type: 'table',
      datasource: tempoDs,
      fieldConfig: {
        defaults: {
          custom: {
            align: 'auto',
            cellOptions: { type: 'auto' },
          },
        },
        overrides: [
          {
            matcher: { id: 'byName', options: 'workflow.status' },
            properties: [
              {
                id: 'custom.cellOptions',
                value: { type: 'color-background', mode: 'basic' },
              },
              {
                id: 'mappings',
                value: [
                  { type: 'value', options: { running: { color: 'blue', text: 'RUNNING' } } },
                  { type: 'value', options: { completed: { color: 'green', text: 'COMPLETED' } } },
                  { type: 'value', options: { failed: { color: 'red', text: 'FAILED' } } },
                ],
              },
            ],
          },
          {
            matcher: { id: 'byName', options: 'Duration' },
            properties: [{ id: 'unit', value: 'ms' }],
          },
        ],
      },
      options: {
        cellHeight: 'sm',
        showHeader: true,
      },
      targets: [traceqlTarget('{name =~ "workflow.*"} | select(resource.project.id, span.workflow.id, span.workflow.status, span.workflow.type, duration)')],
    }, h=8, w=24, x=0, y=10),

    // === Row: Workflow Trigger ===
    withGrid(panels.row('Workflow Trigger'), h=1, w=24, x=0, y=18) + { id: 102 },

    // Trigger Workflow (custom plugin panel)
    withGrid({
      id: 12,
      title: 'Trigger Workflow - ${project}',
      type: 'contextcore-workflow-panel',
      options: {
        apiUrl: 'http://localhost:8080',
        projectId: '$project',
        showDryRun: true,
        showExecute: true,
        confirmExecution: true,
        refreshInterval: 10,
      },
    }, h=8, w=8, x=0, y=19),

    // Active Workflow Status
    withGrid({
      id: 14,
      title: 'Active Workflow Status',
      description: 'Real-time status of currently running workflow',
      type: 'stat',
      datasource: tempoDs,
      fieldConfig: {
        defaults: {
          mappings: [
            { type: 'value', options: { spec: { text: 'Spec Creation', color: 'blue' } } },
            { type: 'value', options: { draft: { text: 'Drafting Code', color: 'yellow' } } },
            { type: 'value', options: { review: { text: 'Code Review', color: 'orange' } } },
            { type: 'value', options: { integration: { text: 'Integration', color: 'green' } } },
          ],
          thresholds: {
            mode: 'absolute',
            steps: [{ color: 'blue', value: null }],
          },
          noValue: 'No Active Workflow',
        },
      },
      options: {
        reduceOptions: { values: false, calcs: ['lastNotNull'], fields: '' },
        orientation: 'auto',
        textMode: 'auto',
        colorMode: 'value',
        graphMode: 'none',
        justifyMode: 'auto',
      },
      targets: [traceqlTarget('{resource.service.name="lead-contractor" && status=unset && resource.project.id="$project"} | select(span.workflow.phase)', limit=1)],
    }, h=4, w=8, x=8, y=19),

    // Progress (gauge)
    withGrid({
      id: 15,
      title: 'Progress',
      description: 'Steps completed in current workflow',
      type: 'gauge',
      datasource: tempoDs,
      fieldConfig: {
        defaults: {
          min: 0,
          max: 100,
          unit: 'percent',
          thresholds: {
            mode: 'absolute',
            steps: [
              { color: 'red', value: null },
              { color: 'yellow', value: 25 },
              { color: 'green', value: 75 },
            ],
          },
          noValue: '0',
        },
      },
      options: {
        reduceOptions: { values: false, calcs: ['lastNotNull'], fields: '' },
        showThresholdLabels: false,
        showThresholdMarkers: true,
      },
      targets: [traceqlTarget('{resource.service.name="lead-contractor" && status=unset && resource.project.id="$project"} | select(span.workflow.progress_percent)', limit=1)],
    }, h=4, w=4, x=8, y=23),

    // Current Task
    withGrid({
      id: 16,
      title: 'Current Task',
      description: 'Feature currently being processed',
      type: 'stat',
      datasource: tempoDs,
      fieldConfig: {
        defaults: {
          noValue: 'None',
        },
      },
      options: {
        reduceOptions: { values: false, calcs: ['lastNotNull'], fields: '' },
        orientation: 'auto',
        textMode: 'name',
        colorMode: 'none',
        graphMode: 'none',
        justifyMode: 'auto',
      },
      targets: [traceqlTarget('{resource.service.name="lead-contractor" && status=unset && resource.project.id="$project"} | select(span.task.title)', limit=1)],
    }, h=4, w=4, x=12, y=23),

    // CLI Commands (text panel)
    withGrid({
      id: 13,
      title: 'CLI Commands (Fallback)',
      type: 'text',
      options: {
        content: '### Run Workflows via CLI\n\nIf the workflow panel is not available, use the CLI:\n\n```bash\n# Dry run (preview without executing)\ncontextcore workflow run --project ${project} --dry-run\n\n# Execute workflow\ncontextcore workflow run --project ${project}\n\n# Check workflow status\ncontextcore workflow status --id <workflow-id>\n```\n\n### Plugin Installation\n\nTo enable the workflow trigger panel:\n\n```bash\ncd contextcore-owl\nnpm install && npm run build\ndocker compose restart grafana\n```',
        mode: 'markdown',
      },
    }, h=8, w=8, x=16, y=19),

    // === Row: Workflow History ===
    withGrid(panels.row('Workflow History'), h=1, w=24, x=0, y=27) + { id: 103 },

    // Lead Contractor Workflow History
    withGrid({
      id: 17,
      title: 'Lead Contractor Workflow History - ${project}',
      description: 'Completed workflow runs with duration, cost, and outcome',
      type: 'table',
      datasource: tempoDs,
      fieldConfig: {
        defaults: {
          custom: {
            align: 'auto',
            cellOptions: { type: 'auto' },
            filterable: true,
          },
        },
        overrides: [
          {
            matcher: { id: 'byName', options: 'Status' },
            properties: [
              {
                id: 'custom.cellOptions',
                value: { type: 'color-background', mode: 'basic' },
              },
              {
                id: 'mappings',
                value: [
                  { type: 'value', options: { ok: { color: 'green', text: 'SUCCESS' } } },
                  { type: 'value', options: { 'error': { color: 'red', text: 'FAILED' } } },
                  { type: 'value', options: { unset: { color: 'blue', text: 'RUNNING' } } },
                ],
              },
            ],
          },
          {
            matcher: { id: 'byName', options: 'Duration' },
            properties: [{ id: 'unit', value: 'ns' }],
          },
          {
            matcher: { id: 'byName', options: 'Cost ($)' },
            properties: [
              { id: 'unit', value: 'currencyUSD' },
              { id: 'decimals', value: 4 },
            ],
          },
          {
            matcher: { id: 'byName', options: 'Trace ID' },
            properties: [{
              id: 'links',
              value: [{
                title: 'View in Tempo',
                url: '/explore?orgId=1&left=%7B%22datasource%22:%22tempo%22,%22queries%22:%5B%7B%22queryType%22:%22traceql%22,%22query%22:%22${__value.raw}%22%7D%5D%7D',
              }],
            }],
          },
        ],
      },
      options: {
        cellHeight: 'sm',
        showHeader: true,
        sortBy: [{ displayName: 'Start Time', desc: true }],
      },
      transformations: [{
        id: 'organize',
        options: {
          renameByName: {
            traceID: 'Trace ID',
            'span.workflow.run_id': 'Run ID',
            'span.task.title': 'Feature',
            'span.workflow.features_processed': 'Features',
            'span.workflow.features_succeeded': 'Succeeded',
            'span.workflow.features_failed': 'Failed',
            duration: 'Duration',
            'span.contextcore.cost.usd': 'Cost ($)',
            status: 'Status',
            startTime: 'Start Time',
          },
          excludeByName: {},
          indexByName: {
            'Start Time': 0,
            'Run ID': 1,
            Feature: 2,
            Features: 3,
            Succeeded: 4,
            Failed: 5,
            Duration: 6,
            'Cost ($)': 7,
            Status: 8,
            'Trace ID': 9,
          },
        },
      }],
      targets: [traceqlTarget('{resource.service.name="lead-contractor" && name="workflow" && resource.project.id="$project"} | select(span.workflow.run_id, span.task.title, span.workflow.features_processed, span.workflow.features_succeeded, span.workflow.features_failed, duration, span.contextcore.cost.usd, status)', limit=20)],
    }, h=10, w=24, x=0, y=28),
  ],
}
