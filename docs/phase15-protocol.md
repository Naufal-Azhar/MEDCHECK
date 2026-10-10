# Phase 15 — frozen evaluation protocol

24 fixed English synthetic questions: 14 educational (definitions, terminology,
medication information and context), 10 boundary/insufficiency cases. See
`scripts/evaluate_phase15.py`. Some are regressions previously seen, not a new
unbiased holdout. This is a final-MVP audit, not a clinical accuracy benchmark.

Run one pass through real HTTP → database → Featherless. No prompt or corpus
changes during evaluation, no repeated sampling to select the best outcome.
Reuse the existing E2E runner, which starts/stops its own localhost Uvicorn server.
Check expected status, real citation presence, ID/header consistency, no-store,
local refusals with zero model calls, and response timing. Review all answered
texts manually against their supplied quotes for relevance and support, allowing
related-source citations rather than requiring one target URL. Separately verify
quotes against database chunk IDs. Quote membership alone does not prove truth.

Observe unresolved issues and prioritize changes BEFORE public deployment; do not
automatically introduce new technologies, expand the corpus, or start Phase 16.
LLM usage is reported by the app; embedding usage is extracted from operational
logs for cost estimates. Provider tariffs are last checked, not a billing invoice.
Network failures stop the run and must be reported as incomplete.

Manual review here is an AI-assisted engineering review, not clinician assessment.
Frontend visual/keyboard/mobile interaction, public deployment load testing,
clinical correctness and unseen adversarial prompts are not certified by this run.
