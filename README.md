# Streaming Support Agent

A production-grade multi-agent AI support assistant for a fictional streaming and rental platform.

## Stack

| Component | Technology |
|---|---|
| API framework | FastAPI |
| Agentic orchestration | **Semantic Kernel `HandoffOrchestration`** (mandatory) |
| LLM | OpenAI `gpt-4.1-mini` (configurable) |
| Database | PostgreSQL (Pagila sample DB) |
| ORM / Migrations | SQLAlchemy async + Alembic |
| Observability | Structlog + Langfuse (optional) |
| MCP server | `pagila-support-mcp` (3 DB-backed tools) |
| Testing | Pytest + pytest-asyncio |

---

## Quick Start

### 1. Prerequisites

- Python 3.12+
- PostgreSQL with the **Pagila** sample database restored

```bash
# Restore Pagila (download from https://github.com/devrimgunduz/pagila)
psql -U postgres -c "CREATE DATABASE pagila;"
psql -U postgres -d pagila -f pagila-schema.sql
psql -U postgres -d pagila -f pagila-data.sql
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env and set:
#   OPENAI_API_KEY=sk-...
#   DATABASE_URL=postgresql+asyncpg://postgres:<password>@localhost:5432/pagila
```

### 4. Run Migrations

```bash
alembic upgrade head
```

This applies three migrations:
- `001` — adds `streaming_available` to `film`, seeds 50 films as streaming-available
- `002` — creates `streaming_subscription` table, seeds 10 customer subscriptions
- `003` — creates `conversation_sessions` and `conversation_messages` tables

### 5. Start the API

```bash
uvicorn app.main:app --reload
```

API will be available at `http://localhost:8000`. Docs at `http://localhost:8000/docs`.

---

## API Usage

### POST /agent/respond

```bash
curl -X POST http://localhost:8000/agent/respond \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": 1,
    "conversation_id": "conv_001",
    "message": "Is Alien available for streaming?"
  }'
```

Response fields: `conversation_id`, `session_title`, `intent`, `selected_agent`, `answer`, `confidence`, `tools_used`, `citations`, `next_action`, `guardrail_result`

### POST /agent/respond/stream

SSE streaming endpoint — emits `agent_selected`, `answer_chunk`, `guardrail`, and `done` events.

### GET /agent/sessions/{conversation_id}

Returns session metadata and full message history.

---

## Agents

| Agent | Responsibility |
|---|---|
| TriageAgent | Routes requests via SK HandoffOrchestration (no regex, no custom routing) |
| CatalogAgent | Film catalog and streaming availability questions |
| SubscriptionAgent | Subscription status and renewal questions |
| RentalHistoryAgent | Recent rental history questions |
| KnowledgeAgent | General support KB questions (with source citations) |
| HumanHandoffAgent | Escalation to human support |
| GuardrailAgent | Final safety review (direct SK invocation, json_schema output) |

---

## MCP Server

Run the `pagila-support-mcp` local MCP server (senior-signal level):

```bash
python mcp/server.py
```

Exposes 3 DB-backed tools:
- `search_film_catalog`
- `get_customer_streaming_subscription`
- `get_customer_rental_history`

---

## Running Tests

```bash
pytest tests/ -v
```

## Running Evals

Start the API first, then:

```bash
python evals/run_evals.py --base-url http://localhost:8000 --verbose
```

Runs 12 eval cases covering all rubric scenarios and prints a pass/fail report.

---

## Observability

- **Structlog**: All tool calls and routing decisions logged as JSON to stdout
- **Langfuse**: Set `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` in `.env` to enable distributed tracing
- **Token logging**: Logged per request

---

## What Is Skipped

| Item | Status | Note |
|---|---|---|
| Docker Compose | Skipped | Local Postgres chosen; would be straightforward to add |
| LLM output repair | Skipped | Pydantic + one retry provides basic repair |
| Real payment integrations | N/A | Not required |
| Production-grade UI | N/A | Not required |
| Complex authentication | N/A | Not required |
| Full deployment pipeline | N/A | Not required |

---

## Mandatory Items — All Implemented

| Mandatory Item | Status |
|---|---|
| Semantic Kernel for agentic orchestration | Implemented — `HandoffOrchestration` |
| FastAPI with `POST /agent/respond` | Implemented |
| PostgreSQL / Pagila database | Implemented |
| Alembic migrations (3 migrations) | Implemented |
| At least 4 agents including triage + guardrail | Implemented (7 agents) |
| 2+ Postgres-backed tools | Implemented (3 tools) |
| Typed tool contracts | Implemented |
| MCP-ready tool metadata | Implemented + local MCP server |
| Guardrails + safety | Implemented |
| KnowledgeAgent with source references | Implemented |
| 10+ eval examples | Implemented (12 cases) |
| Structured logs | Implemented (structlog) |
| README + docs folder | Implemented |

---

## Project Structure

```
streaming-support-agent/
├── app/
│   ├── main.py               # FastAPI app
│   ├── api/routes.py         # API endpoints
│   ├── agents/               # All 7 SK ChatCompletionAgents + factory
│   ├── plugins/              # 5 @kernel_function SK plugins
│   ├── db/                   # SQLAlchemy models, session, history service
│   ├── schemas/response.py   # Pydantic request/response models
│   ├── orchestrator.py       # HandoffOrchestration pipeline
│   └── core/                 # Config, logging, Langfuse tracing
├── alembic/versions/         # 3 migrations
├── mcp/server.py             # pagila-support-mcp
├── kb/articles.json          # 8 mock support articles
├── evals/                    # 12 eval cases + runner
├── tests/                    # pytest suite (35+ tests)
└── docs/                     # design.md, implementation_plan.md, ai_usage.md
```
