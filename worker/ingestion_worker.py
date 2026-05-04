"""
Worker de Ingestão de PDFs — F1-ING-002
Consome jobs da fila BullMQ via Redis, processa PDFs e insere vetores no pgvector.
"""
import asyncio
import json
import logging
import os
import tempfile
from typing import Any

import asyncpg
import boto3
import pdfplumber
from dotenv import load_dotenv
from openai import OpenAI
from redis.asyncio import Redis
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

load_dotenv()

# ──────────────────────────────────────────────────────────────
# Configuração de Logging
# ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ingestion_worker")

# ──────────────────────────────────────────────────────────────
# Configurações
# ──────────────────────────────────────────────────────────────
WORKER_DATABASE_URL: str = os.getenv("WORKER_DATABASE_URL", "")
WORKER_REDIS_URL: str = os.getenv("WORKER_REDIS_URL", "redis://localhost:6379/0")
R2_ENDPOINT: str = f"https://{os.getenv('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com"
R2_BUCKET: str = os.getenv("R2_BUCKET_NAME", "")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

BULLMQ_QUEUE_NAME = "ebook-ingestion"
BULLMQ_WAIT_KEY = f"bull:{BULLMQ_QUEUE_NAME}:wait"
BULLMQ_ACTIVE_KEY = f"bull:{BULLMQ_QUEUE_NAME}:active"
BULLMQ_JOB_KEY_PREFIX = f"bull:{BULLMQ_QUEUE_NAME}"

# OpenAI text-embedding-3-small: $0.02/1M tokens, suporta Matryoshka (dimensões reduzidas)
# 768 dims compatível com a coluna vector(768) do banco, sem migration necessária
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 768  # Compatível com coluna vector(768) do banco
EMBEDDING_BATCH_SIZE = 100  # OpenAI suporta até 2048 textos por batch; 100 é seguro
CHUNK_SIZE_TOKENS = 500
POLL_TIMEOUT_SECONDS = 5


# ──────────────────────────────────────────────────────────────
# Funções de Processamento
# ──────────────────────────────────────────────────────────────

def _extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extrai texto de um PDF preservando ordem de leitura. Levanta ValueError se vazio."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name
    try:
        with pdfplumber.open(tmp_path) as pdf:
            pages_text = []
            for page in pdf.pages:
                text = page.extract_text(layout=True) or ""
                pages_text.append(text.strip())
        full_text = "\n\n".join(p for p in pages_text if p)
        if not full_text.strip():
            raise ValueError("PDF sem conteúdo textual extraível (pode ser um PDF de imagem escaneada)")
        return full_text
    finally:
        os.unlink(tmp_path)


def _chunk_text(text: str) -> list[str]:
    """
    Divide o texto em chunks por tokens usando chonkie.
    Retorna lista de strings (textos dos chunks).
    """
    from chonkie import TokenChunker
    chunker = TokenChunker(
        chunk_size=CHUNK_SIZE_TOKENS,
        chunk_overlap=50,
    )
    chunks = chunker.chunk(text)
    return [c.text for c in chunks if c.text.strip()]


def _sanitize_text(text: str) -> str:
    """Remove caracteres inválidos para o PostgreSQL (null bytes e outros)."""
    # PostgreSQL não aceita o caracter \x00 (null byte) em strings TEXT
    return text.replace('\x00', '').replace('\u0000', '')


def _download_from_r2(r2_key: str) -> bytes:
    """Download síncrono do arquivo do Cloudflare R2 via boto3."""
    s3 = boto3.client(
        "s3",
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
        region_name="auto",
    )
    response = s3.get_object(Bucket=R2_BUCKET, Key=r2_key)
    return response["Body"].read()


@retry(
    retry=retry_if_exception_type(Exception),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=5, max=30),
    reraise=True,
)
async def _generate_embeddings_batched(texts: list[str]) -> list[list[float]]:
    """
    Gera embeddings em batch via OpenAI text-embedding-3-small.
    Sem rate limits problemáticos: $0.02/1M tokens, ~$0.004 por PDF completo.
    Suporta Matryoshka: parâmetro 'dimensions' reduz 1536→768 sem migration no banco.
    """
    client = OpenAI(api_key=OPENAI_API_KEY)
    all_embeddings: list[list[float]] = []
    total_batches = (len(texts) + EMBEDDING_BATCH_SIZE - 1) // EMBEDDING_BATCH_SIZE
    for i in range(0, len(texts), EMBEDDING_BATCH_SIZE):
        batch = texts[i : i + EMBEDDING_BATCH_SIZE]
        batch_num = i // EMBEDDING_BATCH_SIZE + 1
        logger.info("Embedding batch %d/%d (%d textos)...", batch_num, total_batches, len(batch))
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=batch,
            dimensions=EMBEDDING_DIMENSIONS,  # Matryoshka: reduz 1536→768 sem migration
        )
        all_embeddings.extend([item.embedding for item in response.data])
    logger.info("Total de tokens consumidos neste job: ~%d", response.usage.total_tokens)
    return all_embeddings


async def process_ebook_job(pg: asyncpg.Connection, job_data: dict[str, Any]) -> None:
    """
    Orquestra todo o pipeline de ingestão de um único job.
    Atualiza o status no banco em cada etapa.
    """
    ingestion_job_id = job_data.get("jobId") or job_data.get("ingestionJobId")
    product_id = job_data["productId"]
    seller_id = job_data["sellerId"]
    r2_key = job_data["r2Key"]

    if not ingestion_job_id:
        logger.error("Job sem ingestionJobId/jobId — descartando: %s", job_data)
        return

    logger.info("Iniciando ingestão: job=%s produto=%s", ingestion_job_id, product_id)

    try:
        # 1. Marcar como processing
        await pg.execute(
            "UPDATE ingestion_jobs SET status = 'processing', started_at = NOW() WHERE id = $1",
            ingestion_job_id,
        )

        # 2. Download do PDF
        logger.info("Baixando PDF do R2: %s", r2_key)
        pdf_bytes = await asyncio.to_thread(_download_from_r2, r2_key)

        # 3. Extração de texto
        logger.info("Extraindo texto do PDF (%d bytes)...", len(pdf_bytes))
        text = await asyncio.to_thread(_extract_text_from_pdf, pdf_bytes)
        logger.info("Texto extraído: %d caracteres", len(text))

        # 4. Chunking
        logger.info("Dividindo em chunks (size=%d tokens)...", CHUNK_SIZE_TOKENS)
        chunk_texts = await asyncio.to_thread(_chunk_text, text)
        logger.info("Total de chunks gerados: %d", len(chunk_texts))

        if not chunk_texts:
            raise ValueError("Nenhum chunk gerado após o chunking do PDF")

        # 5. Deletar chunks antigos do produto (re-ingestão substitui tudo)
        deleted = await pg.execute(
            "DELETE FROM knowledge_chunks WHERE product_id = $1 AND source_type = 'ebook_pdf'",
            product_id,
        )
        logger.info("Chunks antigos removidos: %s", deleted)

        # 6. Gerar embeddings em batch
        logger.info("Gerando embeddings via %s...", EMBEDDING_MODEL)
        embeddings = await _generate_embeddings_batched(chunk_texts)
        logger.info("Embeddings gerados: %d", len(embeddings))

        # 7. Bulk INSERT no pgvector via SQL raw (TypeORM não suporta vector natively)
        records = [
            (
                product_id,
                seller_id,
                _sanitize_text(chunk_texts[i]),  # Remove null bytes inválidos para o PostgreSQL
                str(embeddings[i]),  # pgvector aceita "[0.1, 0.2, ...]"
                i,
                "ebook_pdf",
                None,
            )
            for i in range(len(chunk_texts))
        ]
        await pg.executemany(
            """
            INSERT INTO knowledge_chunks
                (product_id, seller_id, chunk_text, embedding, chunk_index, source_type, source_meta)
            VALUES ($1, $2, $3, $4::vector, $5, $6, $7)
            """,
            records,
        )
        logger.info("Chunks inseridos no pgvector: %d", len(records))

        # 8. Atualizar produto e job
        await pg.execute(
            "UPDATE product SET knowledge_ready = TRUE, knowledge_updated_at = NOW() WHERE id = $1",
            product_id,
        )
        await pg.execute(
            """
            UPDATE ingestion_jobs
            SET status = 'completed', completed_at = NOW(), chunks_created = $2
            WHERE id = $1
            """,
            ingestion_job_id,
            len(chunk_texts),
        )
        logger.info("Ingestão concluída: produto=%s chunks=%d", product_id, len(chunk_texts))

    except Exception as exc:
        logger.exception("Erro na ingestão do job %s: %s", ingestion_job_id, exc)
        await pg.execute(
            "UPDATE ingestion_jobs SET status = 'failed', error_message = $2 WHERE id = $1",
            ingestion_job_id,
            str(exc),
        )
        raise  # Re-raise para o loop saber que falhou (mas não crasha)


# ──────────────────────────────────────────────────────────────
# Loop Principal do Worker
# ──────────────────────────────────────────────────────────────

async def _parse_bullmq_job(redis: Redis, raw_id: str) -> dict[str, Any] | None:
    """
    Lê os dados de um job do BullMQ a partir do seu ID numérico.
    O BullMQ v5 armazena o job como Hash: bull:{queue}:{id}
    """
    job_key = f"{BULLMQ_JOB_KEY_PREFIX}:{raw_id}"
    job_hash = await redis.hgetall(job_key)
    if not job_hash:
        logger.warning("Job key '%s' não encontrada no Redis", job_key)
        return None
    try:
        data_raw = job_hash.get(b"data") or job_hash.get("data") or b"{}"
        if isinstance(data_raw, bytes):
            data_raw = data_raw.decode()
        return json.loads(data_raw)
    except (json.JSONDecodeError, KeyError) as e:
        logger.error("Erro ao parsear job '%s': %s | raw: %s", job_key, e, job_hash)
        return None


async def run_worker() -> None:
    """Loop infinito do worker: aguarda jobs, processa e repete."""
    logger.info("Worker iniciando... Redis: %s | PostgreSQL: %s", WORKER_REDIS_URL, WORKER_DATABASE_URL)

    if not WORKER_DATABASE_URL:
        raise RuntimeError("WORKER_DATABASE_URL não configurada")
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY não configurada")
    if not R2_BUCKET:
        raise RuntimeError("R2_BUCKET_NAME não configurada")

    redis = Redis.from_url(WORKER_REDIS_URL, decode_responses=False)
    pg = await asyncpg.connect(WORKER_DATABASE_URL)

    try:
        logger.info("Worker aguardando jobs na fila '%s'...", BULLMQ_WAIT_KEY)
        while True:
            try:
                # BRPOPLPUSH: move o job de 'wait' para 'active' atomicamente
                result = await redis.brpoplpush(BULLMQ_WAIT_KEY, BULLMQ_ACTIVE_KEY, timeout=POLL_TIMEOUT_SECONDS)
                if result is None:
                    # Timeout: nenhum job na fila, continua aguardando
                    continue

                raw_id = result.decode() if isinstance(result, bytes) else result
                logger.info("Job recebido da fila: id=%s", raw_id)

                job_data = await _parse_bullmq_job(redis, raw_id)
                if job_data is None:
                    logger.warning("Job id=%s sem dados válidos, descartando", raw_id)
                    continue

                try:
                    await process_ebook_job(pg, job_data)
                except Exception:
                    # Erro já logado em process_ebook_job; worker não crasha
                    logger.warning("Job id=%s falhou, continuando para o próximo", raw_id)

            except asyncpg.PostgresError as db_err:
                logger.error("Erro de banco de dados: %s — reconectando...", db_err)
                try:
                    await pg.close()
                except Exception:
                    pass
                pg = await asyncpg.connect(WORKER_DATABASE_URL)

            except Exception as loop_err:
                logger.exception("Erro inesperado no loop do worker: %s", loop_err)
                await asyncio.sleep(2)  # Pequena pausa antes de continuar
    finally:
        logger.info("Worker encerrando...")
        await pg.close()
        await redis.aclose()


if __name__ == "__main__":
    asyncio.run(run_worker())
