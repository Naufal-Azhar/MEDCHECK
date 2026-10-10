# ForgeHacks Healthcare Information Reasoning Assistant

## Status evaluasi akhir MVP

Lihat [`docs/phase15-conclusion.md`](docs/phase15-conclusion.md) untuk stack aktual,
alur sistem, hasil 24 pertanyaan, batasan dan prioritas sebelum deployment.
Backend/UI sudah berjalan lokal; public deployment belum disetujui oleh evaluasi.

Asisten informasi kesehatan berbasis AI untuk membantu pengguna non-ahli memahami informasi kesehatan dari sumber yang dapat dipercaya.

## Status

Project ini sedang dibangun secara incremental untuk ForgeHacks Online 2026.

Fokus MVP:

- MedlinePlus sebagai sumber healthcare awal
- PostgreSQL + pgvector untuk penyimpanan dan semantic retrieval
- FastAPI sebagai backend
- Featherless sebagai LLM inference layer
- frontend sederhana dengan source attribution dan safety boundaries

Project ini bukan sistem diagnosis, resep, atau pengganti tenaga kesehatan.

## Struktur Project

```text
backend/     Backend FastAPI dan service layer
data/        Data lokal non-sensitif untuk ingestion/evaluation
docs/        Dokumentasi arsitektur dan development plan
frontend/    Frontend application (akan diimplementasikan pada fase berikutnya)
scripts/     Utility scripts untuk development dan data pipeline
```

## Prasyarat

- Docker Desktop
- Python 3.11 atau 3.12 direkomendasikan untuk dependency compatibility
- Git
- Node.js LTS

## Environment

Salin `.env.example` menjadi `.env`, lalu isi secret jika sudah tersedia. Jangan commit `.env`.

## Development Plan

Lihat [`docs/development-plan.md`](docs/development-plan.md).
