#!/usr/bin/env python3
"""
Local judge-style simulation:
- Sends the exact hackathon payload
- Maintains conversationHistory across turns
- Triggers the final callback (dry-run by default)
"""

import os
import time


def _now_ms() -> int:
    return int(time.time() * 1000)


def main() -> None:
    # Ensure we don't spam the real callback endpoint during local simulation.
    os.environ.setdefault("CALLBACK_DRY_RUN", "true")
    # Match common hackathon settings: callback after a couple of turns.
    os.environ.setdefault("CALLBACK_MIN_TURNS", "4")

    from fastapi.testclient import TestClient  # noqa: WPS433 (local import)

    import app  # noqa: WPS433 (local import)

    client = TestClient(app.app)

    api_key = os.getenv("API_KEY", "honeypot-2026-02-03")
    headers = {"x-api-key": api_key, "Content-Type": "application/json"}

    session_id = "judge-sim-001"
    history = []
    metadata = {"channel": "SMS", "language": "English", "locale": "IN"}

    scammer_messages = [
        "Your bank account will be blocked today. Verify immediately.",
        "To verify, click https://fake-bank-verify.example and share OTP 123456.",
    ]

    for i, scammer_text in enumerate(scammer_messages, start=1):
        payload = {
            "sessionId": session_id,
            "message": {"sender": "scammer", "text": scammer_text, "timestamp": _now_ms()},
            "conversationHistory": history,
            "metadata": metadata,
        }

        resp = client.post("/", json=payload, headers=headers)
        print(f"\nTURN {i} -> HTTP {resp.status_code}")
        print(resp.json())

        reply = resp.json().get("reply", "")
        history.append({"sender": "scammer", "text": scammer_text, "timestamp": _now_ms()})
        history.append({"sender": "user", "text": reply, "timestamp": _now_ms()})

    print("\nDone. If CALLBACK_DRY_RUN=true, the callback payload is printed by the server logs.")


if __name__ == "__main__":
    main()
