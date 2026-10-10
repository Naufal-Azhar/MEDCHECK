"""Regression from a public-question diagnostic, not private patient data."""

import json

import httpx
import pytest

from app.llm.config import FeatherlessSettings
from app.llm.featherless import TEST_MODEL
from app.rag.answer import SYSTEM_PROMPT, AnswerValidationError, generate_answer, validate_answer
from app.rag.context import build_context
from app.retrieval.service import SearchHit

QUOTE = (
    "Dehydration is a condition caused by the loss of too much fluid from the body. "
    "It happens when you are losing more fluids than you are taking in, and your body "
    "does not have enough fluids to work properly."
)


def context():
    return build_context("What is dehydration?", [SearchHit(
        1, 1, 0, QUOTE, "Dehydration", 1, "MedlinePlus",
        "https://medlineplus.gov/dehydration.html", 0.8)])


def payload(answer):
    return {"status": "answered", "answer": answer, "key_points": [],
            "citations": [{"id": "S1", "quote": QUOTE}], "uncertainty": "General definition only."}


def test_generation_instructions_address_lexical_mismatch_without_disabling_gate():
    assert "not by substituting synonyms" in SYSTEM_PROMPT
    assert "negation, numbers and qualifiers" in SYSTEM_PROMPT
    paraphrase = "Dehydration occurs when the body loses more fluid than it takes in."
    with pytest.raises(AnswerValidationError, match="absent"):
        validate_answer(json.dumps(payload(paraphrase)), context())


def test_short_source_definition_still_requires_claim_review():
    definition = QUOTE.split(". ")[0] + "."
    calls = []

    def handler(request):
        calls.append(json.loads(request.content))
        content = json.dumps(payload(definition)) if len(calls) == 1 else '{"verdict":"supported"}'
        return httpx.Response(200, json={
            "choices": [{"message": {"content": content}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 50, "completion_tokens": 20}})

    settings = FeatherlessSettings("synthetic-key", "https://api.featherless.ai/v1", TEST_MODEL, 512, 60)
    result = generate_answer(context(), settings, transport=httpx.MockTransport(handler))
    assert result.status == "answered"
    assert result.answer == definition
    assert result.sources[0]["quote"] == QUOTE
    assert len(calls) == 2
