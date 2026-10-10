# Frontend

Frontend MVP menggunakan HTML, CSS dan JavaScript native, tanpa framework, npm
dependency, CDN, font eksternal, analytics, atau build step. File publik saja
disajikan oleh FastAPI, sehingga tidak memerlukan dev server frontend atau CORS.

## Jalankan

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Buka http://127.0.0.1:8000/ (bukan file HTML langsung). Jika server sebelumnya
berjalan tanpa reload, restart terlebih dahulu. `/docs` tetap tersedia.

Hanya tombol submit yang mengirim `POST /chat`. Contoh pertanyaan hanya mengisi
input. Tidak ada history/localStorage atau penyimpanan pertanyaan di frontend.
Browser/network/backend dapat memproses request; jangan memasukkan data pribadi.
State: kosong, loading, jawaban, penolakan, evidence kurang, error HTTP/network,
timeout dan respons tidak valid. Key points kosong disembunyikan. Kutipan sumber
terpisah dari penjelasan AI; semua teks dinamis ditulis dengan `textContent`.

## Testing

```powershell
node --test scripts/test_frontend.mjs
.\.venv\Scripts\python.exe -m pytest backend/tests/test_frontend_routes.py -q
```

Uji browser manual: contoh tidak membuat request, submit sekali saat loading,
penolakan tanpa sumber palsu, kegagalan jaringan tidak meninggalkan jawaban lama,
navigasi keyboard, layar kecil/zoom, dan link sumber terbuka di tab baru.
Tes lokal ini belum menggantikan uji visual/interaksi di browser pengguna.

Development-only: belum ada auth/rate limit untuk public deployment. Backend
safety/grounding masih memiliki keterbatasan; UI tidak mengklaim confidence medis.
ProjectAAL belum digunakan: tidak dibutuhkan untuk UI kecil ini dan akses/integrasi
tidak diasumsikan tersedia. Tidak ada fitur backlog tambahan yang diaktifkan.
