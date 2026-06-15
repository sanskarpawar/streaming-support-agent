"""
Shared pytest fixtures.

Provides:
  - mock_db        : AsyncMock simulating an AsyncSession
  - mock_catalog_rows : fake film rows for catalog plugin tests
  - mock_sub_row      : fake subscription row for subscription plugin tests
  - mock_rental_rows  : fake rental rows for rental plugin tests
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
import os


@pytest.fixture(autouse=True)
def set_dummy_openai_key(monkeypatch):
    """Provide a dummy API key so SK agents can be constructed in tests."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-dummy-key-for-unit-tests")
    # Reset lru_cache on config so the env var is picked up
    from app.core.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def mock_db() -> AsyncMock:
    """A minimal AsyncSession mock — execute returns a mock result."""
    db = AsyncMock()
    return db


@pytest.fixture
def conversation_id() -> str:
    return "test-conv-001"


@pytest.fixture
def mock_catalog_rows():
    row = MagicMock()
    row.title = "Alien"
    row.category = "Science Fiction"
    row.rating = "R"
    row.rental_rate = "4.99"
    row.streaming_available = True
    return [row]


@pytest.fixture
def mock_empty_rows():
    return []


@pytest.fixture
def mock_sub_row():
    sub = MagicMock()
    sub.plan_name = "Premium"
    sub.status = "active"
    sub.end_date = datetime(2027, 1, 1, tzinfo=timezone.utc)
    sub.auto_renew = True
    return sub


@pytest.fixture
def mock_rental_rows():
    rows = []
    for i in range(3):
        row = MagicMock()
        row.title = f"Film {i + 1}"
        row.rental_date = datetime(2025, 12, i + 1, tzinfo=timezone.utc)
        row.return_date = datetime(2025, 12, i + 5, tzinfo=timezone.utc)
        row.first_name = "Mary"
        row.last_name = "Smith"
        rows.append(row)
    return rows
