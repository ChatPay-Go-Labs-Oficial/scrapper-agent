"""
Testes unitários e de integração para o Worker de Ingestão de PDFs.
Execução: uv run pytest worker/test_ingestion.py -v
"""
import asyncio
import os
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Adiciona raiz do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from worker.ingestion_worker import (
    _chunk_text,
    _extract_text_from_pdf,
    _parse_bullmq_job,
)


# ──────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────

SAMPLE_TEXT = """
Este é o capítulo 1 do nosso e-book sobre chá.
O chá é uma das bebidas mais consumidas do mundo, com história milenar.
Existem diferentes tipos: chá verde, preto, branco, oolong e pu-erh.

Capítulo 2: Benefícios do Chá
O chá possui antioxidantes como catequinas e polifenóis.
Estudos mostram que o consumo regular pode reduzir o risco de doenças cardiovasculares.
A cafeína presente no chá proporciona energia sem o pico e queda do café.

Capítulo 3: Como Preparar o Chá Perfeito
A temperatura da água é crucial para cada tipo de chá.
Chá verde: 70-80°C por 2-3 minutos.
Chá preto: 95-100°C por 3-5 minutos.
Chá branco: 75-85°C por 2-4 minutos.
""" * 20  # Repetindo para ter texto suficiente para chunking


# ──────────────────────────────────────────────────────────────
# Testes Unitários
# ──────────────────────────────────────────────────────────────

class TestChunkText:
    def test_chunks_texto_longo(self):
        """Texto longo deve ser dividido em múltiplos chunks."""
        chunks = _chunk_text(SAMPLE_TEXT)
        assert len(chunks) > 1, "Texto longo deve gerar múltiplos chunks"

    def test_chunks_nao_vazios(self):
        """Nenhum chunk deve ser uma string vazia."""
        chunks = _chunk_text(SAMPLE_TEXT)
        for chunk in chunks:
            assert chunk.strip(), f"Chunk vazio encontrado: '{chunk}'"

    def test_chunk_texto_curto(self):
        """Texto curto deve gerar no mínimo 1 chunk."""
        texto_curto = "Este é um texto curto de teste."
        chunks = _chunk_text(texto_curto)
        assert len(chunks) >= 1

    def test_chunk_texto_vazio(self):
        """Texto vazio deve retornar lista vazia."""
        chunks = _chunk_text("")
        assert chunks == []


class TestExtractTextFromPdf:
    def test_pdf_invalido_levanta_erro(self, tmp_path):
        """Bytes inválidos (não são PDF) devem levantar exceção."""
        fake_pdf = b"this is not a pdf"
        with pytest.raises(Exception):
            _extract_text_from_pdf(fake_pdf)

    def test_pdf_real_extrai_texto(self, tmp_path):
        """PDF real com texto deve retornar texto não vazio."""
        # Cria um PDF mínimo com texto usando o próprio pdfplumber/reportlab se disponível
        # Por simplicidade, apenas verifica que a função existe e levanta em caso de PDF vazio
        try:
            import reportlab.pdfgen.canvas as canvas
            import io

            buf = io.BytesIO()
            c = canvas.Canvas(buf)
            c.drawString(100, 750, "Chá para todos!")
            c.save()
            pdf_bytes = buf.getvalue()

            text = _extract_text_from_pdf(pdf_bytes)
            assert "Chá" in text or len(text) > 0
        except ImportError:
            pytest.skip("reportlab não instalado, pulando teste de PDF real")


class TestParseBullmqJob:
    @pytest.mark.asyncio
    async def test_parse_job_valido(self):
        """Job com dados válidos deve retornar dicionário correto."""
        import json

        mock_redis = AsyncMock()
        mock_redis.hgetall.return_value = {
            b"data": json.dumps({
                "jobId": "abc-123",
                "productId": "prod-456",
                "sellerId": "seller-789",
                "r2Key": "ebooks/seller-789/prod-456/file.pdf",
            }).encode()
        }

        result = await _parse_bullmq_job(mock_redis, "1")
        assert result is not None
        assert result["productId"] == "prod-456"
        assert result["sellerId"] == "seller-789"

    @pytest.mark.asyncio
    async def test_parse_job_vazio(self):
        """Job key inexistente no Redis deve retornar None."""
        mock_redis = AsyncMock()
        mock_redis.hgetall.return_value = {}

        result = await _parse_bullmq_job(mock_redis, "999")
        assert result is None

    @pytest.mark.asyncio
    async def test_parse_job_json_invalido(self):
        """Job com data inválida (JSON quebrado) deve retornar None."""
        mock_redis = AsyncMock()
        mock_redis.hgetall.return_value = {
            b"data": b"isto nao e json valido!!!"
        }

        result = await _parse_bullmq_job(mock_redis, "1")
        assert result is None
