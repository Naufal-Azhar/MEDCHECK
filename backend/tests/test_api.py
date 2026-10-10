from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_openapi_and_validation_without_external_services():
    response = client.post("/search", json={"question": "   "})
    assert response.status_code == 422
    assert response.headers.get("x-request-id")


def test_chat_rejects_blank_question():
    response = client.post("/chat", json={"question": ""})
    assert response.status_code == 422


def test_unknown_source_uses_database_service(monkeypatch):
    class MissingConnection:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def execute(self, *_args):
            return self
        def fetchone(self):
            return None
    monkeypatch.setattr("app.api.connect", lambda: MissingConnection())
    response = client.get("/sources/999999")
    assert response.status_code == 404
