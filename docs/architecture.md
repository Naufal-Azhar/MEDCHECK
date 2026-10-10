# Architecture

```text
Frontend
    ↓
FastAPI
    ↓
Service layer
    ├── healthcare sources
    ├── ingestion and normalization
    ├── chunking
    ├── embeddings
    ├── retrieval
    ├── Featherless LLM
    └── safety validation
    ↓
PostgreSQL + pgvector
```

Arsitektur awal menggunakan modular monolith. PostgreSQL dengan pgvector menjadi satu-satunya database/vector store pada MVP.

Schema aplikasi berada di `db/migrations/`. Dimensi embedding belum dikunci sampai model embedding dipilih secara eksplisit; setelah itu kolom dan index vector akan disesuaikan.
