# Phase 10 preparation — no live inference yet

## Current selection (2026-10-08; supersedes earlier candidate notes below)

User selected `Qwen/Qwen3-4B-Instruct-2507`: non-gated, Apache 2.0,
non-thinking Instruct variant. Root `.env`, `.env.example`, and client allowlist
now select ONLY this model. Earlier Qwen models and gated Llama are disabled.
The existing API key, 512-token output cap, and 60-second timeout are unchanged.
This switch does not download weights, install dependencies, change BGE embeddings,
or re-embed the database. No automatic retries or model fallback are introduced.

Last checked price: $0.40/M input tokens and $0.80/M output tokens, excluding
cached-input discounts and account-specific terms. Example: 2000 input + 500
output = $0.0012/request. This is an estimate, not a measured account charge.

Source: https://featherless.ai/models/Qwen/Qwen3-4B-Instruct-2507

Live generation and claim-review smoke tests have succeeded with this model;
minimum safety limitations remain documented in `docs/safety-minimum.md`.
Historical tests below refer to earlier models and do not change the active selection.

## Historical setup and pricing notes (not current configuration)

Fill `FEATHERLESS_API_KEY` in the root `.env` (ignored by Git). Do not paste keys
into chat, commits, logs, or screenshots. User approved the low-cost technical test
model `Qwen/Qwen2.5-0.5B-Instruct`. No model is downloaded for Featherless;
the local BGE embedding model is unchanged.

## Candidate and pricing comparison

Checked official model pages and pricing on 2026-10-07. USD per million tokens:

| Candidate | Input | Output | Purpose |
| --- | ---: | ---: | --- |
| Qwen/Qwen2.5-0.5B-Instruct | 0.04 | 0.08 | Approved technical smoke-test model |
| meta-llama/Llama-3.2-3B-Instruct | 0.0509 | 0.335 | Suggested small English testing baseline |
| meta-llama/Llama-3.1-8B-Instruct | 0.2 | 0.32 | Optional comparison if baseline fails evaluation |

Illustration only: 2000 input + 500 output tokens costs approximately $0.0002693
for 3B or $0.00056 for 8B, excluding any plan minimums/taxes. Actual cost depends
on measured usage, plan, and current rates; no billed requests have been made.
Small does not guarantee lower output pricing or safe/grounded healthcare answers.
Both require citation, abstention, clarity, and safety testing before acceptance.

Official pricing currently specifies Developer/API credits (from $50/month);
the $25 Chat plan explicitly excludes app/API traffic and benchmarking. Sponsor
credits may have different terms: verify in your account rather than buying a
plan solely from these notes.

For the approved Qwen model, 2000 input + 500 output tokens is approximately
$0.00012/request or $0.012/100 requests. This is not a guaranteed account charge.

Sources:
- https://featherless.ai/models/Qwen/Qwen2.5-0.5B-Instruct
- https://featherless.ai/models/meta-llama/Llama-3.2-3B-Instruct
- https://featherless.ai/models/meta-llama/Llama-3.1-8B-Instruct
- https://featherless.ai/pricing
- https://featherless.ai/docs/quickstart-guide

## Local check (no network)

```powershell
.\.venv\Scripts\python.exe scripts/check_featherless_config.py
```

An empty key or unselected model is expected to fail this check. Passing it only
validates local configuration, NOT key validity, credits, API availability, or model
access. Limits: 512 output tokens and 60-second HTTP timeout; these are passed
by the client, not enforced as an account-wide spending limit. HTTP timeouts are
not a guarantee that a provider did not process/bill the request.

Next step after key/model setup: explicit small live test, then grounded prompt,
response parsing, citation validation, and integration. Phase 10 remains incomplete.

## Placeholder and offline-first testing

Edit the existing root `.env`:

```dotenv
FEATHERLESS_API_KEY=
FEATHERLESS_BASE_URL=https://api.featherless.ai/v1
FEATHERLESS_MODEL=Qwen/Qwen3-4B-Instruct-2507
FEATHERLESS_MAX_TOKENS=512
FEATHERLESS_TIMEOUT_SECONDS=60
```

Paste the key immediately after `FEATHERLESS_API_KEY=`; keep it local only.

```powershell
# No request, no key needed:
.\.venv\Scripts\python.exe scripts/test_featherless_connection.py
# Later, explicitly permit ONE potentially billed synthetic request:
.\.venv\Scripts\python.exe scripts/test_featherless_connection.py --live
```

The smoke test caps output at 32 tokens, does not include medical/user data,
does not retry, and does not print raw responses. The adapter uses the existing
httpx installation (now declared as a direct dependency), refuses redirects and
unapproved models, and returns token usage. Mock tests make no external requests.
Filling the key alone does not trigger a request. No live request has been run yet.
This is transport preparation, NOT finished grounded answer generation or safety validation.

To inspect an acknowledgement mismatch, opt in for this fixed synthetic prompt:

```powershell
.\.venv\Scripts\python.exe scripts/test_featherless_connection.py --live --show-response
```

This makes a NEW potentially billed request; it cannot recover a previous response.
Content is JSON-escaped for terminal safety and the key is redacted defensively.
Without `--show-response` content stays hidden. `Expected acknowledgement` uses
exact equality with `OK` after whitespace trimming, so punctuation or different
capitalization yields False even when the API request succeeded. Do not relax
this check to claim instruction-following success. This test does not establish
healthcare grounding or citation correctness.
