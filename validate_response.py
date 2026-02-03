import argparse
import json
import sys
import requests


def validate_response(data: dict) -> None:
    required_keys = [
        "is_scam",
        "confidence",
        "reason",
        "risk",
        "agent_mode",
        "agent_reply",
        "intelligence",
        "analyst_summary",
    ]

    missing = [k for k in required_keys if k not in data]
    if missing:
        raise ValueError(f"Missing keys: {', '.join(missing)}")

    if not isinstance(data["is_scam"], bool):
        raise TypeError("is_scam must be bool")
    if not isinstance(data["confidence"], (int, float)):
        raise TypeError("confidence must be number")
    if not isinstance(data["risk"], (int, float)):
        raise TypeError("risk must be number")
    if data["reason"] is not None and not isinstance(data["reason"], str):
        raise TypeError("reason must be string or null")
    if data["agent_mode"] is not None and not isinstance(data["agent_mode"], str):
        raise TypeError("agent_mode must be string or null")
    if data["agent_reply"] is not None and not isinstance(data["agent_reply"], str):
        raise TypeError("agent_reply must be string or null")
    if data["intelligence"] is not None and not isinstance(data["intelligence"], dict):
        raise TypeError("intelligence must be object or null")
    if data["analyst_summary"] is not None and not isinstance(data["analyst_summary"], dict):
        raise TypeError("analyst_summary must be object or null")

    if not (0.0 <= float(data["confidence"]) <= 1.0):
        raise ValueError("confidence out of range")
    if not (0.0 <= float(data["risk"]) <= 1.0):
        raise ValueError("risk out of range")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate /detect response schema")
    parser.add_argument("--url", required=True, help="Full /detect URL")
    parser.add_argument("--api-key", required=True, help="API key for X-API-Key header")
    parser.add_argument("--text", default="urgent refund, click https://x.com", help="Test message")
    parser.add_argument("--conversation-id", default="schema-check-1")
    parser.add_argument("--channel", default="sms")
    args = parser.parse_args()

    payload = {
        "conversation_id": args.conversation_id,
        "text": args.text,
        "channel": args.channel,
    }

    try:
        resp = requests.post(
            args.url,
            headers={"X-API-Key": args.api_key, "Content-Type": "application/json"},
            data=json.dumps(payload),
            timeout=20,
        )
    except Exception as exc:
        print(f"Request failed: {exc}")
        return 2

    if resp.status_code != 200:
        print(f"Non-200 response: {resp.status_code}\n{resp.text}")
        return 3

    try:
        data = resp.json()
    except Exception as exc:
        print(f"Invalid JSON: {exc}\n{resp.text}")
        return 4

    try:
        validate_response(data)
    except Exception as exc:
        print(f"Schema validation failed: {exc}\n{json.dumps(data, indent=2)}")
        return 5

    print("OK: response schema valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
