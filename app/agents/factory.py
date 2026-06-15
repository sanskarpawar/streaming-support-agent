"""
Agent factory — builds all ChatCompletionAgents and the OrchestrationHandoffs config.

Returns (agents_list, handoffs) ready for HandoffOrchestration.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from semantic_kernel.agents import ChatCompletionAgent, OrchestrationHandoffs

from app.agents.triage import build_triage_agent
from app.agents.catalog import build_catalog_agent
from app.agents.subscription import build_subscription_agent
from app.agents.rental_history import build_rental_history_agent
from app.agents.knowledge import build_knowledge_agent
from app.agents.human_handoff import build_human_handoff_agent


def build_agents(
    db: AsyncSession,
    conversation_id: str,
) -> tuple[list[ChatCompletionAgent], OrchestrationHandoffs]:
    """
    Build all specialist agents with their plugins and declare handoff relationships.

    The TriageAgent routes to specialists by calling SK-injected transfer functions.
    No custom routing logic lives here — it is all declared via OrchestrationHandoffs.
    """
    triage = build_triage_agent()
    catalog = build_catalog_agent(db, conversation_id)
    subscription = build_subscription_agent(db, conversation_id)
    rental = build_rental_history_agent(db, conversation_id)
    knowledge = build_knowledge_agent(conversation_id)
    handoff = build_human_handoff_agent(conversation_id)

    agents = [triage, catalog, subscription, rental, knowledge, handoff]

    handoffs = (
        OrchestrationHandoffs()
        .add_many(
            source_agent=triage.name,
            target_agents={
                catalog.name: (
                    "Transfer when the customer asks about a specific film, streaming availability, "
                    "film categories, ratings, or rental rates."
                ),
                subscription.name: (
                    "Transfer when the customer asks about their streaming subscription, "
                    "plan status, renewal date, or auto-renew setting."
                ),
                rental.name: (
                    "Transfer when the customer asks about their rental history, "
                    "past rentals, or currently rented items."
                ),
                knowledge.name: (
                    "Transfer when the customer has a general support question such as "
                    "how to update payment, cancel subscription, manage devices, or refund policy."
                ),
                handoff.name: (
                    "Transfer when the customer explicitly requests a human agent, "
                    "or when the request involves sensitive account actions like immediate "
                    "cancellation, account deletion, or suspected fraud."
                ),
            },
        )
        .add(
            source_agent=catalog.name,
            target_agent=triage.name,
            description="Transfer back to triage if the question is not about the film catalog.",
        )
        .add(
            source_agent=subscription.name,
            target_agent=triage.name,
            description="Transfer back to triage if the question is not about subscriptions.",
        )
        .add(
            source_agent=rental.name,
            target_agent=triage.name,
            description="Transfer back to triage if the question is not about rental history.",
        )
        .add(
            source_agent=knowledge.name,
            target_agent=triage.name,
            description="Transfer back to triage if the question is not a general support topic.",
        )
        .add(
            source_agent=handoff.name,
            target_agent=triage.name,
            description="Transfer back to triage if escalation to human is not needed.",
        )
    )

    return agents, handoffs
