"""FastAPI HTTP layer around the retrieval and grounded-generation services."""

from __future__ import annotations

import logging
from dataclasses import asdict
from time import perf_counter
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request

from app.db import connect
from app.llm.config import ConfigurationError, load_settings
from app.rag.answer import generate_answer
from app.rag.answer import preflight_answer
from app.rag.pipeline import retrieve_context
from app.retrieval.service import SearchHit, validate_request
from app.schemas import ChatResponse, QuestionRequest, SearchHitResponse, SearchResponse, SourceResponse
from app.safety.policy import requires_refusal

logger = logging.getLogger(__name__)
router = APIRouter()


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", str(uuid4()))


def _hit_response(hit: SearchHit, index: int) -> SearchHitResponse:
    return SearchHitResponse(
        citation_id=f"S{index}", chunk_id=hit.chunk_id, document_id=hit.document_id,
        chunk_index=hit.chunk_index, title=hit.title, source=hit.source,
        source_url=hit.source_url, content=hit.content, similarity=hit.similarity,
    )


@router.get("/health")
def health() -> dict:
    result = {"status": "ok", "service": "forgehacks-healthcare-assistant", "database": "unknown"}
    try:
        with connect() as connection:
            connection.execute("SELECT 1")
        result["database"] = "ok"
    except Exception:
        result["database"] = "unavailable"
        # Health stays safe and useful even if DB is temporarily down.
        result["status"] = "degraded"
    return result


@router.post("/search", response_model=SearchResponse)
def search(request: Request, payload: QuestionRequest) -> SearchResponse:
    request_id = _request_id(request)
    started = perf_counter()
    try:
        validate_request(payload.question, payload.top_k)
        preflight = preflight_answer(payload.question)
        if preflight:
            logger.info("api_preflight request_id=%s reason=%s", request_id, preflight.safety_reason)
            return SearchResponse(request_id=request_id, question="", hits=[], embedding_ms=0,
                                  retrieval_ms=0, notice=preflight.answer, status=preflight.status,
                                  safety_reason=preflight.safety_reason)
        with connect() as connection:
            result, _ = retrieve_context(connection, payload.question, payload.top_k)
        hits = [_hit_response(hit, index) for index, hit in enumerate(result.hits, 1)]
        logger.info("api_search request_id=%s chunks=%s duration_ms=%.2f", request_id, len(hits),
                    (perf_counter() - started) * 1000)
        return SearchResponse(request_id=request_id, question=payload.question, hits=hits,
                              embedding_ms=result.embedding_ms, retrieval_ms=result.retrieval_ms,
                              notice=result.notice)
    except ValueError:
        raise HTTPException(status_code=422, detail="Search input could not be processed") from None
    except Exception as exc:
        logger.error("api_search_failed request_id=%s error_type=%s", request_id, type(exc).__name__)
        raise HTTPException(status_code=503, detail="Search service unavailable") from None


@router.post("/chat", response_model=ChatResponse)
def chat(request: Request, payload: QuestionRequest) -> ChatResponse:
    request_id = _request_id(request)
    try:
        validate_request(payload.question, payload.top_k)
        preflight = preflight_answer(payload.question)
        if preflight:
            logger.info("api_preflight request_id=%s reason=%s", request_id, preflight.safety_reason)
            return ChatResponse(request_id=request_id, **asdict(preflight))
        settings = load_settings()
        with connect() as connection:
            retrieval, context = retrieve_context(connection, payload.question, payload.top_k)
        result = generate_answer(context, settings)
        logger.info("api_chat request_id=%s status=%s chunks=%s", request_id, result.status,
                    len(context.evidence))
        return ChatResponse(request_id=request_id, status=result.status, answer=result.answer,
                            key_points=result.key_points, sources=result.sources,
                            confidence_or_uncertainty=result.confidence_or_uncertainty,
                            safety_note=result.safety_note, usage=result.usage, safety_reason=result.safety_reason)
    except ConfigurationError:
        raise HTTPException(status_code=503, detail="LLM service is not configured") from None
    except ValueError:
        raise HTTPException(status_code=422, detail="Chat input could not be processed") from None
    except Exception as exc:
        logger.error("api_chat_failed request_id=%s error_type=%s", request_id, type(exc).__name__)
        raise HTTPException(status_code=503, detail="Chat service unavailable") from None


@router.get("/sources/{source_id}", response_model=SourceResponse)
def source(source_id: int) -> SourceResponse:
    try:
        with connect() as connection:
            row = connection.execute(
                "SELECT id, name, base_url, authority_level, metadata FROM sources WHERE id = %s",
                (source_id,),
            ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Source not found")
        return SourceResponse(id=row[0], name=row[1], base_url=row[2],
                              authority_level=row[3], metadata=row[4])
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("api_source_failed source_id=%s error_type=%s", source_id, type(exc).__name__)
        raise HTTPException(status_code=503, detail="Source service unavailable") from None
