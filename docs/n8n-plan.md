# Phase 12 — rencana workflow n8n

Status: happy path berhasil di n8n Cloud 2.42.3 berdasarkan output pengguna
2026-10-08T16:43:14.437Z. Tests lokal: 5 passed. Uji kegagalan pada Cloud belum
dilaporkan. Panduan dan hasil: `docs/n8n-setup.md`.

## Tujuan dan nilai

Satu workflow manual untuk memeriksa ketersediaan dan format respons MedlinePlus
sebelum developer menjalankan ingestion. Workflow menghasilkan laporan singkat
yang bisa diperiksa di execution history n8n. Ini bukan bukti data di database
mutakhir, bukan ingestion otomatis, dan bukan syarat agar chat bisa berjalan.

## Alur yang diusulkan

1. Manual Trigger — hanya berjalan ketika developer menekan Execute Workflow.
2. HTTP Request — GET endpoint resmi, satu keyword tetap dari corpus yang ada:
   `https://wsearch.nlm.nih.gov/ws/query?db=healthTopics&term=diabetes&retmax=1&rettype=brief&tool=forgehacks_health_assistant`
3. XML parsing — parse sebagai data; jangan mengambil external entities/tautan.
4. Validasi — periksa status HTTP, struktur hasil, judul, summary nonkosong dan URL
   HTTPS dengan hostname tepat `medlineplus.gov`.
5. Laporan — waktu pengecekan, jumlah hasil valid, status siap/tidak siap, serta
   alasan kegagalan. Error jaringan/parser tidak boleh dinyatakan sebagai sukses.

## Batasan

- Tidak ada pertanyaan pengguna, data pasien, API key Featherless atau password DB.
- Tidak menambahkan artikel, memotong ulang chunks atau menghasilkan embedding.
- Tidak memasang schedule, retry otomatis, tunnel publik atau endpoint baru.
- Tidak mengeksekusi teks dari hasil sumber sebagai instruksi/kode.
- Kegagalan dihentikan/ditandai gagal, bukan disamarkan menjadi laporan hijau.
- Tidak membutuhkan akses dari n8n ke PostgreSQL/FastAPI lokal. `localhost` di
  n8n Cloud bukan laptop developer. Jangan expose database/API untuk workflow ini.

## Rencana file implementasi setelah akses dikonfirmasi

- `workflows/n8n/medlineplus-source-check.json`: workflow importable, inactive.
- `docs/n8n-setup.md`: langkah import, menjalankan manual, batasan dan hasil uji.
- Tests lokal terhadap transformasi/struktur workflow bila diperlukan.

## Kriteria verifikasi

1. Import berhasil pada versi instance n8n pengguna.
2. Execute Workflow menghasilkan respons sumber valid dan laporan sesuai data.
3. Respons kosong, format salah, dan error HTTP tidak menghasilkan sukses palsu.
4. Tidak ada secret yang dibutuhkan/disimpan dalam export workflow.
5. Corpus database dan saldo Featherless tidak berubah karena workflow ini.

Tes lokal saja tidak membuktikan integrasi n8n berhasil. Jangan menyatakan Phase 12
selesai sebelum ada execution nyata pada instance pengguna. Selanjutnya tunggu
konfirmasi sebelum Phase 13 frontend.

Referensi Manual Trigger:
https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.manualworkflowtrigger/
