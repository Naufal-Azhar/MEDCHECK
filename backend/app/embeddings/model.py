"""Locked remote embeddings; no local inference or model download."""

import logging
import math
from time import perf_counter
from uuid import uuid4

import httpx

from app.llm.config import load_settings

MODEL_NAME = "Qwen/Qwen3-Embedding-4B"
EMBEDDING_DIMENSION = 384
QUERY_INSTRUCTION = "Instruct: Given a healthcare question, retrieve relevant passages that answer the question\nQuery: "
logger = logging.getLogger(__name__)


class EmbeddingError(RuntimeError):
    pass


def encode_texts(texts, *, transport=None):
    if not texts:
        return [], 0
    if len(texts) > 32 or any(not isinstance(t, str) or not t.strip() or len(t) > 10000 for t in texts):
        raise ValueError("Invalid embedding input or batch size")
    settings = load_settings()
    request_id = str(uuid4())
    started = perf_counter()
    try:
        with httpx.Client(transport=transport, timeout=settings.timeout_seconds,
                          follow_redirects=False, trust_env=False) as client:
            response = client.post(settings.base_url + "/embeddings",
                headers={"Authorization": "Bearer " + settings.api_key},
                json={"model": MODEL_NAME, "input": texts, "dimensions": EMBEDDING_DIMENSION,
                      "encoding_format": "float"})
        if response.status_code != 200:
            raise EmbeddingError(f"Embedding provider returned HTTP {response.status_code}; no retry made.")
        data = response.json()
        rows = data["data"]
        if len(rows) != len(texts) or sorted(r["index"] for r in rows) != list(range(len(texts))):
            raise ValueError("Invalid indices")
        vectors = []
        for row in sorted(rows, key=lambda r: r["index"]):
            v = row["embedding"]
            if not isinstance(v, list) or len(v) != EMBEDDING_DIMENSION:
                raise ValueError("Invalid dimension")
            if any(type(x) not in (int, float) or not math.isfinite(x) for x in v):
                raise ValueError("Invalid vector")
            norm = math.sqrt(sum(x*x for x in v))
            if not math.isfinite(norm) or norm <= 0:
                raise ValueError("Invalid norm")
            vectors.append([x / norm for x in v])
        tokens = data["usage"]["prompt_tokens"]
        if type(tokens) is not int or tokens < 0:
            raise ValueError("Invalid usage")
    except httpx.HTTPError:
        raise EmbeddingError("Embedding network/timeout failure; no retry made.") from None
    except (ValueError, KeyError, TypeError, IndexError):
        raise EmbeddingError("Invalid embedding response; no retry made.") from None
    logger.info("embedding_completed request_id=%s count=%s prompt_tokens=%s duration_ms=%.2f",
                request_id, len(vectors), tokens, (perf_counter()-started)*1000)
    return vectors, tokens


def encode_documents(texts):
    vectors = []
    total = 0
    for start in range(0, len(texts), 16):
        batch, tokens = encode_texts(texts[start:start+16])
        vectors.extend(batch)
        total += tokens
    logger.info("document_embedding_tokens=%s", total)
    return vectors


def encode_query(query):
    if not isinstance(query, str) or not query.strip() or len(query) > 2000:
        raise ValueError("Query must contain 1-2000 characters")
    return encode_texts([QUERY_INSTRUCTION + query])[0][0]
