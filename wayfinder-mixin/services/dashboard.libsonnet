// Dashboard factory: Takes service params, produces Grafana dashboard JSON.
// Uses lib/panels.libsonnet and lib/dashboards.libsonnet helpers.
local panels = import '../lib/panels.libsonnet';
local dashboards = import '../lib/dashboards.libsonnet';
local defaults = import './service_config.libsonnet';

// Factory function: takes service params, returns Grafana dashboard JSON
function(params)
  local s = defaults + params;

  // Determine metric prefix based on protocol
  local isGrpc = s.protocol == 'grpc';
  local metricPrefix = if isGrpc then 'grpc_server' else 'http_server';

  // Parse latency threshold for panels (e.g., "100ms" -> 0.1)
  local latencyStr = std.get(s.slo, 'latencyP99', '500ms');
  local latencyMs = std.parseInt(std.rstripChars(latencyStr, 'ms'));
  local latencySeconds = latencyMs / 1000;

  // Build service label matcher
  local serviceMatcher = if isGrpc
    then 'grpc_service=~".*%s.*"' % s.name
    else 'service="%s"' % s.name;

  // Build the dashboard
  local dashboard = dashboards.dashboard(
    title='%s Service Dashboard' % s.name,
    uid='%s-dashboard' % s.name,
    description='Operational dashboard for %s (%s, %s tier)' % [s.name, s.language, s.criticality],
    tags=['online-boutique', s.name, s.criticality],
  );

  // RED metrics row
  local redRow = panels.row('RED Metrics (Rate, Errors, Duration)', y=0);

  // Request Rate panel
  local requestRateExpr = if isGrpc
    then 'sum(rate(grpc_server_handled_total{%s}[5m]))' % serviceMatcher
    else 'sum(rate(http_server_requests_total{%s}[5m]))' % serviceMatcher;

  local requestRatePanel = panels.stat(
    title='Request Rate',
    expr=requestRateExpr,
    unit='reqps',
  ) + { gridPos: { h: 4, w: 6, x: 0, y: 1 } };

  // Error Rate panel
  local errorRateExpr = if isGrpc
    then |||
      sum(rate(grpc_server_handled_total{grpc_code!="OK",%s}[5m]))
      / sum(rate(grpc_server_handled_total{%s}[5m])) * 100
    ||| % [serviceMatcher, serviceMatcher]
    else |||
      sum(rate(http_server_requests_total{status=~"5..",%s}[5m]))
      / sum(rate(http_server_requests_total{%s}[5m])) * 100
    ||| % [serviceMatcher, serviceMatcher];

  local errorThreshold = 100 - std.get(s.slo, 'availability', 99.9);
  local errorRatePanel = panels.stat(
    title='Error Rate',
    expr=errorRateExpr,
    unit='percent',
    thresholds=[
      { color: 'green', value: null },
      { color: 'yellow', value: errorThreshold * 0.5 },
      { color: 'red', value: errorThreshold },
    ],
  ) + { gridPos: { h: 4, w: 6, x: 6, y: 1 } };

  // Latency P99 panel
  local latencyExpr = if isGrpc
    then |||
      histogram_quantile(0.99,
        sum(rate(grpc_server_handling_seconds_bucket{%s}[5m])) by (le)
      )
    ||| % serviceMatcher
    else |||
      histogram_quantile(0.99,
        sum(rate(http_server_request_duration_seconds_bucket{%s}[5m])) by (le)
      )
    ||| % serviceMatcher;

  local latencyPanel = panels.stat(
    title='Latency P99',
    expr=latencyExpr,
    unit='s',
    thresholds=[
      { color: 'green', value: null },
      { color: 'yellow', value: latencySeconds * 0.8 },
      { color: 'red', value: latencySeconds },
    ],
  ) + { gridPos: { h: 4, w: 6, x: 12, y: 1 } };

  // Availability panel
  local availabilityExpr = if isGrpc
    then |||
      (1 - (
        sum(rate(grpc_server_handled_total{grpc_code!="OK",%s}[5m]))
        / sum(rate(grpc_server_handled_total{%s}[5m]))
      )) * 100
    ||| % [serviceMatcher, serviceMatcher]
    else |||
      (1 - (
        sum(rate(http_server_requests_total{status=~"5..",%s}[5m]))
        / sum(rate(http_server_requests_total{%s}[5m]))
      )) * 100
    ||| % [serviceMatcher, serviceMatcher];

  local availTarget = std.get(s.slo, 'availability', 99.9);
  local availabilityPanel = panels.gauge(
    title='Availability',
    expr=availabilityExpr,
    unit='percent',
    min=95,
    max=100,
    thresholds=[
      { color: 'red', value: null },
      { color: 'yellow', value: availTarget - 0.5 },
      { color: 'green', value: availTarget },
    ],
  ) + { gridPos: { h: 4, w: 6, x: 18, y: 1 } };

  // Latency timeseries row
  local latencyRow = panels.row('Latency Distribution', y=5);

  local latencyTimeseriesExpr = if isGrpc
    then |||
      histogram_quantile({{quantile}},
        sum(rate(grpc_server_handling_seconds_bucket{%s}[5m])) by (le)
      )
    ||| % serviceMatcher
    else |||
      histogram_quantile({{quantile}},
        sum(rate(http_server_request_duration_seconds_bucket{%s}[5m])) by (le)
      )
    ||| % serviceMatcher;

  local p50Expr = std.strReplace(latencyTimeseriesExpr, '{{quantile}}', '0.50');
  local p95Expr = std.strReplace(latencyTimeseriesExpr, '{{quantile}}', '0.95');
  local p99Expr = std.strReplace(latencyTimeseriesExpr, '{{quantile}}', '0.99');

  local latencyTimeseries = panels.timeseries(
    title='Latency Percentiles',
    expr=p50Expr,
    unit='s',
    legendFormat='P50',
  ) + {
    targets+: [
      { expr: p95Expr, refId: 'B', legendFormat: 'P95' },
      { expr: p99Expr, refId: 'C', legendFormat: 'P99' },
    ],
    gridPos: { h: 8, w: 12, x: 0, y: 6 },
  };

  // Request rate timeseries
  local requestRateTimeseries = panels.timeseries(
    title='Request Rate Over Time',
    expr=requestRateExpr,
    unit='reqps',
    legendFormat='requests/s',
  ) + { gridPos: { h: 8, w: 12, x: 12, y: 6 } };

  // Resource saturation row
  local saturationRow = panels.row('Resource Saturation', y=14);

  local cpuExpr = 'sum(rate(container_cpu_usage_seconds_total{container="%s"}[5m])) * 100' % s.name;
  local cpuPanel = panels.timeseries(
    title='CPU Usage',
    expr=cpuExpr,
    unit='percent',
    legendFormat='CPU %',
  ) + { gridPos: { h: 8, w: 12, x: 0, y: 15 } };

  local memExpr = 'sum(container_memory_working_set_bytes{container="%s"}) / (1024*1024)' % s.name;
  local memPanel = panels.timeseries(
    title='Memory Usage',
    expr=memExpr,
    unit='decmbytes',
    legendFormat='Memory MB',
  ) + { gridPos: { h: 8, w: 12, x: 12, y: 15 } };

  // Error budget row (if SLO defined)
  local errorBudgetRow = panels.row('Error Budget', y=23);

  local errorBudgetExpr = |||
    (1 - (
      sum(rate(grpc_server_handled_total{grpc_code!="OK",%s}[30d]))
      / sum(rate(grpc_server_handled_total{%s}[30d]))
    )) * 100 - %s
  ||| % [serviceMatcher, serviceMatcher, availTarget];

  local errorBudgetPanel = panels.gauge(
    title='Error Budget Remaining',
    expr=errorBudgetExpr,
    unit='percent',
    min=-1,
    max=100 - availTarget,
    thresholds=[
      { color: 'red', value: null },
      { color: 'yellow', value: (100 - availTarget) * 0.25 },
      { color: 'green', value: (100 - availTarget) * 0.5 },
    ],
  ) + { gridPos: { h: 6, w: 8, x: 0, y: 24 } };

  // Dependencies row (if dependencies defined)
  local depsRow = if std.length(s.dependencies) > 0
    then panels.row('Dependency Health', y=30)
    else null;

  // Assemble all panels
  local allPanels = [
    redRow,
    requestRatePanel,
    errorRatePanel,
    latencyPanel,
    availabilityPanel,
    latencyRow,
    latencyTimeseries,
    requestRateTimeseries,
    saturationRow,
    cpuPanel,
    memPanel,
    errorBudgetRow,
    errorBudgetPanel,
  ] + (if depsRow != null then [depsRow] else []);

  // Return dashboard with panels
  dashboards.withPanels(dashboard, allPanels) + {
    // Add template variables
    templating: {
      list: [
        {
          name: 'datasource',
          label: 'Datasource',
          type: 'datasource',
          query: 'prometheus',
          current: { text: 'Mimir', value: 'mimir' },
        },
        {
          name: 'namespace',
          label: 'Namespace',
          type: 'query',
          datasource: { type: 'prometheus', uid: '${datasource}' },
          query: 'label_values(namespace)',
          current: { text: 'online-boutique', value: 'online-boutique' },
        },
      ],
    },
    // Override time range and refresh for service dashboards
    time: { from: 'now-1h', to: 'now' },
    refresh: '30s',
  }
