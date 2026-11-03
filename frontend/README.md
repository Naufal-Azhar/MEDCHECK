# Aplikasi SvelteKit

UI dan API FORGE sekarang berjalan dalam **satu aplikasi SvelteKit 3 / Svelte 5** dengan TypeScript dan adapter Node. Tidak ada server FastAPI, proxy Python, atau pemanggilan subprocess Python pada request aplikasi.

## Development

Dari root project:

```sh
npm --prefix frontend ci
npm --prefix frontend run dev
```

Buka `http://127.0.0.1:5173`. Database disiapkan melalui `docker compose up -d postgres` dan migrasi/ingestion Python yang sudah ada. Dependensi membutuhkan Node 24 LTS atau 22.17+.

`vite.config.ts` menetapkan `env.dir: '..'` agar konfigurasi memakai `.env` root. `src/env.ts` mendeklarasikan variabel private runtime; secret tidak boleh diekspor ke client. Build dan refusal lokal dapat berjalan tanpa API key.

## Pengujian

```sh
npm --prefix frontend run check
npm --prefix frontend test
npm --prefix frontend run build
npm --prefix frontend run test:smoke
```

Vitest menguji kontrak tampilan, safety, grounding, provider, retrieval dan endpoint dengan mock, tanpa biaya API. Smoke test menjalankan hasil build pada port loopback sementara lalu menghentikannya otomatis; tes ini tidak melakukan panggilan provider atau memakai DB nyata. Pengujian visual/interaksi browser pengguna tetap perlu dilakukan.

## Production lokal

```sh
npm --prefix frontend run build
npm --prefix frontend start
```

Default port 3000. `start` memuat `../.env` bila tersedia melalui Node `--env-file-if-exists`. Set `ORIGIN` sesuai origin publik jika menjalankan di belakang reverse proxy. Jangan membuka server ke publik sebelum access control, rate limit, HTTPS, secrets, dan evaluasi kualitas siap.

## Perilaku UI

- Pertanyaan kesehatan umum diterima dalam bahasa Inggris maupun Bahasa Indonesia.
  Untuk pertanyaan Indonesia yang dikenali, model diminta menjawab dalam bahasa
  Indonesia dengan kutipan sumber asli MedlinePlus tetap dalam bahasa Inggris.
  Terjemahan hanya boleh ditampilkan bila kutipan persis dan review klaim lintas
  bahasa lolos; ini bukan jaminan akurasi medis. Pengenalan bahasa heuristik,
  jadi pertanyaan ambigu dapat salah dikenali.
- Hanya submit mengirim `POST /chat`; contoh pertanyaan hanya mengisi textarea.
- Kontrol dinonaktifkan saat loading; ada timeout 210 detik dan tidak ada retry otomatis.
- Status refusal, urgent, kurang evidence, error, dan respons tidak valid tidak menampilkan klaim model yang ditolak.
- Source wording dibedakan dari penjelasan AI; link sumber hanya HTTPS MedlinePlus.
- Svelte melakukan escaping teks; tidak menggunakan `{@html}`, localStorage, analytics, atau history pertanyaan.

API: `/chat`, `/search`, `/health`, `/sources/{id}`; `/docs` adalah OpenAPI JSON. Aset disajikan oleh SvelteKit, bukan folder `public` lama. Lihat `../docs/sveltekit-migration.md`.
