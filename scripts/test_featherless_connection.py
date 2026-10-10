"""Dry run by default; --live explicitly permits one small billed API request."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.llm.config import ConfigurationError, load_settings
from app.llm.featherless import InferenceError, TEST_MODEL, complete


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Make ONE potentially billed request")
    parser.add_argument("--show-response", action="store_true",
                        help="Display escaped response to this fixed synthetic prompt (live only)")
    args = parser.parse_args()
    if not args.live:
        print(f"Dry run. Selected model: {TEST_MODEL}")
        print("No API call. Fill FEATHERLESS_API_KEY in D:\\project\\FORGE\\.env.")
        print("When ready, --live sends one synthetic prompt, at most 32 output tokens, no retries.")
        return 0
    try:
        settings = load_settings()
        result = complete(settings, [{"role": "user", "content": "Reply with exactly OK."}],
                          max_tokens=min(32, settings.max_tokens))
    except (ConfigurationError, InferenceError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"Request completed: {result.request_id}")
    print(f"Prompt tokens: {result.prompt_tokens}; output tokens: {result.completion_tokens}")
    print(f"Duration: {result.duration_ms:.2f} ms")
    # Explicit opt-in, fixed synthetic prompt only. Escape terminal control characters
    # and redact the key defensively; never print request headers or settings.
    if args.show_response:
        safe_content = result.content.replace(settings.api_key, "[REDACTED]")
        print("Synthetic response: " + json.dumps(safe_content, ensure_ascii=True))
    print(f"Expected acknowledgement: {result.content.strip() == 'OK'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
