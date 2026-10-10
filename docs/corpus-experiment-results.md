# Corpus expansion result — stopped at NET proxy plateau

Official snapshot 2026-10-08: 1017 English and 1016 Spanish topics; automated
metadata/length/table/deduplication rules accepted 1001 English candidates.
5000 unique English Health Topics are not available from this snapshot. Chunks,
Spanish translations and external links are not counted as extra English documents.
This curation is automated, not medical editorial review.

## Measured results

Frozen dataset: 24 development (18 educational + 6 boundary) and 6 holdout questions.
No model, prompt, chunking, or validator tuning during the experiment.

| Metric | Baseline 24 documents | Candidate 100 documents |
| --- | ---: | ---: |
| Expected topic rank 1 | 4/18 | 6/18 |
| Expected topic top 5 | 6/18 | 8/18 |
| MRR@5 | 0.2685 | 0.3796 |
| NET proxy: answered + expected URL + concepts in answer/quote | 1/18 | 1/18 |
| Educational questions with status answered | 2/18 | 2/18 |
| invalid_response across 24 questions | 10 | 14 |
| Expected boundary statuses | 5/6 | 6/6 |

16/24 displayed answers and 8/24 retrieval sets were unchanged. Many identical
answers are fallbacks, not useful explanations. Stop rule fired on unchanged NET
proxy, NOT all retrieval being identical. No 300/600/... stage was run.
The 76-document candidate batch was rolled back; original documents preserved.
**Active database remains 24 documents / 106 chunks/vectors.** Snapshot, candidate
embeddings and evaluation results remain on D for audit/reuse without repeat calls.

## Interpretation and limitations

This is a local plateau for a fixed small evaluation, not proof MedlinePlus is
exhausted or that more data cannot help. Topic retrieval actually improved.
Exact target-URL scoring undercounts valid alternative sources. Manual inspection:
the baseline A1C definition was supported by a quote in Diabetes Type 2; at 100
documents the sleep-apnea definition was supported by the Adenoids summary. Both
received zero proxy credit because their designated target URLs were absent.
Diabetes answers at both sizes followed their displayed definition quotes.
These observations are not clinician-adjudicated medical accuracy scores.

The most visible bottleneck is output validation: many generated answers introduce
terms absent from their quotes, or fail exact quote matching. The conservative
lexical gate can reject valid paraphrases. More documents alone do not resolve this.
The ambiguous baseline `Is it safe?` produced invalid_response, not the expected
insufficient_evidence status; the 100-document candidate abstained correctly.

Holdout on baseline and retained final baseline: 0/4 expected educational topic
hits/NET proxy, all four abstained; 2/2 boundary cases passed. Final holdout reused
identical cached contexts/responses. No generalization improvement claimed.

## Usage

- Embedding: 33806 input tokens, 77 requests (query batch + 76 documents).
- Chat generation/review: 59944 input, 2957 output tokens, 46 calls.
- Estimated cost: **$0.02701932** at $0.02/M embedding input and $0.40/M chat input,
  $0.80/M chat output. Actual dashboard balance was not accessed.

Artifacts: `data/processed/corpus-experiment/completed.json`, `answers.json`,
`inventory.json`, `queries.json` and `embeddings/`; official XML in `data/raw/`.
Question set: `data/evaluation/health_questions.json`. Completed checkpoint blocks
accidental repetition. Do not erase checkpoints and repeatedly tune against this
same set while describing it as unbiased evaluation.

## Next source investigation

Per user instruction, stop MedlinePlus expansion and investigate another source.
DailyMed official v2 REST API provides SPL label documents, identifiers and version
history: https://dailymed.nlm.nih.gov/dailymed/app-support-web-services.cfm
It is a useful candidate for medication-label explanation, not a solution to the
current validator/answer bottleneck. No secondary-source records were ingested.

Before more ingestion: fix evaluation to accept valid alternative evidence, assess
false rejection without weakening safety, and define medication-label questions
and section-aware extraction for DailyMed. No model fine-tuning or zero-error claim.
