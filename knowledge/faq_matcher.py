"""FAQ matcher using pgvector similarity for product-scoped FAQs."""

from __future__ import annotations

DEFAULT_THRESHOLD = 0.92


async def search(
    query_embedding: list[float],
    product_id: str,
    db_pool,
    threshold: float = DEFAULT_THRESHOLD,
) -> str | None:
    """
    Return a FAQ answer if the semantic similarity is above the threshold.

    Always scoped by product_id to prevent cross-tenant leakage.
    """
    vector_str = str(query_embedding)
    row = await db_pool.fetchrow(
        """
        SELECT answer, 1 - (q_embedding <=> $1::vector) AS similarity
        FROM product_faqs
        WHERE product_id = $2
          AND is_active = TRUE
        ORDER BY q_embedding <=> $1::vector
        LIMIT 1
        """,
        vector_str,
        product_id,
    )

    if not row:
        return None

    if row["similarity"] < threshold:
        return None

    return row["answer"]
