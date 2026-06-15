"""
Orchestrator — run_turn()

Full pipeline for a single customer turn:
  1. Upsert conversation session in PostgreSQL
  2. Load message history → format as context string
  3. Run HandoffOrchestration (SK-native, no custom routing)
  4. Capture specialist answer + metadata via agent_response_callback
  5. Run GuardrailAgent (direct invoke, json_schema structured output)
  6. Persist user + assistant messages to PostgreSQL
  7. Generate session title on first turn (direct LLM call)
  8. Return structured AgentResponse
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

from semantic_kernel.agents import HandoffOrchestration
from semantic_kernel.agents.runtime import InProcessRuntime
from semantic_kernel.contents import ChatMessageContent

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.factory import build_agents
from app.agents.guardrail import run_guardrail
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.tracing import Tracer
from app.db.history import ChatHistoryService
from app.schemas.response import AgentResponse, GuardrailResult, TitleResult

logger = get_logger(__name__)


# ── Captured turn data ────────────────────────────────────────────────────────

@dataclass
class TurnCapture:
    """Collects data from agent_response_callback during HandoffOrchestration."""
    messages: list[ChatMessageContent] = field(default_factory=list)

    @property
    def specialist_answer(self) -> str:
        """Last non-triage agent message — the final specialist response."""
        for msg in reversed(self.messages):
            name = getattr(msg, "name", "") or ""
            if name and name != "TriageAgent":
                return msg.content or ""
        # Fallback: last message
        return self.messages[-1].content if self.messages else ""

    @property
    def selected_agent(self) -> str:
        for msg in reversed(self.messages):
            name = getattr(msg, "name", "") or ""
            if name and name != "TriageAgent":
                return name
        return "TriageAgent"

    @property
    def tools_used(self) -> list[str]:
        """Extract tool call names from captured messages (SK includes them in metadata)."""
        tools: list[str] = []
        seen: set[str] = set()
        for msg in self.messages:
            items = getattr(msg, "items", []) or []
            for item in items:
                fn_name = getattr(item, "name", None) or getattr(item, "function_name", None)
                if fn_name and fn_name not in seen and not fn_name.startswith("transfer_to"):
                    tools.append(fn_name)
                    seen.add(fn_name)
        return tools


# ── Title generation ──────────────────────────────────────────────────────────

async def _generate_title(first_message: str) -> str:
    """Single cheap LLM call to produce a 4-6 word conversation title."""
    from openai import AsyncOpenAI
    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    class _Title(TitleResult):
        pass

    response = await client.beta.chat.completions.parse(
        model=settings.openai_model,
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": (
                    "Generate a short 4-6 word title that captures the topic of this "
                    "customer support conversation. Return only the title text, no punctuation."
                ),
            },
            {"role": "user", "content": first_message},
        ],
        response_format=_Title,
    )
    parsed = response.choices[0].message.parsed
    return parsed.title if parsed else first_message[:50]


# ── Main entry point ──────────────────────────────────────────────────────────

async def run_turn(
    conversation_id: str,
    customer_id: int,
    message: str,
    db: AsyncSession,
) -> AgentResponse:
    start = time.perf_counter()
    svc = ChatHistoryService(db)
    tracer = Tracer(conversation_id=conversation_id, customer_id=customer_id, user_message=message)

    # 1. Upsert session
    await svc.upsert_session(conversation_id, customer_id)

    # 2. Load history → format context
    prior_messages = await svc.load_messages(conversation_id)
    is_first_turn = not any(m.role == "assistant" for m in prior_messages)
    context_str = svc.format_context(prior_messages)

    # Task string = history + current message
    task = f"{context_str}Customer (ID {customer_id}): {message}"

    # 3. Build agents + handoffs (per-request, with scoped DB session + conversation_id)
    agents, handoffs = build_agents(db=db, conversation_id=conversation_id)

    # 4. Collect messages via callback
    capture = TurnCapture()

    def agent_response_callback(msg: ChatMessageContent) -> None:
        capture.messages.append(msg)

    # 5. Run HandoffOrchestration
    runtime = InProcessRuntime()
    runtime.start()
    try:
        with tracer.span("handoff_orchestration", {"task_preview": task[:200]}):
            orchestration = HandoffOrchestration(
                members=agents,
                handoffs=handoffs,
                agent_response_callback=agent_response_callback,
            )
            result = await orchestration.invoke(task=task, runtime=runtime)
            await result.get(timeout=60)
    finally:
        await runtime.stop_when_idle()

    specialist_answer = capture.specialist_answer
    selected_agent = capture.selected_agent
    tools_used = capture.tools_used

    logger.info(
        "orchestration_complete",
        conversation_id=conversation_id,
        selected_agent=selected_agent,
        tools_used=tools_used,
        latency_ms=round((time.perf_counter() - start) * 1000, 2),
    )

    # 6. GuardrailAgent (direct SK invocation, json_schema structured output)
    with tracer.span("guardrail", {"selected_agent": selected_agent}):
        pass  # span wraps the call below
    guardrail_result: GuardrailResult = await run_guardrail(
        original_answer=specialist_answer,
        customer_message=message,
        conversation_id=conversation_id,
    )
    final_answer = guardrail_result.revised_answer

    # Derive intent from selected_agent name
    intent_map = {
        "CatalogAgent": "catalog_search",
        "SubscriptionAgent": "subscription_question",
        "RentalHistoryAgent": "rental_history",
        "KnowledgeAgent": "knowledge_question",
        "HumanHandoffAgent": "human_handoff",
        "TriageAgent": "triage_fallback",
    }
    intent = intent_map.get(selected_agent, "unknown")

    # next_action
    next_action = "human_handoff" if selected_agent == "HumanHandoffAgent" else "none"
    if guardrail_result.guardrail_triggered:
        next_action = "guardrail_review"

    # citations from KB tool results
    citations: list[str] = []
    if selected_agent == "KnowledgeAgent":
        for msg in capture.messages:
            content = msg.content or ""
            for line in content.splitlines():
                if line.strip().startswith("[Source:"):
                    citations.append(line.strip())

    # confidence: simple heuristic — 1.0 if not triage fallback, 0.5 if guardrail triggered
    confidence = 0.5 if guardrail_result.guardrail_triggered else (
        0.6 if selected_agent == "TriageAgent" else 0.9
    )

    # 7. Persist turn
    await svc.save_turn(
        conversation_id=conversation_id,
        user_content=message,
        assistant_content=final_answer,
        agent_used=selected_agent,
        intent=intent,
        tools_used=tools_used,
        metadata={
            "latency_ms": round((time.perf_counter() - start) * 1000, 2),
            "confidence": confidence,
            "guardrail_triggered": guardrail_result.guardrail_triggered,
            "tools_used": tools_used,
        },
    )

    # 8. Session title (first turn only)
    session_title: str | None = None
    if is_first_turn:
        try:
            session_title = await _generate_title(message)
            await svc.update_title(conversation_id, session_title)
        except Exception as exc:
            logger.warning("title_generation_failed", error=str(exc))
            session_title = None
    else:
        session = await svc.get_session(conversation_id)
        session_title = session.title if session else None

    # Escalated session status
    if selected_agent == "HumanHandoffAgent":
        await svc.update_status(conversation_id, "escalated")

    tracer.finish(final_answer)

    return AgentResponse(
        conversation_id=conversation_id,
        session_title=session_title,
        intent=intent,
        selected_agent=selected_agent,
        answer=final_answer,
        confidence=confidence,
        tools_used=tools_used,
        citations=citations,
        next_action=next_action,
        guardrail_result=guardrail_result,
    )
