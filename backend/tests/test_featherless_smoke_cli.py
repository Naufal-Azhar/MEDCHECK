import runpy
import sys
from pathlib import Path
from types import SimpleNamespace

from app.llm import config, featherless

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/test_featherless_connection.py"


def run_cli(monkeypatch, args, content):
    calls = []
    settings = SimpleNamespace(api_key="synthetic-secret", max_tokens=512)
    monkeypatch.setattr(config, "load_settings", lambda: settings)

    def fake_complete(settings, messages, **kwargs):
        calls.append((messages, kwargs))
        return SimpleNamespace(content=content, request_id="synthetic-id", prompt_tokens=34,
                               completion_tokens=2, duration_ms=1.0)

    monkeypatch.setattr(featherless, "complete", fake_complete)
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), *args])
    module = runpy.run_path(str(SCRIPT), run_name="smoke_cli_test")
    assert module["main"]() == 0
    return calls


def test_show_response_requires_live(monkeypatch, capsys):
    assert run_cli(monkeypatch, ["--show-response"], "OK") == []
    assert "Synthetic response:" not in capsys.readouterr().out


def test_live_hides_content_by_default(monkeypatch, capsys):
    calls = run_cli(monkeypatch, ["--live"], "OK.")
    output = capsys.readouterr().out
    assert len(calls) == 1
    assert calls[0][1]["max_tokens"] == 32
    assert "Synthetic response:" not in output
    assert "Expected acknowledgement: False" in output


def test_opt_in_escapes_content_and_redacts_key(monkeypatch, capsys):
    calls = run_cli(monkeypatch, ["--live", "--show-response"], "OK.\n\x1bsynthetic-secret")
    output = capsys.readouterr().out
    assert len(calls) == 1
    assert "synthetic-secret" not in output
    assert "[REDACTED]" in output
    assert "\\n\\u001b" in output


def test_exact_acknowledgement(monkeypatch, capsys):
    run_cli(monkeypatch, ["--live", "--show-response"], "OK")
    assert "Expected acknowledgement: True" in capsys.readouterr().out
