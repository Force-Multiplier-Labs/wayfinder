// SLO factory: Takes service params, produces Sloth PrometheusServiceLevel YAML.
local defaults = import './service_config.libsonnet';

// Factory function: takes service params, returns PrometheusServiceLevel object
function(params)
  local s = defaults + params;

  // Determine metric prefix based on protocol
  local isGrpc = s.protocol == 'grpc';

  // Build service label matcher
  local serviceMatcher = if isGrpc
    then 'grpc_service=~".*%s.*"' % s.name
    else 'service="%s"' % s.name;

  // Parse latency threshold (e.g., "100ms" -> 0.1)
  local latencyStr = std.get(s.slo, 'latencyP99', '500ms');
  local latencyMs = std.parseInt(std.rstripChars(latencyStr, 'ms'));
  local latencySeconds = latencyMs / 1000;

  // Get availability target
  local availability = std.get(s.slo, 'availability', 99.9);

  // Error query for availability SLI
  local errorQuery = if isGrpc
    then |||
      sum(rate(grpc_server_handled_total{grpc_code!="OK",%s}[{{.window}}]))
    ||| % serviceMatcher
    else |||
      sum(rate(http_server_requests_total{status=~"5..",%s}[{{.window}}]))
    ||| % serviceMatcher;

  // Total query for availability SLI
  local totalQuery = if isGrpc
    then |||
      sum(rate(grpc_server_handled_total{%s}[{{.window}}]))
    ||| % serviceMatcher
    else |||
      sum(rate(http_server_requests_total{%s}[{{.window}}]))
    ||| % serviceMatcher;

  // Latency error query (requests exceeding threshold)
  local latencyErrorQuery = if isGrpc
    then |||
      sum(rate(grpc_server_handling_seconds_count{%s}[{{.window}}]))
      - sum(rate(grpc_server_handling_seconds_bucket{le="%s",%s}[{{.window}}]))
    ||| % [serviceMatcher, latencySeconds, serviceMatcher]
    else |||
      sum(rate(http_server_request_duration_seconds_count{%s}[{{.window}}]))
      - sum(rate(http_server_request_duration_seconds_bucket{le="%s",%s}[{{.window}}]))
    ||| % [serviceMatcher, latencySeconds, serviceMatcher];

  // Latency total query
  local latencyTotalQuery = if isGrpc
    then |||
      sum(rate(grpc_server_handling_seconds_count{%s}[{{.window}}]))
    ||| % serviceMatcher
    else |||
      sum(rate(http_server_request_duration_seconds_count{%s}[{{.window}}]))
    ||| % serviceMatcher;

  // Build the PrometheusServiceLevel resource
  {
    apiVersion: 'sloth.slok.dev/v1',
    kind: 'PrometheusServiceLevel',
    metadata: {
      name: '%s-slo' % s.name,
      namespace: 'online-boutique',
      labels: {
        app: s.name,
        team: s.owner,
        tier: s.criticality,
      },
    },
    spec: {
      service: s.name,
      labels: {
        team: s.owner,
        tier: s.criticality,
        env: 'production',
      },
      slos: [
        // Availability SLO
        {
          name: 'availability',
          objective: availability,
          description: '%s service availability - percentage of successful requests' % s.name,
          sli: {
            events: {
              errorQuery: errorQuery,
              totalQuery: totalQuery,
            },
          },
          alerting: {
            name: '%sAvailabilitySLO' % s.name,
            labels: {
              service: s.name,
              category: 'availability',
            },
            annotations: {
              runbook_url: 'https://runbooks.example.com/%s#availability' % s.name,
            },
            pageAlert: {
              labels: {
                severity: if s.criticality == 'critical' then 'critical' else 'warning',
              },
            },
            ticketAlert: {
              labels: {
                severity: 'info',
              },
            },
          },
        },
        // Latency SLO
        {
          name: 'latency',
          objective: 99.0,  // 99% of requests should be under latencyP99
          description: '%s service latency - percentage of requests under %s' % [s.name, latencyStr],
          sli: {
            events: {
              errorQuery: latencyErrorQuery,
              totalQuery: latencyTotalQuery,
            },
          },
          alerting: {
            name: '%sLatencySLO' % s.name,
            labels: {
              service: s.name,
              category: 'latency',
            },
            annotations: {
              runbook_url: 'https://runbooks.example.com/%s#latency' % s.name,
            },
            pageAlert: {
              labels: {
                severity: if s.criticality == 'critical' then 'critical' else 'warning',
              },
            },
            ticketAlert: {
              labels: {
                severity: 'info',
              },
            },
          },
        },
      ],
    },
  }
