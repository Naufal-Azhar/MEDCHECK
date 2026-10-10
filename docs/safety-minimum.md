# Phase 10 minimum safety remediation (2026-10-08)

User approved pulling minimum safety corrections forward. Deferred initial-help
and nearby-facility ideas are recorded in `docs/backlog.md`, NOT implemented.

## Changes

- Local conservative English rules reject personal medical interpretation,
  diagnosis/dosage requests and explicit immediate-distress wording before query
  embedding, retrieval, or generation in `retrieve_context`. The answer function
  and direct parser also enforce this check. The CLI checks before opening the DB
  or loading the API key. Matched requests require no Featherless call.
- Unknown phrasing can evade regex rules; general educational requests with personal
  wording may be overblocked. This is NOT a medical triage classifier or full safety layer.
- Citation quotes must still match source text exactly. A new conservative lexical
  check withholds explanations introducing substantive terms absent from their
  quotes. This catches the observed frequent-urination failure and insulin claims
  supported only by a glucose-definition quote. It can reject valid paraphrases;
  shared vocabulary does NOT prove correct meaning, polarity, or causal support.
- A structurally/lexically accepted candidate gets one additional Qwen claim review
  against only the quoted excerpts. Unsupported/malformed/unavailable review means
  no candidate is displayed. No automatic repair or retry. Uncertainty text is now
  application-owned, avoiding an unchecked channel for extra factual claims.
- Max two model calls for an educational answer (generation + review); review output
  capped at 64 tokens. Local refusals and empty context use zero; a model abstention
  uses one. Usage combines known calls; `usage_complete=false` flags unavailable
  review usage rather than assuming it was free. No new dependency or global install.

## Actual validation and tradeoffs

During testing, the model reviewer accepted the old diabetes answer even though its
quote lacked the insulin claim. This demonstrated correlated model errors: the
reviewer is NOT independent medical verification. The lexical gate and narrower
prompt were then added; never treat a supported verdict as clinical certification.

Final diabetes probe returned a narrow glucose-definition sentence, supported by
the displayed quote, and passed both gates. The final fixed boundary run passed all
six expected cases: empty context, outside topic, unsupported dated statistic,
personal diagnosis, personal dosage, and immediate distress. Three personal/urgent
cases were refused locally with no query embedding or provider usage. Status checks
are smoke tests, not a percentage claim of product safety.

116 automated tests passed including real PostgreSQL tests, varied phrasing,
general-information false positives, original contradiction regression, review
rejection, review outage and no-network preflight behavior. An initial test wrongly
blocked the educational dosage-definition question; the rule was narrowed and the
test passed. No failed test was ignored.

Live testing in this remediation used eight calls total:
- First boundary run: 2266 input / 77 output tokens (2 calls).
- First diabetes generation+review: 1401 / 116 (2 calls; found review weakness).
- Final diabetes generation+review: 1437 / 100 (2 calls).
- Final boundary run: 2364 / 77 (2 calls).
Total 7468 input / 370 output; estimated $0.0032832 at $0.40/M input + $0.80/M output.
Not a dashboard balance/invoice. Final boundary report is local/ignored:
`data/processed/rag-boundaries-20261007T172514210136Z.json`.
Machine UTC date is October 7 while session date is October 8; no medical-source
freshness inference is made from these filenames.

## Remaining limitations

Regex coverage, prompt injection, claim-level semantic support, regional emergency
guidance, multilingual behavior, and clinical suitability are not comprehensively
evaluated. Exact quotes can omit caveats in earlier word-based chunks. The lexical
gate sacrifices paraphrase quality for conservatism. Do not expose this as a public
medical advisor. Phase 14 safety and Phase 15 evaluation still remain. No first aid,
location collection, map integration or facility recommendation was added.
