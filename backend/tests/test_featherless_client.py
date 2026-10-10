import json
from dataclasses import replace

import httpx
import pytest

from app.llm.config import ConfigurationError, FeatherlessSettings
from app.llm.featherless import APPROVED_MODELS, InferenceError, TEST_MODEL, complete

SETTINGS = FeatherlessSettings("synthetic-secret", "https://api.featherless.ai/v1", TEST_MODEL, 512, 60)
MESSAGES = [{"role": "user", "content": "synthetic private question"}]


def payload():
    return {"choices": [{"message": {"content": "OK"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 1}}


def test_request_and_usage(caplog):
    def handler(request):
        assert str(request.url) == "https://api.featherless.ai/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer synthetic-secret"
        body = json.loads(request.content)
        assert body["model"] == TEST_MODEL
        assert body["max_tokens"] == 32
        assert body["messages"] == MESSAGES
        return httpx.Response(200, json=payload())
    with caplog.at_level("INFO", logger="app.llm.featherless"):
        result = complete(SETTINGS, MESSAGES, max_tokens=32, transport=httpx.MockTransport(handler))
    assert result.content == "OK"
    assert result.prompt_tokens == 10
    assert "synthetic-secret" not in caplog.text
    assert "synthetic private" not in caplog.text


@pytest.mark.parametrize("status", [301, 401, 402, 403, 429, 500, 503])
def test_no_redirect_or_retry_or_body_leak(status, caplog):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(status, text="synthetic-secret", headers={"Location": "https://example.invalid"})
    with pytest.raises(InferenceError) as exc:
        complete(SETTINGS, MESSAGES, transport=httpx.MockTransport(handler))
    assert len(calls) == 1
    assert "synthetic-secret" not in str(exc.value) + caplog.text


def test_timeout_no_retry():
    calls = []
    def handler(request):
        calls.append(request)
        raise httpx.ReadTimeout("synthetic-secret")
    with pytest.raises(InferenceError, match="timed out"):
        complete(SETTINGS, MESSAGES, transport=httpx.MockTransport(handler))
    assert len(calls) == 1


@pytest.mark.parametrize("body", [{}, {"choices": []},
    {"choices": [{"message": {"content": "partial"}, "finish_reason": "length"}]},
    {"choices": [{"message": {"content": ""}, "finish_reason": "stop"}]},
])
def test_invalid_response(body):
    with pytest.raises(InferenceError):
        complete(SETTINGS, MESSAGES, transport=httpx.MockTransport(lambda _: httpx.Response(200, json=body)))


@pytest.mark.parametrize("changes", [{"api_key": ""}, {"model": "expensive/other"},
                                     {"model": "meta-llama/Llama-3.2-3B-Instruct"},
                                     {"model": "Qwen/Qwen2.5-0.5B-Instruct"},
                                     {"model": "Qwen/Qwen2.5-1.5B-Instruct"},
                                     {"base_url": "https://example.invalid"}])
def test_invalid_config_never_sends(changes):
    def handler(_):
        pytest.fail("Network must not be reached")
    with pytest.raises(ConfigurationError):
        complete(replace(SETTINGS, **changes), MESSAGES, transport=httpx.MockTransport(handler))


def test_output_limit_never_sends():
    with pytest.raises(ValueError):
        complete(SETTINGS, MESSAGES, max_tokens=1024)


def test_only_selected_non_gated_model_is_enabled():
    assert APPROVED_MODELS == {"Qwen/Qwen3-4B-Instruct-2507"}


@pytest.mark.parametrize("model", sorted(APPROVED_MODELS))
def test_explicit_model_selection_only(model):
    calls = []
    def handler(request):
        calls.append(json.loads(request.content)["model"])
        return httpx.Response(200, json=payload())
    result = complete(replace(SETTINGS, model=model), MESSAGES,
                      transport=httpx.MockTransport(handler))
    assert calls == [model]
    assert result.model == model
