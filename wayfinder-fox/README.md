# wayfinder-fox

**Fox (Waagosh)** - Context enrichment for alert automation.

Fox enriches alerts with ProjectContext business metadata (criticality, owner, SLOs) and routes them by criticality to appropriate actions.

## Architecture

```
Alert (from Rabbit) → Fox Enricher → CriticalityRouter → Actions
                         │                                    │
                    ProjectContext                     claude_analysis
                    (K8s CRD or YAML)                 context_notify
                                                      log
```

## Span Contract

Fox emits spans matching the Fox Alert Automation dashboard:

| Span Name | Attributes |
|-----------|-----------|
| `fox.alert.received` | `alert.name`, `alert.criticality`, `alert.source` |
| `fox.context.enrich` | `alert.name`, `project.id`, `alert.criticality`, `business.owner` |
| `fox.action.*` | `alert.name`, `project.id`, `action.name` |

## Installation

```bash
pip install wayfinder-fox

# With Kubernetes support
pip install "wayfinder-fox[kubernetes]"

# Development
pip install -e ".[dev]"
```

## Usage

```python
from wayfinder_fox import ProjectContextEnricher, CriticalityRouter, FoxTracer
from wayfinder_fox.kubernetes import ProjectContextReader
from wayfinder_fox.enricher import Alert

tracer = FoxTracer()
reader = ProjectContextReader(yaml_path=".contextcore.yaml")
enricher = ProjectContextEnricher(reader=reader, tracer=tracer)
router = CriticalityRouter(tracer=tracer)

alert = Alert(name="HighErrorRate", labels={"project_id": "checkout"})
enriched = enricher.enrich(alert)
actions = router.dispatch(enriched)
```

## Testing

```bash
cd wayfinder-fox
python3 -m pytest tests/ -v
```
