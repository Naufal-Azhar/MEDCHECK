from app.embeddings.model import EMBEDDING_DIMENSION, MODEL_NAME


def test_embedding_configuration_is_locked() -> None:
    assert MODEL_NAME == "Qwen/Qwen3-Embedding-4B"
    assert EMBEDDING_DIMENSION == 384
