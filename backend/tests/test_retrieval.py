from unittest.mock import MagicMock

import pytest

from app.retrieval import service
from app.embeddings import model


@pytest.mark.parametrize("question,k", [("", 5), ("  ", 5), (None, 5), ("x" * 2001, 5),
                                         ("test", 0), ("test", 21), ("test", True)])
def test_invalid_requests_do_not_encode(monkeypatch, question, k):
    encoder = MagicMock()
    monkeypatch.setattr(service, "encode_query", encoder)
    with pytest.raises(ValueError):
        service.search(MagicMock(), question, k)
    encoder.assert_not_called()


@pytest.mark.parametrize("vector", [[], [0.0] * 384, [float("nan")] * 384,
                                     [float("inf")] * 384, [True] * 384])
def test_invalid_vector_does_not_query_database(vector):
    connection = MagicMock()
    with pytest.raises(ValueError):
        service.retrieve_chunks(connection, vector, 3)
    connection.cursor.assert_not_called()


def test_empty_corpus_and_no_query_logging(monkeypatch, caplog):
    monkeypatch.setattr(service, "encode_query", lambda _: [1.0] + [0.0] * 383)
    connection = MagicMock()
    connection.cursor.return_value.__enter__.return_value.fetchall.return_value = []
    with caplog.at_level("INFO"):
        result = service.search(connection, "synthetic private test question")
    assert result.hits == []
    assert result.request_id
    assert "synthetic private" not in caplog.text
    assert "chunks=0" in caplog.text


def test_database_error_is_not_an_empty_result(monkeypatch, caplog):
    monkeypatch.setattr(service, "encode_query", lambda _: [1.0] + [0.0] * 383)
    connection = MagicMock()
    connection.cursor.side_effect = RuntimeError("secret connection details")
    with pytest.raises(RuntimeError):
        service.search(connection, "test question")
    assert "retrieval_failed" in caplog.text
    assert "secret connection details" not in caplog.text


def test_provider_model_configuration():
    assert model.MODEL_NAME == "Qwen/Qwen3-Embedding-4B"
    assert model.EMBEDDING_DIMENSION == 384
