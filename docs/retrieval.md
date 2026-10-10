# Phase 8 — similarity retrieval

MVP menerima pertanyaan bahasa Inggris. BGE small tetap memakai CPU, vector
384 dimensi, normalisasi, dan query instruction yang sama dengan Phase 6.
Cache model diarahkan ke `.cache/huggingface/hub` di root project, termasuk saat
encoder dipanggil tanpa script aktivasi. CLI search offline: cache harus sudah ada.

## Menjalankan

```powershell
. .\scripts\activate-project.ps1
python scripts/search_documents.py "What is high blood pressure?" --top-k 3
```

Search membaca `.env` jika tersedia; environment process memiliki prioritas.
Output JSON berisi request ID, hit chunks, source ID, judul, URL asli dari database,
similarity, dan durasi embedding/retrieval. Log operasional tidak menyimpan pertanyaan
atau teks evidence. Output CLI memang menampilkan evidence untuk inspeksi developer.
Gunakan pertanyaan edukasi/sintetis, bukan informasi pasien pribadi.

SQL memakai cosine distance `<=>`, filter model dan MedlinePlus, urutan jarak
terkecil lalu ID chunk untuk tie-break, serta parameter `LIMIT` (1–20, default 5).
Search exact tanpa HNSW untuk corpus kecil. Satu dokumen boleh menghasilkan beberapa
chunks; deduplication/reranking belum dilakukan. Database tidak diubah oleh pencarian.

## Batasan

- Similarity bukan confidence, probabilitas, diagnosis, atau penilaian grounding.
- Pertanyaan di luar corpus tetap dapat menghasilkan tetangga terdekat yang tidak relevan.
  Belum ada threshold relevansi yang dikalibrasi; jangan gunakan hasil ini untuk
  mengklaim evidence mencukupi. Penanganan evidence insufficient masuk fase RAG.
- Database kosong/tanpa vector yang cocok menghasilkan `hits: []`. Error koneksi
  atau model ditampilkan sebagai kegagalan, bukan disamarkan sebagai hasil kosong.
- Input kosong, >2000 karakter, dan query melewati batas token model ditolak.
  Bahasa Inggris merupakan batas scope; belum ada pendeteksi bahasa otomatis.
- Durasi embedding pertama mencakup pemuatan model, bukan hanya encoding.
- Tidak ada Featherless, API, atau jawaban AI pada fase ini.

## Tests

```powershell
python -m pytest backend/tests -q
$env:RUN_DB_TESTS = '1'
python -m pytest backend/tests -q
Remove-Item Env:RUN_DB_TESTS
```

Test database menggunakan temporary tables untuk menguji ranking, top-K, tie-break,
model/source filtering, NULL vectors, corpus kosong dan atribusi tanpa mengubah data
MedlinePlus. Pemeriksaan relevansi pada beberapa pertanyaan hanyalah smoke test,
bukan evaluation 20–30 pertanyaan atau klaim akurasi produk.

## Hasil verifikasi awal

Pada corpus 106 vector, pertanyaan berikut menghasilkan topik sesuai di peringkat
pertama (juga diperiksa URL-nya dalam top-3):

| Pertanyaan sintetis | Topik pertama |
| --- | --- |
| What is diabetes? | Diabetes |
| What is high blood pressure? | High Blood Pressure |
| What are antibiotics used for? | Antibiotics |
| What is dehydration? | Dehydration |

Negative probe `How do I repair a bicycle chain?` tetap menghasilkan chunks tidak
relevan, dengan similarity teratas sekitar 0.492. Ini menegaskan perlunya penanganan
evidence insufficient pada fase berikutnya, bukan alasan menetapkan threshold dari
satu contoh. Query tekanan darah juga mengambil topik pregnancy pada peringkat
ketiga: konteks khusus tersebut tidak otomatis relevan untuk semua pengguna.

Satu run CLI membutuhkan sekitar 16.65 detik untuk load+query embedding pertama,
dan 14.33 ms untuk retrieval SQL. Ini pengamatan satu run, bukan benchmark umum.
Tidak ada dependency baru atau package global yang dipasang pada fase ini.
