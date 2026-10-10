-- Apply with psql --single-transaction -v ON_ERROR_STOP=1.
ALTER TABLE document_chunks
    ALTER COLUMN embedding TYPE vector(384) USING embedding::vector(384);

ALTER TABLE document_chunks
    ADD COLUMN IF NOT EXISTS embedding_model TEXT;

ALTER TABLE document_chunks DROP CONSTRAINT IF EXISTS document_chunks_embedding_model_check;
ALTER TABLE document_chunks ADD CONSTRAINT document_chunks_embedding_model_check CHECK (
    (embedding IS NULL AND embedding_model IS NULL)
    OR (embedding IS NOT NULL AND embedding_model IS NOT NULL
        AND embedding_model = 'BAAI/bge-small-en-v1.5')
);

COMMENT ON COLUMN document_chunks.embedding IS
    'Normalized 384-dimensional BAAI/bge-small-en-v1.5 embedding; cosine distance.';
