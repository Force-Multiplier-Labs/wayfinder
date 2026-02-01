# Gap Analysis: interop.aos_compliance

OWASP Agent Observability Standard (AOS) Compliance

---

## Benefit Summary

- **Name**: OWASP AOS Standards Compliance
- **Value**: Users can integrate ContextCore with AOS-compliant agent tools so they get interoperability without custom adapters
- **Primary Personas**: ai_agent, operator, developer
- **Priority**: medium
- **Effort**: medium

---

## Current State

ContextCore has substantial overlap with AOS but uses different attribute names and event structures:

| AOS Event | ContextCore Equivalent | Gap |
|-----------|----------------------|-----|
| `steps/message` | Message handling in A2A | Attribute names differ |
| `steps/toolCallRequest` | `handoff.*` spans | Aligned via PRODUCER spans |
| `steps/toolCallResult` | `handoff.status` | Aligned |
| `steps/memoryStore` | `InsightEmitter` | Extended, not fully AOS-compliant |
| `steps/memoryContextRetrieval` | `InsightQuerier` | Extended, not fully AOS-compliant |
| `steps/agentTrigger` | Guidance system | Missing `trigger.type = "autonomous"` |
| Decision Events | `insight.type = "decision"` | No Allow/Deny/Modify enum |
| `protocols/A2A` | Full A2A stack | Aligned |
| `protocols/MCP` | Not implemented | **Major gap** |

### What Works Today

1. **A2A Protocol**: Full JSON-RPC 2.0 implementation in `src/contextcore/agent/a2a_*.py`
2. **Tool Calls**: Handoff system emits PRODUCER spans with tool attributes
3. **Memory**: Insight system stores/queries agent knowledge via OTel spans
4. **Knowledge**: Capability querier provides RAG-like queries

### What's Missing

1. **AOS Event Names**: Events don't use `steps/` or `protocols/` prefixes
2. **Message Attributes**: Missing `sender.role`, `reasoning`, `citations` in standard format
3. **Trigger Type**: No `trigger.type = "autonomous"` for webhook/scheduled triggers
4. **Decision Enum**: No structured Allow/Deny/Modify outcome
5. **MCP Telemetry**: No `protocols/MCP` events emitted

---

## Gap Description

To achieve AOS compliance, ContextCore needs to:

1. **Emit AOS-named events** alongside existing spans (dual-emit pattern)
2. **Add missing attributes** to existing event types
3. **Implement MCP telemetry** for tool/resource protocol events

This follows the same dual-emit strategy used for OTel GenAI migration.

---

## Technical Requirements

### Data Layer

- [x] Insight spans stored in Tempo (existing)
- [x] Handoff spans with tool attributes (existing)
- [ ] Add `steps/message` event emission
- [ ] Add `trigger.type` attribute to guidance spans
- [ ] Add `decision.outcome` enum to insight spans
- [ ] Add `decision.reason_code` structured attribute

**Schema Additions:**

```python
# New enum for decision outcomes
class DecisionOutcome(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    MODIFY = "modify"

# New attribute on insights
insight.decision.outcome: DecisionOutcome
insight.decision.reason_code: str  # e.g., "rate_limit_exceeded"
insight.decision.modified_request: dict  # For MODIFY outcomes

# New attribute on guidance
guidance.trigger.type: str  # "user" | "autonomous" | "webhook" | "scheduled"
```

**Storage:** Tempo (traces)

### Processing Layer

- [ ] Event name mapping: ContextCore events → AOS event names
- [ ] Attribute transformation for AOS compliance
- [ ] Validation against AOS schema

**Processing:** Real-time at emit time (no batch processing)

**Trigger:** On span/event creation

### Presentation Layer

- [ ] Dashboard panel showing AOS event compliance status
- [ ] CLI command to validate AOS compliance
- [ ] Export capability for AOS-formatted traces

**Interface:** Dashboard + CLI

**Grafana Panels:**
- AOS Event Type Distribution (pie chart)
- AOS Compliance Score (gauge)
- Missing Attributes by Event Type (table)

### Integration Layer

- [ ] MCP protocol telemetry emitter
- [ ] MCP tool call → capability invocation mapping
- [ ] MCP resource read → knowledge query mapping

**External Systems:**
- Model Context Protocol (Anthropic)
- Any AOS-compliant observability backend

---

## Dependencies

### Benefits
- `ai.memory_persistent` (delivered) — Insight system foundation
- `incident.context_instant` (delivered) — Alert enrichment patterns

### Capabilities
- `contextcore.insight.emit` (stable) — Base for decision events
- `contextcore.handoff.create` (stable) — Base for tool call events
- `contextcore.a2a.*` (stable) — A2A protocol already implemented

### Infrastructure
- Tempo for trace storage
- OTel SDK for span creation
- Existing dual-emit infrastructure from GenAI migration

---

## Risks

### Technical
- **Event volume increase**: Dual-emit pattern doubles event count
  - Mitigation: Make AOS events opt-in via config flag
- **Schema drift**: AOS spec may evolve
  - Mitigation: Version-pin AOS schema, track spec changes

### Adoption
- **Learning curve**: Teams must understand AOS event model
  - Mitigation: Documentation and examples
- **Tooling gaps**: Not all tools support AOS yet
  - Mitigation: Focus on Grafana/OTel ecosystem first

### Dependencies
- **MCP spec stability**: MCP is relatively new
  - Mitigation: Implement core events first, extend as spec stabilizes

---

## Effort Estimate

- **Size**: medium
- **Rationale**:
  - Phase 1 (AOS events): Small — attribute additions to existing emitters
  - Phase 2 (MCP telemetry): Medium — new emitter module required
  - Total: ~2-3 weeks development, 1 week testing

---

## Recommendation

**Priority**: Implement after `time.status_compilation_eliminated` (high priority gap)

**Sequencing**:

1. **Phase 1A** (small): Add `trigger.type` to guidance system
2. **Phase 1B** (small): Add `DecisionOutcome` enum to insights
3. **Phase 1C** (small): Emit `steps/message` events
4. **Phase 2** (medium): Implement MCP telemetry emitter

**Exit Criteria**:
- All AOS execution step events emittable
- Decision events include Allow/Deny/Modify outcome
- MCP tool calls emit `protocols/MCP` events
- Validation CLI confirms AOS compliance

---

## References

- [OWASP AOS Trace Events](https://aos.owasp.org/spec/trace/events/)
- [ContextCore Standards Alignment](../STANDARDS_ALIGNMENT.md)
- [OTel GenAI Migration Guide](../OTEL_GENAI_MIGRATION_GUIDE.md)
- [A2A Protocol](https://a2a-protocol.org)
- [Model Context Protocol](https://modelcontextprotocol.io/)

---

*Created: 2026-01-28*
