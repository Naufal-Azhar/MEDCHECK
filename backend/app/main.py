"""ForgeHacks Healthcare Information Assistant API."""

import logging
from uuid import UUID, uuid4
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles

from app.api import router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

app = FastAPI(
    title="ForgeHacks Healthcare Information Assistant",
    version="0.1.0",
    description="Grounded healthcare information retrieval and explanation API.",
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    try:
        request.state.request_id = str(UUID(request.headers.get("X-Request-ID", "")))
    except ValueError:
        request.state.request_id = str(uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    if request.url.path in {"/chat", "/search"}:
        response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(RequestValidationError)
async def invalid_input(request: Request, exc: RequestValidationError):
    # Do not echo invalid user input / personal information in validation errors.
    return JSONResponse(status_code=422, content={
        "detail": "Invalid request. Supply a question of 1–2000 characters and top_k of 1–20.",
        "request_id": request.state.request_id,
    })


app.include_router(router)

# Serve only public frontend assets, never the repository root or .env.
FRONTEND = Path(__file__).resolve().parents[2] / "frontend" / "public"
app.mount("/assets", StaticFiles(directory=FRONTEND), name="frontend-assets")


@app.get("/", include_in_schema=False)
def frontend():
    return FileResponse(FRONTEND / "index.html", headers={"Cache-Control": "no-store"})
