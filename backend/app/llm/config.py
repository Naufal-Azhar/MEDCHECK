A"""  """"""Read local Featherless configuration without displaying secrets or making requests."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import dotenv_values

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class ConfigurationError(ValueError):
    """Safe-to-display configuration error (never includes input values)."""


@dataclass(frozen=True)
class FeatherlessSettings:
    api_key: str = field(repr=False)
    base_url: str
    model: str
    max_tokens: int
    timeout_seconds: int


def load_settings(env_file: Path | None = None) -> FeatherlessSettings:
    # Do not interpolate secrets or mutate process-wide environment variables.
    values = dict(dotenv_values(env_file or PROJECT_ROOT / ".env", interpolate=False))
    values.update(os.environ)

    def text(name: str, default: str = "") -> str:
        return (values.get(name) or default).strip()

    key = text("FEATHERLESS_API_KEY")
    if not key or key.lower() in {"...", "your_api_key", "replace_me"}:
        raise ConfigurationError("Fill FEATHERLESS_API_KEY in the project .env file.")
    if any(c.isspace() for c in key):
        raise ConfigurationError("FEATHERLESS_API_KEY must not contain whitespace.")
    model = text("FEATHERLESS_MODEL")
    if not model or "/" not in model or any(c.isspace() for c in model):
        raise ConfigurationError("Choose FEATHERLESS_MODEL using its exact catalogue ID.")
    base_url = text("FEATHERLESS_BASE_URL", "https://api.featherless.ai/v1").rstrip("/")
    # Avoid accidentally sending the API key to an unverified endpoint.
    if base_url != "https://api.featherless.ai/v1":
        raise ConfigurationError("FEATHERLESS_BASE_URL must use the verified Featherless endpoint.")
    try:
        max_tokens = int(text("FEATHERLESS_MAX_TOKENS", "512"))
        timeout = int(text("FEATHERLESS_TIMEOUT_SECONDS", "60"))
    except ValueError:
        raise ConfigurationError("Token and timeout settings must be integers.") from None
    if not 1 <= max_tokens <= 1024:
        raise ConfigurationError("Testing output limit must be between 1 and 1024 tokens.")
    if not 1 <= timeout <= 120:
        raise ConfigurationError("Timeout must be between 1 and 120 seconds.")
    return FeatherlessSettings(key, base_url, model, max_tokens, timeout)
