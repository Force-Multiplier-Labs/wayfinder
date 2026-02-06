// Loki recording rules factory: Takes service params, produces Loki RecordingRule YAML.
// Uses lib/rules.libsonnet helpers.
local rules = import '../lib/rules.libsonnet';
local defaults = import './service_config.libsonnet';

// Factory function: takes service params, returns Loki RecordingRule object
function(params)
  local s = defaults + params;

  // Get log field names (language-specific)
  local logFields = std.get(s, 'logFields', {
    level: 'level',
    message: 'msg',
    duration: 'duration_ms',
    durationUnit: 'ms',
  });

  // Duration divisor to convert to seconds
  local durationDivisor = if logFields.durationUnit == 'ms' then 1000
    else if logFields.durationUnit == 'us' then 1000000
    else if logFields.durationUnit == 'ns' then 1000000000
    else 1;  // assume seconds

  // Base log selector
  local logSelector = '{app="%s"}' % s.name;

  // Build the RecordingRule resource
  {
    apiVersion: 'loki.grafana.com/v1',
    kind: 'RecordingRule',
    metadata: {
      name: '%s-loki-rules' % s.name,
      namespace: 'online-boutique',
      labels: {
        app: s.name,
        tier: s.criticality,
      },
    },
    spec: {
      groups: [
        {
          name: '%s.log_metrics' % s.name,
          interval: '1m',
          rules: [
            // Error rate from logs
            rules.lokiRule(
              record='%s:log_errors:rate1m' % s.name,
              expr=|||
                sum(rate(%s |= "error" | json | %s="error" [1m]))
              ||| % [logSelector, logFields.level],
            ),

            // Request rate from logs
            rules.lokiRule(
              record='%s:log_requests:rate1m' % s.name,
              expr=|||
                sum(rate(%s | json [1m]))
              ||| % logSelector,
            ),

            // Average latency from logs (if duration field exists)
            rules.lokiRule(
              record='%s:log_latency_seconds:avg1m' % s.name,
              expr=|||
                avg(rate(%s | json | unwrap %s [1m])) / %s
              ||| % [logSelector, logFields.duration, durationDivisor],
            ),

            // Log volume (bytes per second)
            rules.lokiRule(
              record='%s:log_bytes:rate1m' % s.name,
              expr=|||
                sum(bytes_rate(%s [1m]))
              ||| % logSelector,
            ),

            // Error count by level
            rules.lokiRule(
              record='%s:log_level_error:count1m' % s.name,
              expr=|||
                count_over_time(%s | json | %s="error" [1m])
              ||| % [logSelector, logFields.level],
            ),

            // Warning count by level
            rules.lokiRule(
              record='%s:log_level_warn:count1m' % s.name,
              expr=|||
                count_over_time(%s | json | %s=~"warn|warning" [1m])
              ||| % [logSelector, logFields.level],
            ),

            // Info count by level
            rules.lokiRule(
              record='%s:log_level_info:count1m' % s.name,
              expr=|||
                count_over_time(%s | json | %s="info" [1m])
              ||| % [logSelector, logFields.level],
            ),
          ],
        },
      ],
    },
  }
