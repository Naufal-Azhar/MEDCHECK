"""Checkpointed corpus-size experiment; --live permits paid embedding/generation."""

import argparse
import hashlib
import json
import sys
from dataclasses import asdict
from pathlib import Path
from time import perf_counter

import psycopg

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.embeddings.model import MODEL_NAME, EMBEDDING_DIMENSION, QUERY_INSTRUCTION, encode_texts
from app.ingestion.medlineplus import database_url
from app.ingestion.chunking import chunk_text
from app.ingestion.topic_xml import parse_snapshot, balanced_order
from app.llm.config import load_settings
from app.rag.answer import generate_answer, SYSTEM_PROMPT
from app.rag.context import build_context
from app.retrieval.service import retrieve_chunks
from app.safety.policy import requires_refusal

WORK = ROOT / "data/processed/corpus-experiment"


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data, indent=2, ensure_ascii=True), encoding="utf-8")
    temp.replace(path)


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def concepts_match(text, groups):
    text = text.casefold()
    return any(all(word.casefold() in text for word in group) for group in groups)


def evaluate(connection, cases, vectors, settings, cache):
    results = []
    for case in cases:
        started = perf_counter()
        hits = [] if requires_refusal(case["question"]) else retrieve_chunks(connection, vectors[case["id"]], 5)
        elapsed = (perf_counter() - started) * 1000
        context = build_context(case["question"], hits)
        key = fingerprint([settings.model, SYSTEM_PROMPT, asdict(context)])
        cached = key in cache
        if cached:
            answer = cache[key]
        else:
            answer = asdict(generate_answer(context, settings))
            if answer["status"] == "provider_error" or (answer.get("usage") and not answer["usage"].get("usage_complete", True)):
                raise RuntimeError("Provider failure: experiment stopped, no automatic retry")
            cache[key] = answer
            write(WORK / "answers.json", cache)
        target = "https://medlineplus.gov/" + case["topic"] + ".html" if case.get("topic") else None
        rank = next((i for i, hit in enumerate(hits, 1) if hit.source_url == target), None)
        net = False
        if target:
            net = (answer["status"] == "answered" and any(s["source_url"] == target for s in answer["sources"])
                   and concepts_match(answer["answer"], case["concepts"])
                   and concepts_match(" ".join(s["quote"] for s in answer["sources"]), case["concepts"]))
        row = {"id": case["id"], "question": case["question"], "target": target, "rank": rank,
               "retrieval_ms": elapsed, "net_proxy_pass": net,
               "boundary_pass": answer["status"] == case.get("expected") if not target else None,
               "evidence_concepts": concepts_match(" ".join(h.content for h in hits), case.get("concepts", [])),
               "evidence": [asdict(h) for h in hits], "answer": answer, "cached": cached}
        results.append(row)
        write(WORK / "inflight-evaluation.json", results)
        print(f"  {case['id']}: rank={rank} status={answer['status']} net={net} cached={cached}", flush=True)
    educational = [r for r in results if r["target"]]
    metrics = {"net_count": sum(r["net_proxy_pass"] for r in educational),
               "educational_count": len(educational),
               "hit1_count": sum(r["rank"] == 1 for r in educational),
               "hit5_count": sum(r["rank"] is not None for r in educational),
               "mrr5": sum(1/r["rank"] if r["rank"] else 0 for r in educational) / len(educational),
               "boundary_pass": sum(r["boundary_pass"] is True for r in results),
               "boundary_count": len(results)-len(educational)}
    return {"metrics": metrics, "results": results}


def add_document(connection, record, source_id):
    chunks = chunk_text(record["content"])
    key = fingerprint([MODEL_NAME, EMBEDDING_DIMENSION, record["url"], [c.content for c in chunks]])
    path = WORK / "embeddings" / (key + ".json")
    if path.exists():
        vectors = json.loads(path.read_text())["vectors"]
    else:
        vectors, tokens = encode_texts([c.content for c in chunks])
        write(path, {"model": MODEL_NAME, "url": record["url"], "vectors": vectors, "prompt_tokens": tokens})
    metadata = {**record, "snapshot": "2026-10-08", "language": "English", "curation": "automated_topic_rules_v1"}
    row = connection.execute("""INSERT INTO documents (source_id,title,source,source_url,external_id,metadata)
        VALUES (%s,%s,'MedlinePlus',%s,%s,%s::jsonb) RETURNING id""",
        (source_id, record["title"], record["url"], record["url"], json.dumps(metadata))).fetchone()
    with connection.cursor() as cursor:
        cursor.executemany("""INSERT INTO document_chunks
            (document_id,chunk_index,content,embedding,embedding_model,metadata)
            VALUES (%s,%s,%s,%s::vector,%s,%s::jsonb)""",
            [(row[0], c.chunk_index, c.content, str(v), MODEL_NAME, json.dumps(c.metadata))
             for c, v in zip(chunks, vectors, strict=True)])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    records, inventory = parse_snapshot(ROOT / "data/raw/mplus_topics_2026-10-08.xml")
    write(WORK / "inventory.json", inventory)
    print("INVENTORY", inventory["languages"], "eligible", len(records), flush=True)
    if not args.live:
        return 0
    if (WORK / "completed.json").exists():
        print("Completed checkpoint exists; refusing to silently rerun experiment.")
        return 0
    settings = load_settings()
    cases = json.loads((ROOT / "data/evaluation/health_questions.json").read_text())
    dev = [c for c in cases if c["split"] == "development"]
    holdout = [c for c in cases if c["split"] == "holdout"]
    vector_path = WORK / "queries.json"
    if vector_path.exists():
        vectors = json.loads(vector_path.read_text())["vectors"]
    else:
        active = [c for c in cases if not requires_refusal(c["question"])]
        values, tokens = encode_texts([QUERY_INSTRUCTION+c["question"] for c in active])
        vectors = {c["id"]: v for c, v in zip(active, values, strict=True)}
        write(vector_path, {"model": MODEL_NAME, "vectors": vectors, "prompt_tokens": tokens})
    cache = json.loads((WORK / "answers.json").read_text()) if (WORK / "answers.json").exists() else {}
    report_path = WORK / "progress.json"
    report = json.loads(report_path.read_text()) if report_path.exists() else {"stages": []}
    with psycopg.connect(database_url(), connect_timeout=10, autocommit=True) as connection:
        urls = {r[0] for r in connection.execute("SELECT source_url FROM documents").fetchall()}
        source_id = connection.execute("SELECT id FROM sources WHERE name='MedlinePlus'").fetchone()[0]
        if not report["stages"]:
            baseline = evaluate(connection, dev, vectors, settings, cache)
            baseline["documents"] = len(urls)
            baseline["holdout"] = evaluate(connection, holdout, vectors, settings, cache)
            report["stages"].append(baseline)
            report["accepted_documents"] = len(urls)
            write(report_path, report)
        if len(urls) != report["accepted_documents"]:
            raise RuntimeError("Corpus/checkpoint mismatch; manual inspection needed")
        pending = [r for r in balanced_order(records) if r["url"] not in urls]
        best = next(s for s in reversed(report["stages"]) if s["documents"] == report["accepted_documents"])
        ceiling = min(5000, len(urls)+len(pending))
        stop = "source_exhausted"
        for target in sorted(set([100, 300, 600, ceiling])):
            if target <= len(urls) or target > ceiling:
                continue
            additions = pending[:target-len(urls)]
            print(f"STAGE {len(urls)} -> {target}", flush=True)
            with connection.transaction() as tx:
                for n, record in enumerate(additions, 1):
                    add_document(connection, record, source_id)
                    print(f"  ingested {n}/{len(additions)} {record['title']}", flush=True)
                stage = evaluate(connection, dev, vectors, settings, cache)
                stage["documents"] = target
                prev, now = best["metrics"], stage["metrics"]
                improved = now["net_count"] > prev["net_count"] and now["boundary_pass"] >= prev["boundary_pass"]
                stage["accepted"] = improved
                report["stages"].append(stage)
                if not improved:
                    stop = "no_net_gain_or_regression"
                    # Intentional rollback, preserving the best committed corpus.
                    raise psycopg.Rollback(tx)
            if not stage["accepted"]:
                write(report_path, report)
                break
            urls.update(r["url"] for r in additions)
            pending = pending[len(additions):]
            best = stage
            report["accepted_documents"] = len(urls)
            write(report_path, report)
        report["stop_reason"] = stop
        report["final_holdout"] = evaluate(connection, holdout, vectors, settings, cache)
        report["final_counts"] = dict(zip(["documents", "chunks"], connection.execute(
            "SELECT (SELECT count(*) FROM documents), (SELECT count(*) FROM document_chunks)").fetchone()))
        write(WORK / "completed.json", report)
        print("COMPLETED", report["stop_reason"], report["final_counts"], flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"BLOCKER {type(exc).__name__}: experiment stopped; active transaction rolled back. Inspect checkpoints.", flush=True)
        raise SystemExit(1)
