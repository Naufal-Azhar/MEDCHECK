# Frozen corpus-expansion experiment

Objective: test whether adding authoritative topic summaries improves the existing
RAG pipeline. This is corpus/retrieval tuning, NOT fine-tuning model weights or a
clinical accuracy guarantee. User authorized running stages until no measurable gain.

## Before running

- Source: official `mplus_topics_2026-10-08.xml` from the compressed link on
  https://medlineplus.gov/xml.html. Snapshot reports 1017 English and 1016 Spanish
  topics. 5000 unique English health-topic documents cannot be obtained from it.
  Count documents separately from chunks. External links are NOT extra MedlinePlus
  documents and must not be counted as such.
- Existing 24 documents are retained without edits to avoid confounding data size
  with parser/chunking changes. New English summaries require official HTTPS URLs,
  IDs/titles, 30+ words, no tables, and URL/content deduplication. This is automated
  rule-based curation, not expert review. Old summaries may retain table artifacts.
- Addition order: deterministic round-robin official groups and alphabetical title
  within groups. Independent of evaluation labels; do not inject expected topics.
- Stages: baseline → 100 → 300 → 600 → all eligible (cap 5000). Stop at the FIRST
  unchanged or worse development result; no further source integration in this run.
- Freeze model, dimensions, query instruction, prompt, safety rules and chunking.
  Cache query vectors once; cache identical evidence/prompt calls across stages.
- 24 development questions plus 6 holdout questions, frozen in
  `data/evaluation/health_questions.json`. Holdout is run only on baseline and the
  selected final snapshot, not used to drive expansion.

## Metrics and stopping rule

For 18 educational development questions, report exact expected topic URL hit@1,
hit@5 and MRR@5. These are source-location proxies, not graded passage relevance.
Report reference concept matches in retrieved text and returned answer separately.
Do NOT interpret presence of words as entailment, medical accuracy or hallucination
absence. Reference concepts are lightweight manual expectations, not clinical gold.

Primary NET proxy: count of questions with ALL of: status answered, expected topic
URL cited, and at least one expected concept group present in BOTH the answer and
cited quotes. This is intentionally conservative and can reject valid alternate
sources/paraphrases. Boundary questions must return the predeclared abstention status.

Continue only if the primary count strictly improves AND boundary pass count does
not decrease. Equal count = stop even if retrieval improves. Lower count or safety
regression = stop. Keep newly ingested source records for audit but revert the
active candidate batch on no improvement or regression via transaction rollback. The best stage is
selected on development only; holdout then checks generalization without tuning.
Repeated/identical text alone is not a universal saturation proof; report unchanged
answers/evidence and reason for stopping on this fixed dataset only.

Checkpoint each document's embedding artifact under ignored `data/processed/`.
On external service failure stop immediately and retain the last committed corpus.
No silent retries or expensive model switch. Snapshots, usage and per-question
results are retained locally; publish summary and limitations in docs afterward.
