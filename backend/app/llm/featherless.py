"""Small, single-attempt Featherless adapter. No automatic retry or model fallback."""

import logging
from dataclasses import dataclass, field
from time import perf_counter
from uuid import uuid4

import httpx

from app.llm.config import ConfigurationError, FeatherlessSettings

TEST_MODEL = "Qwen/Qwen3-4B-Instruct-2507"
# Single active model: no gated candidates or fallback to earlier experiments.
APPROVED_MODELS = {TEST_MODEL}
logger = logging.getLogger(__name__)


class InferenceError(RuntimeError):
    """Safe error message: excludes key, provider body, and prompt."""


@dataclass(frozen=True)
class Completion:
    content: str = field(repr=False)
    request_id: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    duration_ms: float


def complete(settings: FeatherlessSettings, messages: list[dict[str, str]], *,
             max_tokens: int | None = None,
             transport: httpx.BaseTransport | None = None) -> Completion:
    # Also validate directly constructed settings before sending credentials.
    if settings.base_url != "https://api.featherless.ai/v1":
        raise ConfigurationError("Unverified Featherless endpoint.")
    if not settings.api_key or settings.api_key.lower() in {"replace_me", "your_api_key", "..."}:
        raise ConfigurationError("Fill FEATHERLESS_API_KEY in the project .env file.")
    if any(c.isspace() for c in settings.api_key):
        raise ConfigurationError("Invalid API key format.")
    if settings.model not in APPROVED_MODELS:
        raise ConfigurationError("Only explicitly approved low-cost testing models are enabled.")
    if type(settings.max_tokens) is not int or not 1 <= settings.max_tokens <= 1024:
        raise ConfigurationError("Invalid configured output limit.")
    if type(settings.timeout_seconds) is not int or not 1 <= settings.timeout_seconds <= 120:
        raise ConfigurationError("Invalid request timeout.")
    limit = settings.max_tokens if max_tokens is None else max_tokens
    if type(limit) is not int or not 1 <= limit <= settings.max_tokens:
        raise ValueError("Output limit must not exceed the configured limit.")
    if not messages or len(messages) > 3:
        raise ValueError("Supply 1 to 3 messages for this testing adapter.")
    for message in messages:
        if (set(message) != {"role", "content"}
                or message["role"] not in {"system", "user", "assistant"}
                or not isinstance(message["content"], str) or not message["content"].strip()):
            raise ValueError("Invalid chat message.")
    if sum(len(m["content"]) for m in messages) > 12000:
        raise ValueError("Testing prompt exceeds the 12000-character limit.")

    request_id = str(uuid4())
    started = perf_counter()
    try:
        with httpx.Client(transport=transport, timeout=settings.timeout_seconds,
                          follow_redirects=False, trust_env=False) as client:
            response = client.post(
                settings.base_url + "/chat/completions",
                headers={"Authorization": "Bearer " + settings.api_key,
                         "X-Title": "ForgeHacks Healthcare Information Assistant"},
                json={"model": settings.model, "messages": messages,
                      "max_tokens": limit, "temperature": 0, "stream": False},
            )
    except httpx.TimeoutException:
        logger.warning("llm_failed request_id=%s type=timeout", request_id)
        raise InferenceError("Featherless timed out; no automatic retry was made.") from None
    except httpx.HTTPError:
        logger.warning("llm_failed request_id=%s type=network", request_id)
        raise InferenceError("Featherless network request failed; no automatic retry was made.") from None
    duration = (perf_counter() - started) * 1000
    if response.status_code != 200:
        logger.warning("llm_failed request_id=%s status=%s duration_ms=%.2f",
                       request_id, response.status_code, duration)
        raise InferenceError(f"Featherless returned HTTP {response.status_code}; no automatic retry was made.")
    try:
        data = response.json()
        choice = data["choices"][0]
        content = choice["message"]["content"]
        usage = data["usage"]
        prompt_tokens, completion_tokens = usage["prompt_tokens"], usage["completion_tokens"]
        if choice["finish_reason"] != "stop":
            raise ValueError("Incomplete or unsupported completion")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Empty completion")
        if any(type(v) is not int or v < 0 for v in (prompt_tokens, completion_tokens)):
            raise ValueError("Invalid usage")
    except (ValueError, KeyError, IndexError, TypeError):
        logger.warning("llm_failed request_id=%s type=invalid_response", request_id)
        raise InferenceError("Invalid or incomplete Featherless response; no automatic retry was made.") from None
    logger.info("llm_completed request_id=%s duration_ms=%.2f prompt_tokens=%s completion_tokens=%s",
                request_id, duration, prompt_tokens, completion_tokens)
    return Completion(content, request_id, settings.model, prompt_tokens, completion_tokens, duration)
