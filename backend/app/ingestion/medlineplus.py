"""Small, idempotent MedlinePlus Web Service ingestion client."""

from __future__ import annotations

import html
import os
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass


MEDLINEPLUS_BASE_URL = "https://wsearch.nlm.nih.gov/ws/query"
MEDLINEPLUS_SOURCE_URL = "https://medlineplus.gov"
DEFAULT_TERMS = (
    "diabetes",
    "high blood pressure",
    "asthma",
    "cholesterol",
    "fever",
    "dehydration",
    "antibiotics",
    "medical tests",
)


@dataclass(frozen=True)
class MedlinePlusDocument:
    title: str
    source_url: str
    summary: str
    external_id: str
    metadata: dict[str, object]


def _clean_content(value: str) -> str:
    """Decode escaped markup returned by the service and remove HTML tags."""
    decoded = html.unescape(value)
    without_tags = re.sub(r"<[^>]+>", " ", decoded)
    return re.sub(r"\s+", " ", without_tags).strip()


def _fetch_xml(term: str, retmax: int, timeout: float) -> bytes:
    params = urllib.parse.urlencode(
        {
            "db": "healthTopics",
            "term": term,
            "retmax": retmax,
            "rettype": "brief",
            "tool": "forgehacks_health_assistant",
        }
    )
    request = urllib.request.Request(
        f"{MEDLINEPLUS_BASE_URL}?{params}",
        headers={"User-Agent": "ForgeHacksHealthcareAssistant/0.1"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def fetch_documents(
    terms: tuple[str, ...] = DEFAULT_TERMS,
    retmax: int = 3,
    timeout: float = 30.0,
) -> list[MedlinePlusDocument]:
    """Fetch and deduplicate a small set of public MedlinePlus health topics."""
    documents: dict[str, MedlinePlusDocument] = {}

    for term in terms:
        root = ET.fromstring(_fetch_xml(term, retmax, timeout))
        for document in root.findall("./list/document"):
            source_url = document.attrib.get("url", "").strip()
            fields = {
                node.attrib.get("name", ""): _clean_content("".join(node.itertext()))
                for node in document.findall("content")
            }
            title = fields.get("title", "").strip()
            summary = fields.get("fullSummary", "") or fields.get("FullSummary", "")
            if not source_url or not title or not summary:
                continue

            documents[source_url] = MedlinePlusDocument(
                title=title,
                source_url=source_url,
                summary=summary,
                external_id=source_url,
                metadata={
                    "retrieval_term": term,
                    "organization": fields.get("organizationName"),
                    "alt_titles": fields.get("altTitle"),
                    "groups": fields.get("groupName"),
                },
            )

    return list(documents.values())


def database_url() -> str:
    return os.getenv(
        "DATABASE_URL",
        "postgresql://forgehacks:forgehacks_dev@localhost:5433/forgehacks",
    ).replace("postgresql+psycopg://", "postgresql://", 1)
