"""Validate an entire artifact before storing vectors in one transaction."""

import hashlib
import math

from app.embeddings.model import EMBEDDING_DIMENSION, MODEL_NAME


def validate_records(records: list[dict], contents: dict[int, str]) -> None:
    if not records:
        raise ValueError("Embedding artifact is empty")
    seen = set()
    for record in records:
        chunk_id = record.get("chunk_id")
        if type(chunk_id) is not int or chunk_id not in contents or chunk_id in seen:
            raise ValueError("Unknown or duplicate chunk ID; regenerate embeddings")
        seen.add(chunk_id)
        digest = hashlib.sha256(contents[chunk_id].encode("utf-8")).hexdigest()
        if record.get("content_sha256") != digest:
            raise ValueError("Chunk content changed or hash missing; regenerate embeddings")
        if record.get("model") != MODEL_NAME or record.get("dimension") != EMBEDDING_DIMENSION:
            raise ValueError("Incompatible embedding model or dimension")
        vector = record.get("embedding")
        if not isinstance(vector, list) or len(vector) != EMBEDDING_DIMENSION:
            raise ValueError("Invalid vector dimension")
        if any(type(v) not in (int, float) or not math.isfinite(v) for v in vector):
            raise ValueError("Vector must contain finite numbers")
        if not math.isclose(math.sqrt(sum(v * v for v in vector)), 1.0, abs_tol=1e-4):
            raise ValueError("Vector must be normalized")
    if seen != set(contents):
        raise ValueError("Artifact does not cover current chunks; regenerate embeddings")


def store_records(connection, records: list[dict]) -> int:
    with connection.transaction():
        with connection.cursor() as cursor:
            # Prevent concurrent chunk replacement while checking and writing.
            cursor.execute("LOCK TABLE document_chunks IN SHARE ROW EXCLUSIVE MODE")
            cursor.execute("SELECT id, content FROM document_chunks")
            validate_records(records, dict(cursor.fetchall()))
            cursor.executemany(
                "UPDATE document_chunks SET embedding = %s::vector, embedding_model = %s WHERE id = %s",
                [(str(r["embedding"]), MODEL_NAME, r["chunk_id"]) for r in records],
            )
    return len(records)
