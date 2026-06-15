"""RentalHistoryAgent — answers questions about recent rental history."""
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.plugins.rental_plugin import RentalPlugin

RENTAL_HISTORY_INSTRUCTIONS = """\
You are the RentalHistoryAgent for a streaming and rental platform.

Your role is to look up and summarise a customer's recent rental history.

Guidelines:
- Always call get_customer_rental_history with the customer's ID before answering.
- Summarise the rentals in a friendly, readable format: film title, rental date, return date.
- Highlight any unreturned rentals (return_date is "Not returned").
- If no history is found, say so clearly.
- NEVER reveal other customers' rental data — only use the customer_id from the context.
- Keep responses concise — summarise rather than listing every detail if there are many rentals.
"""


def build_rental_history_agent(db: AsyncSession, conversation_id: str) -> ChatCompletionAgent:
    settings = get_settings()
    return ChatCompletionAgent(
        name="RentalHistoryAgent",
        description="Retrieves and summarises recent rental history for a customer.",
        instructions=RENTAL_HISTORY_INSTRUCTIONS,
        service=OpenAIChatCompletion(
            ai_model_id=settings.openai_model,
            api_key=settings.openai_api_key,
        ),
        plugins=[RentalPlugin(db=db, conversation_id=conversation_id)],
    )
