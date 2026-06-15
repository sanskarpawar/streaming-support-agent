"""
FastAPI routes:
  POST /agent/respond                  — full structured JSON response
  POST /agent/respond/stream           — SSE streaming response
  GET  /agent/sessions                 — list sessions for a customer
  POST /agent/sessions                 — explicitly create a new session
  GET  /agent/sessions/{id}            — session metadata + full message history
  PATCH /agent/sessions/{id}           — update session title or status
  DELETE /agent/sessions/{id}          — archive (soft-delete) a session
"""
from __future__ import annotations

import json
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.db.history import ChatHistoryService
from app.db.session import get_db
from app.db.models import ConversationSession, ConversationMessage
from app.orchestrator import run_turn
from app.schemas.response import (
    AgentRequest,
    AgentResponse,
    MessageOut,
    SessionCreate,
    SessionOut,
    SessionPatch,
    SessionSummary,
)

router = APIRouter()


# ── POST /agent/respond ───────────────────────────────────────────────────────

@router.post("/agent/respond", response_model=AgentResponse)
async def agent_respond(
    request: AgentRequest,
    db: AsyncSession = Depends(get_db),
) -> AgentResponse:
    """
    Process a customer support message and return a structured JSON response.

    - Routes to the correct specialist agent via SK HandoffOrchestration
    - Runs a GuardrailAgent safety check on the final answer
    - Persists conversation history to PostgreSQL
    - Returns session_title (LLM-generated on first turn)
    """
    try:
        return await run_turn(
            conversation_id=request.conversation_id,
            customer_id=request.customer_id,
            message=request.message,
            db=db,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ── POST /agent/respond/stream ────────────────────────────────────────────────

@router.post("/agent/respond/stream")
async def agent_respond_stream(
    request: AgentRequest,
    db: AsyncSession = Depends(get_db),
) -> EventSourceResponse:
    """
    SSE streaming endpoint. Emits events as the orchestration progresses:
      - event: "agent_selected"   — which specialist was chosen
      - event: "answer_chunk"     — streamed answer tokens
      - event: "guardrail"        — guardrail result
      - event: "done"             — final complete AgentResponse JSON
    """
    async def event_stream() -> AsyncGenerator[dict, None]:
        try:
            # Run full turn (non-streaming internally; we emit the result as SSE events)
            response = await run_turn(
                conversation_id=request.conversation_id,
                customer_id=request.customer_id,
                message=request.message,
                db=db,
            )

            # Emit agent selection event
            yield {
                "event": "agent_selected",
                "data": json.dumps({
                    "selected_agent": response.selected_agent,
                    "intent": response.intent,
                }),
            }

            # Emit answer in chunks (simulate streaming over SSE)
            words = response.answer.split()
            chunk_size = 5
            for i in range(0, len(words), chunk_size):
                chunk = " ".join(words[i : i + chunk_size])
                yield {"event": "answer_chunk", "data": chunk}

            # Emit guardrail summary
            yield {
                "event": "guardrail",
                "data": json.dumps({
                    "safe": response.guardrail_result.safe,
                    "triggered": response.guardrail_result.guardrail_triggered,
                }),
            }

            # Final complete response
            yield {
                "event": "done",
                "data": response.model_dump_json(),
            }

        except Exception as exc:
            yield {"event": "error", "data": json.dumps({"detail": str(exc)})}

    return EventSourceResponse(event_stream())


# ── GET /agent/sessions ───────────────────────────────────────────────────────

@router.get("/agent/sessions", response_model=list[SessionSummary])
async def list_sessions(
    customer_id: int = Query(..., description="Filter sessions by customer ID"),
    include_archived: bool = Query(False, description="Include archived sessions"),
    db: AsyncSession = Depends(get_db),
) -> list[SessionSummary]:
    """List all sessions for a customer, newest first."""
    svc = ChatHistoryService(db)
    sessions = await svc.list_sessions(
        customer_id, exclude_archived=not include_archived
    )
    return [SessionSummary.model_validate(s) for s in sessions]


# ── POST /agent/sessions ──────────────────────────────────────────────────────

@router.post("/agent/sessions", response_model=SessionOut, status_code=201)
async def create_session(
    body: SessionCreate,
    db: AsyncSession = Depends(get_db),
) -> SessionOut:
    """Explicitly create a new session with a server-generated UUID."""
    svc = ChatHistoryService(db)
    session = await svc.create_session(body.customer_id, title=body.title)
    return SessionOut(
        id=session.id,
        customer_id=session.customer_id,
        title=session.title,
        status=session.status,
        created_at=session.created_at,
        updated_at=session.updated_at,
        messages=[],
    )


# ── GET /agent/sessions/{conversation_id} ─────────────────────────────────────

@router.get("/agent/sessions/{conversation_id}", response_model=SessionOut)
async def get_session(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
) -> SessionOut:
    """Return session metadata and full message history for a conversation."""
    result = await db.execute(
        select(ConversationSession)
        .options(selectinload(ConversationSession.messages))
        .where(ConversationSession.id == conversation_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionOut(
        id=session.id,
        customer_id=session.customer_id,
        title=session.title,
        status=session.status,
        created_at=session.created_at,
        updated_at=session.updated_at,
        messages=[
            MessageOut(
                id=m.id,
                role=m.role,
                content=m.content,
                agent_used=m.agent_used,
                intent=m.intent,
                tools_used=m.tools_used,
                metadata=m.metadata_,
                created_at=m.created_at,
            )
            for m in session.messages
        ],
    )


# ── PATCH /agent/sessions/{conversation_id} ────────────────────────────────────

@router.patch("/agent/sessions/{conversation_id}", response_model=SessionSummary)
async def patch_session(
    conversation_id: str,
    body: SessionPatch,
    db: AsyncSession = Depends(get_db),
) -> SessionSummary:
    """Update a session's title and/or status."""
    svc = ChatHistoryService(db)
    session = await svc.get_session(conversation_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if body.title is not None:
        await svc.update_title(conversation_id, body.title)
        session.title = body.title

    if body.status is not None:
        allowed = {"active", "archived"}
        if body.status not in allowed:
            raise HTTPException(
                status_code=422,
                detail=f"status must be one of {sorted(allowed)}",
            )
        await svc.update_status(conversation_id, body.status)
        session.status = body.status

    # Re-fetch to get updated timestamps
    updated = await svc.get_session(conversation_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionSummary.model_validate(updated)


# ── DELETE /agent/sessions/{conversation_id} ───────────────────────────────────

@router.delete("/agent/sessions/{conversation_id}")
async def delete_session(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Archive (soft-delete) a session. Returns 404 if not found."""
    svc = ChatHistoryService(db)
    found = await svc.archive_session(conversation_id)
    if not found:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"ok": True, "id": conversation_id}
