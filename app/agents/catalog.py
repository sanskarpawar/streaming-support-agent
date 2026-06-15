"""CatalogAgent — answers film catalog and streaming availability questions."""
from semantic_kernel.agents import ChatCompletionAgent
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.llm import build_chat_service
from app.plugins.catalog_plugin import CatalogPlugin

CATALOG_INSTRUCTIONS = """\
You are the CatalogAgent for a streaming and rental platform.

Your role is to answer questions about films, streaming availability, categories,
ratings, and rental rates.

Guidelines:
- Always call search_film_catalog to look up film information before answering.
- Include the film title, category, rating, rental rate, and streaming availability in your answer.
- If streaming_available is false, tell the customer the film is rental-only.
- If no films are found, say so clearly and suggest the customer try a different title.
- Do not make up film information — only use what the tool returns.
- Keep your response friendly and concise.
"""


def build_catalog_agent(db: AsyncSession, conversation_id: str) -> ChatCompletionAgent:
    return ChatCompletionAgent(
        name="CatalogAgent",
        description="Answers questions about the film catalog and streaming availability.",
        instructions=CATALOG_INSTRUCTIONS,
        service=build_chat_service(),
        plugins=[CatalogPlugin(db=db, conversation_id=conversation_id)],
    )
