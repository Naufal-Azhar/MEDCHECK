from app.embeddings.model import EMBEDDING_DIMENSION, MODEL_NAME
from app.llm.featherless import APPROVED_MODELS


def test_hybrid_models_are_locked():
    assert MODEL_NAME == "Qwen/Qwen3-Embedding-4B"
    assert EMBEDDING_DIMENSION == 384
    assert APPROVED_MODELS == {"Qwen/Qwen3-4B-Instruct-2507"}
