"""Ingest a small MedlinePlus dataset into PostgreSQL.

Run from the project root:
    python scripts/ingest_medlineplus.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.ingestion.medlineplus import (  # noqa: E402
    MEDLINEPLUS_SOURCE_URL,
    database_url,
    fetch_documents,
)


def main() -> int:
    documents = fetch_documents()
    inserted = 0
    updated = 0

    with psycopg.connect(database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO sources (name, base_url, authority_level, metadata)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (name) DO UPDATE SET
                    base_url = EXCLUDED.base_url,
                    authority_level = EXCLUDED.authority_level,
                    metadata = EXCLUDED.metadata,
                    updated_at = NOW()
                RETURNING id
                """,
                (
                    "MedlinePlus",
                    MEDLINEPLUS_SOURCE_URL,
                    "authoritative",
                    json.dumps({"provider": "U.S. National Library of Medicine"}),
                ),
            )
            source_id = cursor.fetchone()[0]

            for document in documents:
                cursor.execute(
                    """
                    INSERT INTO documents
                        (source_id, title, source, source_url, external_id, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (source, external_id) DO UPDATE SET
                        source_id = EXCLUDED.source_id,
                        title = EXCLUDED.title,
                        source_url = EXCLUDED.source_url,
                        metadata = EXCLUDED.metadata,
                        updated_at = NOW()
                    RETURNING (xmax = 0) AS inserted
                    """,
                    (
                        source_id,
                        document.title,
                        "MedlinePlus",
                        document.source_url,
                        document.external_id,
                        json.dumps(
                            {
                                **document.metadata,
                                "content": document.summary,
                            }
                        ),
                    ),
                )
                was_inserted = cursor.fetchone()[0]
                inserted += int(was_inserted)
                updated += int(not was_inserted)

    print(f"Source: MedlinePlus")
    print(f"Documents fetched: {len(documents)}")
    print(f"Documents inserted: {inserted}")
    print(f"Documents updated: {updated}")
    print("Documents failed: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
