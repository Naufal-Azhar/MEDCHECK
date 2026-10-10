# Backend

Backend FastAPI akan menjadi modular monolith untuk ingestion, embeddings, retrieval, LLM, safety, dan API.

Pada fase ini backend baru menyiapkan struktur project. Endpoint dan database schema akan ditambahkan pada fase berikutnya.

## FastAPI

From the project root with the project environment active:

```powershell
. .\scripts\activate-project.ps1
uvicorn app.main:app --app-dir backend --reload
```

Endpoints: `GET /health`, `POST /search`, `POST /chat`, and `GET /sources/{id}`.

Example requests:

PowerShell's `curl` command is an alias for `Invoke-WebRequest`, so use
`Invoke-RestMethod`:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health

$body = @{ question = "What is diabetes?"; top_k = 3 } | ConvertTo-Json
Invoke-RestMethod http://127.0.0.1:8000/search -Method Post -ContentType "application/json" -Body $body

$body = @{ question = "What is diabetes?" } | ConvertTo-Json
Invoke-RestMethod http://127.0.0.1:8000/chat -Method Post -ContentType "application/json" -Body $body
```

Alternatively, call the real curl executable explicitly:

```powershell
curl.exe -X POST http://127.0.0.1:8000/search `
  -H "Content-Type: application/json" `
  -d '{"question":"What is diabetes?","top_k":3}'
```

## Menjalankan nanti

Environment Python sebaiknya dibuat dari Python 3.11 atau 3.12:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
