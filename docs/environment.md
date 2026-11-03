# Project Environment

## Runtime aplikasi SvelteKit

Aplikasi web sekarang memakai Node.js 24 LTS (minimum 22.17), bukan server Python.
Dari root: `npm --prefix frontend ci`, lalu `npm --prefix frontend run dev`.
Konfigurasi private memakai `.env` root. Lihat `sveltekit-migration.md` untuk
build, production, database dan validasi.

## Utilitas Python (ingestion/evaluation)

Environment berikut hanya diperlukan untuk skrip data dan tes domain Python.

ForgeHacks uses an isolated Python environment inside the project:

```text
D:\project\FORGE\.venv
```

Project package installations must use `.venv`; the global Python interpreter is only used to create the environment.

## PowerShell setup

From the project root:

```powershell
python -m venv .venv
. .\scripts\activate-project.ps1
python -m pip install -r backend\requirements-dev.txt
```

The script redirects local caches to:

```text
D:\project\FORGE\.cache\pip
D:\project\FORGE\.cache\huggingface
```

Verify isolation:

```powershell
python -c "import sys; print(sys.executable)"
python -m pip -V
```

Both paths should point inside `D:\project\FORGE\.venv`.
