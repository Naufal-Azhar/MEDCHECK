# Python data and evaluation utilities

`backend/` contains Python offline data/evaluation utilities and their domain
modules: ingestion, chunking, embedding artifacts, retrieval, grounded-answer
validation, and safety policy. It is not an application server. The application
framework, HTTP API, and server-rendered UI now live in the SvelteKit app under
`frontend/`; FastAPI/Uvicorn and the legacy Python HTTP modules have been retired.

## Install Python utilities

Run from the project root (`FORGE`) using Python 3.11 or 3.12:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
```

For development and tests, install the development requirements (which include
the utility dependencies):

```powershell
.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
.venv\Scripts\python.exe -m pytest backend/tests -q
```

The Python entry points remain in `scripts/`. Offline processing and validation
remain available without running a web server. Database operations require local
PostgreSQL/pgvector; provider-backed embedding and evaluation commands require
explicit configuration and may incur charges. Do not run live provider checks as
part of an offline test run. The opt-in PostgreSQL test requires `RUN_DB_TESTS=1`
and a running local database.

`python-dotenv` is an explicit dependency for utility configuration;
`pydantic-settings`, `psycopg`, and `httpx` remain for Python settings, database,
and provider-client utilities respectively.

## Run the SvelteKit application

From the project root, install and run the frontend using Node.js compatible with
`frontend/package.json`:

```powershell
npm --prefix frontend install
npm --prefix frontend run dev
```

For a production build and Node server:

```powershell
npm --prefix frontend run build
npm --prefix frontend start
```

There is no Python HTTP startup command. API contracts, validation, privacy,
request IDs, source errors, and HTTP safety preflight are tested in
`frontend/tests/api.test.ts`; SvelteKit UI/SSR smoke coverage replaces the legacy
FastAPI homepage/static-file tests. Python tests retain non-HTTP safety policy,
preflight, prompt-injection, retrieval, and answer-validation coverage.
