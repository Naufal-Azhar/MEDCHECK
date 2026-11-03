# SvelteKit API

Semua endpoint sekarang diimplementasikan sebagai route server SvelteKit pada origin yang sama dengan UI. Tidak ada FastAPI/Uvicorn.

## Jalankan

Dari root project:

```sh
npm --prefix frontend ci
npm --prefix frontend run dev
```

Development URL: `http://127.0.0.1:5173`; production adapter-node default port 3000. Konfigurasi provider/database dibaca dari `.env` root, hanya pada server. Database memerlukan migrasi dan ingestion manual yang sudah ada.

## Endpoint

| Method | URL | Fungsi |
| --- | --- | --- |
| GET | `/` | Halaman UI Svelte dengan SSR |
| GET | `/health` | HTTP 200 dengan `status=ok` atau `degraded`, bergantung koneksi DB |
| POST | `/search` | Retrieval MedlinePlus; bukan jawaban AI |
| POST | `/chat` | Preflight, retrieval, generation, validasi, claim review |
| GET | `/sources/{id}` | Metadata sumber; 404 jika tidak ditemukan |
| GET | `/docs` | Dokumen OpenAPI JSON, bukan Swagger UI |

Body JSON `/chat` dan `/search`:

```json
{"question":"What is diabetes?","top_k":5}
```

Pertanyaan kesehatan umum dapat diajukan dalam bahasa Inggris, misalnya
`What is diabetes?`, atau Bahasa Indonesia, misalnya `Apa itu diabetes?`.
Bahasa dikenali dari frasa pertanyaan, bukan dari field request terpisah.
Jawaban Indonesia harus didukung kutipan MedlinePlus asli yang tetap berbahasa
Inggris dan disetujui oleh review bilingual; tidak ada jaminan kesetaraan
terjemahan secara klinis. Pendeteksi bahasa masih heuristik.

`question` wajib string non-blank, maksimal 2000 karakter; `top_k` integer 1–20 (default 5). Body dibatasi 32 KiB. Validation errors tidak menggemakan input. Kirim `Content-Type: application/json`.

Contoh PowerShell (menggunakan API provider berbayar bila konfigurasi lengkap):

```powershell
$body = @{ question = "What is diabetes?"; top_k = 5 } | ConvertTo-Json
Invoke-RestMethod http://127.0.0.1:5173/chat -Method Post -ContentType "application/json" -Body $body
```

## Respons dan safety

Chat mempertahankan field `request_id`, `status`, `answer`, `key_points`, `sources`, `confidence_or_uncertainty`, `safety_note`, `usage`, `safety_reason`. Status: `answered`, `insufficient_evidence`, `safety_refusal`, `privacy_refusal`, `clarification_needed`, `invalid_response`, `provider_error`.

Preflight berjalan sebelum DB/API key/provider. Urgent wording yang dikenali mendapat arahan generik ke layanan darurat, bukan diagnosis. Search yang diblokir mengembalikan `question` kosong, `hits` kosong, notice dan safety reason. Nearest-neighbor similarity bukan confidence medis.

`/search` edukatif dapat menggunakan satu embedding API call. `/chat` edukatif dapat memakai tiga provider call: embedding, generation dan review. Tidak ada retry otomatis. Abort pada browser tidak menjamin server/provider berhenti memproses atau menagih.

## Operasional

- UUID valid pada `X-Request-ID` dipakai kembali; selain itu dibuat UUID baru. ID dikembalikan pada header respons.
- Respons memakai `Cache-Control: no-store` dan `X-Content-Type-Options: nosniff`.
- Invalid request: 422; DB/provider/config unavailable: 503, dengan pesan aman tanpa detail sensitif.
- Penolakan atau respons LLM yang ditahan dapat tetap HTTP 200: client harus memeriksa `status`.
- Tidak ada autentikasi/rate limit. Hanya untuk demo lokal; jangan membuka endpoint berbayar ke publik tanpa kontrol akses dan pembatasan biaya.

Lihat `sveltekit-migration.md` dan source `frontend/src/routes/docs/+server.ts` untuk kontrak OpenAPI.
