import runpy
import sys
from pathlib import Path

from app.llm import config
from app.rag import answer, pipeline


def test_boundary_runner_default_is_offline(monkeypatch, capsys):
    def forbidden(*args, **kwargs):
        raise AssertionError("Dry run must not load secrets, retrieve, or call inference")

    monkeypatch.setattr(config, "load_settings", forbidden)
    monkeypatch.setattr(pipeline, "retrieve_context", forbidden)
    monkeypatch.setattr(answer, "generate_answer", forbidden)
    script = Path(__file__).resolve().parents[2] / "scripts/check_rag_boundaries.py"
    monkeypatch.setattr(sys, "argv", [str(script)])
    module = runpy.run_path(str(script), run_name="boundary_runner_test")
    assert module["main"]() == 0
    assert len(module["CASES"]) == 5
    assert "No network calls" in capsys.readouterr().out
