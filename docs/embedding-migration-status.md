# Embedding migration status

The requested API-first configuration is active:

```text
Embeddings: Featherless Qwen/Qwen3-Embedding-4B
Generation: Featherless Qwen/Qwen3-4B-Instruct-2507
```

The first API candidate `Qwen/Qwen3-Embedding-0.6B` returned HTTP 503 with
`no_capacity_available`. A one-input probe of `Qwen/Qwen3-Embedding-4B` returned
HTTP 200 with 384 dimensions. The 106 chunks were then regenerated through API
batches and stored successfully in pgvector.

Validation after restoration:

- `124 passed`, `1 skipped` automated tests.
- `106` chunks and `106` vectors stored, dimension `384`, model `Qwen/Qwen3-Embedding-4B`.
- Live diabetes RAG answer passed generation, citation, and claim-review gates.
- No patient data was sent; only public MedlinePlus chunks and synthetic/public questions.
- No global package installation occurred.

The local BGE model, sentence-transformers and PyTorch were removed only after API
re-embedding, pgvector storage, retrieval, chat and tests succeeded. A future model
change must re-embed all chunks, verify dimensions/model metadata, store in a
transaction, test retrieval, then remove previous embedding dependencies.

The failed 503 attempts did not return usage. Absence of usage is not proof of
zero billing; the provider dashboard is authoritative.
