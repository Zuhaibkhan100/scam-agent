#!/usr/bin/env python3
"""
Quick test to verify endpoints work
"""
import requests
import json
import time

def quick_test():
    base_url = "http://localhost:8000"
    api_key = "honeypot-2026-02-03"
    
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }
    
    payload = {
        "sessionId": "quick-test",
        "message": {
            "sender": "scammer",
            "text": "Urgent: Your account will be blocked",
            "timestamp": int(time.time() * 1000),
        },
        "conversationHistory": [],
    }
    
    endpoints_to_test = [
        "/",
        "/detect"
    ]
    
    print("Quick endpoint test...")
    
    for endpoint in endpoints_to_test:
        try:
            print(f"\nTesting {endpoint}")
            response = requests.post(f"{base_url}{endpoint}", json=payload, headers=headers, timeout=5)
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Success! Response: {json.dumps(data, indent=2)}")
            else:
                print(f"❌ Failed: {response.text}")
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    quick_test()
