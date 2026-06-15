"""
RentalPlugin — get_customer_rental_history

Backed by PostgreSQL (rental, inventory, film, customer tables).
"""
from __future__ import annotations

import time
from typing import Annotated

from semantic_kernel.functions import kernel_function
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models import Customer, Film, Inventory, Rental

logger = get_logger(__name__)


class RentalPlugin:
    """SK plugin to retrieve rental history for a customer."""

    def __init__(self, db: AsyncSession, conversation_id: str = "") -> None:
        self._db = db
        self._conversation_id = conversation_id

    @kernel_function(
        name="get_customer_rental_history",
        description=(
            "Retrieve the recent rental history for a customer. "
            "Returns film titles, rental dates, and return dates for the last 10 rentals."
        ),
    )
    async def get_customer_rental_history(
        self,
        customer_id: Annotated[int, "The numeric customer ID"],
    ) -> str:
        """Return the last 10 rentals for the given customer_id."""
        start = time.perf_counter()
        try:
            stmt = (
                select(
                    Rental.rental_id,
                    Rental.rental_date,
                    Rental.return_date,
                    Film.title,
                    Customer.first_name,
                    Customer.last_name,
                )
                .join(Inventory, Rental.inventory_id == Inventory.inventory_id)
                .join(Film, Inventory.film_id == Film.film_id)
                .join(Customer, Rental.customer_id == Customer.customer_id)
                .where(Rental.customer_id == customer_id)
                .order_by(desc(Rental.rental_date))
                .limit(10)
            )
            result = await self._db.execute(stmt)
            rows = result.fetchall()

            latency_ms = round((time.perf_counter() - start) * 1000, 2)

            if not rows:
                logger.info(
                    "tool_call",
                    conversation_id=self._conversation_id,
                    tool="get_customer_rental_history",
                    status="ok_empty",
                    latency_ms=latency_ms,
                )
                return f"No rental history found for customer ID {customer_id}."

            first = rows[0]
            lines = [
                f"Recent rentals for {first.first_name} {first.last_name} (ID: {customer_id}):"
            ]
            for row in rows:
                rental_dt = row.rental_date.strftime("%Y-%m-%d")
                return_dt = row.return_date.strftime("%Y-%m-%d") if row.return_date else "Not returned"
                lines.append(f"- {row.title} | Rented: {rental_dt} | Returned: {return_dt}")

            logger.info(
                "tool_call",
                conversation_id=self._conversation_id,
                tool="get_customer_rental_history",
                status="ok",
                result_count=len(rows),
                latency_ms=latency_ms,
            )
            return "\n".join(lines)

        except Exception as exc:
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.error(
                "tool_call_error",
                conversation_id=self._conversation_id,
                tool="get_customer_rental_history",
                status="error",
                error=str(exc),
                latency_ms=latency_ms,
            )
            return f"Error retrieving rental history: {exc}"
