"""Knowledge router to resolve context with ordered fallbacks."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from knowledge import faq_matcher, rag_retriever
from knowledge.scraping_cache import get_or_fetch


class KnowledgeSource(str, Enum):
    FAQ = "faq"
    RAG = "rag"
    SCRAPING = "scraping"
    FALLBACK = "fallback"


@dataclass
class KnowledgeResult:
    source: KnowledgeSource
    context: str
    confidence: float


FALLBACK_CONTEXT = "[Contexto do produto nao disponivel no momento]"


async def resolve_knowledge(
    product_id: str,
    seller_id: str,
    query: str,
    query_embedding: list[float],
    db_pool,
    redis_client=None,
    sales_page_url: Optional[str] = None,
) -> KnowledgeResult:
    """
    Resolve knowledge in priority order: FAQ -> RAG -> Scraping -> Fallback.

    The returned context is for internal prompt use only. Do not expose directly
    to end users without output guards.
    """
    try:
        faq_answer = await faq_matcher.search(query_embedding, product_id, db_pool)
        if faq_answer:
            return KnowledgeResult(
                source=KnowledgeSource.FAQ,
                context=faq_answer,
                confidence=0.95,
            )
    except Exception:
        pass

    try:
        rag_context = await rag_retriever.retrieve(
            query_embedding,
            product_id,
            seller_id,
            db_pool,
        )
        if rag_context:
            return KnowledgeResult(
                source=KnowledgeSource.RAG,
                context=rag_context,
                confidence=0.80,
            )
    except Exception:
        pass

    try:
        if sales_page_url:
            scraping_context = get_or_fetch(product_id=product_id, url=sales_page_url)
            if scraping_context:
                return KnowledgeResult(
                    source=KnowledgeSource.SCRAPING,
                    context=scraping_context,
                    confidence=0.50,
                )
    except Exception:
        pass

    return KnowledgeResult(
        source=KnowledgeSource.FALLBACK,
        context=FALLBACK_CONTEXT,
        confidence=0.0,
    )
