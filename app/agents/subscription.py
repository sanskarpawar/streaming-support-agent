"""SubscriptionAgent — answers streaming subscription and renewal questions."""
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.plugins.subscription_plugin import SubscriptionPlugin

SUBSCRIPTION_INSTRUCTIONS = """\
You are the SubscriptionAgent for a streaming and rental platform.

Your role is to look up and explain the customer's streaming subscription status.

Guidelines:
- Always call get_customer_streaming_subscription with the customer's ID before answering.
- Report the plan name, status (active/cancelled), renewal date, and auto-renew setting.
- If no subscription is found, clearly state that and suggest how to sign up.
- NEVER reveal other customers' subscription details — only use the customer_id from the context.
- Do not perform account mutations (cancellations, upgrades) — inform the customer to use
  account settings or escalate to a human agent for sensitive changes.
- Be empathetic if the customer has a billing concern.
"""


def build_subscription_agent(db: AsyncSession, conversation_id: str) -> ChatCompletionAgent:
    settings = get_settings()
    return ChatCompletionAgent(
        name="SubscriptionAgent",
        description="Handles streaming subscription status and renewal questions.",
        instructions=SUBSCRIPTION_INSTRUCTIONS,
        service=OpenAIChatCompletion(
            ai_model_id=settings.openai_model,
            api_key=settings.openai_api_key,
        ),
        plugins=[SubscriptionPlugin(db=db, conversation_id=conversation_id)],
    )
