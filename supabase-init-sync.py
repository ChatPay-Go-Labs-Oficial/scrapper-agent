"""
One-time script: populate product_min in Supabase from the backend Railway PostgreSQL.

Usage:
    BACKEND_DATABASE_URL="postgresql://..." AI_DATABASE_URL="postgresql://..." uv run python supabase-init-sync.py

Run this ONCE after setting up the Supabase schema and before the first deploy.
"""
import asyncio
import os
import asyncpg


async def main() -> None:
    backend_url = os.environ["BACKEND_DATABASE_URL"]
    ai_url = os.environ["AI_DATABASE_URL"]

    pg_backend = await asyncpg.connect(backend_url)
    pg_ai = await asyncpg.connect(ai_url)

    try:
        rows = await pg_backend.fetch(
            'SELECT id, "userId", "salesPageUrl" FROM product'
        )
        print(f"Found {len(rows)} products in backend DB")

        if not rows:
            print("Nothing to sync.")
            return

        records = [(str(r["id"]), str(r["userId"]), r["salesPageUrl"]) for r in rows]

        await pg_ai.executemany(
            """
            INSERT INTO product_min (product_id, seller_id, sales_page_url, updated_at)
            VALUES ($1, $2, $3, NOW())
            ON CONFLICT (product_id) DO UPDATE
              SET seller_id      = EXCLUDED.seller_id,
                  sales_page_url = EXCLUDED.sales_page_url,
                  updated_at     = NOW()
            """,
            records,
        )
        print(f"Synced {len(records)} products to Supabase product_min")
    finally:
        await pg_backend.close()
        await pg_ai.close()


if __name__ == "__main__":
    asyncio.run(main())
