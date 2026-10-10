import hashlib

import pytest

from app.embeddings.model import MODEL_NAME
from app.embeddings.storage import validate_records


def record():
    return {"chunk_id": 1, "content_sha256": hashlib.sha256(b"text").hexdigest(),
            "model": MODEL_NAME, "dimension": 384, "embedding": [1.0] + [0.0] * 383}


def test_valid_artifact():
    validate_records([record()], {1: "text"})


@pytest.mark.parametrize("change", [
    {"chunk_id": 2}, {"content_sha256": "outdated"}, {"model": "other"},
    {"dimension": 768}, {"embedding": [1.0]},
    {"embedding": [float("nan")] + [0.0] * 383}, {"embedding": [0.0] * 384},
])
def test_rejects_invalid_artifact(change):
    with pytest.raises(ValueError):
        validate_records([record() | change], {1: "text"})


def test_rejects_duplicate_and_incomplete_artifacts():
    with pytest.raises(ValueError):
        validate_records([record(), record()], {1: "text"})
    with pytest.raises(ValueError):
        validate_records([record()], {1: "text", 2: "another"})
