import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/honeypot/message")
API_KEY = os.getenv("API_KEY", "honeypot-2026-02-03")
SESSION_ID = os.getenv("SESSION_ID", "auto-chat-session-001")

HEADERS = {"x-api-key": API_KEY, "Content-Type": "application/json"}

history = []
metadata = {"channel": "SMS", "language": "English", "locale": "IN"}

print("=" * 70)
print("AGENTIC HONEYPOT - CHAT SIMULATOR (HACKATHON SCHEMA)")
print("=" * 70)
print("Type scammer messages. Type 'exit' to stop.\n")

while True:
    scammer_msg = input("[SCAMMER] > ").strip()
    if scammer_msg.lower() in {"exit", "quit"}:
        print("\nSession ended.")
        break
    if not scammer_msg:
        print("Empty message. Try again.\n")
        continue

    ts = int(time.time() * 1000)
    payload = {
        "sessionId": SESSION_ID,
        "message": {"sender": "scammer", "text": scammer_msg, "timestamp": ts},
        "conversationHistory": history,
        "metadata": metadata,
    }

    try:
        resp = requests.post(API_URL, json=payload, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"API error: {e}\n")
        continue

    reply = str(data.get("reply", "")).strip()
    print(f"[AGENT ] > {reply}\n")

    # Persist history exactly in the hackathon format.
    history.append({"sender": "scammer", "text": scammer_msg, "timestamp": ts})
    history.append({"sender": "user", "text": reply, "timestamp": int(time.time() * 1000)})

