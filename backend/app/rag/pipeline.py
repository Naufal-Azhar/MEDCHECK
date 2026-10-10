"""Phase 9 retrieval-to-context pipeline; no LLM call yet."""

from app.rag.context import GroundedContext, build_context
from app.retrieval.service import SearchResult, search
from app.retrieval.service import validate_request
from app.safety.policy import requires_refusal
from uuid import uuid4


def retrieve_context(connection, question: str, top_k: int = 5) -> tuple[SearchResult, GroundedContext]:
    question = validate_request(question, top_k)
    if requires_refusal(question):
        # Do not embed or retrieve personal case descriptions.
        return SearchResult(str(uuid4()), [], 0.0, 0.0), build_context(question, [])
    result = search(connection, question, top_k)
    return result, build_context(question, result.hits)
