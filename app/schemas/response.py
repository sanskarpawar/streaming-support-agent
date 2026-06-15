from __future__ import annotations
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


# ── Request ───────────────────────────────────────────────────────────────────

class AgentRequest(BaseModel):
    customer_id: int
    conversation_id: str
    message: str


# ── Structured LLM outputs (json_schema mode) ─────────────────────────────────

class GuardrailResult(BaseModel):
    safe: bool = Field(description="Whether the response is safe to return to the customer")
    guardrail_triggered: bool = Field(description="Whether any guardrail rule was triggered")
    issues: list[str] = Field(default_factory=list, description="List of identified issues")
    revised_answer: str = Field(description="The final answer — revised if issues were found, original otherwise")


class TitleResult(BaseModel):
    title: str = Field(description="A short 4-6 word title summarising the conversation topic")


# ── Agent response ────────────────────────────────────────────────────────────

class AgentResponse(BaseModel):
    conversation_id: str
    session_title: str | None = None
    intent: str
    selected_agent: str
    answer: str
    confidence: float = Field(ge=0.0, le=1.0)
    tools_used: list[str] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)
    next_action: str = "none"
    guardrail_result: GuardrailResult


# ── Session history (GET /agent/sessions/{id}) ────────────────────────────────

class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: str
    agent_used: str | None = None
    intent: str | None = None
    tools_used: list[str] | None = None
    metadata: dict[str, Any] | None = None
    created_at: datetime


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    customer_id: int
    title: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime
    messages: list[MessageOut] = Field(default_factory=list)


# ── Session management schemas ────────────────────────────────────────────────

class SessionSummary(BaseModel):
    """Lightweight session record returned by the list endpoint (no messages)."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    customer_id: int
    title: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime


class SessionCreate(BaseModel):
    """Request body for POST /agent/sessions."""
    customer_id: int
    title: str | None = None


class SessionPatch(BaseModel):
    """Request body for PATCH /agent/sessions/{id}. All fields are optional."""
    title: str | None = None
    status: str | None = None  # accepted values: "active" | "archived"
