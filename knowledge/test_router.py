"""Unit tests for the knowledge router (F2-KNW-003)."""

import pytest

from knowledge.router import KnowledgeSource, resolve_knowledge


class _FakeDbPool:
    def __init__(self, rows):
        self._rows = rows

    async def fetchrow(self, _query, *_args):
        return self._rows.get("faq")

    async def fetchval(self, _query, *_args):
        return self._rows.get("ownership")

    async def fetch(self, _query, *_args):
        return self._rows.get("rag", [])


@pytest.mark.asyncio
async def test_router_prefers_faq(monkeypatch):
    async def _faq_search(_embedding, _product_id, _db_pool, threshold=0.92):
        return "FAQ answer"

    async def _rag_retrieve(*_args, **_kwargs):
        return "RAG context"

    monkeypatch.setattr("knowledge.faq_matcher.search", _faq_search)
    monkeypatch.setattr("knowledge.rag_retriever.retrieve", _rag_retrieve)

    db_pool = _FakeDbPool({})
    result = await resolve_knowledge(
        "prod-1",
        "seller-1",
        "query",
        [0.1],
        db_pool,
        sales_page_url="https://example.com",
    )

    assert result.source == KnowledgeSource.FAQ
    assert result.context == "FAQ answer"


@pytest.mark.asyncio
async def test_router_uses_rag_when_faq_missing(monkeypatch):
    async def _faq_search(_embedding, _product_id, _db_pool, threshold=0.92):
        return None

    async def _rag_retrieve(*_args, **_kwargs):
        return "RAG context"

    monkeypatch.setattr("knowledge.faq_matcher.search", _faq_search)
    monkeypatch.setattr("knowledge.rag_retriever.retrieve", _rag_retrieve)

    db_pool = _FakeDbPool({})
    result = await resolve_knowledge(
        "prod-1",
        "seller-1",
        "query",
        [0.1],
        db_pool,
        sales_page_url="https://example.com",
    )

    assert result.source == KnowledgeSource.RAG
    assert result.context == "RAG context"


@pytest.mark.asyncio
async def test_router_uses_scraping_when_rag_missing(monkeypatch):
    async def _faq_search(_embedding, _product_id, _db_pool, threshold=0.92):
        return None

    async def _rag_retrieve(*_args, **_kwargs):
        return None

    def _scrape(*_args, **_kwargs):
        return "Scraping context"

    monkeypatch.setattr("knowledge.faq_matcher.search", _faq_search)
    monkeypatch.setattr("knowledge.rag_retriever.retrieve", _rag_retrieve)
    monkeypatch.setattr("knowledge.router.get_or_fetch", _scrape)

    db_pool = _FakeDbPool({})
    result = await resolve_knowledge(
        "prod-1",
        "seller-1",
        "query",
        [0.1],
        db_pool,
        sales_page_url="https://example.com",
    )

    assert result.source == KnowledgeSource.SCRAPING
    assert result.context == "Scraping context"


@pytest.mark.asyncio
async def test_router_fallback_when_all_missing(monkeypatch):
    async def _faq_search(_embedding, _product_id, _db_pool, threshold=0.92):
        return None

    async def _rag_retrieve(*_args, **_kwargs):
        return None

    def _scrape(*_args, **_kwargs):
        return None

    monkeypatch.setattr("knowledge.faq_matcher.search", _faq_search)
    monkeypatch.setattr("knowledge.rag_retriever.retrieve", _rag_retrieve)
    monkeypatch.setattr("knowledge.router.get_or_fetch", _scrape)

    db_pool = _FakeDbPool({})
    result = await resolve_knowledge(
        "prod-1",
        "seller-1",
        "query",
        [0.1],
        db_pool,
        sales_page_url="https://example.com",
    )

    assert result.source == KnowledgeSource.FALLBACK
    assert result.context
