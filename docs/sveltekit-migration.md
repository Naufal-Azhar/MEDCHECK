# Migrasi framework ke SvelteKit

## Runtime baru

Aplikasi full-stack berada di `frontend/`: **SvelteKit 3, Svelte 5, TypeScript, Vite, Node adapter**. UI native DOM lama digantikan halaman reaktif Svelte; endpoint HTTP Python digantikan `+server.ts`. Tidak ada proxy FastAPI atau subprocess Python pada jalur request.

```text
Browser — Svelte UI
  → SvelteKit /chat atau /search
  → safety preflight lokal
  → Featherless embedding
  → PostgreSQL + pgvector (driver pg)
  → bounded context + exact source attribution
  → Featherless generation
  → schema/citation/unsafe-output/lexical validation
  → Featherless claim review (fail closed)
  → respons JSON dan UI
```

Sumber, tabel, data dan model yang dipakai tetap sama. Migrasi framework tidak memerlukan re-embedding atau perubahan schema database. Pipeline ingestion/chunking/penyimpanan embedding tetap berupa CLI Python. Modul domain Python dipertahankan untuk utilitas dan regression testing; bukan framework aplikasi kedua.

## File dan kompatibilitas

- `frontend/src/routes/+page.svelte`: halaman utama; `+layout.svelte` memuat CSS.
- `frontend/src/routes/{chat,search,health,sources/[id],docs}/+server.ts`: endpoint kompatibel pada URL lama.
- `frontend/src/lib/server/`: provider, database, retrieval, safety, grounding, validasi JSON duplikat dan answer generation.
- `frontend/src/env.ts`: deklarasi konfigurasi private runtime SvelteKit 3.
- `frontend/vite.config.ts`: plugin SvelteKit 3, adapter Node, dan `.env` root.
- `frontend/package-lock.json`: dependency tree reproducible via `npm ci`.
- FastAPI/Uvicorn dan entrypoint HTTP Python dihapus. Tes HTTP Python digantikan Vitest dan smoke test build.
- `/docs` adalah OpenAPI JSON; tidak ada Swagger UI. Aset kini di `/_app/...`, bukan `/assets`.
- Skrip pengujian view-model lama sekarang mengimpor modul dari `frontend/src/lib/`.
- Runner evaluasi live Python (`scripts/verify_phase14_e2e.py`, dipakai juga oleh
  `evaluate_phase15.py`) kini menjalankan hasil build Node, bukan Uvicorn. Tetap
  wajib `--live` untuk mengizinkan API berbayar; jalankan build terlebih dahulu.

## Menjalankan

Dari root project, Node 24 LTS direkomendasikan (minimum 22.17):

```sh
npm --prefix frontend ci
docker compose up -d postgres
npm --prefix frontend run dev
```

Development memakai `http://127.0.0.1:5173`. Database harus sudah memiliki schema dan corpus melalui migrasi/ingestion manual yang ada. Jangan menjalankan ulang chunking pada data aktif hanya untuk migrasi framework.

Untuk production lokal:

```sh
npm --prefix frontend run build
npm --prefix frontend start
```

`start` membaca `.env` root melalui Node `--env-file-if-exists`; default port 3000. Atur `HOST`, `PORT`, dan `ORIGIN` sesuai deployment. Untuk DB/provider, nilai environment proses mengungguli file `.env`. Secret tidak di-inline ke client dan tidak memakai prefix `PUBLIC_`.

`DATABASE_URL` (opsional) diutamakan. Jika kosong, driver memakai `PGHOST`, `POSTGRES_PORT`/`PGPORT`, `POSTGRES_DB`/`PGDATABASE`, `POSTGRES_USER`/`PGUSER`, `POSTGRES_PASSWORD`/`PGPASSWORD`. Default lokal mengikuti Compose port 5433; default password hanya untuk development. Config Python CLI masih terpisah: jangan mengasumsikan `DATABASE_URL` baru mengubah semua CLI lama.

Featherless tetap dibatasi ke endpoint resmi dan model generation yang disetujui. Kunci diperlukan untuk query edukatif; refusal lokal tidak membutuhkan DB/API key. Tidak ada download/inference model lokal.

## Perilaku yang dipertahankan

- Preflight urgent/privacy/personal/injection/ambiguity sebelum DB atau provider.
- Respons gagal/refusal tidak mengekspos klaim model yang tidak lolos.
- Exact cosine retrieval, maksimum 5 dokumen/6000 karakter context default.
- Kutipan harus substring sumber dan ID valid. Jawaban bahasa Inggris tetap memakai
  lexical gate untuk istilah baru. Terjemahan jawaban bahasa Indonesia tidak bisa
  memakai gate leksikal Inggris; pemeriksaan lokal menahan angka yang tidak ada
  pada kutipan dan instruksi berbahaya, lalu review klaim bilingual wajib lolos
  sebelum jawaban ditampilkan. Review model bukan verifikasi medis independen.
- Input maksimal 2000 karakter, `top_k` 1–20, request UUID, validasi tanpa echo input, `no-store`.
- Maksimum payload JSON request 32 KiB; error provider/database tidak membocorkan detail.
- Tidak ada retry otomatis. Query edukatif dapat memakai embedding + generation + review (tiga panggilan berbayar).
- Tidak ada localStorage/history pertanyaan, analytics, atau rendering HTML mentah.

## Verifikasi dan keterbatasan

```sh
npm --prefix frontend run check
npm --prefix frontend test
npm --prefix frontend run build
npm --prefix frontend run test:smoke
node --test scripts/test_frontend.mjs
```

Vitest memakai provider/database mock; tes `pipeline.test.ts` menjalankan modul
safety/retrieval/provider/generation/review asli dengan mock hanya di boundary
DB dan HTTP provider. Belum memverifikasi query ke instance PostgreSQL nyata.
Smoke test menjalankan build pada loopback sementara dengan kredensial kosong dan DB sintetis yang tidak tersedia, menguji SSR/aset/API/refusal serta isolasi file, lalu mematikan server. Tidak menjalankan panggilan AI berbayar. Hasil evaluasi medis/runtime Python sebelumnya tidak otomatis berlaku sebagai evaluasi runtime SvelteKit baru.

Pertanyaan Indonesia yang terdeteksi memakai prompt dan safety preflight berbahasa
Indonesia; sumber masih MedlinePlus bahasa Inggris. Pendeteksi bahasa berbasis
frasa (heuristik), bukan klasifikasi bahasa menyeluruh. Pengujian bilingual saat
ini menggunakan provider/database mock; belum ada uji live untuk kecocokan
makna terjemahan atau kualitas retrieval lintas bahasa. `provider_error`
sebelumnya tidak otomatis selesai karena penambahan dukungan bahasa ini.

Belum ada autentikasi/rate limit, uji visual browser formal, atau verifikasi medis independen. Abort browser tidak menjamin provider berhenti menagih. Database/data ingestion masih membutuhkan pengelolaan manual. Jangan membuka aplikasi ke publik sebelum kontrol akses, pembatasan biaya, HTTPS dan evaluasi ulang selesai.

Audit dependency saat migrasi melaporkan empat advisory tingkat **low** pada jalur dev dependency `deepmerge` melalui toolchain Svelte; `npm audit --omit=dev` bersih. Tidak memakai `audit fix --force` karena saran tersebut menurunkan SvelteKit ke versi tidak kompatibel.
