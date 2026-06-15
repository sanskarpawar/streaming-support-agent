"""
KBPlugin — search_kb

Backed by a local JSON file (kb/articles.json).
Simple keyword search — returns source references.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Annotated

from semantic_kernel.functions import kernel_function

from app.core.logging import get_logger

logger = get_logger(__name__)

_KB_PATH = Path(__file__).parent.parent.parent / "kb" / "articles.json"


def _load_articles() -> list[dict]:
    with open(_KB_PATH, encoding="utf-8") as f:
        return json.load(f)


class KBPlugin:
    """SK plugin that searches the local knowledge base."""

    def __init__(self, conversation_id: str = "") -> None:
        self._conversation_id = conversation_id
        self._articles = _load_articles()

    @kernel_function(
        name="search_kb",
        description=(
            "Search the support knowledge base for articles related to a query. "
            "Returns article content and source references."
        ),
    )
    def search_kb(
        self,
        query: Annotated[str, "The support question or topic to search for"],
    ) -> str:
        """Keyword search across KB articles. Returns top 3 matching articles."""
        start = time.perf_counter()
        try:
            query_lower = query.lower()
            scored: list[tuple[int, dict]] = []

            for article in self._articles:
                score = 0
                text = (article["title"] + " " + article["content"]).lower()
                for word in query_lower.split():
                    if word in text:
                        score += text.count(word)
                if score > 0:
                    scored.append((score, article))

            scored.sort(key=lambda x: x[0], reverse=True)
            top = [a for _, a in scored[:3]]

            latency_ms = round((time.perf_counter() - start) * 1000, 2)

            if not top:
                logger.info(
                    "tool_call",
                    conversation_id=self._conversation_id,
                    tool="search_kb",
                    status="ok_empty",
                    latency_ms=latency_ms,
                )
                return (
                    "No knowledge base articles found for that query. "
                    "Please contact support directly for further help."
                )

            lines = [f"Knowledge base results for '{query}':"]
            for article in top:
                lines.append(
                    f"\n[Source: {article['source']}]\n"
                    f"**{article['title']}**\n"
                    f"{article['content']}"
                )

            logger.info(
                "tool_call",
                conversation_id=self._conversation_id,
                tool="search_kb",
                status="ok",
                result_count=len(top),
                latency_ms=latency_ms,
            )
            return "\n".join(lines)

        except Exception as exc:
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.error(
                "tool_call_error",
                conversation_id=self._conversation_id,
                tool="search_kb",
                status="error",
                error=str(exc),
                latency_ms=latency_ms,
            )
            return f"Error searching knowledge base: {exc}"
