# Phase 12 — n8n Cloud source check

Status: happy-path execution n8n Cloud 2.42.3 terverifikasi berdasarkan output
pengguna pada 2026-10-08T16:43:14.437Z setelah perbaikan field HTTP.
Workflow mengecek satu respons MedlinePlus saja, bukan ingestion, update corpus,
diagnosis, atau validasi isi medis. Tidak membutuhkan API key atau akses laptop.

## Import dan jalankan

1. Buka n8n Cloud di browser, buat workflow baru.
2. Buka menu workflow (biasanya ikon tiga titik di kanan atas).
3. Pilih **Import from File**, lalu pilih file lokal:
   `D:\project\FORGE\workflows\n8n\medlineplus-source-check.json`.
4. Pastikan ada lima node berurutan: Run manually → Fetch MedlinePlus →
   Check HTTP and XML safety → Parse XML as data → Validate and report.
5. Simpan workflow. Tidak perlu publish/activate, credential, schedule, atau webhook.
6. Klik **Execute Workflow** (nama tombol bisa berbeda menurut versi).
7. Buka output JSON node **Validate and report**.

Expected: `status: source_check_passed`, `http_status: 200`, `valid_documents: 1`,
judul, URL asli MedlinePlus dan waktu pengecekan. Judul hasil search dapat berubah;
tidak di-hardcode sebagai keberhasilan medis. Laporkan output tersebut atau error
node (tanpa cookie/token login) agar integrasi Cloud bisa dinyatakan terverifikasi.

## Jika gagal

- HTTP error/timeout: workflow harus berhenti merah, tidak retry otomatis.
- Format berubah/summary hilang: node validasi harus gagal, jangan aktifkan
  Continue On Fail atau Never Error untuk membuatnya hijau.
- XML node: mode XML to JSON; Property Name `data`; Explicit Root on,
  Explicit Array off, Merge Attributes off, Ignore Attributes off.
- Guard mengharapkan HTTP node mengembalikan `body` dan `statusCode` karena
  Include Response Headers and Status aktif, Response Format Text, dan
  **Put Output in Field = `body`**. Default field Text adalah `data`, bukan `body`.
- Jika import/version node tidak cocok, beri tahu versi n8n dan nama node/error.
  Belum ada klaim bahwa JSON ini sudah diuji di instance Cloud pengguna.

## Uji lokal dan batasnya

```powershell
node --test scripts/test_n8n_workflow.cjs
```

Menggunakan Node bawaan, tidak menginstal n8n atau npm package. Tests mengeksekusi
kode node dari file JSON dengan fixture bentuk output XML node (`xml2js`), tetapi
tidak menggantikan pengujian parser dan execution engine n8n yang sesungguhnya.
DTD/entity ditolak sebelum parsing. Tidak ada eval terhadap data sumber atau
pengambilan link eksternal. Tidak ada panggilan ke backend, database atau Featherless.

Setiap manual execution membuat satu GET MedlinePlus. Jangan spam Execute;
MedlinePlus membatasi 85 request/menit/IP dan menyarankan cache 12–24 jam.
Tidak ada biaya Featherless; kuota execution n8n Cloud mengikuti paket pengguna.
Execution history dapat menyimpan XML kesehatan publik; jangan mengubah input
menjadi data pasien pribadi. File export tidak mengandung credentials.

Referensi:
- https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/
- https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.xml/
- https://medlineplus.gov/about/developers/webservices/

## Perbaikan field respons (laporan Cloud 2.42.3)

Export pertama tidak menentukan `outputPropertyName`; HTTP Text menggunakan
default `data`, sementara guard membaca `body`. Ini menyebabkan error
`Source body missing or unexpectedly large` meskipun status HTTP sudah 200.
Export sekarang menetapkan `outputPropertyName: body` secara eksplisit.

Untuk workflow yang sudah diimpor: buka Fetch MedlinePlus → Options → Response,
set Put Output in Field ke `body`, simpan dan jalankan workflow dari awal.
Jika node memakai pinned data, unpin agar output lama tidak dipakai. Alternatif:
import file JSON yang diperbarui sebagai workflow baru, tanpa menghapus workflow
lama yang mungkin sudah kamu ubah. Perubahan file lokal tidak otomatis menyinkron
ke n8n Cloud. Jika masih gagal, periksa nama field/tipe/ukuran output HTTP; jangan
melewati guard atau mengaktifkan Never Error.

## Hasil Cloud yang dilaporkan pengguna

- `status`: `source_check_passed`
- `checked_at`: `2026-10-08T16:43:14.437Z`
- `http_status`: `200`
- `valid_documents`: `1`
- `title`: `Diabetes`
- `source_url`: `https://medlineplus.gov/diabetes.html`
- `summary_characters`: `5794`

Ini membuktikan happy path workflow pada instance pengguna, bukan validasi medis,
ingestion, atau pembaruan database. Kasus error/empty/unsafe XML sudah diuji secara
lokal (5 tests); simulasi kasus gagal di Cloud belum dilaporkan. Kriteria pengujian
kegagalan Cloud tetap terbuka dan tidak diklaim sudah dilakukan.
