import os

import pytest

from app.llm.config import ConfigurationError, load_settings


@pytest.fixture
def config_file(tmp_path, monkeypatch):
    for key in os.environ:
        if key.startswith("FEATHERLESS_"):
            monkeypatch.delenv(key)
    path = tmp_path / ".env"
    path.write_text(
        "FEATHERLESS_API_KEY=synthetic-test-key\n"
        "FEATHERLESS_MODEL=Qwen/Qwen3-4B-Instruct-2507\n", encoding="utf-8",
    )
    return path


def test_valid_settings_hide_key(config_file):
    settings = load_settings(config_file)
    assert settings.api_key == "synthetic-test-key"
    assert "synthetic-test-key" not in repr(settings)
    assert settings.max_tokens == 512
    assert settings.base_url == "https://api.featherless.ai/v1"


@pytest.mark.parametrize("key,value", [
    ("FEATHERLESS_API_KEY", ""), ("FEATHERLESS_MODEL", ""),
    ("FEATHERLESS_BASE_URL", "https://example.invalid/v1"),
    ("FEATHERLESS_MAX_TOKENS", "2048"), ("FEATHERLESS_MAX_TOKENS", "oops"),
    ("FEATHERLESS_TIMEOUT_SECONDS", "0"),
])
def test_reject_invalid_config(config_file, monkeypatch, key, value):
    monkeypatch.setenv(key, value)
    with pytest.raises(ConfigurationError) as exc:
        load_settings(config_file)
    assert "synthetic-test-key" not in str(exc.value)


def test_process_environment_has_priority(config_file, monkeypatch):
    monkeypatch.setenv("FEATHERLESS_MAX_TOKENS", "256")
    assert load_settings(config_file).max_tokens == 256
