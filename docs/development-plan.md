# Development Plan

Urutan implementasi yang disepakati:

| Phase | Pekerjaan |
| --- | --- |
| 0 | Project definition |
| 1 | Repository + environment |
| 2 | Docker PostgreSQL + pgvector |
| 3 | Database schema |
| 4 | Healthcare source ingestion |
| 5 | Chunking |
| 6 | Embedding generation |
| 7 | Vector storage |
| 8 | Similarity retrieval |
| 9 | RAG pipeline |
| 10 | Featherless integration |
| 11 | FastAPI |
| 12 | n8n workflows, hanya jika berguna |
| 13 | Frontend sederhana |
| 14 | Safety layer |
| 15 | Evaluation |
| 16 | Deployment |
| 17 | Demo preparation |
| 18 | Hackathon submission |

Setiap fase harus diuji sebelum berpindah ke fase mayor berikutnya.

## Kembali ke urutan awal — keputusan pengguna

Backend dasar sampai Phase 11 sudah diimplementasikan; bukan berarti kualitas
grounding, safety dan evaluasi produk sudah tuntas. Berikutnya adalah perencanaan
Phase 12 (n8n), bukan ekspansi dataset atau eksperimen model tambahan.
Perbaikan bug yang menghalangi core flow tetap ditangani dan dilaporkan.

Update Phase 15: evaluasi 24 kasus dan audit stack sudah dijalankan; lihat
`docs/phase15-conclusion.md`. Hasil 18/24 status sesuai target, 6/14 edukatif ditahan.
Deployment publik ditahan sampai remediasi P0; ini bukan kelulusan kualitas medis.

Permintaan tambahan di `docs/backlog.md` hanya dikerjakan setelah pengguna
secara eksplisit mengaktifkannya kembali. Tidak ada auto-resume setelah fase lain
selesai. Pertahankan implementasi, data dan hasil eksperimen yang sudah ada;
kembali ke urutan awal tidak berarti menghapus pekerjaan atau mengganti stack.
