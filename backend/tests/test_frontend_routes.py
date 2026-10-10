from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_homepage_assets_and_api_docs_remain_available():
    home = client.get("/")
    assert home.status_code == 200
    assert 'id="question-form"' in home.text
    for path in ("/assets/styles.css", "/assets/app.mjs", "/assets/view-model.mjs", "/docs"):
        assert client.get(path).status_code == 200


def test_static_mount_never_exposes_repo_or_env():
    for path in ("/.env", "/assets/.env", "/assets/%2e%2e/%2e%2e/.env", "/assets/backend/app/main.py"):
        assert client.get(path).status_code == 404
