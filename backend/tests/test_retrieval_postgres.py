"""Opt-in real pgvector tests using connection-local temporary tables only."""

import os

import psycopg
import pytest

from app.embeddings.model import MODEL_NAME
from app.ingestion.medlineplus import database_url
from app.retrieval.service import retrieve_chunks

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1", reason="Set RUN_DB_TESTS=1 with Docker PostgreSQL running",
)


def test_exact_ranking_filters_and_attribution():
    vector = [1.0] + [0.0] * 383
    with psycopg.connect(database_url(), connect_timeout=10) as connection:
        with connection.cursor() as cursor:
            # Shadow real tables; nothing is inserted/deleted in the application corpus.
            cursor.execute("CREATE TEMP TABLE sources (id bigint, name text) ON COMMIT DROP")
            cursor.execute("CREATE TEMP TABLE documents (id bigint, source_id bigint, title text, source text, source_url text) ON COMMIT DROP")
            cursor.execute("CREATE TEMP TABLE document_chunks (id bigint, document_id bigint, chunk_index int, content text, embedding vector(384), embedding_model text) ON COMMIT DROP")
            assert retrieve_chunks(connection, vector, 3) == []
            cursor.execute("INSERT INTO sources VALUES (1, 'MedlinePlus'), (2, 'Other')")
            cursor.execute("INSERT INTO documents VALUES (1, 1, 'Synthetic topic', 'MedlinePlus', 'https://example.invalid/synthetic'), (2, 2, 'Other', 'Other', 'https://example.invalid/other')")
            cursor.executemany(
                "INSERT INTO document_chunks VALUES (%s, %s, 0, 'Synthetic evidence', %s::vector, %s)",
                [(1, 1, str(vector), MODEL_NAME),
                 (2, 1, str([0.0, 1.0] + [0.0] * 382), MODEL_NAME),
                 (3, 1, str([-1.0] + [0.0] * 383), MODEL_NAME),
                 (4, 1, str(vector), "wrong-model"),
                 (5, 1, None, MODEL_NAME), (6, 2, str(vector), MODEL_NAME),
                 (7, 1, str(vector), MODEL_NAME)],
            )
        hits = retrieve_chunks(connection, vector, 20)
        assert [h.chunk_id for h in hits] == [1, 7, 2, 3]
        assert [h.similarity for h in hits] == pytest.approx([1, 1, 0, -1])
        assert hits[0].source_url == "https://example.invalid/synthetic"
        assert hits[0].title == "Synthetic topic"
        assert len(retrieve_chunks(connection, vector, 1)) == 1
