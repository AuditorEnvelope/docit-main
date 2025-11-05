"""Utility script to debug GitHub App JWT generation.

Run this module directly (``python -m utilities.jwt_debugger``) to verify
that the READER/WRITER private keys in the current environment can be
parsed and used to mint a JWT. This isolates PEM formatting issues without
running the full event consumer pipeline.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import jwt

from utilities.github_dual_app_helper import GitHubDualAppHelper

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency
    load_dotenv = None


def _generate_jwt(app_id: str, private_key: str) -> str:
    """Mint a short-lived JWT for the given GitHub App."""
    now = datetime.utcnow()
    payload = {
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=10)).timestamp()),
        "iss": app_id,
    }
    return jwt.encode(payload, private_key, algorithm="RS256")


def _dump_helper_state(helper: GitHubDualAppHelper) -> None:
    print("\n=== Dual App Helper State ===")
    print(f"Dual app mode: {helper.dual_app_mode}")
    print(f"Reader key loaded: {helper.reader_private_key is not None}")
    print(f"Writer key loaded: {helper.writer_private_key is not None}")


def _test_key(label: str, app_id_var: str, key_var: str) -> None:
    app_id = os.getenv(app_id_var)
    print(f"\n=== Testing {label.upper()} credentials ===")
    print(f"{app_id_var}: {app_id}")

    if not app_id:
        print(f"❌ Missing {app_id_var} in environment")
        return

    helper = GitHubDualAppHelper()
    pem = helper.reader_private_key if label == "reader" else helper.writer_private_key

    if not pem:
        print("❌ Helper failed to decode PEM")
        return

    print(f"PEM length: {len(pem)}")
    preview = pem.splitlines()[0] if pem else ""
    print(f"PEM header: {preview}")

    try:
        token = _generate_jwt(app_id, pem)
        print("✅ JWT generated successfully")
        print(f"JWT preview: {token[:60]}...")
    except Exception as exc:
        print("❌ Failed to generate JWT:", exc)


def main(argv: list[str]) -> int:
    # Ensure .env is loaded so variables are present when the helper initializes
    project_root = Path(__file__).resolve().parents[2]
    env_path = project_root / ".env"

    if load_dotenv:
        if env_path.exists():
            load_dotenv(env_path)
            print(f"Loaded environment from {env_path}")
        else:
            print(f"⚠️  No .env file found at {env_path}")
    else:
        print("⚠️  python-dotenv not installed; skipping .env auto-load")

    helper = GitHubDualAppHelper()
    _dump_helper_state(helper)

    _test_key("reader", "READER_APP_ID", "READER_PRIVATE_KEY")
    _test_key("writer", "WRITER_APP_ID", "WRITER_PRIVATE_KEY")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
