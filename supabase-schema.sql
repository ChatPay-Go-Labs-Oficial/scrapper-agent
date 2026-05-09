-- Supabase Schema — AI Service Database
-- Run this once in the Supabase SQL editor before deploying the AI service.

CREATE EXTENSION IF NOT EXISTS vector;

-- product_min: synced from backend. Used for ownership validation without
-- requiring a cross-service DB call to the backend Railway PostgreSQL.
CREATE TABLE IF NOT EXISTS product_min (
    product_id     UUID        PRIMARY KEY,
    seller_id      UUID        NOT NULL,
    sales_page_url TEXT,
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_product_min_seller ON product_min(seller_id);

-- knowledge_chunks: ebook content split into chunks with vector embeddings.
-- Isolated strictly per product_id — no cross-tenant queries allowed.
CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id  UUID        NOT NULL,
    seller_id   UUID        NOT NULL,
    chunk_text  TEXT        NOT NULL,
    embedding   vector(768) NOT NULL,
    chunk_index INT         NOT NULL,
    source_type VARCHAR(20) NOT NULL CHECK (source_type IN ('ebook_pdf', 'faq', 'landing_page')),
    source_meta JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_kc_product_embedding
    ON knowledge_chunks USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
CREATE INDEX IF NOT EXISTS idx_kc_product_id ON knowledge_chunks(product_id);
CREATE INDEX IF NOT EXISTS idx_kc_seller_id  ON knowledge_chunks(seller_id);

-- product_faqs: seller-defined Q&A pairs with semantic embeddings for zero-LLM answers.
CREATE TABLE IF NOT EXISTS product_faqs (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id  UUID        NOT NULL,
    seller_id   UUID        NOT NULL,
    question    TEXT        NOT NULL,
    answer      TEXT        NOT NULL,
    q_embedding vector(768) NOT NULL,
    is_active   BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_faq_product_embedding
    ON product_faqs USING hnsw (q_embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_faq_product_id ON product_faqs(product_id);

-- ai_usage_logs: per-session token and cost tracking written by the AI service.
-- Used for billing and observability (Phase 3+).
CREATE TABLE IF NOT EXISTS ai_usage_logs (
    id               UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    seller_id        UUID          NOT NULL,
    product_id       UUID          NOT NULL,
    session_id       VARCHAR(64)   NOT NULL,
    tokens_in        INT           NOT NULL,
    tokens_out       INT           NOT NULL,
    model_used       VARCHAR(50)   NOT NULL,
    knowledge_source VARCHAR(20)   NOT NULL,
    cost_usd         NUMERIC(10,8) NOT NULL,
    latency_ms       INT,
    created_at       TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_usage_seller_month
    ON ai_usage_logs(seller_id, created_at);
