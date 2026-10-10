"""Store the validated local embedding artifact in pgvector."""

import json
import sys
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.embeddings.storage import store_records
from app.ingestion.medlineplus import database_url


def main() -> None:
    with (ROOT / "data/processed/embeddings.jsonl").open(encoding="utf-8") as artifact:
        records = [json.loads(line) for line in artifact if line.strip()]
    with psycopg.connect(database_url()) as connection:
        count = store_records(connection, records)
    print(f"Vectors stored: {count}")


if __name__ == "__main__":
    main()
