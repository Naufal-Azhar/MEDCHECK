# Phase 11 — FastAPI

## Phase 14 safety update

Preflight runs before DB/key access on both `/chat` and `/search`. Blocked search
returns no hits and an empty question, with `status`, `safety_reason` and a notice.
Chat adds `safety_reason` and supports `privacy_refusal` and `clarification_needed`.
Known urgent wording gets immediate generic emergency referral, with no AI call.
Request IDs are accepted only as UUIDs; otherwise regenerated. Validation errors
do not echo input. Chat/search responses use `Cache-Control: no-store`.
See `docs/phase14-safety.md` for limitations and verification status; this supersedes
earlier request-ID handling below.

Run from the project root with the project-local environment:

```powershell
. .\scripts\activate-project.ps1
uvicorn app.main:app --app-dir backend --reload
```

On Windows PowerShell, `curl` is commonly an alias for `Invoke-WebRequest` and
does not accept Linux curl flags. Use `Invoke-RestMethod` or explicitly call
`curl.exe`.

## Endpoints

### `GET /health`

Returns service and database status. `200` with `status=ok` means the database
check passed; `status=degraded` means the process is alive but DB unavailable.

### `POST /search`

Request:

```json
{"question":"What is diabetes?","top_k":3}
```

PowerShell example:

```powershell
$body = @{ question = "What is diabetes?"; top_k = 3 } | ConvertTo-Json
Invoke-RestMethod http://127.0.0.1:8000/search -Method Post -ContentType "application/json" -Body $body
```

Returns retrieved MedlinePlus chunks, original URLs, similarity scores and timing.
It does not call Featherless chat generation and is not an answer.

### `POST /chat`

Request:

```json
{"question":"What is diabetes?","top_k":5}
```

PowerShell example:

```powershell
$body = @{ question = "What is diabetes?"; top_k = 5 } | ConvertTo-Json
Invoke-RestMethod http://127.0.0.1:8000/chat -Method Post -ContentType "application/json" -Body $body
```

Runs retrieval, safety preflight, grounded Featherless generation and claim review.
Personal medical decision requests are refused before embedding/provider calls.
An educational answer can use two provider calls: generation and review.

### `GET /sources/{id}`

Returns configured source metadata and `404` if absent.

## Operational behavior

- `X-Request-ID` is accepted or generated and returned on every response.
- Logs include request ID, durations, hit count and source IDs, but not question,
  evidence text, API key, or provider response.
- `422` is used for invalid request data; `503` for unavailable database/provider.
- Error responses intentionally avoid database/provider details.
- No authentication, rate limiting, CORS policy, or public deployment is implemented.
  This is a development API; those are required before exposure beyond localhost.
- Response schema is MVP and may evolve before frontend integration.
