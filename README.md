# FORGE — Healthcare Information Assistant

Asisten informasi kesehatan berbasis sumber MedlinePlus. **Framework aplikasi sekarang SvelteKit 3 + Svelte 5**, dengan TypeScript untuk UI dan endpoint server; FastAPI/Uvicorn tidak lagi digunakan.

Ajukan pertanyaan kesehatan umum dalam **bahasa Inggris atau Bahasa Indonesia**. Penjelasan mengikuti bahasa pertanyaan yang dikenali; kutipan sumber MedlinePlus tetap dalam bahasa Inggris. Pengenalan bahasa bersifat heuristik dan kualitas terjemahan medis belum diverifikasi independen.

Project ini bukan sistem diagnosis, resep, atau pengganti tenaga kesehatan. Status tetap **demo lokal terbatas, belum untuk deployment publik**. Evaluasi Python sebelumnya di `docs/phase15-conclusion.md` adalah catatan historis, bukan hasil evaluasi runtime baru.

## Stack aktif

- **SvelteKit 3 / Svelte 5 / TypeScript**: SSR, UI reaktif, dan API dalam satu aplikasi.
- **Node.js**: runtime server melalui `@sveltejs/adapter-node`; Vite untuk development/build.
- **PostgreSQL 16 + pgvector**, driver `pg`: exact cosine retrieval dari corpus yang sama.
- **Featherless API**: `Qwen/Qwen3-Embedding-4B` (384 dimensi) dan `Qwen/Qwen3-4B-Instruct-2507` untuk generation/review.
- **Vitest + svelte-check**: pengujian dan type-check aplikasi.
- **Python**: hanya utilitas ingestion, chunking, embedding, serta evaluasi offline di `backend/` dan `scripts/`; bukan server aplikasi.

## Menjalankan lokal

Prasyarat: Node.js 24 LTS (atau 22.17+), npm, Docker Desktop. Jalankan perintah berikut dari root project:

```sh
npm --prefix frontend ci
docker compose up -d postgres
npm --prefix frontend run dev
```

Buka `http://127.0.0.1:5173`. Untuk jawaban AI, database harus sudah diisi melalui pipeline ingestion yang ada. Compose hanya menjalankan database, tidak otomatis menjalankan migrasi atau ingestion.

Konfigurasi ada di `.env` **root project**, bukan di browser. Jika belum ada, salin `.env.example` ke `.env` dan isi API key sendiri. Jangan commit `.env`. SvelteKit memuat file ini saat development/preview; perintah `start` memuatnya saat production. Tidak ada secret memakai prefix publik.

## Validasi dan production build

```sh
npm --prefix frontend run check
npm --prefix frontend test
npm --prefix frontend run build
npm --prefix frontend run test:smoke
npm --prefix frontend start
```

`start` menggunakan port 3000 secara default. Sesuaikan `HOST`, `PORT`, dan `ORIGIN` lewat environment saat deployment. Smoke test berjalan dengan konfigurasi sintetis, tanpa database eksternal atau panggilan AI berbayar.

## Endpoint

`GET /`, `GET /health`, `POST /search`, `POST /chat`, `GET /sources/{id}`, dan `GET /docs`. `/docs` sekarang mengembalikan **OpenAPI JSON**, bukan Swagger UI FastAPI. Aset UI menggunakan URL build SvelteKit (`/_app/...`), bukan `/assets` lama.

## Struktur

```text
frontend/src/routes/       Halaman Svelte dan endpoint SvelteKit
frontend/src/lib/server/   Database, provider, retrieval, safety, RAG
frontend/tests/            Pengujian TypeScript tanpa panggilan provider
backend/                  Utilitas/data pipeline Python dan tes domain
scripts/                  CLI ingestion dan evaluasi
db/migrations/            Migrasi SQL manual
docs/                     Dokumentasi dan evaluasi historis
```

Lihat `docs/sveltekit-migration.md` untuk batas migrasi, konfigurasi, dan risiko operasional. Satu pertanyaan edukatif dapat memakai tiga panggilan provider (embedding, generation, review); tidak ada retry otomatis. Auth/rate limit dan evaluasi medis independen belum tersedia. Dukungan bilingual tidak memperbaiki error layanan provider; `provider_error` masih perlu didiagnosis terpisah.
