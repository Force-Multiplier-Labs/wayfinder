// Panel construction helpers for Wayfinder dashboards.
{
  // Stat panel (single value)
  stat(title, expr, datasource={ type: 'prometheus', uid: '${datasource}' }, unit='', thresholds=[]):: {
    title: title,
    type: 'stat',
    datasource: datasource,
    targets: [{ expr: expr, refId: 'A' }],
    fieldConfig: {
      defaults: {
        [if unit != '' then 'unit']: unit,
        color: { mode: 'thresholds' },
        thresholds: {
          mode: 'absolute',
          steps: if std.length(thresholds) > 0 then thresholds else [
            { color: 'green', value: null },
          ],
        },
      },
      overrides: [],
    },
    options: {
      reduceOptions: { calcs: ['lastNotNull'], fields: '', values: false },
      colorMode: 'value',
      graphMode: 'area',
      justifyMode: 'auto',
      textMode: 'auto',
      wideLayout: true,
      orientation: 'auto',
    },
  },

  // Gauge panel
  gauge(title, expr, datasource={ type: 'prometheus', uid: '${datasource}' }, unit='percent', min=0, max=100, thresholds=[]):: {
    title: title,
    type: 'gauge',
    datasource: datasource,
    targets: [{ expr: expr, refId: 'A' }],
    fieldConfig: {
      defaults: {
        unit: unit,
        min: min,
        max: max,
        color: { mode: 'thresholds' },
        thresholds: {
          mode: 'absolute',
          steps: if std.length(thresholds) > 0 then thresholds else [
            { color: 'red', value: null },
            { color: 'yellow', value: 80 },
            { color: 'green', value: 100 },
          ],
        },
        mappings: [],
      },
      overrides: [],
    },
    options: {
      showThresholdLabels: false,
      showThresholdMarkers: true,
      orientation: 'auto',
      reduceOptions: { calcs: ['lastNotNull'], fields: '', values: false },
      text: {},
    },
  },

  // Time series panel
  timeseries(title, expr, datasource={ type: 'prometheus', uid: '${datasource}' }, unit='', legendFormat=''):: {
    title: title,
    type: 'timeseries',
    datasource: datasource,
    targets: [{
      expr: expr,
      refId: 'A',
      [if legendFormat != '' then 'legendFormat']: legendFormat,
    }],
    fieldConfig: {
      defaults: {
        [if unit != '' then 'unit']: unit,
        color: { mode: 'palette-classic' },
        custom: {
          drawStyle: 'line',
          lineInterpolation: 'linear',
          fillOpacity: 10,
          pointSize: 5,
          showPoints: 'auto',
        },
      },
      overrides: [],
    },
    options: {
      tooltip: { mode: 'single', sort: 'none' },
      legend: { displayMode: 'list', placement: 'bottom', calcs: [] },
    },
  },

  // Table panel
  table(title, expr, datasource={ type: 'prometheus', uid: '${datasource}' }):: {
    title: title,
    type: 'table',
    datasource: datasource,
    targets: [{ expr: expr, refId: 'A', format: 'table', instant: true }],
    fieldConfig: { defaults: {}, overrides: [] },
    options: {
      showHeader: true,
      sortBy: [],
    },
  },

  // Bar gauge panel
  barGauge(title, expr, datasource={ type: 'prometheus', uid: '${datasource}' }, unit='percent', min=0, max=100, thresholds=[]):: {
    title: title,
    type: 'bargauge',
    datasource: datasource,
    targets: [{ expr: expr, refId: 'A' }],
    fieldConfig: {
      defaults: {
        unit: unit,
        min: min,
        max: max,
        color: { mode: 'thresholds' },
        thresholds: {
          mode: 'absolute',
          steps: if std.length(thresholds) > 0 then thresholds else [
            { color: 'red', value: null },
            { color: 'yellow', value: 60 },
            { color: 'green', value: 80 },
          ],
        },
      },
      overrides: [],
    },
    options: {
      displayMode: 'gradient',
      orientation: 'horizontal',
      reduceOptions: { calcs: ['lastNotNull'], fields: '', values: false },
      showUnfilled: true,
      valueMode: 'color',
    },
  },

  // Pie chart panel
  piechart(title, targets, datasource={ type: 'prometheus', uid: '${datasource}' }):: {
    title: title,
    type: 'piechart',
    datasource: datasource,
    targets: targets,
    fieldConfig: {
      defaults: {
        color: { mode: 'palette-classic' },
        custom: {
          hideFrom: { legend: false, tooltip: false, viz: false },
        },
        mappings: [],
      },
      overrides: [],
    },
    options: {
      legend: { displayMode: 'list', placement: 'right', showLegend: true },
      pieType: 'pie',
      reduceOptions: { calcs: ['count'], fields: '', values: false },
      tooltip: { mode: 'single', sort: 'none' },
    },
  },

  // Histogram panel
  histogram(title, targets, datasource={ type: 'prometheus', uid: '${datasource}' }, unit=''):: {
    title: title,
    type: 'histogram',
    datasource: datasource,
    targets: targets,
    fieldConfig: {
      defaults: {
        color: { mode: 'palette-classic' },
        custom: {
          fillOpacity: 80,
          gradientMode: 'none',
          hideFrom: { legend: false, tooltip: false, viz: false },
          lineWidth: 1,
          stacking: { group: 'A', mode: 'none' },
        },
        mappings: [],
        thresholds: {
          mode: 'absolute',
          steps: [{ color: 'green', value: null }],
        },
        [if unit != '' then 'unit']: unit,
      },
      overrides: [],
    },
    options: {
      bucketOffset: 0,
      legend: {
        calcs: ['mean', 'max'],
        displayMode: 'list',
        placement: 'bottom',
        showLegend: true,
      },
    },
  },

  // Stat panel for TraceQL queries (count-based)
  traceqlStat(title, query, datasource={ type: 'tempo', uid: '${tempo_datasource}' }, limit=1000, thresholds=[]):: {
    title: title,
    type: 'stat',
    datasource: datasource,
    targets: [{
      datasource: datasource,
      limit: limit,
      query: query,
      queryType: 'traceql',
      refId: 'A',
    }],
    fieldConfig: {
      defaults: {
        color: { mode: if std.length(thresholds) > 0 then 'thresholds' else 'palette-classic' },
        mappings: [],
        thresholds: {
          mode: 'absolute',
          steps: if std.length(thresholds) > 0 then thresholds else [
            { color: 'green', value: null },
          ],
        },
      },
      overrides: [],
    },
    options: {
      colorMode: 'value',
      graphMode: 'none',
      justifyMode: 'auto',
      orientation: 'auto',
      reduceOptions: { calcs: ['count'], fields: '', values: false },
      textMode: 'auto',
    },
    pluginVersion: '10.2.0',
  },

  // Table panel for TraceQL queries
  traceqlTable(title, query, datasource={ type: 'tempo', uid: '${tempo_datasource}' }, limit=100):: {
    title: title,
    type: 'table',
    datasource: datasource,
    targets: [{
      datasource: datasource,
      limit: limit,
      query: query,
      queryType: 'traceql',
      refId: 'A',
    }],
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
          steps: [{ color: 'green', value: null }],
        },
      },
      overrides: [],
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
    },
    pluginVersion: '10.2.0',
  },

  // Row (section header)
  row(title, y=0):: {
    type: 'row',
    title: title,
    collapsed: false,
    gridPos: { h: 1, w: 24, x: 0, y: y },
    panels: [],
  },
}
