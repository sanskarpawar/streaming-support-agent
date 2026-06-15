# Streaming Support Agent

A multi-agent AI support assistant for a fictional streaming and rental platform, built with **Semantic Kernel `HandoffOrchestration`**, FastAPI, PostgreSQL, and a React + Tailwind CSS frontend.

---

## Architecture

The system routes every customer message through a triage agent that hands off to the correct specialist using Semantic Kernel's native `HandoffOrchestration` 

![Architecture Diagram](docs/Arch_Diag_Mermaid.png)


---

## UI Preview

**Default chat view** — session sidebar with conversation history, quick-start chips, and health indicator:

![Chat Default Page](docs/Chat_Default_Page.png)

**Active conversation** — streaming responses from the correct specialist agent with tool badges:

![Chat Page](docs/Chat_Page.png)

**Langfuse tracing dashboard** — every agent turn traced with spans, tool calls, and guardrail results:

![Langfuse Dashboard](docs/LangFuse_DashBoard.png)

---

## Stack

| Component | Technology |
|---|---|
| API framework | FastAPI |
| Agentic orchestration | **Semantic Kernel `HandoffOrchestration`** (mandatory) |
| LLM | OpenAI `gpt-4.1-mini` (configurable) |
| Database | PostgreSQL (Pagila sample DB) |
| ORM / Migrations | SQLAlchemy async + Alembic |
| Package manager | **uv** |
| Observability | Structlog + Langfuse (optional) |
| MCP server | `pagila-support-mcp` (3 DB-backed tools) |
| Testing | Pytest + pytest-asyncio |

---

## Quick Start

### 1. Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) — install once with:
  ```bash
  # Windows (PowerShell)
  irm https://astral.sh/uv/install.ps1 | iex

  # macOS / Linux
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- PostgreSQL with the **Pagila** sample database restored

```bash
# Restore Pagila (download from https://github.com/devrimgunduz/pagila)
psql -U postgres -c "CREATE DATABASE pagila;"
psql -U postgres -d pagila -f pagila-schema.sql
psql -U postgres -d pagila -f pagila-data.sql
```

### 2. Install Dependencies

```bash
uv sync
```

This creates a `.venv` in the project root and installs all dependencies (including dev) from `pyproject.toml` and the pinned `uv.lock`.

### 3. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and fill in the required values:

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | Yes (or Azure) | OpenAI API key — if blank, falls back to Azure OpenAI |
| `DATABASE_URL` | Yes | PostgreSQL connection string, e.g. `postgresql+asyncpg://postgres:admin@localhost:5432/pagila` |
| `AZURE_OPENAI_ENDPOINT` | If no OpenAI key | Azure OpenAI endpoint URL |
| `AZURE_OPENAI_API_VERSION` | If no OpenAI key | e.g. `2024-02-01` |
| `AZURE_OPENAI_CHAT_MODEL` | If no OpenAI key | Deployment name, e.g. `gpt-4.1` |
| `APIM_BASE_URL` | Optional | Azure API Management proxy URL (overrides endpoint if set) |
| `LANGFUSE_PUBLIC_KEY` | Optional | Langfuse public key (`pk-lf-...`) — leave blank to disable tracing |
| `LANGFUSE_SECRET_KEY` | Optional | Langfuse secret key (`sk-lf-...`) |
| `LANGFUSE_BASE_URL` | Optional | Langfuse host — EU: `https://cloud.langfuse.com`, US: `https://us.cloud.langfuse.com` |

**Langfuse** is an open-source LLM observability platform. When configured, every agent turn is traced (intent, agent selected, tools used, guardrail result, latency). To get keys:
1. Sign up at [langfuse.com](https://langfuse.com) (free tier available)
2. Create a project → copy the **Public Key** and **Secret Key**
3. Set `LANGFUSE_BASE_URL` to match your account region (`us.cloud.langfuse.com` for US)

### 4. Run Migrations

```bash
uv run alembic upgrade head
```

This applies three migrations:
- `001` — adds `streaming_available` to `film`, seeds 50 films as streaming-available
- `002` — creates `streaming_subscription` table, seeds 10 customer subscriptions
- `003` — creates `conversation_sessions` and `conversation_messages` tables

### 5. Start the API

```bash
uv run uvicorn app.main:app --reload
```

API will be available at `http://localhost:8000`. Docs at `http://localhost:8000/docs`.

### 6. Start the Frontend (optional)

In a separate terminal:

```bash
cd frontend
npm install       # first time only
npm run dev
```

UI will be available at `http://localhost:5173`. The Vite dev server proxies all `/agent` and `/health` requests to the FastAPI backend on port 8000 automatically — no extra configuration needed.

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

## Session Management API

Full CRUD control over conversation sessions.

### GET /agent/sessions — List sessions for a customer

```bash
curl "http://localhost:8000/agent/sessions?customer_id=1"
# Add &include_archived=true to include archived sessions
```

Response: array of `SessionSummary` objects (no messages), newest first.

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "customer_id": 1,
    "title": "Streaming availability question",
    "status": "active",
    "created_at": "2026-06-15T10:00:00",
    "updated_at": "2026-06-15T10:05:00"
  }
]
```

### POST /agent/sessions — Create a new session

```bash
curl -X POST http://localhost:8000/agent/sessions \
  -H "Content-Type: application/json" \
  -d '{"customer_id": 1, "title": "My support request"}'
```

Returns a `SessionOut` (with server-generated UUID) and HTTP 201.

### PATCH /agent/sessions/{id} — Rename or change status

```bash
curl -X PATCH http://localhost:8000/agent/sessions/<id> \
  -H "Content-Type: application/json" \
  -d '{"title": "Updated title"}'
```

Both `title` and `status` are optional. `status` accepts `"active"` or `"archived"`.

### DELETE /agent/sessions/{id} — Archive (soft-delete) a session

```bash
curl -X DELETE http://localhost:8000/agent/sessions/<id>
```

Sets `status = "archived"`. The session is hidden from the default list but is not permanently deleted. Returns `{"ok": true, "id": "<id>"}` or 404 if not found.

---

## Frontend

A React + Vite + Tailwind CSS chat UI lives in `frontend/`.

```bash
cd frontend
npm install
npm run dev   # http://localhost:5173
```

The Vite dev server proxies `/agent` and `/health` to the FastAPI backend on port 8000 — no CORS configuration needed.

**Features:**
- Session sidebar (left panel) — lists all sessions for the active customer, newest first
- Click a session to switch conversations and load history
- Double-click a session title to rename it inline (PATCH)
- Hover a session to reveal a delete button (archives via DELETE)
- "New conversation" button creates a session via POST before the first message
- Streaming responses via SSE with real-time typing indicator
- Session titles appear in the header after the first AI response
- Health indicator dot — polls `GET /health` every 30 seconds

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
uv run python mcp/server.py
```

Exposes 3 DB-backed tools:
- `search_film_catalog`
- `get_customer_streaming_subscription`
- `get_customer_rental_history`

---

## Running Tests

```bash
uv run pytest tests/ -v
```

## Running Evals

Start the API first, then:

```bash
uv run python evals/run_evals.py --base-url http://localhost:8000 --verbose
```

Runs 12 eval cases covering all rubric scenarios and saves timestamped JSON + Markdown reports to `evals/reports/`.

### Known Limitation — Non-deterministic LLM Output

The eval runner checks agent routing, tool usage, and safety behaviors (all deterministic) but also does **keyword matching** against the LLM-generated answer (`must_include` / `must_not_include` terms in `eval_cases.json`).

**LLM output is non-deterministic.** The same prompt may produce subtly different phrasing on different runs — e.g., "you do not have an active subscription" vs. "no subscription was found on your account". Both are correct answers but only one may contain the keyword the eval expects.

As a result:
- Structural checks (agent selection, tool invocation, guardrail triggering, safety escalation) are reliable and repeatable.
- Keyword checks on generated text **may occasionally fail or pass differently across runs** — this is expected behavior, not a code defect.
- If a keyword check fails but the agent, tools, and safety behavior are all correct, the eval is functionally passing.

For production-grade eval reliability, replace keyword matching with an LLM-as-judge scoring model or a semantic similarity threshold.

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
├── frontend/                 # React + Vite + Tailwind CSS chat UI
├── mcp/server.py             # pagila-support-mcp
├── kb/articles.json          # 8 mock support articles
├── evals/                    # 12 eval cases + runner
├── tests/                    # pytest suite (35+ tests)
└── docs/
    ├── Arch_Diag_Mermaid.png           # Architecture diagram (shown above)
    ├── Chat_Default_Page.png           # UI screenshot — default state
    ├── Chat_Page.png                   # UI screenshot — active conversation
    ├── LangFuse_DashBoard.png          # Langfuse tracing dashboard screenshot
    ├── design.md                       # Architecture & design decisions
    ├── implementation_plan.md          # Original implementation plan
    ├── ai_usage.md                     # AI tool usage log
    ├── cursor_chats_1_thread.md        # Cursor chat — initial project planning & build
    └── cursor_chat_2_thread.md         # Cursor chat — DB setup, evals, UI, session mgmt
```

---

## Development Journal

The `docs/` folder includes exported Cursor AI chat transcripts that document how this project was built:

| File | What it covers |
|---|---|
| [`docs/cursor_chats_1_thread.md`](docs/cursor_chats_1_thread.md) | Initial project planning — requirements analysis, architectural decisions (SK `HandoffOrchestration`, DB-backed history, structured JSON outputs, session titles), and full implementation of all 7 agents, plugins, migrations, evals, and tests |
| [`docs/cursor_chat_2_thread.md`](docs/cursor_chat_2_thread.md) | DB setup, `uv` migration, MCP server, Azure OpenAI / APIM fallback, Langfuse v4 integration, eval debugging, React UI construction, and session management CRUD endpoints |
| [`docs/Initial_plan_multi-agent_ai_support_75ca371f.plan.md`](docs/Initial_plan_multi-agent_ai_support_75ca371f.plan.md) | The formal implementation plan agreed upon before coding began |
