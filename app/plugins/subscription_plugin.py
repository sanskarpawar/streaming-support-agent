"""
SubscriptionPlugin — get_customer_streaming_subscription

Backed by PostgreSQL (streaming_subscription, customer tables).
"""
from __future__ import annotations

import time
from typing import Annotated

from semantic_kernel.functions import kernel_function
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models import Customer, StreamingSubscription

logger = get_logger(__name__)


class SubscriptionPlugin:
    """SK plugin to retrieve streaming subscription data for a customer."""

    def __init__(self, db: AsyncSession, conversation_id: str = "") -> None:
        self._db = db
        self._conversation_id = conversation_id

    @kernel_function(
        name="get_customer_streaming_subscription",
        description=(
            "Retrieve the streaming subscription status for a customer. "
            "Returns plan name, status (active/cancelled), renewal date, and auto-renew flag."
        ),
    )
    async def get_customer_streaming_subscription(
        self,
        customer_id: Annotated[int, "The numeric customer ID"],
    ) -> str:
        """Return streaming subscription info for the given customer_id."""
        start = time.perf_counter()
        try:
            stmt = (
                select(StreamingSubscription, Customer.first_name, Customer.last_name)
                .join(Customer, StreamingSubscription.customer_id == Customer.customer_id)
                .where(StreamingSubscription.customer_id == customer_id)
                .order_by(StreamingSubscription.id.desc())
                .limit(1)
            )
            result = await self._db.execute(stmt)
            row = result.first()

            latency_ms = round((time.perf_counter() - start) * 1000, 2)

            if not row:
                logger.info(
                    "tool_call",
                    conversation_id=self._conversation_id,
                    tool="get_customer_streaming_subscription",
                    status="ok_not_found",
                    latency_ms=latency_ms,
                )
                return (
                    f"No streaming subscription found for customer ID {customer_id}. "
                    "The customer may not have signed up for a streaming plan."
                )

            sub, first_name, last_name = row
            auto_renew = "Yes" if sub.auto_renew else "No"
            end_date = sub.end_date.strftime("%Y-%m-%d") if sub.end_date else "N/A"

            logger.info(
                "tool_call",
                conversation_id=self._conversation_id,
                tool="get_customer_streaming_subscription",
                status="ok",
                latency_ms=latency_ms,
            )
            return (
                f"Customer: {first_name} {last_name} (ID: {customer_id})\n"
                f"Plan: {sub.plan_name}\n"
                f"Status: {sub.status}\n"
                f"Renewal Date: {end_date}\n"
                f"Auto-Renew: {auto_renew}"
            )

        except Exception as exc:
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.error(
                "tool_call_error",
                conversation_id=self._conversation_id,
                tool="get_customer_streaming_subscription",
                status="error",
                error=str(exc),
                latency_ms=latency_ms,
            )
            return f"Error retrieving subscription: {exc}"
