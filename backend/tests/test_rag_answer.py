import json
import httpx
import pytest

from app.llm.config import FeatherlessSettings
from app.llm.featherless import TEST_MODEL
from app.rag.answer import AnswerValidationError, build_messages, generate_answer, validate_answer
from app.rag.context import build_context
from app.retrieval.service import SearchHit

TEXT = "This is a synthetic evidence excerpt used only for software tests."
SETTINGS = FeatherlessSettings("synthetic-secret", "https://api.featherless.ai/v1", TEST_MODEL, 512, 60)


def context():
    return build_context("Synthetic question", [SearchHit(1, 1, 0, TEXT, "Synthetic topic", 1,
                         "MedlinePlus", "https://example.invalid/source", 0.8)])


def valid():
    return {"status": "answered", "answer": TEXT, "key_points": [],
            "citations": [{"id": "S1", "quote": TEXT}], "uncertainty": "Limited evidence."}


def test_prompt_separates_untrusted_data():
    messages = build_messages(context())
    assert messages[0]["role"] == "system"
    assert "untrusted" in messages[0]["content"]
    assert json.loads(messages[1]["content"])["evidence"][0]["text"] == TEXT


def test_attribution_from_database_only():
    result = validate_answer(json.dumps(valid()), context())
    assert result.sources[0]["source_url"] == "https://example.invalid/source"
    assert result.sources[0]["quote"] == TEXT
    assert result.status == "answered"


@pytest.mark.parametrize("changes", [
    {"citations": []}, {"citations": [{"id": "S9", "quote": TEXT}]},
    {"citations": [{"id": "S1", "quote": "Fabricated source excerpt."}]},
    {"citations": [{"id": "S1", "quote": TEXT, "url": "invented"}]},
    {"answer": "Read https://example.invalid"}, {"answer": "Explanation [S99]"},
    {"status": "insufficient_evidence"}, {"uncertainty": ""}, {"key_points": "invalid"},
    {"status": []},
])
def test_invalid_content_is_rejected(changes):
    with pytest.raises(AnswerValidationError):
        validate_answer(json.dumps(valid() | changes), context())


@pytest.mark.parametrize("raw", ["not json", "[]", '{"status": "answered", "status": "answered"}'])
def test_malformed_json(raw):
    with pytest.raises(AnswerValidationError):
        validate_answer(raw, context())


def test_empty_evidence_never_calls_provider():
    def forbidden(_):
        pytest.fail("No network call allowed")
    result = generate_answer(build_context("question", []), None, transport=httpx.MockTransport(forbidden))
    assert result.status == "insufficient_evidence"


@pytest.mark.parametrize("status", ["insufficient_evidence", "safety_refusal"])
def test_abstention_uses_fixed_text(status):
    raw = {"status": status, "answer": "", "key_points": [], "citations": [],
           "uncertainty": "Potentially unsafe arbitrary model text"}
    result = validate_answer(json.dumps(raw), context())
    assert result.status == status
    assert "arbitrary" not in result.confidence_or_uncertainty
    assert result.sources == []


def test_invalid_completion_never_leaks_text(caplog):
    def handler(_):
        return httpx.Response(200, json={"choices": [{"message": {"content": "unsafe generated text"},
                                                      "finish_reason": "stop"}],
                                        "usage": {"prompt_tokens": 100, "completion_tokens": 10}})
    result = generate_answer(context(), SETTINGS, transport=httpx.MockTransport(handler))
    assert result.status == "invalid_response"
    assert result.usage["completion_tokens"] == 10
    assert "unsafe generated text" not in result.answer + caplog.text


def test_success_with_mocked_api():
    calls = []
    def handler(request):
        calls.append(request)
        content = json.dumps(valid()) if len(calls) == 1 else '{"verdict":"supported"}'
        return httpx.Response(200, json={"choices": [{"message": {"content": content},
                                                      "finish_reason": "stop"}],
                                        "usage": {"prompt_tokens": 100, "completion_tokens": 50}})
    result = generate_answer(context(), SETTINGS, transport=httpx.MockTransport(handler))
    assert result.status == "answered"
    assert len(calls) == 2
    assert result.usage["prompt_tokens"] == 200
    assert result.usage["completion_tokens"] == 100


def test_context_budget_keeps_whole_items():
    item = context().evidence[0]
    hits = [SearchHit(i, i, 0, TEXT, "Synthetic topic", 1, "MedlinePlus", item.source_url, 0.8)
            for i in range(1, 6)]
    ctx = build_context("question", hits, max_chars=500)
    assert len(ctx.prompt_context) <= 500
    assert ctx.evidence
    for evidence in ctx.evidence:
        assert evidence.content == TEXT
        assert f"[{evidence.citation_id}] SOURCE:" in ctx.prompt_context
