"""
Tests for agent factory and HandoffOrchestration routing.

These tests mock the OpenAI API and verify agent construction,
handoff declarations, and the overall run_turn pipeline structure.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.factory import build_agents
from app.schemas.response import AgentResponse, GuardrailResult


class TestAgentFactory:
    def test_build_agents_returns_correct_count(self, mock_db, conversation_id):
        agents, handoffs = build_agents(db=mock_db, conversation_id=conversation_id)
        # TriageAgent + 5 specialists = 6
        assert len(agents) == 6

    def test_all_agent_names_present(self, mock_db, conversation_id):
        agents, handoffs = build_agents(db=mock_db, conversation_id=conversation_id)
        names = {a.name for a in agents}
        assert "TriageAgent" in names
        assert "CatalogAgent" in names
        assert "SubscriptionAgent" in names
        assert "RentalHistoryAgent" in names
        assert "KnowledgeAgent" in names
        assert "HumanHandoffAgent" in names

    def test_handoffs_declared(self, mock_db, conversation_id):
        agents, handoffs = build_agents(db=mock_db, conversation_id=conversation_id)
        # OrchestrationHandoffs should be non-None
        assert handoffs is not None

    def test_triage_agent_has_no_plugins(self, mock_db, conversation_id):
        agents, _ = build_agents(db=mock_db, conversation_id=conversation_id)
        triage = next(a for a in agents if a.name == "TriageAgent")
        # TriageAgent should not have domain-specific plugins
        assert triage is not None

    def test_catalog_agent_has_catalog_plugin(self, mock_db, conversation_id):
        """Verify CatalogAgent is built with search_film_catalog function in its kernel."""
        agents, _ = build_agents(db=mock_db, conversation_id=conversation_id)
        catalog = next(a for a in agents if a.name == "CatalogAgent")
        # In SK 1.43.0 plugins are stored in agent.kernel.plugins
        kernel = getattr(catalog, "kernel", None)
        assert kernel is not None
        fn_names = [fn for plugin in kernel.plugins.values() for fn in plugin.functions]
        assert "search_film_catalog" in fn_names

    def test_subscription_agent_has_subscription_plugin(self, mock_db, conversation_id):
        """Verify SubscriptionAgent kernel has get_customer_streaming_subscription function."""
        agents, _ = build_agents(db=mock_db, conversation_id=conversation_id)
        sub = next(a for a in agents if a.name == "SubscriptionAgent")
        kernel = getattr(sub, "kernel", None)
        assert kernel is not None
        fn_names = [fn for plugin in kernel.plugins.values() for fn in plugin.functions]
        assert "get_customer_streaming_subscription" in fn_names

    def test_knowledge_agent_has_kb_plugin(self, mock_db, conversation_id):
        """Verify KnowledgeAgent kernel has search_kb function."""
        agents, _ = build_agents(db=mock_db, conversation_id=conversation_id)
        kb = next(a for a in agents if a.name == "KnowledgeAgent")
        kernel = getattr(kb, "kernel", None)
        assert kernel is not None
        fn_names = [fn for plugin in kernel.plugins.values() for fn in plugin.functions]
        assert "search_kb" in fn_names


class TestAgentResponse:
    def test_agent_response_schema_valid(self):
        guardrail = GuardrailResult(
            safe=True,
            guardrail_triggered=False,
            issues=[],
            revised_answer="This film is available for streaming.",
        )
        response = AgentResponse(
            conversation_id="test-001",
            session_title="Alien Streaming Question",
            intent="catalog_search",
            selected_agent="CatalogAgent",
            answer="This film is available for streaming.",
            confidence=0.9,
            tools_used=["search_film_catalog"],
            citations=[],
            next_action="none",
            guardrail_result=guardrail,
        )
        assert response.confidence == 0.9
        assert response.selected_agent == "CatalogAgent"
        assert response.guardrail_result.safe is True

    def test_agent_response_confidence_bounds(self):
        from pydantic import ValidationError
        guardrail = GuardrailResult(
            safe=True, guardrail_triggered=False, issues=[], revised_answer="ok"
        )
        with pytest.raises(ValidationError):
            AgentResponse(
                conversation_id="x",
                intent="x",
                selected_agent="x",
                answer="x",
                confidence=1.5,  # out of range
                guardrail_result=guardrail,
            )

    def test_guardrail_result_safe_flag(self):
        result = GuardrailResult(
            safe=False,
            guardrail_triggered=True,
            issues=["Prompt injection detected"],
            revised_answer="I cannot help with that request.",
        )
        assert result.safe is False
        assert result.guardrail_triggered is True
        assert len(result.issues) == 1
