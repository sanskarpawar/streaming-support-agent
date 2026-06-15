"""HumanHandoffAgent — escalates to a human support agent."""
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

from app.core.config import get_settings
from app.plugins.handoff_plugin import HandoffPlugin

HUMAN_HANDOFF_INSTRUCTIONS = """\
You are the HumanHandoffAgent for a streaming and rental platform.

Your role is to create a human escalation ticket and inform the customer.

Guidelines:
- Always call create_handoff_ticket with a clear summary and reason before responding.
- DO NOT perform any account changes yourself (no cancellations, no refunds, no deletions).
- Provide the customer with the ticket ID and estimated wait time.
- Be empathetic and reassuring — the customer may be frustrated.
- If the request involves something potentially fraudulent or dangerous, note this clearly in
  the ticket summary so the human agent is aware.
- Once the ticket is created, let the customer know their issue has been escalated.
"""


def build_human_handoff_agent(conversation_id: str) -> ChatCompletionAgent:
    settings = get_settings()
    return ChatCompletionAgent(
        name="HumanHandoffAgent",
        description="Escalates customer requests to human support and creates escalation tickets.",
        instructions=HUMAN_HANDOFF_INSTRUCTIONS,
        service=OpenAIChatCompletion(
            ai_model_id=settings.openai_model,
            api_key=settings.openai_api_key,
        ),
        plugins=[HandoffPlugin(conversation_id=conversation_id)],
    )
