"""Offline configuration check. Does not validate account access or call Featherless."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.llm.config import ConfigurationError, load_settings


def main() -> int:
    try:
        settings = load_settings()
    except ConfigurationError as exc:
        print(f"Not configured: {exc}")
        return 1
    print("Local configuration valid. API key present (not displayed).")
    print(f"Model: {settings.model}")
    print(f"Output limit: {settings.max_tokens} tokens")
    print("No API call made. Key validity, model access, and billing remain unverified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
