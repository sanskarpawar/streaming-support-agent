"""Quick smoke-test for MCP tool DB connectivity. Run with: uv run python mcp/test_tools.py"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

import asyncpg


async def main() -> None:
    db_url = (
        os.getenv("DATABASE_URL", "postgresql://postgres:admin@localhost:5432/pagila")
        .replace("postgresql+asyncpg://", "postgresql://")
    )
    pool = await asyncpg.create_pool(db_url, min_size=1, max_size=1)

    # Tool 1 — search_film_catalog
    rows = await pool.fetch(
        "SELECT title FROM film WHERE title ILIKE $1 LIMIT 2", "%ace%"
    )
    print("search_film_catalog:", [r["title"] for r in rows])

    # Tool 2 — get_customer_streaming_subscription
    row = await pool.fetchrow(
        "SELECT plan_name, status FROM streaming_subscription WHERE customer_id=$1 LIMIT 1", 1
    )
    print("subscription:", dict(row) if row else "NOT FOUND")

    # Tool 3 — get_customer_rental_history
    rows2 = await pool.fetch(
        "SELECT f.title FROM rental r "
        "JOIN inventory i ON r.inventory_id = i.inventory_id "
        "JOIN film f ON i.film_id = f.film_id "
        "WHERE r.customer_id=$1 ORDER BY r.rental_date DESC LIMIT 3",
        1,
    )
    print("rental_history:", [r["title"] for r in rows2])

    await pool.close()
    print("\nAll MCP tool DB queries: OK")


if __name__ == "__main__":
    asyncio.run(main())
