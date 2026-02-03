// Value Capabilities Dashboard
// Developer dashboard for exploring and filtering value capabilities.
local config = (import '../../config.libsonnet')._config;
local dashboards = import '../../lib/dashboards.libsonnet';
local panels = import '../../lib/panels.libsonnet';

local tempoDs = { type: 'tempo', uid: 'tempo' };

local withGrid(panel, h, w, x, y) = panel + { gridPos: { h: h, w: w, x: x, y: y } };

local traceqlTarget(query, limit=1000) = {
  datasource: tempoDs,
  query: query,
  queryType: 'traceql',
  refId: 'A',
  [if limit != 1000 then 'limit']: limit,
};

// Reusable stat panel for KPI row
local kpiStat(id, title, query, color) = {
  id: id,
  title: title,
  type: 'stat',
  datasource: tempoDs,
  fieldConfig: {
    defaults: {
      color: { mode: 'thresholds' },
      mappings: [],
      thresholds: {
        mode: 'absolute',
        steps: [{ color: color, value: null }],
      },
    },
    overrides: [],
  },
  options: {
    colorMode: 'value',
    graphMode: 'area',
    justifyMode: 'auto',
    orientation: 'auto',
    reduceOptions: { calcs: ['count'], fields: '', values: false },
    textMode: 'auto',
    wideLayout: true,
  },
  pluginVersion: '10.0.0',
  targets: [traceqlTarget(query)],
};

// Reusable table panel with footer pagination
local tableWithFooter(id, title, query, overrides=[], transformations=[]) = {
  id: id,
  title: title,
  type: 'table',
  datasource: tempoDs,
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
    overrides: overrides,
  },
  options: {
    cellHeight: 'sm',
    footer: {
      countRows: true,
      enablePagination: true,
      fields: '',
      reducer: ['count'],
      show: true,
    },
    showHeader: true,
  },
  pluginVersion: '10.0.0',
  targets: [traceqlTarget(query)],
  [if std.length(transformations) > 0 then 'transformations']: transformations,
};

// Barchart panel
local barchart(id, title, query, groupByField, transformations) = {
  id: id,
  title: title,
  type: 'barchart',
  datasource: tempoDs,
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
    barWidth: 0.8,
    fullHighlight: false,
    groupWidth: 0.7,
    legend: {
      calcs: [],
      displayMode: 'list',
      placement: 'bottom',
      showLegend: false,
    },
    orientation: 'horizontal',
    showValue: 'auto',
    stacking: 'none',
    tooltip: { mode: 'single', sort: 'none' },
    xTickLabelRotation: 0,
    xTickLabelSpacing: 0,
  },
  pluginVersion: '10.0.0',
  targets: [traceqlTarget(query)],
  transformations: transformations,
};

local baseDashboard = dashboards.dashboard(
  title='Value Capabilities Dashboard',
  uid='contextcore-value-capabilities',
  description='Developer dashboard for exploring and filtering value capabilities from capability-value-promoter. Enables discovery of capabilities by persona, value type, channel, and skill.',
  tags=['contextcore', 'value', 'capabilities', 'developer'],
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
  links: [{
    asDropdown: false,
    icon: 'external link',
    includeVars: false,
    keepTime: true,
    tags: ['contextcore'],
    targetBlank: true,
    title: 'ContextCore Dashboards',
    tooltip: '',
    type: 'dashboards',
    url: '',
  }],
  schemaVersion: 39,
  time: { from: 'now-7d', to: 'now' },
  timezone: 'browser',
  templating: {
    list: [
      {
        current: { selected: true, text: 'All', value: '$__all' },
        hide: 0,
        includeAll: true,
        multi: true,
        name: 'persona',
        options: [
          { selected: true, text: 'All', value: '$__all' },
          { selected: false, text: 'developer', value: 'developer' },
          { selected: false, text: 'operator', value: 'operator' },
          { selected: false, text: 'architect', value: 'architect' },
          { selected: false, text: 'creator', value: 'creator' },
          { selected: false, text: 'designer', value: 'designer' },
          { selected: false, text: 'manager', value: 'manager' },
          { selected: false, text: 'executive', value: 'executive' },
          { selected: false, text: 'product', value: 'product' },
          { selected: false, text: 'security', value: 'security' },
          { selected: false, text: 'data', value: 'data' },
        ],
        query: 'developer,operator,architect,creator,designer,manager,executive,product,security,data',
        queryValue: '',
        skipUrlSync: false,
        type: 'custom',
      },
      {
        current: { selected: true, text: 'All', value: '$__all' },
        hide: 0,
        includeAll: true,
        multi: true,
        name: 'value_type',
        options: [
          { selected: true, text: 'All', value: '$__all' },
          { selected: false, text: 'direct', value: 'direct' },
          { selected: false, text: 'indirect', value: 'indirect' },
          { selected: false, text: 'ripple', value: 'ripple' },
        ],
        query: 'direct,indirect,ripple',
        queryValue: '',
        skipUrlSync: false,
        type: 'custom',
      },
      {
        current: { selected: true, text: 'All', value: '$__all' },
        hide: 0,
        includeAll: true,
        multi: true,
        name: 'channel',
        options: [
          { selected: true, text: 'All', value: '$__all' },
          { selected: false, text: 'slack', value: 'slack' },
          { selected: false, text: 'email', value: 'email' },
          { selected: false, text: 'docs', value: 'docs' },
          { selected: false, text: 'in_app', value: 'in_app' },
          { selected: false, text: 'social', value: 'social' },
          { selected: false, text: 'blog', value: 'blog' },
          { selected: false, text: 'press', value: 'press' },
          { selected: false, text: 'video', value: 'video' },
          { selected: false, text: 'alert', value: 'alert' },
          { selected: false, text: 'changelog', value: 'changelog' },
          { selected: false, text: 'meeting', value: 'meeting' },
        ],
        query: 'slack,email,docs,in_app,social,blog,press,video,alert,changelog,meeting',
        queryValue: '',
        skipUrlSync: false,
        type: 'custom',
      },
      {
        current: { selected: true, text: 'All', value: '$__all' },
        datasource: tempoDs,
        definition: '',
        hide: 0,
        includeAll: true,
        multi: true,
        name: 'skill_id',
        options: [],
        query: {
          query: '{ name =~ "value_skill:.*" } | select(skill.id)',
          queryType: 'traceql',
        },
        refresh: 2,
        regex: '',
        skipUrlSync: false,
        sort: 1,
        type: 'query',
      },
      {
        current: { selected: true, text: 'All', value: '$__all' },
        hide: 0,
        includeAll: true,
        multi: true,
        name: 'knowledge_category',
        options: [
          { selected: true, text: 'All', value: '$__all' },
          { selected: false, text: 'value_proposition', value: 'value_proposition' },
          { selected: false, text: 'messaging', value: 'messaging' },
          { selected: false, text: 'persona', value: 'persona' },
          { selected: false, text: 'channel', value: 'channel' },
          { selected: false, text: 'workflow', value: 'workflow' },
          { selected: false, text: 'architecture', value: 'architecture' },
          { selected: false, text: 'api', value: 'api' },
          { selected: false, text: 'configuration', value: 'configuration' },
        ],
        query: 'value_proposition,messaging,persona,channel,workflow,architecture,api,configuration',
        queryValue: '',
        skipUrlSync: false,
        type: 'custom',
      },
    ],
  },
  timepicker: {},
  weekStart: '',
  panels: [
    // === Row: Value Capability KPIs ===
    withGrid(panels.row('Value Capability KPIs'), h=1, w=24, x=0, y=0) + { id: 1 },

    // Total Capabilities
    withGrid(kpiStat(
      id=2,
      title='Total Capabilities',
      query='{ name =~ "value_capability:.*" && value.persona =~ "${persona:regex}" && value.type =~ "${value_type:regex}" && value.channel =~ "${channel:regex}" && skill.id =~ "${skill_id:regex}" }',
      color='blue',
    ), h=4, w=4, x=0, y=1),

    // Direct Value
    withGrid(kpiStat(
      id=3,
      title='Direct Value',
      query='{ name =~ "value_capability:.*" && value.type = "direct" && value.persona =~ "${persona:regex}" && value.channel =~ "${channel:regex}" }',
      color='green',
    ), h=4, w=4, x=4, y=1),

    // Indirect Value
    withGrid(kpiStat(
      id=4,
      title='Indirect Value',
      query='{ name =~ "value_capability:.*" && value.type = "indirect" && value.persona =~ "${persona:regex}" && value.channel =~ "${channel:regex}" }',
      color='yellow',
    ), h=4, w=4, x=8, y=1),

    // Ripple Value
    withGrid(kpiStat(
      id=5,
      title='Ripple Value',
      query='{ name =~ "value_capability:.*" && value.type = "ripple" && value.persona =~ "${persona:regex}" && value.channel =~ "${channel:regex}" }',
      color='purple',
    ), h=4, w=4, x=12, y=1),

    // Skills Parsed
    withGrid(kpiStat(
      id=6,
      title='Skills Parsed',
      query='{ name =~ "value_skill:.*" && value.persona =~ "${persona:regex}" }',
      color='orange',
    ), h=4, w=4, x=16, y=1),

    // Cross-Links
    withGrid(kpiStat(
      id=7,
      title='Cross-Links',
      query='{ name =~ "value_link:.*" }',
      color='semi-dark-blue',
    ), h=4, w=4, x=20, y=1),

    // === Row: Capability Discovery ===
    withGrid(panels.row('Capability Discovery'), h=1, w=24, x=0, y=5) + { id: 8 },

    // Value Capabilities Browser
    withGrid(tableWithFooter(
      id=9,
      title='Value Capabilities Browser',
      query='{ name =~ "value_capability:.*" && value.persona =~ "${persona:regex}" && value.type =~ "${value_type:regex}" && value.channel =~ "${channel:regex}" && skill.id =~ "${skill_id:regex}" && knowledge.category =~ "${knowledge_category:regex}" } | select(skill.id, capability.name, value.type, value.persona, value.channel, value.pain_point, value.benefit)',
      overrides=[
        {
          matcher: { id: 'byName', options: 'value.type' },
          properties: [
            { id: 'custom.displayMode', value: 'color-background' },
            {
              id: 'mappings',
              value: [{
                options: {
                  direct: { color: 'green', index: 0, text: 'Direct' },
                  indirect: { color: 'yellow', index: 1, text: 'Indirect' },
                  ripple: { color: 'purple', index: 2, text: 'Ripple' },
                },
                type: 'value',
              }],
            },
          ],
        },
        {
          matcher: { id: 'byName', options: 'capability.name' },
          properties: [{ id: 'custom.width', value: 250 }],
        },
        {
          matcher: { id: 'byName', options: 'value.pain_point' },
          properties: [{ id: 'custom.width', value: 300 }],
        },
        {
          matcher: { id: 'byName', options: 'value.benefit' },
          properties: [{ id: 'custom.width', value: 300 }],
        },
      ],
      transformations=[{
        id: 'organize',
        options: {
          excludeByName: {},
          indexByName: {
            'skill.id': 0,
            'capability.name': 1,
            'value.type': 2,
            'value.persona': 3,
            'value.channel': 4,
            'value.pain_point': 5,
            'value.benefit': 6,
          },
          renameByName: {
            'skill.id': 'Skill',
            'capability.name': 'Capability',
            'value.type': 'Value Type',
            'value.persona': 'Persona',
            'value.channel': 'Channel',
            'value.pain_point': 'Pain Point',
            'value.benefit': 'Benefit',
          },
        },
      }],
    ) + {
      options+: {
        sortBy: [{ desc: false, displayName: 'capability.name' }],
      },
    }, h=10, w=24, x=0, y=6),

    // === Row: Value Distribution ===
    withGrid(panels.row('Value Distribution'), h=1, w=24, x=0, y=16) + { id: 10 },

    // By Value Type (piechart)
    withGrid({
      id: 11,
      title: 'By Value Type',
      type: 'piechart',
      datasource: tempoDs,
      fieldConfig: {
        defaults: {
          color: { mode: 'palette-classic' },
          custom: {
            hideFrom: { legend: false, tooltip: false, viz: false },
          },
          mappings: [],
        },
        overrides: [
          {
            matcher: { id: 'byName', options: 'direct' },
            properties: [{ id: 'color', value: { fixedColor: 'green', mode: 'fixed' } }],
          },
          {
            matcher: { id: 'byName', options: 'indirect' },
            properties: [{ id: 'color', value: { fixedColor: 'yellow', mode: 'fixed' } }],
          },
          {
            matcher: { id: 'byName', options: 'ripple' },
            properties: [{ id: 'color', value: { fixedColor: 'purple', mode: 'fixed' } }],
          },
        ],
      },
      options: {
        legend: {
          displayMode: 'list',
          placement: 'right',
          showLegend: true,
          values: ['value'],
        },
        pieType: 'pie',
        reduceOptions: { calcs: ['count'], fields: '', values: false },
        tooltip: { mode: 'single', sort: 'none' },
      },
      pluginVersion: '10.0.0',
      targets: [traceqlTarget('{ name =~ "value_capability:.*" && value.persona =~ "${persona:regex}" && value.channel =~ "${channel:regex}" && skill.id =~ "${skill_id:regex}" } | select(value.type)')],
      transformations: [{
        id: 'groupBy',
        options: {
          fields: {
            'value.type': {
              aggregations: ['count'],
              operation: 'groupby',
            },
          },
        },
      }],
    }, h=8, w=8, x=0, y=17),

    // By Persona (barchart)
    withGrid(barchart(
      id=12,
      title='By Persona',
      query='{ name =~ "value_capability:.*" && value.type =~ "${value_type:regex}" && value.channel =~ "${channel:regex}" && skill.id =~ "${skill_id:regex}" } | select(value.persona)',
      groupByField='value.persona',
      transformations=[
        {
          id: 'groupBy',
          options: {
            fields: {
              'value.persona': {
                aggregations: ['count'],
                operation: 'groupby',
              },
            },
          },
        },
        {
          id: 'sortBy',
          options: {
            fields: {},
            sort: [{ field: 'count', desc: true }],
          },
        },
      ],
    ), h=8, w=8, x=8, y=17),

    // By Channel (barchart)
    withGrid(barchart(
      id=13,
      title='By Channel',
      query='{ name =~ "value_capability:.*" && value.persona =~ "${persona:regex}" && value.type =~ "${value_type:regex}" && skill.id =~ "${skill_id:regex}" } | select(value.channel)',
      groupByField='value.channel',
      transformations=[
        {
          id: 'groupBy',
          options: {
            fields: {
              'value.channel': {
                aggregations: ['count'],
                operation: 'groupby',
              },
            },
          },
        },
        {
          id: 'sortBy',
          options: {
            fields: {},
            sort: [{ field: 'count', desc: true }],
          },
        },
      ],
    ), h=8, w=8, x=16, y=17),

    // === Row: Pain Points & Benefits ===
    withGrid(panels.row('Pain Points & Benefits'), h=1, w=24, x=0, y=25) + { id: 14 },

    // Pain Points Addressed
    withGrid(tableWithFooter(
      id=15,
      title='Pain Points Addressed',
      query='{ name =~ "value_capability:.*" && value.persona =~ "${persona:regex}" && value.type =~ "${value_type:regex}" && value.channel =~ "${channel:regex}" && skill.id =~ "${skill_id:regex}" } | select(value.pain_point, value.pain_point_category, value.persona)',
      overrides=[
        {
          matcher: { id: 'byName', options: 'value.pain_point' },
          properties: [{ id: 'custom.width', value: 400 }],
        },
        {
          matcher: { id: 'byName', options: 'value.pain_point_category' },
          properties: [
            { id: 'custom.displayMode', value: 'color-background-solid' },
            {
              id: 'mappings',
              value: [{
                options: {
                  time: { color: 'red', index: 0, text: 'Time' },
                  complexity: { color: 'orange', index: 1, text: 'Complexity' },
                  cognitive: { color: 'yellow', index: 2, text: 'Cognitive' },
                  coordination: { color: 'blue', index: 3, text: 'Coordination' },
                  quality: { color: 'purple', index: 4, text: 'Quality' },
                },
                type: 'value',
              }],
            },
          ],
        },
      ],
      transformations=[{
        id: 'organize',
        options: {
          renameByName: {
            'value.pain_point': 'Pain Point',
            'value.pain_point_category': 'Category',
            'value.persona': 'For Persona',
          },
        },
      }],
    ), h=8, w=12, x=0, y=26),

    // Benefits Delivered
    withGrid(tableWithFooter(
      id=16,
      title='Benefits Delivered',
      query='{ name =~ "value_capability:.*" && value.persona =~ "${persona:regex}" && value.type =~ "${value_type:regex}" && value.channel =~ "${channel:regex}" && skill.id =~ "${skill_id:regex}" } | select(value.benefit, value.benefit_metric, value.time_savings)',
      overrides=[
        {
          matcher: { id: 'byName', options: 'value.benefit' },
          properties: [{ id: 'custom.width', value: 400 }],
        },
      ],
      transformations=[{
        id: 'organize',
        options: {
          renameByName: {
            'value.benefit': 'Benefit',
            'value.benefit_metric': 'Metric',
            'value.time_savings': 'Time Saved',
          },
        },
      }],
    ), h=8, w=12, x=12, y=26),

    // === Row: Cross-Linking & Related Skills ===
    withGrid(panels.row('Cross-Linking & Related Skills'), h=1, w=24, x=0, y=34) + { id: 17 },

    // Capabilities with Cross-Links
    withGrid(tableWithFooter(
      id=18,
      title='Capabilities with Cross-Links',
      query='{ name =~ "value_capability:.*" && value.related_skills != "" && value.persona =~ "${persona:regex}" && value.type =~ "${value_type:regex}" && skill.id =~ "${skill_id:regex}" } | select(capability.name, value.related_skills, value.related_capabilities)',
      overrides=[
        {
          matcher: { id: 'byName', options: 'value.related_skills' },
          properties: [{ id: 'custom.width', value: 300 }],
        },
      ],
      transformations=[{
        id: 'organize',
        options: {
          renameByName: {
            'capability.name': 'Value Capability',
            'value.related_skills': 'Related Technical Skills',
            'value.related_capabilities': 'Related Capabilities',
          },
        },
      }],
    ), h=8, w=12, x=0, y=35),

    // Value-to-Technical Links
    withGrid(tableWithFooter(
      id=19,
      title='Value-to-Technical Links',
      query='{ name =~ "value_link:.*" } | select(link.value_capability_id, link.technical_skill_id, link.technical_capability_id, link.type)',
      overrides=[
        {
          matcher: { id: 'byName', options: 'link.type' },
          properties: [
            { id: 'custom.displayMode', value: 'color-background-solid' },
            {
              id: 'mappings',
              value: [{
                options: {
                  describes: { color: 'blue', index: 0 },
                  complements: { color: 'green', index: 1 },
                  extends: { color: 'purple', index: 2 },
                },
                type: 'value',
              }],
            },
          ],
        },
      ],
      transformations=[{
        id: 'organize',
        options: {
          renameByName: {
            'link.value_capability_id': 'Value Capability',
            'link.technical_skill_id': 'Technical Skill',
            'link.technical_capability_id': 'Technical Capability',
            'link.type': 'Link Type',
          },
        },
      }],
    ), h=8, w=12, x=12, y=35),

    // === Row: Messaging Preview ===
    withGrid(panels.row('Messaging Preview'), h=1, w=24, x=0, y=43) + { id: 20 },

    // Pre-Generated Messaging
    withGrid(tableWithFooter(
      id=21,
      title='Pre-Generated Messaging',
      query='{ name =~ "value_capability:.*" && value.slack_message != "" && value.persona =~ "${persona:regex}" && value.type =~ "${value_type:regex}" && value.channel =~ "${channel:regex}" && skill.id =~ "${skill_id:regex}" } | select(capability.name, value.one_liner, value.slack_message, value.email_subject)',
      overrides=[
        {
          matcher: { id: 'byName', options: 'value.slack_message' },
          properties: [{ id: 'custom.width', value: 400 }],
        },
        {
          matcher: { id: 'byName', options: 'value.one_liner' },
          properties: [{ id: 'custom.width', value: 300 }],
        },
      ],
      transformations=[{
        id: 'organize',
        options: {
          renameByName: {
            'capability.name': 'Capability',
            'value.one_liner': 'One-Liner',
            'value.slack_message': 'Slack Message',
            'value.email_subject': 'Email Subject',
          },
        },
      }],
    ), h=8, w=24, x=0, y=44),

    // === Row: Creator Value (Audience of 1) ===
    withGrid(panels.row('Creator Value (Audience of 1)'), h=1, w=24, x=0, y=52) + { id: 22 },

    // Creator Value Breakdown
    withGrid(tableWithFooter(
      id=23,
      title='Creator Value Breakdown',
      query='{ name =~ "value_capability:.*" && (value.creator_direct != "" || value.creator_indirect != "" || value.creator_ripple != "") && value.type =~ "${value_type:regex}" && skill.id =~ "${skill_id:regex}" } | select(capability.name, value.creator_direct, value.creator_indirect, value.creator_ripple)',
      overrides=[
        {
          matcher: { id: 'byName', options: 'value.creator_direct' },
          properties: [
            { id: 'custom.displayMode', value: 'color-background-solid' },
            { id: 'color', value: { fixedColor: 'green', mode: 'fixed' } },
          ],
        },
        {
          matcher: { id: 'byName', options: 'value.creator_indirect' },
          properties: [
            { id: 'custom.displayMode', value: 'color-background-solid' },
            { id: 'color', value: { fixedColor: 'yellow', mode: 'fixed' } },
          ],
        },
        {
          matcher: { id: 'byName', options: 'value.creator_ripple' },
          properties: [
            { id: 'custom.displayMode', value: 'color-background-solid' },
            { id: 'color', value: { fixedColor: 'purple', mode: 'fixed' } },
          ],
        },
      ],
      transformations=[{
        id: 'organize',
        options: {
          renameByName: {
            'capability.name': 'Capability',
            'value.creator_direct': 'Direct Value',
            'value.creator_indirect': 'Indirect Value',
            'value.creator_ripple': 'Ripple Value',
          },
        },
      }],
    ), h=8, w=24, x=0, y=53),

    // === Row: Recent Activity ===
    withGrid(panels.row('Recent Activity'), h=1, w=24, x=0, y=61) + { id: 24 },

    // Value Capability Events (traces)
    withGrid({
      id: 25,
      title: 'Value Capability Events',
      type: 'traces',
      datasource: tempoDs,
      options: {
        dedupStrategy: 'none',
        enableInfiniteScrolling: false,
        enableLogDetails: true,
        prettifyLogMessage: false,
        showCommonLabels: false,
        showLabels: true,
        showTime: true,
        sortOrder: 'Descending',
        wrapLogMessage: true,
      },
      pluginVersion: '10.0.0',
      targets: [traceqlTarget('{ name =~ "value_.*" && value.persona =~ "${persona:regex}" && skill.id =~ "${skill_id:regex}" }')],
    }, h=8, w=24, x=0, y=62),
  ],
}
