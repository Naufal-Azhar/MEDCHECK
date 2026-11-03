# Scripts

## Runtime setelah migrasi SvelteKit

Server aplikasi dijalankan dengan `npm --prefix frontend run dev`, bukan Uvicorn.
Skrip Python di sini tetap merupakan utilitas ingestion/data/evaluasi legacy;
modul Python tidak dipanggil oleh request SvelteKit. Evaluasi HTTP lama perlu
menggunakan base URL baru (development port 5173, production default 3000).
`node --test scripts/test_frontend.mjs` menguji view-model Svelte yang aktif.
Lihat `docs/sveltekit-migration.md`; uraian fase di bawah adalah riwayat pipeline.

## Corpus experiment

See [`docs/corpus-experiment-results.md`](../docs/corpus-experiment-results.md).
`python scripts/expand_evaluate.py` inspects the cached snapshot offline. `--live`
permits paid calls but blocks rerun if a completed checkpoint exists. The tested
100-document candidate was rolled back after no NET proxy gain; active corpus
remains 24 documents / 106 chunks. Candidate artifacts are retained locally.

**Current safety behavior:** personal medical decision requests are refused locally.
An educational `ask_question.py --live` run now permits up to TWO requests:
generation and a short claim review. Older one-request descriptions below are
historical. See [`docs/safety-minimum.md`](../docs/safety-minimum.md) for limitations
and [`docs/backlog.md`](../docs/backlog.md) for deferred emergency-feature ideas.

## Phase 10 boundary smoke tests

`python scripts/check_rag_boundaries.py` is offline by default. `--live` permits
up to five billed requests using fixed synthetic questions only. A failure returns
a nonzero exit code; reports are local under `data/processed/`. The first run found
a safety/grounding failure; see [`docs/phase10-boundary-results.md`](../docs/phase10-boundary-results.md).

## Grounded generation (Phase 10, development only)

```powershell
.\.venv\Scripts\python.exe scripts/ask_question.py "What is diabetes?"
# Explicit one-request live test; may incur token charges:
.\.venv\Scripts\python.exe scripts/ask_question.py "What is diabetes?" --live
```

See [`docs/rag-generation.md`](../docs/rag-generation.md). The active generation
model is Qwen3-4B-Instruct-2507; invalid answers are withheld.

## RAG context (Phase 9)

```powershell
. .\scripts\activate-project.ps1
python scripts/build_context.py "What is diabetes?" --top-k 5
```

Menampilkan konteks evidence berlabel citation untuk inspeksi sebelum integrasi
Featherless. Belum menghasilkan jawaban AI.

## Similarity search (Phase 8)

```powershell
. .\scripts\activate-project.ps1
python scripts/search_documents.py "What is high blood pressure?" --top-k 3
```

Menggunakan model cache lokal/offline dan pgvector. Menampilkan evidence dan URL,
bukan jawaban AI. Detail dan batasan: [`docs/retrieval.md`](../docs/retrieval.md).

Aktifkan environment project sebelum menjalankan command Python:
`. .\scripts\activate-project.ps1`

## Vector storage (Phase 7)

Jalankan dari root project setelah database aktif:

```powershell
Get-Content db/migrations/002_vector_storage.sql | docker compose exec -T postgres psql -U forgehacks -d forgehacks --single-transaction -v ON_ERROR_STOP=1
python scripts/generate_embeddings.py
python scripts/store_embeddings.py
```

Generation menggunakan cache model lokal setelah aktivasi. Penyimpanan bersifat
transactional dan dapat diulang tanpa membuat chunk baru. Artifact lama tanpa
content hash harus dihasilkan ulang. Belum ada HNSW index untuk corpus kecil ini.

Utility scripts untuk ingestion, chunking, embeddings, retrieval evaluation, dan development akan ditambahkan secara bertahap.

## MedlinePlus ingestion

Setelah dependency backend terpasang, jalankan dari project root:

```powershell
python scripts/ingest_medlineplus.py
```

Script menggunakan MedlinePlus Web Service resmi tanpa API key dan bersifat idempotent.

## Document chunking

Setelah ingestion berhasil, jalankan:

```powershell
python scripts/chunk_documents.py
```

Chunking menggunakan window berbasis kata dengan overlap. Script dapat dijalankan ulang dan akan mengganti chunks milik setiap dokumen secara deterministik.

## Embedding generation

Model embedding MVP yang dikunci:

```text
BAAI/bge-small-en-v1.5
dimension: 384
```

Generate artifact embedding dengan:

```powershell
python scripts/generate_embeddings.py
```

Model dijalankan lokal dan diunduh dari Hugging Face saat pertama kali dipakai. Embedding baru disimpan sebagai artifact JSONL; penyimpanan ke pgvector dilakukan pada fase berikutnya.
