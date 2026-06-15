"""
CatalogPlugin — search_film_catalog

Backed by PostgreSQL (Pagila film, film_category, category tables).
Logs every call with conversation_id, tool name, status, latency, errors.
"""
from __future__ import annotations

import time
from typing import Annotated

from semantic_kernel.functions import kernel_function
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models import Category, Film, FilmCategory

logger = get_logger(__name__)


class CatalogPlugin:
    """SK plugin that searches the Pagila film catalog."""

    def __init__(self, db: AsyncSession, conversation_id: str = "") -> None:
        self._db = db
        self._conversation_id = conversation_id

    @kernel_function(
        name="search_film_catalog",
        description=(
            "Search the film catalog by title keyword. Returns title, category, "
            "rating, rental rate, and streaming availability."
        ),
    )
    async def search_film_catalog(
        self,
        query: Annotated[str, "Keyword to search in film titles and descriptions"],
    ) -> str:
        """Search films by title keyword and return a formatted result string."""
        start = time.perf_counter()
        try:
            stmt = (
                select(
                    Film.film_id,
                    Film.title,
                    Film.description,
                    Film.rating,
                    Film.rental_rate,
                    Film.streaming_available,
                    Category.name.label("category"),
                )
                .outerjoin(FilmCategory, Film.film_id == FilmCategory.film_id)
                .outerjoin(Category, FilmCategory.category_id == Category.category_id)
                .where(
                    or_(
                        Film.title.ilike(f"%{query}%"),
                        Film.description.ilike(f"%{query}%"),
                    )
                )
                .limit(5)
            )
            result = await self._db.execute(stmt)
            rows = result.fetchall()

            latency_ms = round((time.perf_counter() - start) * 1000, 2)

            if not rows:
                logger.info(
                    "tool_call",
                    conversation_id=self._conversation_id,
                    tool="search_film_catalog",
                    status="ok_empty",
                    latency_ms=latency_ms,
                )
                return f"No films found matching '{query}'."

            lines = [f"Films matching '{query}':"]
            for row in rows:
                streaming = "Yes" if row.streaming_available else "No"
                lines.append(
                    f"- {row.title} | Category: {row.category or 'N/A'} | "
                    f"Rating: {row.rating} | Rental Rate: ${row.rental_rate} | "
                    f"Streaming: {streaming}"
                )

            logger.info(
                "tool_call",
                conversation_id=self._conversation_id,
                tool="search_film_catalog",
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
                tool="search_film_catalog",
                status="error",
                error=str(exc),
                latency_ms=latency_ms,
            )
            return f"Error searching film catalog: {exc}"
