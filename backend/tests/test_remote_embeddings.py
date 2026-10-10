from types import SimpleNamespace

import httpx
import pytest

from app.embeddings import model


@pytest.fixture(autouse=True)
def settings(monkeypatch):
    monkeypatch.setattr(model, "load_settings", lambda: SimpleNamespace(
        api_key="synthetic-secret", base_url="https://api.featherless.ai/v1", timeout_seconds=60))


def test_order_and_normalization():
    def handler(request):
        return httpx.Response(200, json={"data": [
            {"index": 1, "embedding": [0., 2.] + [0.] * 382},
            {"index": 0, "embedding": [2.] + [0.] * 383}], "usage": {"prompt_tokens": 2}})
    vectors, tokens = model.encode_texts(["one", "two"], transport=httpx.MockTransport(handler))
    assert vectors[0][0] == vectors[1][1] == 1
    assert tokens == 2


@pytest.mark.parametrize("data", [[], [{"index": 0, "embedding": [0.] * 384}],
    [{"index": 1, "embedding": [1.] * 384}], [{"index": 0, "embedding": [float('inf')] * 384}]])
def test_invalid_vectors(data):
    with pytest.raises(model.EmbeddingError):
        model.encode_texts(["text"], transport=httpx.MockTransport(lambda _: httpx.Response(
            200, json={"data": data, "usage": {"prompt_tokens": 1}})))


def test_no_retry_on_capacity_failure():
    calls = []
    def handler(_):
        calls.append(1)
        return httpx.Response(503)
    with pytest.raises(model.EmbeddingError):
        model.encode_texts(["text"], transport=httpx.MockTransport(handler))
    assert len(calls) == 1
