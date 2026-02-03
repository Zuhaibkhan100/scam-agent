#!/usr/bin/env python3
"""
Test API using Python requests (works on any platform)
"""
import requests
import json

def test_api_endpoints():
    base_url = "http://localhost:8000"
    api_key = "honeypot-2026-02-03"
    
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key
    }
    
    # Test 1: Full format from docs
    payload_1 = {
        "sessionId": "wertyu-dfghj-ertyui",
        "message": {
            "sender": "scammer",
            "text": "Your bank account will be blocked today. Verify immediately.",
            "timestamp": 1770005528731
        },
        "conversationHistory": [],
        "metadata": {
            "channel": "SMS",
            "language": "English",
            "locale": "IN"
        }
    }
    
    # Test 2: Minimal format
    payload_2 = {
        "sessionId": "test-123",
        "message": {
            "sender": "scammer",
            "text": "Urgent: Act now"
        }
    }
    
    print("🧪 TESTING API WITH PYTHON REQUESTS")
    print("=" * 60)
    
    # Test root endpoint
    print("\n1. Testing ROOT endpoint (/) with full format:")
    try:
        response = requests.post(f"{base_url}/", json=payload_1, headers=headers, timeout=10)
        print(f"✅ Status Code: {response.status_code}")
        print(f"✅ Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            data = response.json()
            if "status" in data and "reply" in data:
                print("✅ Response format is correct!")
            else:
                print("❌ Response format is incorrect")
        
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error - Server not running!")
        print("Start server with: python -m uvicorn app:app --host 0.0.0.0 --port 8000")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test detect endpoint
    print("\n2. Testing DETECT endpoint (/detect) with minimal format:")
    try:
        response = requests.post(f"{base_url}/detect", json=payload_2, headers=headers, timeout=10)
        print(f"✅ Status Code: {response.status_code}")
        print(f"✅ Response: {json.dumps(response.json(), indent=2)}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("📋 NEXT STEPS:")
    print("1. If tests pass above, your API works locally")
    print("2. Deploy to Render and test with:")
    print(f"   https://your-app-name.onrender.com/")
    print(f"   https://your-app-name.onrender.com/detect")
    print("3. Use these URLs on the hackathon website")

if __name__ == "__main__":
    test_api_endpoints()
