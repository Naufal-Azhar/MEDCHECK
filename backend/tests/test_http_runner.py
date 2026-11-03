"""Offline launcher tests: no subprocesses, sockets, secrets, or paid requests."""

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import httpx
import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts/verify_phase14_e2e.py"


@pytest.fixture
def runner(monkeypatch, tmp_path):
    spec = importlib.util.spec_from_file_location("http_runner_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", [str(SCRIPT)])

    def forbidden(*args, **kwargs):
        raise AssertionError("Offline test attempted real process or network access")

    monkeypatch.setattr(module.subprocess, "Popen", forbidden)
    monkeypatch.setattr(module.socket, "socket", forbidden)
    monkeypatch.setattr(module.httpx, "Client", forbidden)
    monkeypatch.setattr(module.shutil, "which", Mock(return_value="mock-node"))
    return module


def test_default_guard_has_no_side_effects(runner, monkeypatch, capsys):
    def forbidden(*args, **kwargs):
        raise AssertionError("Dry run must not inspect runtime prerequisites")

    monkeypatch.setattr(runner.shutil, "which", forbidden)
    monkeypatch.setattr(Path, "is_file", forbidden)
    assert runner.main() == 0
    assert "Dry run: 12 cases" in capsys.readouterr().out
    assert not list(runner.ROOT.iterdir())


def test_case_selection_remains_offline(runner, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--case", "privacy"])
    assert runner.main() == 0
    assert "Dry run: 1 cases" in capsys.readouterr().out


@pytest.mark.parametrize("missing", ["node", "build"])
def test_missing_runtime_fails_before_process_or_requests(runner, monkeypatch, missing):
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--live"])
    if missing == "node":
        runner.shutil.which.return_value = None
    message = "Node.js executable not found" if missing == "node" else "Production build not found"
    with pytest.raises(RuntimeError, match=message):
        runner.main()
    runner.shutil.which.assert_called_once_with("node")
    assert not (runner.ROOT / "data").exists()


@pytest.fixture
def launched(runner, monkeypatch):
    build = runner.ROOT / "frontend/build/index.js"
    build.parent.mkdir(parents=True)
    build.write_text("// Synthetic build; never executed", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--live", "--case", "privacy"])
    sock = MagicMock()
    sock.__enter__.return_value = sock
    sock.getsockname.return_value = ("127.0.0.1", 43210)
    socket_factory = Mock(return_value=sock)
    monkeypatch.setattr(runner.socket, "socket", socket_factory)
    process = Mock()
    process.poll.return_value = None
    popen = Mock(return_value=process)
    monkeypatch.setattr(runner.subprocess, "Popen", popen)
    client = MagicMock()
    client.__enter__.return_value = client

    def get(path, **kwargs):
        if path == "/docs":
            return httpx.Response(200, json={"openapi": "3.1.0"})
        if path == "/health":
            return httpx.Response(200, json={"database": "ok"})
        if path == "/":
            return httpx.Response(200, text="Synthetic frontend")
        raise AssertionError(f"Unexpected route: {path}")

    client.get.side_effect = get
    client.post.return_value = httpx.Response(200, json={
        "status": "privacy_refusal", "safety_reason": "personal_identifiers",
        "usage": None, "sources": [], "request_id": "synthetic-id",
    }, headers={"x-request-id": "synthetic-id", "cache-control": "no-store"})
    client_factory = Mock(return_value=client)
    monkeypatch.setattr(runner.httpx, "Client", client_factory)
    sleep = Mock()
    monkeypatch.setattr(runner.time, "sleep", sleep)
    return SimpleNamespace(runner=runner, build=build, sock=sock, process=process,
                           popen=popen, client=client, client_factory=client_factory,
                           sleep=sleep, get=get)


def read_report(runner):
    reports = list((runner.ROOT / "data/processed/phase14-e2e").glob("*.json"))
    assert len(reports) == 1
    return json.loads(reports[0].read_text(encoding="utf-8"))


def test_node_launcher_overrides_caller_loopback_config(launched, monkeypatch):
    state = launched
    for key, value in {"HOST": "0.0.0.0", "PORT": "80", "ORIGIN": "https://invalid.example",
                       "FORGE_TEST_INHERITED": "synthetic"}.items():
        monkeypatch.setenv(key, value)
    assert state.runner.main() == 0
    state.runner.shutil.which.assert_called_once_with("node")
    args, kwargs = state.popen.call_args
    assert args == (["mock-node", f"--env-file-if-exists={state.runner.ROOT / '.env'}", str(state.build)],)
    assert Path(args[0][1].split("=", 1)[1]).is_absolute()
    assert kwargs["cwd"] == state.runner.ROOT
    assert kwargs["stdout"] is kwargs["stderr"]
    assert kwargs["stdout"].closed
    env = kwargs["env"]
    assert env["HOST"] == "127.0.0.1"
    assert env["PORT"] == "43210"
    assert env["ORIGIN"] == "http://127.0.0.1:43210"
    assert env["FORGE_TEST_INHERITED"] == "synthetic"
    assert state.runner.os.environ["HOST"] == "0.0.0.0"
    state.sock.bind.assert_called_once_with(("127.0.0.1", 0))
    state.client_factory.assert_called_once_with(base_url=env["ORIGIN"], timeout=210, trust_env=False)
    state.client.get.assert_any_call("/docs", timeout=1)
    assert [call.args[0] for call in state.client.get.call_args_list] == ["/docs", "/health", "/", "/docs"]
    state.client.post.assert_called_once_with("/chat", json={"question": state.runner.CASES[6][1]})
    report = read_report(state.runner)
    assert report["framework"] == "sveltekit-node"
    assert report["frontend_routes"] == {"/": 200, "/docs": 200}
    assert report["cases"][0]["passed"] is True
    state.process.terminate.assert_called_once_with()
    state.process.wait.assert_called_once_with(timeout=15)
    state.process.kill.assert_not_called()


def test_readiness_retries_non_json_and_unavailable_docs(launched):
    state = launched
    responses = iter([
        httpx.ConnectError("Synthetic connection failure"),
        httpx.Response(503), httpx.Response(200, text="Not JSON"),
        httpx.Response(200, json=[]), httpx.Response(200, json={}),
    ])

    def get(path, **kwargs):
        if path == "/docs" and kwargs.get("timeout") == 1:
            response = next(responses, httpx.Response(200, json={"openapi": "3.1.0"}))
            if isinstance(response, Exception):
                raise response
            return response
        return state.get(path, **kwargs)

    state.client.get.side_effect = get
    assert state.runner.main() == 0
    assert state.sleep.call_count == 5


@pytest.mark.parametrize("failure", ["exit", "timeout", "health", "request"])
def test_failures_stop_before_paid_requests_and_cleanup(launched, failure):
    state = launched
    if failure == "exit":
        state.process.poll.return_value = 1
        message = "Test server exited"
    elif failure == "timeout":
        state.client.get.return_value = httpx.Response(503)
        state.client.get.side_effect = None
        message = "Server startup timed out"
    else:
        def get(path, **kwargs):
            if path == "/health":
                if failure == "request":
                    raise RuntimeError("Synthetic health request failure")
                return httpx.Response(200, json={"database": "unavailable"})
            return state.get(path, **kwargs)
        state.client.get.side_effect = get
        message = "Synthetic health request failure" if failure == "request" else "Database health unavailable"
    with pytest.raises(RuntimeError, match=message):
        state.runner.main()
    state.client.post.assert_not_called()
    state.process.terminate.assert_called_once_with()
    state.process.wait.assert_called_once_with(timeout=15)
    assert state.sleep.call_count == (60 if failure == "timeout" else 0)
    assert read_report(state.runner)["cases"] == []


@pytest.mark.parametrize("kill_times_out", [False, True])
def test_shutdown_uses_bounded_kill_fallback_and_writes_report(launched, kill_times_out):
    state = launched
    timeout = state.runner.subprocess.TimeoutExpired("mock-node", 15)
    state.process.wait.side_effect = [timeout, timeout if kill_times_out else 0]
    if kill_times_out:
        with pytest.raises(state.runner.subprocess.TimeoutExpired):
            state.runner.main()
    else:
        assert state.runner.main() == 0
    state.process.terminate.assert_called_once_with()
    state.process.kill.assert_called_once_with()
    assert [call.kwargs for call in state.process.wait.call_args_list] == [{"timeout": 15}, {"timeout": 5}]
    assert read_report(state.runner)["cases"][0]["passed"] is True
