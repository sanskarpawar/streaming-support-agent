"""
ChatHistoryService — PostgreSQL-backed conversation state.

Provides:
  - upsert_session()   : create or touch a conversation_sessions row
  - load_messages()    : load all messages ordered by created_at
  - format_context()   : render history as a plain text block for HandoffOrchestration
  - save_turn()        : persist user + assistant messages after a turn completes
  - get_session()      : fetch session row (for title / status reads)
  - update_title()     : store the LLM-generated session title
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ConversationMessage, ConversationSession


class ChatHistoryService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ── Session ──────────────────────────────────────────────────────────────

    async def upsert_session(self, conversation_id: str, customer_id: int) -> ConversationSession:
        stmt = pg_insert(ConversationSession).values(
            id=conversation_id,
            customer_id=customer_id,
            status="active",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ).on_conflict_do_update(
            index_elements=["id"],
            set_={"updated_at": datetime.now(timezone.utc)},
        ).returning(ConversationSession)

        result = await self._db.execute(stmt)
        await self._db.commit()
        return result.scalar_one()

    async def get_session(self, conversation_id: str) -> ConversationSession | None:
        result = await self._db.execute(
            select(ConversationSession).where(ConversationSession.id == conversation_id)
        )
        return result.scalar_one_or_none()

    async def update_title(self, conversation_id: str, title: str) -> None:
        await self._db.execute(
            update(ConversationSession)
            .where(ConversationSession.id == conversation_id)
            .values(title=title)
        )
        await self._db.commit()

    async def update_status(self, conversation_id: str, status: str) -> None:
        await self._db.execute(
            update(ConversationSession)
            .where(ConversationSession.id == conversation_id)
            .values(status=status)
        )
        await self._db.commit()

    # ── Messages ─────────────────────────────────────────────────────────────

    async def load_messages(self, conversation_id: str) -> list[ConversationMessage]:
        result = await self._db.execute(
            select(ConversationMessage)
            .where(ConversationMessage.conversation_id == conversation_id)
            .order_by(ConversationMessage.created_at)
        )
        return list(result.scalars().all())

    async def count_turns(self, conversation_id: str) -> int:
        """Return number of assistant turns (proxy for whether this is the first turn)."""
        messages = await self.load_messages(conversation_id)
        return sum(1 for m in messages if m.role == "assistant")

    async def save_turn(
        self,
        conversation_id: str,
        user_content: str,
        assistant_content: str,
        agent_used: str,
        intent: str,
        tools_used: list[str],
        metadata: dict[str, Any],
    ) -> None:
        now = datetime.now(timezone.utc)
        self._db.add_all([
            ConversationMessage(
                conversation_id=conversation_id,
                role="user",
                content=user_content,
                created_at=now,
            ),
            ConversationMessage(
                conversation_id=conversation_id,
                role="assistant",
                content=assistant_content,
                agent_used=agent_used,
                intent=intent,
                tools_used=tools_used,
                metadata_=metadata,
                created_at=now,
            ),
        ])
        await self._db.commit()

    # ── Context formatting ────────────────────────────────────────────────────

    def format_context(self, messages: list[ConversationMessage]) -> str:
        """Render conversation history as a readable block for the orchestration task string."""
        if not messages:
            return ""
        lines = ["=== Conversation History ==="]
        for msg in messages:
            prefix = "Customer" if msg.role == "user" else "Assistant"
            lines.append(f"{prefix}: {msg.content}")
        lines.append("=== End of History ===\n")
        return "\n".join(lines)
