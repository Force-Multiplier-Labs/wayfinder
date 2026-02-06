// Service parameter schema with defaults for Online Boutique microservices.
// LLM drafters generate simple .libsonnet files using this schema.
// Factory functions (dashboard.libsonnet, alerts.libsonnet, etc.) consume these params.
{
  // Required fields (must be provided by drafter)
  name:: error 'name is required',

  // Service metadata with sensible defaults
  language:: 'unknown',
  description:: '',
  criticality:: 'medium',  // critical, high, medium, low
  businessValue:: 'internal',  // revenue-primary, revenue-secondary, internal, cost-center
  owner:: 'unknown',

  // Protocol and methods
  protocol:: 'grpc',  // grpc, http
  grpcMethods:: [],  // ['AddItem', 'GetCart', 'EmptyCart']
  httpEndpoints:: [],  // ['/api/products', '/api/cart']

  // SLO configuration
  slo:: {
    availability: 99.9,
    latencyP99: '500ms',
    errorBudget: 0.1,  // percent, derived from 100 - availability
    throughput: '100rps',
  },

  // Service dependencies (other service names)
  dependencies:: [],

  // Operational risks
  risks:: [],  // [{ priority: 'P1', description: '...' }]

  // Alert routing
  alertChannels:: [],  // ['pagerduty-p1', 'slack-incidents']

  // Kubernetes configuration
  k8s:: {
    port: 8080,
    cpuRequest: '100m',
    memoryRequest: '128Mi',
    cpuLimit: '200m',
    memoryLimit: '256Mi',
    probeType: 'grpc',  // grpc, http, exec
  },

  // Log field mappings (language-specific)
  logFields:: {
    level: 'level',
    message: 'msg',
    duration: 'duration_ms',
    durationUnit: 'ms',
  },
}
