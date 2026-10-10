# Phase 9 — RAG context construction

Phase ini mengubah hasil similarity retrieval menjadi konteks terbatas untuk LLM
berikutnya. Setiap item mempertahankan judul dan URL dari database, diberi ID
`S1`, `S2`, dan seterusnya, serta deduplikasi pada tingkat dokumen.

Konteks dibatasi default menjadi maksimal 5 dokumen dan 6000 karakter. Flag
`insufficient_evidence` hanya berarti tidak ada item usable setelah filtering dasar;
flag ini bukan penilaian medis dan belum memakai threshold similarity yang terkalibrasi.

Phase 10 correction: budget mencakup header/separator dan hanya memasukkan chunk
utuh yang muat. Tidak ada pemotongan akhir prompt yang berbeda dari evidence list.
Flag false hanya menandakan ada kandidat, bukan bukti bahwa jawaban dapat diberikan.

```powershell
. .\scripts\activate-project.ps1
python scripts/build_context.py "What is diabetes?" --top-k 5
```

Tidak ada panggilan Featherless atau jawaban AI pada fase ini. Teks yang tercetak
oleh script hanya untuk inspeksi developer.
