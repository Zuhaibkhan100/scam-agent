#!/usr/bin/env python3
"""
Test the exact hackathon sample payload and validate the exact response format.

AI-only mode:
- By default, this script runs the FastAPI app in-process and forces:
  - LLM_PROVIDER=gemini
  - LLM_STRICT=true (no deterministic/mock fallbacks allowed)
  - CALLBACK_ENABLED=false (avoid sending real callbacks during tests)

If you pass --url, the script will send the payload over HTTP to that URL instead.
In that mode, AI-only behavior depends on the server's environment (set LLM_STRICT=true on the server).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

import requests
from dotenv import load_dotenv


PAYLOAD = {
    "sessionId": "1fc994e9-f4c5-47ee-8806-90aeb969928f",
    "message": {
        "sender": "scammer",
        "text": "Your bank account will be blocked today. Verify immediately.",
        "timestamp": 1769776085000,
    },
    "conversationHistory": [],
    "metadata": {
        "channel": "SMS",
        "language": "English",
        "locale": "IN",
    },
}


def _fail(msg: str, code: int = 1) -> None:
    print(f"FAIL: {msg}")
    raise SystemExit(code)


def _validate_response(data: Any) -> None:
    if not isinstance(data, dict):
        _fail("Response is not a JSON object.")

    keys = set(data.keys())
    if keys != {"status", "reply"}:
        _fail(f"Response keys must be exactly {{'status','reply'}}; got {sorted(keys)}")

    if data.get("status") != "success":
        _fail(f"status must be 'success'; got {data.get('status')!r}")

    reply = data.get("reply")
    if not isinstance(reply, str) or not reply.strip():
        _fail("reply must be a non-empty string.")


def _headers(api_key: str) -> dict[str, str]:
    return {"x-api-key": api_key, "Content-Type": "application/json"}


def _post_http(url: str, api_key: str) -> tuple[int, Any]:
    resp = requests.post(url, json=PAYLOAD, headers=_headers(api_key), timeout=30)
    try:
        data = resp.json()
    except Exception:
        data = resp.text
    return resp.status_code, data


def _post_inprocess(api_key: str) -> tuple[int, Any]:
    # Force AI-only behavior for this test run.
    os.environ["LLM_PROVIDER"] = "gemini"
    os.environ["LLM_STRICT"] = "true"
    os.environ.setdefault("LLM_MODEL_NAME", "gemini-flash-latest")
    os.environ.setdefault("LLM_REQUEST_TIMEOUT_SECONDS", "15")
    os.environ["CALLBACK_ENABLED"] = "false"

    from fastapi.testclient import TestClient  # noqa: WPS433 (local import)

    import app  # noqa: WPS433 (local import)

    client = TestClient(app.app, raise_server_exceptions=False)
    resp = client.post("/", json=PAYLOAD, headers=_headers(api_key))
    try:
        data = resp.json()
    except Exception:
        data = resp.text
    return resp.status_code, data


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--url",
        default="",
        help="Send the payload over HTTP to this URL (ex: https://scam-agent.onrender.com/).",
    )
    args = parser.parse_args()

    load_dotenv(dotenv_path=".env")

    api_key = (os.getenv("API_KEY") or "").strip()
    if not api_key:
        _fail("API_KEY is not set (add it to .env).", code=2)

    gemini_key = (os.getenv("GEMINI_API_KEY") or "").strip()
    if not gemini_key:
        _fail("GEMINI_API_KEY is not set (add it to .env).", code=2)

    if args.url:
        status, data = _post_http(args.url, api_key)
    else:
        status, data = _post_inprocess(api_key)

    print(f"HTTP {status}")
    print(json.dumps(data, indent=2, ensure_ascii=False) if isinstance(data, dict) else str(data))

    if status != 200:
        _fail(
            "Non-200 response. If you want AI-only replies, ensure Gemini is working and (for HTTP mode) set "
            "LLM_STRICT=true on the server.",
            code=1,
        )

    _validate_response(data)
    print("PASS: Response format is exactly {status, reply} and status=success.")


if __name__ == "__main__":
    main()

