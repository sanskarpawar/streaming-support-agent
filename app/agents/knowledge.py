"""KnowledgeAgent — answers general support questions from the KB."""
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

from app.core.config import get_settings
from app.plugins.kb_plugin import KBPlugin

KNOWLEDGE_INSTRUCTIONS = """\
You are the KnowledgeAgent for a streaming and rental platform.

Your role is to answer general support questions using the knowledge base.

Guidelines:
- Always call search_kb before answering — never make up information.
- Include the source reference ([Source: ...]) in your answer so the customer
  knows where the information comes from.
- If the knowledge base does not contain the answer, say clearly:
  "I don't have specific information about that in our knowledge base.
   Please contact support directly for further help."
- Do not speculate or use information not returned by search_kb.
- Keep answers clear, structured, and helpful.
"""


def build_knowledge_agent(conversation_id: str) -> ChatCompletionAgent:
    settings = get_settings()
    return ChatCompletionAgent(
        name="KnowledgeAgent",
        description="Answers general support questions using the knowledge base.",
        instructions=KNOWLEDGE_INSTRUCTIONS,
        service=OpenAIChatCompletion(
            ai_model_id=settings.openai_model,
            api_key=settings.openai_api_key,
        ),
        plugins=[KBPlugin(conversation_id=conversation_id)],
    )
