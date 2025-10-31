CREATE EXTENSION IF NOT EXISTS vector;

CREATE SCHEMA IF NOT EXISTS public;

GRANT ALL ON SCHEMA public TO PUBLIC;

COMMENT ON EXTENSION vector IS 'Extensão pgvector para armazenamento e busca de vetores (embeddings)';

SELECT
    extname AS extension_name,
    extversion AS version
FROM pg_extension
WHERE extname = 'vector';
