"""Parse official MedlinePlus Health Topics snapshots (no external link ingestion)."""

import hashlib
import re
import xml.etree.ElementTree as ET
from collections import defaultdict, deque
from html.parser import HTMLParser
from urllib.parse import urlsplit


class SummaryText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in {"p", "br", "li", "h1", "h2", "h3", "tr", "td", "th", "div"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"p", "li", "h1", "h2", "h3", "tr", "td", "th", "div"}:
            self.parts.append("\n")

    def handle_data(self, data):
        self.parts.append(data)


def parse_snapshot(path):
    root = ET.parse(path).getroot()
    if root.tag != "health-topics":
        raise ValueError("Unexpected MedlinePlus snapshot format")
    records, seen, rejected = [], set(), []
    counts = defaultdict(int)
    for topic in root.findall("health-topic"):
        counts[topic.get("language", "unknown")] += 1
        if topic.get("language") != "English":
            continue
        url, title = topic.get("url", ""), topic.get("title", "").strip()
        parsed = urlsplit(url)
        html = topic.findtext("full-summary", "")
        # Tables flattened to text can lose medical threshold relationships.
        if (parsed.scheme != "https" or parsed.netloc != "medlineplus.gov"
                or parsed.query or parsed.fragment or not title or not topic.get("id")
                or not parsed.path.endswith(".html") or re.search(r"<table\b", html, re.I)):
            rejected.append({"url": url, "reason": "metadata_or_table"})
            continue
        parser = SummaryText()
        parser.feed(html)
        content = re.sub(r"\s+", " ", "".join(parser.parts)).strip()
        digest = hashlib.sha256(content.encode()).hexdigest()
        if not content or len(content.split()) < 30 or url in seen or digest in seen:
            rejected.append({"url": url, "reason": "short_or_duplicate"})
            continue
        seen.update((url, digest))
        records.append({"url": url, "title": title, "content": content,
                        "external_id": topic.get("id"),
                        "groups": [g.text for g in topic.findall("group") if g.text],
                        "date_created": topic.get("date-created"), "content_sha256": digest})
    return records, {"languages": dict(counts), "eligible": len(records), "rejected": rejected,
                     "snapshot_generated": root.get("date-generated")}


def balanced_order(records):
    """Deterministic group-balanced order, independent of evaluation questions."""
    buckets = defaultdict(list)
    for record in records:
        group = sorted(record["groups"])[0] if record["groups"] else "Ungrouped"
        buckets[group].append(record)
    queues = [deque(sorted(buckets[g], key=lambda r: r["title"].casefold())) for g in sorted(buckets)]
    result = []
    while any(queues):
        for queue in queues:
            if queue:
                result.append(queue.popleft())
    return result
