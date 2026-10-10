# Active configuration

```text
Generation model: Qwen/Qwen3-4B-Instruct-2507 via Featherless API
Embedding model:  Qwen/Qwen3-Embedding-4B via Featherless API
Vector type:     pgvector vector(384)
Database:        PostgreSQL + pgvector in Docker
```

Qwen3-Embedding-0.6B initially returned HTTP 503 `no_capacity_available`. The
verified 4B API model returned HTTP 200 with 384 dimensions and re-embedded the
corpus successfully. The 0.6B model is not used.

All Python packages remain inside `.venv`; no local embedding model cache is needed.
No global package is used by the project.
