"""Unit tests for the FAQ matcher (F2-KNW-002)."""

import pytest

from knowledge.faq_matcher import search


class FakeDbPool:
    def __init__(self, row):
        self._row = row

    async def fetchrow(self, _query, *_args):
        return self._row


@pytest.mark.asyncio
async def test_returns_answer_when_above_threshold():
    row = {"answer": "O produto custa R$ 197,00", "similarity": 0.95}
    db_pool = FakeDbPool(row)
    result = await search([0.1, 0.2], "prod-1", db_pool)
    assert result == "O produto custa R$ 197,00"


@pytest.mark.asyncio
async def test_returns_none_when_below_threshold():
    row = {"answer": "Resposta", "similarity": 0.80}
    db_pool = FakeDbPool(row)
    result = await search([0.1, 0.2], "prod-1", db_pool, threshold=0.92)
    assert result is None


@pytest.mark.asyncio
async def test_returns_none_when_no_row():
    db_pool = FakeDbPool(None)
    result = await search([0.1, 0.2], "prod-1", db_pool)
    assert result is None
