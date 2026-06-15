"""
pagila-support-mcp

A local MCP server that exposes three Pagila-backed tools:
  - search_film_catalog
  - get_customer_streaming_subscription
  - get_customer_rental_history

Run with:  python mcp/server.py
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
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

# ── DB connection ─────────────────────────────────────────────────────────────

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/pagila")
# asyncpg uses postgresql:// not postgresql+asyncpg://
_asyncpg_url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://").replace("postgresql+psycopg2://", "postgresql://")

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(_asyncpg_url, min_size=1, max_size=5)
    return _pool


# ── MCP Server ────────────────────────────────────────────────────────────────

server = Server("pagila-support-mcp")


# Tool: search_film_catalog
@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="search_film_catalog",
            description=(
                "Search the Pagila film catalog by title keyword. "
                "Returns title, category, rating, rental rate, and streaming availability."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Keyword to search in film titles and descriptions.",
                    }
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="get_customer_streaming_subscription",
            description=(
                "Retrieve the streaming subscription status for a customer. "
                "Returns plan name, status (active/cancelled), renewal date, and auto-renew flag."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "integer",
                        "description": "The numeric customer ID.",
                    }
                },
                "required": ["customer_id"],
            },
        ),
        types.Tool(
            name="get_customer_rental_history",
            description=(
                "Retrieve the recent rental history for a customer. "
                "Returns film titles, rental dates, and return dates for the last 10 rentals."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "integer",
                        "description": "The numeric customer ID.",
                    }
                },
                "required": ["customer_id"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    pool = await get_pool()

    if name == "search_film_catalog":
        query = arguments.get("query", "")
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
            text = f"No films found matching '{query}'."
        else:
            lines = [f"Films matching '{query}':"]
            for r in rows:
                streaming = "Yes" if r["streaming_available"] else "No"
                lines.append(
                    f"- {r['title']} | Category: {r['category'] or 'N/A'} | "
                    f"Rating: {r['rating']} | Rate: ${r['rental_rate']} | Streaming: {streaming}"
                )
            text = "\n".join(lines)
        return [types.TextContent(type="text", text=text)]

    elif name == "get_customer_streaming_subscription":
        customer_id = int(arguments.get("customer_id", 0))
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
            text = f"No subscription found for customer ID {customer_id}."
        else:
            end_date = row["end_date"].strftime("%Y-%m-%d") if row["end_date"] else "N/A"
            text = (
                f"Customer: {row['first_name']} {row['last_name']} (ID: {customer_id})\n"
                f"Plan: {row['plan_name']}\nStatus: {row['status']}\n"
                f"Renewal: {end_date}\nAuto-Renew: {'Yes' if row['auto_renew'] else 'No'}"
            )
        return [types.TextContent(type="text", text=text)]

    elif name == "get_customer_rental_history":
        customer_id = int(arguments.get("customer_id", 0))
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
            text = f"No rental history for customer ID {customer_id}."
        else:
            first = rows[0]
            lines = [f"Recent rentals for {first['first_name']} {first['last_name']}:"]
            for r in rows:
                ret = r["return_date"].strftime("%Y-%m-%d") if r["return_date"] else "Not returned"
                lines.append(f"- {r['title']} | Rented: {r['rental_date'].strftime('%Y-%m-%d')} | Returned: {ret}")
            text = "\n".join(lines)
        return [types.TextContent(type="text", text=text)]

    else:
        return [types.TextContent(type="text", text=f"Unknown tool: {name}")]


# ── Entry point ───────────────────────────────────────────────────────────────

async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
