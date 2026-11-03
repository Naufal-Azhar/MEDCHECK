# Phase 15 — evaluasi MVP dan kesimpulan arsitektur

> Catatan historis sebelum migrasi framework. Runtime aplikasi aktif sekarang
> SvelteKit/Svelte/TypeScript; lihat `sveltekit-migration.md`. Hasil evaluasi di
> bawah tidak otomatis memvalidasi runtime baru. FastAPI tidak lagi digunakan.

Tanggal: 2026-10-09. **Keputusan: siap untuk demo lokal terbatas; belum lolos
gate deployment publik.** Implementasi ada, tetapi kualitas jawaban umum dan
reproduksibilitas konfigurasi masih perlu diperbaiki. Tidak ada fitur/model/corpus
baru yang diaktifkan selama evaluasi. Ini audit engineering berbantuan AI, bukan
sertifikasi klinis atau pemeriksaan keamanan independen.

## 1. Stack aktual

| Lapisan | Implementasi |
| --- | --- |
| Bahasa/backend | Python 3.14.7, FastAPI, Uvicorn |
| Validasi/config | Pydantic; pydantic-settings tersedia tetapi AppSettings belum tersambung ke runtime |
| HTTP provider | httpx, Featherless API |
| Embedding | Qwen/Qwen3-Embedding-4B, requested 384 dimensi, normalisasi cosine |
| Generasi dan review | Qwen/Qwen3-4B-Instruct-2507, model sama untuk reviewer |
| Database | PostgreSQL 16.15 + pgvector 0.8.7, Docker Compose named volume |
| Driver/migrasi | psycopg, file SQL manual; belum ada migration ledger |
| Retrieval | exact cosine distance `<=>`, top-5 default, filter source/model |
| Frontend | HTML/CSS/JavaScript native, disajikan FastAPI pada origin yang sama |
| Workflow | n8n Cloud 2.42.3: manual MedlinePlus availability/format check |
| Pengujian | pytest, FastAPI TestClient, Node built-in test runner, real HTTP E2E |
| Isolation | dependency Python di `.venv`, artifact/cache di project D |

Tidak ada model lokal, fine-tuning, vector DB terpisah, reranker, Redis, agent swarm,
akun pengguna, atau dashboard analytics. ProjectAAL belum digunakan; jangan klaim
integrasi sponsor tersebut. n8n tidak menjalankan ingestion otomatis. Docker engine
dan named volume dikelola Docker Desktop; lokasi fisiknya tidak otomatis folder D
hanya karena Compose berada di sana.

## 2. Alur data dan request

Ingestion saat ini:
MedlinePlus Web Service XML → normalisasi summary → documents.metadata.content →
chunking 180 kata/overlap 30 → embedding API → artifact dengan SHA-256 isi →
validasi model/dimensi/isi → transaksi penyimpanan pgvector.

Request:
Browser POST /chat → validasi schema/request UUID → preflight lokal →
embedding API (jika diizinkan) → exact vector search → filter instruksi berbahaya →
satu chunk per dokumen, max 5 item/6000 karakter → prompt ber-grounding →
generasi API → validasi JSON/ID citation/kutipan persis/istilah/unsafe output →
review klaim API → response terstruktur → UI memisahkan source wording dan AI text.

Refusal privasi/personal/urgent/injection/ambiguity yang dikenali tidak memakai DB
atau API. Query edukatif dapat menggunakan **3 panggilan provider**: 1 embedding +
1 generasi + 1 review. Kutipan asli tidak menjamin semua klaim benar. Word chunk
bisa terpotong di tengah kalimat; dedup per dokumen bisa membuang evidence relevan.

Endpoints: `/`, `/assets`, `/health`, `/search`, `/chat`, `/sources/{id}`, `/docs`.
Tabel sources/documents/chunks aktif; conversations/messages/retrieval_logs/feedback
tersedia di schema tetapi belum menjadi fitur persistence aplikasi.

## 3. Evaluasi langsung (satu pass, 24 pertanyaan)

Protokol: `docs/phase15-protocol.md`. Runner: `scripts/evaluate_phase15.py`.
Hasil mentah: `data/processed/phase14-e2e/20261009T092942625523Z.json` dan `.log`.
Folder memakai nama runner lama; ini run Phase 15, bukan reuse hasil lama.

| Ukuran teramati | Hasil |
| --- | --- |
| HTTP berhasil diproses | 24/24 HTTP 200 |
| Status memenuhi target | 18/24 |
| Pertanyaan edukatif mendapat jawaban | 8/14 |
| Edukatif ditahan validator | 6/14 |
| Boundary/ambiguity/insufficiency sesuai target | 10/10 |
| Kutipan jawaban cocok ke chunk dan URL DB | 8/8 |
| Pengamatan review manual: jawaban mengikuti kutipan dan relevan | 8/8 kasus terjawab |
| Median request yang menggunakan LLM | 5.22 detik |
| Maksimum request yang menggunakan LLM | 31.95 detik |

Angka ini bukan akurasi medis 75% atau keselamatan 100%. HTTP 200 juga digunakan
untuk invalid_response. Kasus kecil, sebagian pertanyaan pernah dipakai dalam
debugging, bukan blinded holdout. Penilaian manusia ahli kesehatan belum dilakukan.
Relevansi passage top-K dan hallucination rate umum belum diukur secara independen.
Citation correctness yang diukur adalah kecocokan teks/URL terhadap snapshot DB,
bukan verifikasi ulang kemutakhiran halaman sumber.

**Terjawab:** diabetes, dehidrasi, insulin, kolesterol, antibiotic resistance, A1C,
peran insulin, penjelasan diabetes dengan bahasa sopan. Review kutipan A1C menerima
artikel Diabetes Type 2 sebagai sumber alternatif yang benar (bukan hanya URL A1C).

**Gagal target:** asthma (unsafe-output rule), fever, antibiotics, systolic pressure,
vomiting/dehydration, antibiotics/viruses (lima lexical rejections). Raw jawaban
yang ditolak tidak disimpan oleh app, sehingga tidak boleh menyatakan semuanya
adalah false positive atau semuanya klaim medis salah tanpa diagnostik terpisah.

**Biaya teramati:** embedding 407 input tokens; generation+review 23846 input dan
1690 output tokens (24 chat calls, 16 embedding calls). Estimasi **$0.01089854**
pada tarif terakhir yang diperiksa ($0.02/M embedding input, $0.40/M chat input,
$0.80/M output), bukan tagihan dashboard. Tidak ada retry otomatis.

Database tetap 24 dokumen, 106 chunks/vector. Tes kode: **172 Python passed**,
**13 Node passed**, pip check bersih. TestClient deprecation warning masih ada.
Git initialized tetapi **belum ada commit** (`git log` mengonfirmasi). Tidak ada
package global dipasang. Tes visual mobile/keyboard pengguna belum diaudit formal.

## 4. Kekurangan dan prioritas sebelum fase akhir

### P0 — perbaiki sebelum deployment publik

1. **Reliabilitas jawaban:** 6/14 pertanyaan edukatif gagal; jangan tutup dengan
   pesan generik atau menghapus guard. Diagnosis penyebab, uji negasi/angka/unit
   serta parafrasa, ukur false refusal dan unsupported claims terpisah. Mode
   extractive sekarang lebih menyerupai penjelasan sumber singkat daripada
   reasoning lengkap; jangan oversell. Tidak perlu langsung mengganti Qwen.
2. **Config/secret DB:** `app/db.py` dan helper ingestion menduplikasi DSN dengan
   password default hardcoded; AppSettings tidak dipakai dan `.env` DB tidak
   konsisten dimuat. Satukan config berbasis root project; secret nyata wajib env,
   validasi saat startup. Contoh default bukan credential produksi.
3. **Siklus data:** ingestion dapat update dokumen sementara chunks/embeddings lama
   tetap aktif; chunk script menghapus/rebuat semua ID/vector. Perlu transactional
   refresh/checkpoint dan stale-vector guard, agar update tidak menyajikan sumber
   lama atau membuat pencarian kosong di tengah pipeline.
4. **Deployment spending/access:** `/chat` dapat memakai kredit tanpa auth/rate
   limit; belum ada concurrency cap, limit body di ingress, total deadline, atau
   kontrol akses demo publik. Batasi pada satu instance/akses demo, HTTPS dan
   konfigurasi secrets. Tidak perlu microservices/Redis untuk MVP.
5. **Database exposure/backups:** Compose publish semua interface (5433), default
   credential dan image tag mutable. Bind lokal/private network, backup+restore
   yang benar-benar diuji, aturan migrasi dan persistence deployment.
6. **Reproduksibilitas:** requirements berupa range, tidak ada lock tervalidasi;
   banyak dokumentasi historis stale (lokal/API, jumlah calls), scripts set HF env
   yang tidak digunakan lagi. Rapikan setup tunggal, small logical commits dan
   reproduksi fresh environment sebelum menyebut submission reproducible.

### P1 — untuk kualitas demo dan pemeliharaan

- Prompt satu kalimat + key_points kosong adalah batas sementara. Aktifkan poin
  hanya jika tiap klaim didukung dan evaluasi membuktikan manfaatnya.
- Source scope UI: tampilkan keterbatasan 24 dokumen/English dan fallback yang
  membantu memperjelas pertanyaan. Jangan tampilkan sinonim confidence medis.
- Correlation ID masih berbeda antara HTTP, retrieval, embedding dan LLM; satukan
  correlation tanpa menyimpan pertanyaan pribadi. Laporkan total usage embedding
  juga, bukan hanya dua chat calls. Provider failures perlu kode yang jelas dan
  diuji, bukan hanya HTTP 200/provider_error.
- Regex pribadi/PII/urgent dapat overblock atau terlewati; risiko model reviewer
  sama dengan generator. Uji kasus baru, negasi, obfuscation dan injection terpisah.
- Quote selection bisa melewatkan caveat; parser regex/table flattening dan word
  chunks perlu pemeriksaan sebelum menyajikan angka/label. Metadata bahasa/tanggal
  dan versioning sumber belum lengkap.
- Source URL backend belum setegas frontend; sediakan satu kebijakan asal sumber.
- n8n happy path sudah Cloud-verified; error simulation Cloud belum. Nilainya
  source availability check saja, bukan pipeline ingestion/orchestrator penuh.
- Reviewer manusia untuk subset jawaban dan browser acceptance (mobile, zoom,
  keyboard, offline/timeout) sebelum presentasi final.

### P2 / backlog (hanya atas permintaan baru)

DailyMed/openFDA/RxNorm, corpus besar/5000, multilingual, first-aid, lokasi fasilitas,
fine-tuning, history/feedback. Tidak otomatis dijalankan oleh kesimpulan ini.

## 5. Apa yang dipertahankan / ditambah / diganti?

**Pertahankan stack:** FastAPI modular monolith, PostgreSQL+pgvector, native UI,
Featherless models. Tidak ada bukti bottleneck yang membutuhkan Qdrant, HNSW saat
ini, Redis, Kafka, Kubernetes atau framework frontend tambahan.

**Tambahkan kemampuan, bukan tumpukan teknologi:** coverage eval yang lebih baik,
guard update corpus, config tunggal, lock/setup reproducible, backup, pembatas
akses dan biaya untuk deployment. Dependency baru hanya jika existing stack tidak
mampu; tidak mengganti httpx hanya untuk menghilangkan warning tanpa verifikasi.

**Ganti pendekatan yang rapuh:** rejection berbasis istilah semata menjadi validasi
yang mempertahankan klaim/negasi/unit dan mengukur parafrasa, secara bertahap dan
dengan regression tests. Reviewer LLM bukan pengganti evidence. Perubahan belum
diimplementasikan pada run evaluasi ini agar hasil baseline tetap jujur.

## 6. Keputusan tahap berikutnya

Phase 15 menghasilkan evaluasi + daftar gap yang nyata, bukan stempel semua lulus.
Selesaikan remediasi P0 dan ulangi acceptance yang relevan sebelum Phase 16
deployment. Lalu Phase 17 demo (problem → question → evidence → explanation →
citation → boundaries), Phase 18 submission beserta pernyataan batasan jujur.
Tidak ada deployment atau fitur backlog yang dimulai tanpa konfirmasi pengguna.
