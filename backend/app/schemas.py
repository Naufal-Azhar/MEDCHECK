"""Public API request and response schemas."""

from pydantic import BaseModel, Field, field_validator


class QuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)

    @field_validator("question")
    @classmethod
    def normalize_question(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("question must not be blank")
        return value


class SourceResponse(BaseModel):
    id: int
    name: str
    base_url: str
    authority_level: str
    metadata: dict


class SearchHitResponse(BaseModel):
    citation_id: str
    chunk_id: int
    document_id: int
    chunk_index: int
    title: str
    source: str
    source_url: str
    content: str
    similarity: float


class SearchResponse(BaseModel):
    request_id: str
    question: str
    hits: list[SearchHitResponse]
    embedding_ms: float
    retrieval_ms: float
    notice: str
    status: str = "retrieved"
    safety_reason: str | None = None


class ChatSource(BaseModel):
    citation_id: str
    chunk_id: int
    document_id: int
    title: str
    source: str
    source_url: str
    quote: str


class ChatResponse(BaseModel):
    request_id: str
    status: str
    answer: str
    key_points: list[str]
    sources: list[ChatSource]
    confidence_or_uncertainty: str
    safety_note: str
    usage: dict | None = None
    safety_reason: str | None = None
