"""Developer-only RAG test. Dry run by default; no autonomous medical advice."""

import argparse
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ["HF_HOME"] = str(ROOT / ".cache/huggingface")
os.environ["HF_HUB_CACHE"] = str(ROOT / ".cache/huggingface/hub")
os.environ["HF_HUB_OFFLINE"] = "1"
load_dotenv(ROOT / ".env", override=False)

from app.llm.config import ConfigurationError, load_settings
from app.ingestion.medlineplus import database_url
from app.rag.answer import generate_answer
from app.rag.answer import preflight_answer
from app.safety.policy import requires_refusal
from app.rag.pipeline import retrieve_context
from app.retrieval.service import validate_request


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", help="English public-information question; never private patient data")
    parser.add_argument("--live", action="store_true", help="Permit generation + claim review (at most TWO billed requests)")
    args = parser.parse_args()
    try:
        validate_request(args.question, 5)
        if not args.live:
            print("Dry run: no database, model, or API call. --live permits at most two calls: generation and claim review.")
            return 0
        preflight = preflight_answer(args.question)
        if preflight:
            print(json.dumps(asdict(preflight), indent=2))
            return 0
        settings = load_settings()
        with psycopg.connect(database_url(), connect_timeout=10) as connection:
            retrieval, context = retrieve_context(connection, args.question)
        result = generate_answer(context, settings)
        print(json.dumps({"request_id": retrieval.request_id, **asdict(result)}, indent=2, ensure_ascii=True))
        return 1 if result.status in {"provider_error", "invalid_response"} else 0
    except ConfigurationError as exc:
        print(str(exc), file=sys.stderr)
    except Exception as exc:
        print(f"RAG failed ({type(exc).__name__}); no answer displayed.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
