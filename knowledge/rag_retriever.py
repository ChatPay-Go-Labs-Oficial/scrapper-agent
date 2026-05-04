"""RAG retriever with strict tenant isolation and ownership validation."""

from __future__ import annotations

from typing import Iterable

SIMILARITY_THRESHOLD = 0.65
DEFAULT_TOP_K = 5


async def validate_ownership(product_id: str, seller_id: str, db_pool) -> None:
    """
    Ensure the product belongs to the seller before any retrieval.

    Raises PermissionError when ownership validation fails.
    """
    ownership = await db_pool.fetchval(
        "SELECT id FROM product WHERE id = $1 AND user_id = $2",
        product_id,
        seller_id,
    )
    if not ownership:
        raise PermissionError("Ownership check failed")


def _join_chunks(rows: Iterable[dict]) -> str | None:
    chunks = [row["chunk_text"] for row in rows]
    if not chunks:
        return None
    return "\n\n---\n\n".join(chunks)


async def retrieve(
    query_embedding: list[float],
    product_id: str,
    seller_id: str,
    db_pool,
    top_k: int = DEFAULT_TOP_K,
    similarity_threshold: float = SIMILARITY_THRESHOLD,
) -> str | None:
    """
    Retrieve relevant chunks scoped to a single product.

    Returned text is for internal prompt context only and must not be sent directly
    to end users without output guards.
    """
    await validate_ownership(product_id, seller_id, db_pool)

    vector_str = str(query_embedding)
    rows = await db_pool.fetch(
        """
        SELECT chunk_text, 1 - (embedding <=> $1::vector) AS similarity
        FROM knowledge_chunks
        WHERE product_id = $2
          AND seller_id = $3
          AND source_type = 'ebook_pdf'
        ORDER BY embedding <=> $1::vector
        LIMIT $4
        """,
        vector_str,
        product_id,
        seller_id,
        top_k,
    )

    if not rows:
        return None

    relevant = [row for row in rows if row["similarity"] >= similarity_threshold]
    if not relevant:
        return None

    return _join_chunks(relevant)
