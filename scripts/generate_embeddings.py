"""Generate local embeddings for stored document chunks."""

from __future__ import annotations

import json
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.embeddings.model import EMBEDDING_DIMENSION, MODEL_NAME, encode_documents  # noqa: E402
from app.ingestion.medlineplus import database_url  # noqa: E402


OUTPUT_PATH = Path("data/processed/embeddings.jsonl")


def main() -> int:
    with psycopg.connect(database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, content FROM document_chunks ORDER BY id"
            )
            rows = cursor.fetchall()

    embeddings = encode_documents([content for _, content in rows])
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc).isoformat()
    with OUTPUT_PATH.open("w", encoding="utf-8") as output:
        for (chunk_id, content), embedding in zip(rows, embeddings, strict=True):
            output.write(
                json.dumps(
                    {
                        "chunk_id": chunk_id,
                        "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                        "model": MODEL_NAME,
                        "dimension": EMBEDDING_DIMENSION,
                        "generated_at": generated_at,
                        "embedding": embedding,
                    }
                )
                + "\n"
            )

    print(f"Embedding model: {MODEL_NAME}")
    print(f"Embedding dimension: {EMBEDDING_DIMENSION}")
    print(f"Chunks embedded: {len(embeddings)}")
    print(f"Artifact: {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
