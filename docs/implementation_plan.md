# Implementation Plan

## Phases

### Phase 1 — Foundation
- [x] Project scaffold: `app/`, `alembic/`, `tests/`, `docs/`, `mcp/`, `kb/`, `evals/`
- [x] `requirements.txt`, `.env.example`, `alembic.ini`
- [x] `app/core/config.py` — Pydantic Settings
- [x] `app/core/logging.py` — structlog
- [x] `app/db/session.py` — SQLAlchemy async engine
- [x] `app/db/models.py` — ORM models

### Phase 2 — Database Migrations
- [x] Migration 001: `film.streaming_available` column + seed 50 films as streaming-available
- [x] Migration 002: `streaming_subscription` table + seed 10 customer rows
- [x] Migration 003: `conversation_sessions` + `conversation_messages` tables

### Phase 3 — Plugins / Tools
- [x] `CatalogPlugin.search_film_catalog` — Postgres
- [x] `SubscriptionPlugin.get_customer_streaming_subscription` — Postgres
- [x] `RentalPlugin.get_customer_rental_history` — Postgres
- [x] `KBPlugin.search_kb` — local JSON KB (8 articles)
- [x] `HandoffPlugin.create_handoff_ticket` — mock

All tools: typed inputs/outputs, structured logging, graceful error handling.

### Phase 4 — Agents
- [x] TriageAgent — entry point for HandoffOrchestration
- [x] CatalogAgent — with CatalogPlugin
- [x] SubscriptionAgent — with SubscriptionPlugin
- [x] RentalHistoryAgent — with RentalPlugin
- [x] KnowledgeAgent — with KBPlugin
- [x] HumanHandoffAgent — with HandoffPlugin
- [x] GuardrailAgent — direct invocation, `response_format=GuardrailResult`
- [x] `agents/factory.py` — `build_agents()` + `OrchestrationHandoffs`

### Phase 5 — Orchestrator + API
- [x] `app/orchestrator.py` — `run_turn()` full pipeline
- [x] `app/main.py` — FastAPI app with lifespan
- [x] `app/api/routes.py`:
  - `POST /agent/respond` — structured JSON
  - `POST /agent/respond/stream` — SSE streaming
  - `GET /agent/sessions/{id}` — history + metadata

### Phase 6 — MCP Server
- [x] `mcp/server.py` — `pagila-support-mcp`
- [x] Exposes: `search_film_catalog`, `get_customer_streaming_subscription`, `get_customer_rental_history`
- [x] Full MCP metadata: name, description, inputSchema, outputSchema

### Phase 7 — Evals + Tests
- [x] `evals/eval_cases.json` — 12 cases covering all rubric scenarios
- [x] `evals/run_evals.py` — async eval runner with pass/fail report
- [x] `tests/test_tools.py` — 16 tool unit tests with mocked DB
- [x] `tests/test_agents.py` — 9 agent factory + schema tests
- [x] `tests/test_guardrails.py` — 10 guardrail + safety tests

### Phase 8 — Observability
- [x] `app/core/tracing.py` — Langfuse Tracer (no-op if keys not set)
- [x] Integrated into `orchestrator.py`
- [x] Token/cost logging per request

### Phase 9 — Docs + README
- [x] `docs/design.md`
- [x] `docs/implementation_plan.md`
- [x] `docs/ai_usage.md`
- [x] `README.md` — setup guide, skipped items table

---

## Assumptions

1. Pagila database is already restored into a local PostgreSQL instance before migrations run.
2. `OPENAI_API_KEY` is set in `.env` — the key from the assignment is not committed.
3. Langfuse is optional — the app runs fully without it.
4. `semantic-kernel` v1.17.1 is used (latest stable with HandoffOrchestration).

---

## Testing Approach

- **Unit tests**: All plugin functions tested with mocked DB sessions (no real Postgres required).
- **Schema tests**: AgentResponse, GuardrailResult Pydantic models validated for structure.
- **Guardrail tests**: Safety rules verified as unit logic + mocked LLM response checks.
- **Eval runner**: Integration tests against the live `/agent/respond` endpoint (requires running server + DB).

---

## Known Limitations

| Limitation | Impact | Mitigation |
|---|---|---|
| HandoffOrchestration is experimental | API may change | Pinned `semantic-kernel==1.17.1` |
| KBPlugin uses keyword scoring | Imprecise matching | Sufficient for 8-article KB; replace with embeddings for production |
| Confidence score is heuristic | Not calibrated | Replace with a classifier model in production |
| InProcessRuntime per request | Not horizontally scalable | Use a distributed runtime for production |
| No Docker Compose | Manual Postgres setup required | Docker Compose would be straightforward to add |
