"""
Tests for all SK plugins (tools).

All DB calls are mocked — no real PostgreSQL connection needed.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.plugins.catalog_plugin import CatalogPlugin
from app.plugins.subscription_plugin import SubscriptionPlugin
from app.plugins.rental_plugin import RentalPlugin
from app.plugins.kb_plugin import KBPlugin
from app.plugins.handoff_plugin import HandoffPlugin


# ── CatalogPlugin ──────────────────────────────────────────────────────────────

class TestCatalogPlugin:
    @pytest.mark.asyncio
    async def test_search_returns_results(self, mock_db, mock_catalog_rows, conversation_id):
        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_catalog_rows
        mock_db.execute = AsyncMock(return_value=mock_result)

        plugin = CatalogPlugin(db=mock_db, conversation_id=conversation_id)
        result = await plugin.search_film_catalog(query="Alien")

        assert "Alien" in result
        assert "Streaming: Yes" in result
        assert "Science Fiction" in result

    @pytest.mark.asyncio
    async def test_search_no_results(self, mock_db, conversation_id):
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        plugin = CatalogPlugin(db=mock_db, conversation_id=conversation_id)
        result = await plugin.search_film_catalog(query="XYZ_NONEXISTENT")

        assert "No films found" in result

    @pytest.mark.asyncio
    async def test_search_db_error_returns_error_string(self, mock_db, conversation_id):
        mock_db.execute = AsyncMock(side_effect=Exception("DB connection error"))

        plugin = CatalogPlugin(db=mock_db, conversation_id=conversation_id)
        result = await plugin.search_film_catalog(query="Alien")

        assert "Error" in result
        assert "DB connection error" in result

    @pytest.mark.asyncio
    async def test_streaming_unavailable_shown(self, mock_db, conversation_id):
        row = MagicMock()
        row.title = "OldFilm"
        row.category = "Drama"
        row.rating = "PG"
        row.rental_rate = "2.99"
        row.streaming_available = False

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [row]
        mock_db.execute = AsyncMock(return_value=mock_result)

        plugin = CatalogPlugin(db=mock_db, conversation_id=conversation_id)
        result = await plugin.search_film_catalog(query="OldFilm")

        assert "Streaming: No" in result


# ── SubscriptionPlugin ────────────────────────────────────────────────────────

class TestSubscriptionPlugin:
    @pytest.mark.asyncio
    async def test_active_subscription_returned(self, mock_db, mock_sub_row, conversation_id):
        mock_result = MagicMock()
        mock_result.first.return_value = (mock_sub_row, "Mary", "Smith")
        mock_db.execute = AsyncMock(return_value=mock_result)

        plugin = SubscriptionPlugin(db=mock_db, conversation_id=conversation_id)
        result = await plugin.get_customer_streaming_subscription(customer_id=1)

        assert "Premium" in result
        assert "active" in result
        assert "Mary Smith" in result

    @pytest.mark.asyncio
    async def test_no_subscription_graceful(self, mock_db, conversation_id):
        mock_result = MagicMock()
        mock_result.first.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        plugin = SubscriptionPlugin(db=mock_db, conversation_id=conversation_id)
        result = await plugin.get_customer_streaming_subscription(customer_id=999)

        assert "No streaming subscription found" in result
        assert "999" in result

    @pytest.mark.asyncio
    async def test_db_error_returns_error_string(self, mock_db, conversation_id):
        mock_db.execute = AsyncMock(side_effect=Exception("timeout"))

        plugin = SubscriptionPlugin(db=mock_db, conversation_id=conversation_id)
        result = await plugin.get_customer_streaming_subscription(customer_id=1)

        assert "Error" in result


# ── RentalPlugin ──────────────────────────────────────────────────────────────

class TestRentalPlugin:
    @pytest.mark.asyncio
    async def test_rental_history_returned(self, mock_db, mock_rental_rows, conversation_id):
        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rental_rows
        mock_db.execute = AsyncMock(return_value=mock_result)

        plugin = RentalPlugin(db=mock_db, conversation_id=conversation_id)
        result = await plugin.get_customer_rental_history(customer_id=1)

        assert "Film 1" in result
        assert "Mary Smith" in result
        assert "Rented:" in result

    @pytest.mark.asyncio
    async def test_no_rental_history(self, mock_db, conversation_id):
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        plugin = RentalPlugin(db=mock_db, conversation_id=conversation_id)
        result = await plugin.get_customer_rental_history(customer_id=1)

        assert "No rental history" in result

    @pytest.mark.asyncio
    async def test_db_error_returns_error_string(self, mock_db, conversation_id):
        mock_db.execute = AsyncMock(side_effect=RuntimeError("network error"))

        plugin = RentalPlugin(db=mock_db, conversation_id=conversation_id)
        result = await plugin.get_customer_rental_history(customer_id=1)

        assert "Error" in result


# ── KBPlugin ──────────────────────────────────────────────────────────────────

class TestKBPlugin:
    def test_kb_search_returns_results(self, conversation_id):
        plugin = KBPlugin(conversation_id=conversation_id)
        result = plugin.search_kb(query="payment method")
        assert "payment" in result.lower()
        assert "Source:" in result

    def test_kb_search_no_results(self, conversation_id):
        plugin = KBPlugin(conversation_id=conversation_id)
        result = plugin.search_kb(query="xyznonexistentquery12345")
        assert "No knowledge base articles found" in result

    def test_kb_search_includes_source(self, conversation_id):
        plugin = KBPlugin(conversation_id=conversation_id)
        result = plugin.search_kb(query="cancel subscription")
        assert "Source:" in result

    def test_kb_search_refund_policy(self, conversation_id):
        plugin = KBPlugin(conversation_id=conversation_id)
        result = plugin.search_kb(query="refund policy")
        assert "refund" in result.lower()


# ── HandoffPlugin ─────────────────────────────────────────────────────────────

class TestHandoffPlugin:
    def test_ticket_created(self, conversation_id):
        plugin = HandoffPlugin(conversation_id=conversation_id)
        result = plugin.create_handoff_ticket(
            summary="Customer wants to cancel account",
            reason="Customer requested human agent",
        )
        assert "TICKET-" in result
        assert "human support agent" in result.lower()

    def test_ticket_id_unique(self, conversation_id):
        plugin = HandoffPlugin(conversation_id=conversation_id)
        r1 = plugin.create_handoff_ticket("Issue A", "Reason A")
        r2 = plugin.create_handoff_ticket("Issue B", "Reason B")
        # Extract TICKET-... IDs
        id1 = [w for w in r1.split() if w.startswith("TICKET-")][0]
        id2 = [w for w in r2.split() if w.startswith("TICKET-")][0]
        assert id1 != id2
