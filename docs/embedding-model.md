# Embedding Model Decision

## Locked MVP model

User confirmed English-only MVP and this lightweight CPU model. Phase 7 stores
normalized vectors as `vector(384)` with an explicit model column. Exact cosine
search is sufficient for the initial 106 chunks; HNSW is deferred until measured need.

Artifacts include a SHA-256 of each chunk's content. Storage rejects stale IDs,
changed content, missing chunks, invalid dimensions, and incompatible models.
Re-running chunking replaces chunk IDs and embeddings: regenerate the artifact
and run storage again afterwards.

`Qwen/Qwen3-Embedding-4B` via Featherless API

Properties:

- remote inference through the existing Featherless API key
- no local model weights, PyTorch, or sentence-transformers required
- 384-dimensional output
- multilingual text retrieval model
- normalized embeddings for cosine similarity

Featherless `Qwen/Qwen3-Embedding-0.6B` returned HTTP 503 `no_capacity_available`.
The 4B model was verified with HTTP 200 and is active.
The Featherless chat model remains active independently: `Qwen/Qwen3-4B-Instruct-2507`.
Do not change the model without re-embedding existing chunks and updating vector
schema/index compatibility. This fallback preserves `vector(384)`.
