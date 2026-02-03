#!/usr/bin/env python3
"""
Check the full JSON response without PowerShell formatting
"""
import requests
import json

def check_full_response():
    headers = {
        "Content-Type": "application/json",
        "x-api-key": "honeypot-2026-02-03"
    }
    
    payload = {
        "sessionId": "test-full-response",
        "message": {
            "sender": "scammer",
            "text": "Urgent: Act now"
        }
    }
    
    print("🔍 CHECKING FULL JSON RESPONSE")
    print("=" * 50)
    
    try:
        response = requests.post("http://localhost:8000/", json=payload, headers=headers, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        print(f"Raw Response: {response.text}")
        print()
        
        # Parse and pretty print
        data = response.json()
        print("Parsed JSON:")
        print(json.dumps(data, indent=2))
        print()
        
        print("Field Analysis:")
        print(f"✅ status: '{data['status']}'")
        print(f"✅ reply: '{data['reply']}'")
        print(f"✅ reply length: {len(data['reply'])} characters")
        
        # Check if it matches hackathon requirements
        if "status" in data and "reply" in data:
            print("\n🎯 PERFECT! This matches hackathon requirements exactly!")
        else:
            print("\n❌ Missing required fields")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_full_response()
