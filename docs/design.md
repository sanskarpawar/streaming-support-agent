# Architecture Design — Streaming Support Agent

## Overview

A multi-agent AI support assistant for a fictional streaming and rental platform. The system routes customer requests to specialist agents using **Semantic Kernel's `HandoffOrchestration`**, the SK-native pattern for customer support triage.

---

## Architecture Diagram

```
POST /agent/respond
        │
        ▼
┌─────────────────────┐
│  FastAPI Route      │
│  (routes.py)        │
└────────┬────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│  Orchestrator (orchestrator.py)                     │
│                                                     │
│  1. Upsert conversation_sessions (PostgreSQL)       │
│  2. Load conversation_messages → format context     │
│  3. Build agents + OrchestrationHandoffs            │
│  4. InProcessRuntime.start()                        │
│  5. HandoffOrchestration.invoke(task)               │
│     ┌─────────────────────────────────────────┐    │
│     │ TriageAgent (ChatCompletionAgent)        │    │
│     │   → LLM calls transfer_to_X() fn        │    │
│     │     ↓                                   │    │
│     │  CatalogAgent      [CatalogPlugin]       │    │
│     │  SubscriptionAgent [SubscriptionPlugin]  │    │
│     │  RentalHistoryAgent[RentalPlugin]        │    │
│     │  KnowledgeAgent    [KBPlugin]            │    │
│     │  HumanHandoffAgent [HandoffPlugin]       │    │
│     └─────────────────────────────────────────┘    │
│  6. agent_response_callback → captures answer      │
│  7. runtime.stop_when_idle()                        │
│  8. GuardrailAgent.invoke() [direct, json_schema]  │
│  9. save_turn() → conversation_messages            │
│  10. update_title() if first turn                  │
└─────────────────────────────────────────────────────┘
         │
         ▼
  AgentResponse (Pydantic)
```

---

## Agents

| Agent | Role | Tools |
|---|---|---|
| TriageAgent | Entry point; routes via SK HandoffOrchestration | None (routing is done by SK function calls) |
| CatalogAgent | Film catalog and streaming availability | `search_film_catalog` |
| SubscriptionAgent | Streaming subscription status and renewal | `get_customer_streaming_subscription` |
| RentalHistoryAgent | Recent rental history | `get_customer_rental_history` |
| KnowledgeAgent | General support KB questions | `search_kb` |
| HumanHandoffAgent | Escalation to human support | `create_handoff_ticket` |
| GuardrailAgent | Final safety review (direct invocation) | None |

---

## Routing

**No custom routing code.** Routing is 100% handled by SK's `HandoffOrchestration`:
- SK automatically injects `transfer_to_<AgentName>(reason)` as OpenAI function calls into the TriageAgent's tool list.
- The LLM decides which specialist to call based on the user's message and the natural-language descriptions in `OrchestrationHandoffs`.
- Specialists can also bounce back to TriageAgent if the question is out of their domain.

---

## Tool Contracts

All tools are decorated with `@kernel_function` and have:
- **Typed inputs** via Python type annotations + `Annotated[T, "description"]`
- **Typed outputs** (string — SK tool calling protocol)
- **Structured error handling** — exceptions return `"Error: ..."` strings, never raise through the agent
- **Structured logging** on every call: `{conversation_id, tool_name, status, latency_ms, error}`

### MCP Readiness

Every tool has MCP-ready metadata exposed via `pagila-support-mcp` (`mcp/server.py`):
- `name`, `description`, `inputSchema` (JSON Schema), output as `TextContent`
- Error behavior: graceful string return
- Auth requirement: none (local DB credentials via env)
- Ownership boundary: `pagila-support-mcp` server

---

## Database Access

| Table | Source | Notes |
|---|---|---|
| `film` | Pagila | + `streaming_available` column (migration 001) |
| `film_category`, `category` | Pagila | Used for category join |
| `customer` | Pagila | Customer context |
| `inventory`, `rental` | Pagila | Used for rental history |
| `streaming_subscription` | Migration 002 | Platform-added subscription table |
| `conversation_sessions` | Migration 003 | One row per conversation |
| `conversation_messages` | Migration 003 | Full message history, persisted per turn |

All DB access is via **SQLAlchemy async** with `asyncpg`. No raw SQL strings in ORM queries; only raw SQL in Alembic seed scripts and MCP server (asyncpg directly).

---

## Guardrails

GuardrailAgent checks every response against:
1. System prompt / internal instruction leakage
2. Sensitive account mutations performed directly by the agent
3. Cross-customer data exposure
4. Unsupported claims not backed by tool results
5. Prompt injection attempts
6. Customer-unfriendly language / stack traces

Uses `response_format=GuardrailResult` → OpenAI `json_schema` structured output (enforced schema).

---

## Chat History

- **Source of truth**: PostgreSQL (`conversation_sessions` + `conversation_messages`)
- **L1 cache**: In-process dict for the current server lifetime
- History is loaded per request, formatted as a context string, and included in the `task` passed to `HandoffOrchestration`
- Session title: one LLM call on the first turn, stored in `conversation_sessions.title`, returned in every `AgentResponse`

---

## Observability

- **Structlog**: JSON logs on every tool call, agent routing result, and error
- **Langfuse**: Optional distributed tracing — traces per request, spans per orchestration step and guardrail
- **Token logging**: logged per request via `Tracer.log_token_usage()`

---

## Trade-offs and Limitations

| Area | Decision | Trade-off |
|---|---|---|
| SK HandoffOrchestration | Experimental SK API | No regex routing, fully LLM-driven, but API may change |
| InProcessRuntime | One runtime per request | Simple; Redis/distributed runtime for production |
| In-process L1 cache | Dict in memory | Lost on restart; Redis would fix this |
| KBPlugin | Simple keyword scoring | No vector search; good enough for 8 articles |
| Confidence score | Heuristic | Not a calibrated probability; replaced by classifier in production |
| Docker Compose | Not included | Local Postgres chosen; Docker Compose would be trivial to add |
