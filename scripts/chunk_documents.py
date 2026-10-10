"""Create deterministic chunks for documents stored in PostgreSQL.

Run from the project root:
    python scripts/chunk_documents.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.ingestion.chunking import chunk_text  # noqa: E402
from app.ingestion.medlineplus import database_url  # noqa: E402


def main() -> int:
    documents_processed = 0
    chunks_written = 0

    with psycopg.connect(database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, metadata->>'content' FROM documents "
                "WHERE metadata->>'content' IS NOT NULL ORDER BY id"
            )
            documents = cursor.fetchall()

            for document_id, content in documents:
                chunks = chunk_text(content)
                cursor.execute(
                    "DELETE FROM document_chunks WHERE document_id = %s",
                    (document_id,),
                )
                for chunk in chunks:
                    cursor.execute(
                        """
                        INSERT INTO document_chunks
                            (document_id, chunk_index, content, metadata)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (
                            document_id,
                            chunk.chunk_index,
                            chunk.content,
                            json.dumps(chunk.metadata),
                        ),
                    )
                documents_processed += 1
                chunks_written += len(chunks)

    print(f"Documents processed: {documents_processed}")
    print(f"Chunks written: {chunks_written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
