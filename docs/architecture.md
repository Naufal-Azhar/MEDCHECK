# Architecture

Framework aplikasi aktif: **SvelteKit 3 + Svelte 5 + TypeScript**, dijalankan Node.js melalui adapter-node.

```text
Browser (Svelte UI)
    ↓ same-origin HTTP
SvelteKit routes (+server.ts)
    ├── input validation + request UUID
    ├── local safety/privacy preflight
    ├── Featherless embeddings
    ├── PostgreSQL/pgvector retrieval (pg)
    ├── bounded context + source attribution
    ├── Featherless generation
    └── structural/quote/lexical validation + claim review
    ↓ structured response
Browser (escaped text, citations, safety notices)
```

UI dan endpoint berada di `frontend/src/routes/`; server-only service di `frontend/src/lib/server/`. Tidak ada FastAPI atau Python subprocess pada request. PostgreSQL dengan pgvector tetap satu-satunya database/vector store. Schema di `db/migrations/`; model embedding Qwen3-Embedding-4B menggunakan 384 dimensi.

Ingestion terpisah dari runtime web:

```text
Python CLI → MedlinePlus XML → normalisasi → chunking
           → Featherless embedding → PostgreSQL + pgvector
```

Modul Python di `backend/` dipertahankan untuk pipeline dan evaluasi. n8n tetap hanya workflow pendukung pengecekan sumber, bukan ingestion otomatis. Tidak ada Redis, reranker, model lokal, auth, atau rate limit.

Lihat `sveltekit-migration.md` untuk setup, perubahan kompatibilitas, dan batas validasi. Evaluasi fase sebelumnya adalah catatan historis dan tidak membuktikan akurasi medis runtime baru.
