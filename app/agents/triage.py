"""
TriageAgent — entry point for HandoffOrchestration.

Routes customer requests to the appropriate specialist agent using SK's
HandoffOrchestration. The LLM calls `transfer_to_<AgentName>()` function
calls injected by SK — zero custom routing code here.
"""
from semantic_kernel.agents import ChatCompletionAgent

from app.core.llm import build_chat_service

TRIAGE_INSTRUCTIONS = """\
You are the TriageAgent for a streaming and rental platform support system.

Your job is to greet the customer, understand their request, and transfer them
to the most appropriate specialist agent. You MUST transfer — do not attempt
to answer specialist questions yourself.

Routing rules (use the transfer functions available to you):
- Film catalog or streaming availability questions → CatalogAgent
- Subscription status, renewal, plan, or billing questions → SubscriptionAgent
- Rental history questions → RentalHistoryAgent
- General support how-to questions (payment methods, device management, refunds) → KnowledgeAgent
- Customer explicitly requests a human, or the request involves sensitive account
  mutations (cancel immediately, delete account, etc.) → HumanHandoffAgent

If the intent is unclear, ask one clarifying question before transferring.
Always be polite, concise, and empathetic.
"""


def build_triage_agent() -> ChatCompletionAgent:
    return ChatCompletionAgent(
        name="TriageAgent",
        description="Handles initial customer requests and routes to the appropriate specialist.",
        instructions=TRIAGE_INSTRUCTIONS,
        service=build_chat_service(),
    )
