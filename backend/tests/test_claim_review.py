import json

import httpx
import pytest

from app.llm.config import FeatherlessSettings
from app.llm.featherless import TEST_MODEL
from app.rag.answer import generate_answer
from app.rag.answer import AnswerValidationError, validate_answer
from app.rag.context import build_context
from app.retrieval.service import SearchHit

QUOTE = "In adults, the symptoms of dehydration include: Feeling very thirsty Dry mouth Urinating and sweating less than usual Dark-colored urine"
SETTINGS = FeatherlessSettings("synthetic-secret", "https://api.featherless.ai/v1", TEST_MODEL, 512, 60)


def context():
    return build_context("What does this source say about dehydration?", [
        SearchHit(1, 1, 0, QUOTE, "Synthetic regression fixture", 1, "MedlinePlus",
                  "https://example.invalid/fixture", 0.8)])


@pytest.mark.parametrize("review_body", [
    '{"verdict":"unsupported"}', 'not JSON', '{"verdict":"supported","extra":true}',
    '{"verdict":"unsupported","verdict":"supported"}', '[]',
])
def test_unsupported_or_invalid_review_withholds_candidate(review_body):
    calls = []
    candidate = {"status": "answered", "answer": "Dehydration symptoms: not urinating less than usual.",
                 "key_points": [], "citations": [{"id": "S1", "quote": QUOTE}],
                 "uncertainty": "Synthetic test."}
    def handler(request):
        body = json.loads(request.content)
        calls.append(body)
        if len(calls) == 1:
            content = json.dumps(candidate)
        else:
            assert body["max_tokens"] <= 64
            evidence = json.loads(body["messages"][1]["content"])
            assert evidence["quotes"][0]["text"] == QUOTE
            assert "not urinating less" in evidence["answer"]
            content = review_body
        return httpx.Response(200, json={"choices": [{"message": {"content": content}, "finish_reason": "stop"}],
                                        "usage": {"prompt_tokens": 100, "completion_tokens": 10}})
    result = generate_answer(context(), SETTINGS, transport=httpx.MockTransport(handler))
    assert result.status == "invalid_response"
    assert result.sources == []
    assert "not urinating less" not in result.answer
    assert len(calls) == 2
    assert result.usage["prompt_tokens"] == 200


def test_review_failure_is_not_bypassed():
    calls = []
    def handler(request):
        calls.append(request)
        if len(calls) == 2:
            return httpx.Response(503)
        candidate = {"status": "answered", "answer": QUOTE, "key_points": [],
                     "citations": [{"id": "S1", "quote": QUOTE}], "uncertainty": "Limited."}
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(candidate)}, "finish_reason": "stop"}],
                                        "usage": {"prompt_tokens": 100, "completion_tokens": 10}})
    result = generate_answer(context(), SETTINGS, transport=httpx.MockTransport(handler))
    assert result.status == "invalid_response"
    assert result.usage["usage_complete"] is False
    assert len(calls) == 2


def test_original_frequent_urination_regression_rejected_locally():
    candidate = {"status": "answered", "answer": "Dehydration causes frequent urination.",
                 "key_points": [], "citations": [{"id": "S1", "quote": QUOTE}], "uncertainty": "Limited."}
    with pytest.raises(AnswerValidationError, match="absent"):
        validate_answer(json.dumps(candidate), context())
