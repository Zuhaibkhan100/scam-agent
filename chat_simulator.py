import requests
import json
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

API_URL = "http://127.0.0.1:8000/detect"
API_KEY = os.getenv("API_KEY", "honeypot-2026-02-03")  # Default or from env
HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
CONVERSATION_ID = "auto-chat-session-001"
MESSAGE_COUNTER = 0

print("\n" + "="*70)
print("🕵️  AGENTIC HONEYPOT - AUTOMATED CHAT SIMULATOR")
print("="*70)
print("Type scammer messages. Type 'exit' to stop.\n")

while True:
    MESSAGE_COUNTER += 1
    
    scammer_msg = input(f"\n[Msg #{MESSAGE_COUNTER}] SCAMMER ➜ ").strip()
    
    if scammer_msg.lower() in ["exit", "quit"]:
        print("\n📋 Session ended.")
        break
    
    if not scammer_msg:
        print("⚠️  Empty message. Try again.")
        continue

    payload = {
        "conversation_id": CONVERSATION_ID,
        "text": scammer_msg,
        "channel": "whatsapp"
    }

    try:
        response = requests.post(API_URL, json=payload, headers=HEADERS, timeout=15)
        data = response.json()
    except Exception as e:
        print(f"❌ API error: {e}")
        continue

    # ============================================
    # STAGE-1: SCAM CLASSIFICATION
    # ============================================
    print("\n" + "-"*70)
    print("🤖 STAGE-1: SCAM CLASSIFICATION")
    print("-"*70)
    print(f"Is Scam          : {data.get('is_scam')}")
    print(f"Confidence       : {data.get('confidence', 0):.2%}")
    print(f"Risk Level       : {data.get('risk', 0):.2%}")
    print(f"Classification   : {data.get('reason', 'N/A')}")

    # ============================================
    # AGENT MODE DECISION
    # ============================================
    agent_mode = data.get("agent_mode", "N/A")
    print("\n" + "-"*70)
    print("🎭 AGENT MODE DECISION")
    print("-"*70)
    print(f"Behavior Mode    : {agent_mode.upper()}")

    # ============================================
    # STAGE-2: VICTIM AGENT REPLY
    # ============================================
    agent_reply = data.get("agent_reply")
    if agent_reply:
        print("\n" + "-"*70)
        print("💬 STAGE-2: AI VICTIM AGENT REPLY")
        print("-"*70)
        print(f"AGENT ➜ {agent_reply}")

    # ============================================
    # INTELLIGENCE EXTRACTION
    # ============================================
    intel = data.get("intelligence", {})
    if intel and (intel.get("urls") or intel.get("upi_ids") or intel.get("tactics")):
        print("\n" + "-"*70)
        print("🔎 INTELLIGENCE EXTRACTION")
        print("-"*70)
        if intel.get("urls"):
            print(f"URLs Found       : {', '.join(intel['urls'])}")
        if intel.get("upi_ids"):
            print(f"UPI IDs Found    : {', '.join(intel['upi_ids'])}")
        if intel.get("tactics"):
            print(f"Tactics Detected : {', '.join(intel['tactics'])}")

    # ============================================
    # STAGE-3: ANALYST SUMMARY
    # ============================================
    analyst = data.get("analyst_summary")
    if analyst:
        print("\n" + "-"*70)
        print("📊 STAGE-3: INTELLIGENCE ANALYST")
        print("-"*70)
        print(f"Scam Type        : {analyst.get('scam_type', 'N/A')}")
        print(f"Target           : {analyst.get('target', 'N/A')}")
        print(f"Risk Assessment  : {analyst.get('risk_level', 'N/A')}")
        print(f"Strategy         : {analyst.get('recommended_strategy', 'N/A')}")

    print("\n" + "="*70)

print("\n✅ Chat session complete.\n")
