"""
pagila-support-mcp

A local MCP server that exposes three Pagila-backed tools:
  - search_film_catalog
  - get_customer_streaming_subscription
  - get_customer_rental_history

Run with:  uv run python mcp/server.py
"""
from __future__ import annotations

import asyncio
import os
import sys

# Ensure project root is on PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import asyncpg
from mcp.server.mcpserver import MCPServer

# ── DB connection ──────────────────────────────────────────────────────────────

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:admin@localhost:5432/pagila")
# asyncpg uses postgresql:// not postgresql+asyncpg://
_asyncpg_url = (
    DATABASE_URL
    .replace("postgresql+asyncpg://", "postgresql://")
    .replace("postgresql+psycopg2://", "postgresql://")
)

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(_asyncpg_url, min_size=1, max_size=5)
    return _pool


# ── MCP Server ─────────────────────────────────────────────────────────────────

mcp = MCPServer("pagila-support-mcp")


@mcp.tool()
async def search_film_catalog(query: str) -> str:
    """Search the Pagila film catalog by title or description keyword.

    Returns up to 5 matching films with title, category, rating, rental rate,
    and streaming availability.

    Args:
        query: Keyword to search in film titles and descriptions.
    """
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT f.title, c.name AS category, f.rating,
               f.rental_rate, f.streaming_available
        FROM film f
        LEFT JOIN film_category fc ON f.film_id = fc.film_id
        LEFT JOIN category c ON fc.category_id = c.category_id
        WHERE f.title ILIKE $1 OR f.description ILIKE $1
        LIMIT 5
        """,
        f"%{query}%",
    )
    if not rows:
        return f"No films found matching '{query}'."

    lines = [f"Films matching '{query}':"]
    for r in rows:
        streaming = "Yes" if r["streaming_available"] else "No"
        lines.append(
            f"- {r['title']} | Category: {r['category'] or 'N/A'} | "
            f"Rating: {r['rating']} | Rate: ${r['rental_rate']} | Streaming: {streaming}"
        )
    return "\n".join(lines)


@mcp.tool()
async def get_customer_streaming_subscription(customer_id: int) -> str:
    """Retrieve the streaming subscription status for a customer.

    Returns plan name, status (active/cancelled), renewal date, and auto-renew flag.

    Args:
        customer_id: The numeric customer ID.
    """
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        SELECT s.plan_name, s.status, s.end_date, s.auto_renew,
               c.first_name, c.last_name
        FROM streaming_subscription s
        JOIN customer c ON s.customer_id = c.customer_id
        WHERE s.customer_id = $1
        ORDER BY s.id DESC
        LIMIT 1
        """,
        customer_id,
    )
    if not row:
        return f"No subscription found for customer ID {customer_id}."

    end_date = row["end_date"].strftime("%Y-%m-%d") if row["end_date"] else "N/A"
    return (
        f"Customer: {row['first_name']} {row['last_name']} (ID: {customer_id})\n"
        f"Plan: {row['plan_name']}\nStatus: {row['status']}\n"
        f"Renewal: {end_date}\nAuto-Renew: {'Yes' if row['auto_renew'] else 'No'}"
    )


@mcp.tool()
async def get_customer_rental_history(customer_id: int) -> str:
    """Retrieve the recent rental history for a customer.

    Returns film titles, rental dates, and return dates for the last 10 rentals.

    Args:
        customer_id: The numeric customer ID.
    """
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT f.title, r.rental_date, r.return_date,
               c.first_name, c.last_name
        FROM rental r
        JOIN inventory i ON r.inventory_id = i.inventory_id
        JOIN film f ON i.film_id = f.film_id
        JOIN customer c ON r.customer_id = c.customer_id
        WHERE r.customer_id = $1
        ORDER BY r.rental_date DESC
        LIMIT 10
        """,
        customer_id,
    )
    if not rows:
        return f"No rental history for customer ID {customer_id}."

    first = rows[0]
    lines = [f"Recent rentals for {first['first_name']} {first['last_name']}:"]
    for r in rows:
        ret = r["return_date"].strftime("%Y-%m-%d") if r["return_date"] else "Not returned"
        lines.append(
            f"- {r['title']} | Rented: {r['rental_date'].strftime('%Y-%m-%d')} | Returned: {ret}"
        )
    return "\n".join(lines)


# ── Entry point ────────────────────────────────────────────────────────────────

async def main() -> None:
    await mcp.run_stdio_async()


if __name__ == "__main__":
    asyncio.run(main())
