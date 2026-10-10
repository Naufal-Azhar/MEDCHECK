"""Inspect the evidence context that will later be sent to Featherless."""

import argparse
import os
import sys
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ["HF_HOME"] = str(ROOT / ".cache/huggingface")
os.environ["HF_HUB_CACHE"] = str(ROOT / ".cache/huggingface/hub")
os.environ["HF_HUB_OFFLINE"] = "1"

from app.ingestion.medlineplus import database_url
from app.rag.pipeline import retrieve_context


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", help="English general-health question")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()
    try:
        with psycopg.connect(database_url(), connect_timeout=10) as connection:
            result, context = retrieve_context(connection, args.question, args.top_k)
        print(f"Request ID: {result.request_id}")
        print(f"Evidence items: {len(context.evidence)}")
        print(f"Insufficient evidence: {context.insufficient_evidence}")
        if context.insufficiency_reason:
            print(f"Reason: {context.insufficiency_reason}")
        print("\n" + context.prompt_context)
        return 0
    except (ValueError, RuntimeError) as exc:
        print(f"Context construction failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
