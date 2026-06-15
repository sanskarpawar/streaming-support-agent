"""
HandoffPlugin — create_handoff_ticket

Mock implementation — simulates creating a human escalation ticket.
"""
from __future__ import annotations

import time
import uuid
from typing import Annotated

from semantic_kernel.functions import kernel_function

from app.core.logging import get_logger

logger = get_logger(__name__)


class HandoffPlugin:
    """SK plugin to simulate creating a human support escalation ticket."""

    def __init__(self, conversation_id: str = "") -> None:
        self._conversation_id = conversation_id

    @kernel_function(
        name="create_handoff_ticket",
        description=(
            "Create a human support escalation ticket when the customer requests a human agent "
            "or when the request involves sensitive account changes. "
            "Returns a ticket ID and estimated wait time."
        ),
    )
    def create_handoff_ticket(
        self,
        summary: Annotated[str, "Brief summary of the customer's issue"],
        reason: Annotated[str, "Reason for escalation (e.g. customer requested, sensitive request, etc.)"],
    ) -> str:
        """Simulate ticket creation and return a confirmation with ticket ID."""
        start = time.perf_counter()
        try:
            ticket_id = f"TICKET-{uuid.uuid4().hex[:8].upper()}"

            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.info(
                "tool_call",
                conversation_id=self._conversation_id,
                tool="create_handoff_ticket",
                status="ok",
                ticket_id=ticket_id,
                reason=reason,
                latency_ms=latency_ms,
            )

            return (
                f"Escalation ticket created successfully.\n"
                f"Ticket ID: {ticket_id}\n"
                f"Reason: {reason}\n"
                f"Summary: {summary}\n"
                f"A human support agent will contact you within 2-4 hours during business hours. "
                f"Please keep your ticket ID for reference."
            )

        except Exception as exc:
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.error(
                "tool_call_error",
                conversation_id=self._conversation_id,
                tool="create_handoff_ticket",
                status="error",
                error=str(exc),
                latency_ms=latency_ms,
            )
            return f"Error creating handoff ticket: {exc}"
