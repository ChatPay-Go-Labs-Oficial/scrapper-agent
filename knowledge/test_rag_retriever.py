"""Unit tests for the RAG retriever (F2-KNW-001)."""

import pytest

from knowledge.rag_retriever import retrieve, validate_ownership


class FakeDbPool:
    def __init__(self, ownership_result, rows):
        self._ownership_result = ownership_result
        self._rows = rows

    async def fetchval(self, _query, *_args):
        return self._ownership_result

    async def fetch(self, _query, *_args):
        return self._rows


@pytest.mark.asyncio
async def test_validate_ownership_rejects_invalid():
    db_pool = FakeDbPool(None, [])
    with pytest.raises(PermissionError):
        await validate_ownership("prod-1", "seller-1", db_pool)


@pytest.mark.asyncio
async def test_retrieve_filters_below_threshold():
    rows = [
        {"chunk_text": "A", "similarity": 0.55},
        {"chunk_text": "B", "similarity": 0.59},
    ]
    db_pool = FakeDbPool("prod-1", rows)
    result = await retrieve([0.1, 0.2], "prod-1", "seller-1", db_pool, similarity_threshold=0.60)
    assert result is None


@pytest.mark.asyncio
async def test_retrieve_returns_joined_chunks():
    rows = [
        {"chunk_text": "Primeiro", "similarity": 0.90},
        {"chunk_text": "Segundo", "similarity": 0.80},
    ]
    db_pool = FakeDbPool("prod-1", rows)
    result = await retrieve([0.1, 0.2], "prod-1", "seller-1", db_pool)
    assert result == "Primeiro\n\n---\n\nSegundo"
