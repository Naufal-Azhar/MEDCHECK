"""Search English MedlinePlus evidence, without calling an LLM."""

import argparse
import json
import logging
import os
import sys
from dataclasses import asdict
from pathlib import Path

import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

# This command only uses the model already downloaded into the project.
os.environ["HF_HOME"] = str(ROOT / ".cache/huggingface")
os.environ["HF_HUB_CACHE"] = str(ROOT / ".cache/huggingface/hub")
os.environ["HF_HUB_OFFLINE"] = "1"
load_dotenv(ROOT / ".env", override=False)

from app.ingestion.medlineplus import database_url
from app.retrieval.service import search, validate_request


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", help="English general-health question (no private health data)")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        validate_request(args.question, args.top_k)
        with psycopg.connect(database_url(), connect_timeout=10) as connection:
            result = search(connection, args.question, args.top_k)
        print(json.dumps(asdict(result), indent=2, ensure_ascii=True))
        return 0
    except ValueError as exc:
        print(f"Invalid input: {exc}", file=sys.stderr)
    except Exception as exc:
        print(
            f"Search failed ({type(exc).__name__}). Check Docker, migrations, vectors, "
            "and the project-local model cache. No answer generated.", file=sys.stderr,
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
