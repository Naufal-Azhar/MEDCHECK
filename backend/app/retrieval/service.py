"""Exact cosine retrieval over the configured MedlinePlus corpus."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from time import perf_counter
from uuid import uuid4

from app.embeddings.model import EMBEDDING_DIMENSION, MODEL_NAME, encode_query
from app.safety.policy import screen_question, instruction_attack

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SearchHit:
    chunk_id: int
    document_id: int
    chunk_index: int
    content: str
    title: str
    source_id: int
    source: str
    source_url: str
    similarity: float


@dataclass(frozen=True)
class SearchResult:
    request_id: str
    hits: list[SearchHit]
    embedding_ms: float
    retrieval_ms: float
    notice: str = (
        "Retrieved source excerpts, not an AI answer or medical advice. "
        "Similarity ranks candidates; it does not establish relevance or medical confidence."
    )


def validate_request(question: str, top_k: int) -> str:
    if not isinstance(question, str) or not question.strip():
        raise ValueError("Question must be non-empty text")
    if len(question) > 2000:
        raise ValueError("Question must be at most 2000 characters")
    if type(top_k) is not int or not 1 <= top_k <= 20:
        raise ValueError("top_k must be an integer between 1 and 20")
    return question.strip()


def retrieve_chunks(connection, vector: list[float], top_k: int) -> list[SearchHit]:
    if type(top_k) is not int or not 1 <= top_k <= 20:
        raise ValueError("top_k must be an integer between 1 and 20")
    if len(vector) != EMBEDDING_DIMENSION or any(
        type(v) not in (int, float) or not math.isfinite(v) for v in vector
    ):
        raise ValueError("Query vector must contain 384 finite numbers")
    if not math.isclose(math.sqrt(sum(v * v for v in vector)), 1.0, abs_tol=1e-4):
        raise ValueError("Query vector must be normalized")

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT c.id, d.id, c.chunk_index, c.content, d.title,
                   s.id, s.name, d.source_url,
                   1 - (c.embedding <=> %s::vector) AS similarity
            FROM document_chunks c
            JOIN documents d ON d.id = c.document_id
            JOIN sources s ON s.id = d.source_id
            WHERE c.embedding IS NOT NULL AND c.embedding_model = %s
              AND s.name = %s AND d.source = %s
            ORDER BY c.embedding <=> %s::vector, c.id
            LIMIT %s
            """,
            (str(vector), MODEL_NAME, "MedlinePlus", "MedlinePlus", str(vector), top_k),
        )
        return [hit for row in cursor.fetchall() if not instruction_attack((hit := SearchHit(*row)).content)]


def search(connection, question: str, top_k: int = 5) -> SearchResult:
    request_id = str(uuid4())
    try:
        question = validate_request(question, top_k)
        decision = screen_question(question)
        if decision:
            logger.info("retrieval_blocked request_id=%s reason=%s", request_id, decision.reason)
            return SearchResult(request_id, [], 0.0, 0.0, decision.message)
        started = perf_counter()
        vector = encode_query(question)
        embedding_ms = (perf_counter() - started) * 1000
        started = perf_counter()
        hits = retrieve_chunks(connection, vector, top_k)
        retrieval_ms = (perf_counter() - started) * 1000
    except Exception as exc:
        # No question, chunk text, DSN, or exception message in operational logs.
        logger.error("retrieval_failed request_id=%s error_type=%s", request_id, type(exc).__name__)
        raise
    logger.info(
        "retrieval_completed request_id=%s embedding_ms=%.2f retrieval_ms=%.2f chunks=%s source_ids=%s",
        request_id, embedding_ms, retrieval_ms, len(hits), sorted({hit.source_id for hit in hits}),
    )
    return SearchResult(request_id, hits, embedding_ms, retrieval_ms)
