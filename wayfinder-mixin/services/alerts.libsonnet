// PrometheusRule factory: Takes service params, produces PrometheusRule YAML.
// Uses lib/alerts.libsonnet helpers.
local alerts = import '../lib/alerts.libsonnet';
local defaults = import './service_config.libsonnet';

// Factory function: takes service params, returns PrometheusRule object
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

  // Calculate error threshold from availability
  local availability = std.get(s.slo, 'availability', 99.9);
  local errorThreshold = (100 - availability) / 100;  // e.g., 99.9 -> 0.001

  // Severity based on criticality
  local severity = if s.criticality == 'critical' then 'critical'
    else if s.criticality == 'high' then 'warning'
    else 'info';

  // For duration based on criticality
  local forDuration = if s.criticality == 'critical' then '5m'
    else if s.criticality == 'high' then '10m'
    else '15m';

  // Latency P99 alert expression
  local latencyExpr = if isGrpc
    then |||
      histogram_quantile(0.99,
        sum(rate(grpc_server_handling_seconds_bucket{%s}[5m])) by (le)
      ) > %s
    ||| % [serviceMatcher, latencySeconds]
    else |||
      histogram_quantile(0.99,
        sum(rate(http_server_request_duration_seconds_bucket{%s}[5m])) by (le)
      ) > %s
    ||| % [serviceMatcher, latencySeconds];

  // Error rate alert expression
  local errorExpr = if isGrpc
    then |||
      sum(rate(grpc_server_handled_total{grpc_code!="OK",%s}[5m]))
      / sum(rate(grpc_server_handled_total{%s}[5m])) > %s
    ||| % [serviceMatcher, serviceMatcher, errorThreshold]
    else |||
      sum(rate(http_server_requests_total{status=~"5..",%s}[5m]))
      / sum(rate(http_server_requests_total{%s}[5m])) > %s
    ||| % [serviceMatcher, serviceMatcher, errorThreshold];

  // Capitalize first letter of service name for alert names
  local capitalizedName = std.asciiUpper(s.name[0]) + s.name[1:];

  // Build the PrometheusRule resource
  {
    apiVersion: 'monitoring.coreos.com/v1',
    kind: 'PrometheusRule',
    metadata: {
      name: '%s-rules' % s.name,
      namespace: 'online-boutique',
      labels: {
        app: s.name,
        tier: s.criticality,
        'prometheus': 'online-boutique',
      },
    },
    spec: {
      groups: [
        {
          name: '%s.slo.rules' % s.name,
          rules: [
            // Latency P99 alert
            alerts.mimirAlert(
              name='%sLatencyP99High' % capitalizedName,
              expr=latencyExpr,
              forDuration=forDuration,
              severity=severity,
              summary='%s P99 latency above SLO target (%s)' % [s.name, latencyStr],
              runbookUrl='https://runbooks.example.com/%s#latency' % s.name,
              description='The %s service P99 latency has exceeded the SLO target of %s for more than %s.' % [s.name, latencyStr, forDuration],
            ) + {
              labels+: {
                service: s.name,
                tier: s.criticality,
              },
            },

            // Error rate alert
            alerts.mimirAlert(
              name='%sErrorRateHigh' % capitalizedName,
              expr=errorExpr,
              forDuration=forDuration,
              severity=severity,
              summary='%s error rate above SLO target (%.2f%%)' % [s.name, errorThreshold * 100],
              runbookUrl='https://runbooks.example.com/%s#errors' % s.name,
              description='The %s service error rate has exceeded %.2f%% for more than %s.' % [s.name, errorThreshold * 100, forDuration],
            ) + {
              labels+: {
                service: s.name,
                tier: s.criticality,
              },
            },
          ],
        },
      ],
    },
  }
