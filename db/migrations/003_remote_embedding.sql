-- Permit the verified remote model while keeping the old vectors until atomic replacement.
ALTER TABLE document_chunks DROP CONSTRAINT document_chunks_embedding_model_check;
ALTER TABLE document_chunks ADD CONSTRAINT document_chunks_embedding_model_check CHECK (
    (embedding IS NULL AND embedding_model IS NULL)
    OR (embedding IS NOT NULL AND embedding_model IN (
        'BAAI/bge-small-en-v1.5', 'Qwen/Qwen3-Embedding-4B'
    ))
);
COMMENT ON COLUMN document_chunks.embedding IS 'Normalized 384-dimensional embeddings; query and document model must match.';
