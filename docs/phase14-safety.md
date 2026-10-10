# Phase 14 — safety layer

Scope: English informational MVP; no first-aid instructions, facility search,
geolocation, corpus growth, new model or training. Deferred ideas remain deferred.

## Routing and HTTP contract

`screen_question` returns a reason-coded local decision before database access,
credentials, retrieval or provider calls in `/chat` and `/search`.
Direct retrieval/pipeline/generation/parser entry points also apply the gate.

| status | safety_reason | Behaviour |
| --- | --- | --- |
| safety_refusal | urgent | Fixed emergency-services-now guidance, no triage/diagnosis |
| safety_refusal | personal_medical_decision | No personal diagnosis, test interpretation, dosage or prescribing |
| safety_refusal | instruction_override | No bypassing instructions, secret disclosure or fabricated citations |
| privacy_refusal | personal_identifiers | Ask user to remove identifiers/records |
| clarification_needed | ambiguous | Ask for the topic, not private symptoms |

Known urgent wording has priority over other refusal reasons. Responses are
application-owned and no sources are invented. UI uses fixed messages for these
statuses and gives urgent referral prominence. `/search` returns empty hits and
does not echo blocked question text. Model-generated safety refusals still use
the fixed generic fallback. Recognized requests work even with DB/API key absent.

## Evidence/output checks

Known source instruction-override patterns are removed from returned search hits
and context. Sources remain data in a separate JSON user message, not system rules.
Personal diagnoses, numeric dosing commands and delayed-care wording are rejected
in both generated explanation and quoted text even if found in poisoned evidence.
Existing JSON structure, exact citation/quote, vocabulary gate and fail-closed
semantic reviewer remain active. No automatic retries or additional model calls.

## Privacy/error handling

- API validation errors no longer echo rejected input.
- Backend exception logging records class and request ID, not traceback/exception
  message that may contain a DSN, raw prompt or secret.
- Accept only UUID request IDs; otherwise generate one. No arbitrary header text
  is reused in responses/logs.
- `/chat` and `/search` responses use `Cache-Control: no-store`.
- Raw inference prompts/outputs are not persisted as conversations by the app.

## Limitations to evaluate in Phase 15

These are conservative deterministic English heuristics plus model review, NOT
an exhaustive medical triage system, PII detector, anonymizer or prompt-injection
proof. Unknown wording, multi-turn context, and non-English input may bypass rules.
Broad personal references can overblock educational requests. The vocabulary gate
can reject valid paraphrases, and model reviewers can share generator mistakes.
Quoted excerpts can miss caveats in original word-based chunks. Do not interpret
absence of a rule match or an `answered` status as verified medical accuracy.
No public deployment hardening/auth is claimed in this phase.

Tests: varied personal/urgent requests, privacy and instruction injection, positive
general-health questions, no DB/API calls for refusals, poisoned source/output,
non-leaking errors and UI status handling. Live checks are limited synthetic smoke
tests, not performance claims. See final execution results recorded below.

## Execution results

Local Python tests: 164 passed, one opt-in PostgreSQL test not runnable with the
current environment. The explicit RUN_DB_TESTS=1 attempt failed with a connection
timeout; `docker compose up -d postgres` then failed because Docker Desktop Linux
Engine named pipe was unavailable. This is an unresolved environment blocker,
not a passed database check. Frontend logic tests: 8 passed.

No live Featherless request, additional dependency, model change, or corpus change
was made for this phase. Local HTTP tests mock unavailable services deliberately
to verify refusal still works. Full end-to-end/database verification remains pending
until Docker Desktop is running; do not advance to Phase 15 automatically.

### Docker blocker resolved

At the user's request, Docker Desktop was launched using PowerShell from its
per-user installation under `AppData/Local/Programs/DockerDesktop`. Engine 29.8.2
responded and `docker compose up -d postgres` confirmed the existing container
running. Re-running with `RUN_DB_TESTS=1`: **165 passed**, no skipped tests; the
existing TestClient deprecation warning remains. No volumes were removed and no
live Featherless call was made. A fresh live end-to-end AI check is still distinct
from these automated/database tests.

## Mixed HTTP end-to-end verification and fixes

2026-10-09: `scripts/verify_phase14_e2e.py --live` starts a separate localhost
Uvicorn process using project Python, uses real PostgreSQL + Featherless, then
terminates only its own server. No mock inference. Fixed English synthetic cases
mix education, personal dose/diagnosis, immediate distress, privacy, injection,
ambiguity, unrelated requests and unavailable statistics. No multilingual scope
or additional corpus/source was introduced.

Initial run: 9/12 expected statuses. Issues and fixes:
- Polite `explain diabetes to me` was mistaken for a personal case: strip only
  conversational markers for the personal check, not the remainder of the request.
  Mixed text with symptoms/dosing continues to be blocked.
- Educational source `If you have diabetes ...` was mistaken for a diagnosis:
  permit this conditional phrase, still reject direct `You have ...`, numeric dose
  commands and delayed-care advice. This heuristic is narrow, not full grammar parsing.
- Unrelated topic / missing statistics got model safety_refusal: distinguish missing
  evidence vs unsafe personal decisions explicitly in the prompt. No status rewriting
  or validator bypass after generation.
- Polite explanations are reminded to use the existing short source-based mode.

Final repeat of ALL 12 cases: **12/12 expected HTTP statuses/reasons**, no backend
errors. Three educational answers had real citations; manual inspection found their
insulin/diabetes/dehydration definitions supported by the displayed quotes. Seven
locally screened requests made no LLM calls. One unrelated and one missing-statistic
case returned evidence insufficiency: three answered + seven local + two model abstentions.

Final report: `data/processed/phase14-e2e/20261009T081255877113Z.json`.
Earlier failure/retest reports and safe operational logs retained alongside it.
Assets served over real HTTP; frontend response contract tested against the final
report. Visual clicks/layout were NOT browser-automated; user testing remains useful.

Across initial/targeted/final runs: 19 chat generation/review calls with 18993 input
and 1039 output tokens; one separate synthetic diagnostic added 1416 input/218 output.
Runner logs record 364 embedding input tokens, plus one diagnostic embedding whose
usage was not recorded by the command. Estimated recorded cost about $0.00918 using
previously checked tariffs, excluding that diagnostic embedding and any unreported
provider charges. No account balance/invoice queried. No automatic retries or model
changes, no new dependencies. These are regression smoke tests, not an accuracy
percentage or proof all unsafe wording is caught. Phase 15 evaluation remains pending.
