#!/usr/bin/env python3
"""
Test script to validate the hackathon API compliance
"""
import requests
import json
import time

def test_api():
    base_url = "http://localhost:8000"
    api_key = "honeypot-2026-02-03"
    
    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json"
    }
    
    # Test case 1: First message (no conversation history)
    test_payload_1 = {
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
    
    # Test case 2: Follow-up message (with conversation history)
    test_payload_2 = {
        "sessionId": "wertyu-dfghj-ertyui",
        "message": {
            "sender": "scammer",
            "text": "Share your UPI ID to avoid account suspension.",
            "timestamp": 1770005528731
        },
        "conversationHistory": [
            {
                "sender": "scammer",
                "text": "Your bank account will be blocked today. Verify immediately.",
                "timestamp": 1770005528731
            },
            {
                "sender": "user",
                "text": "Why will my account be blocked?",
                "timestamp": 1770005528731
            }
        ],
        "metadata": {
            "channel": "SMS",
            "language": "English",
            "locale": "IN"
        }
    }
    
    print("Testing Hackathon API Compliance...")
    print("=" * 50)
    
    # Test main endpoint
    try:
        print("\n1. Testing main endpoint (/) with first message...")
        response = requests.post(f"{base_url}/", json=test_payload_1, headers=headers, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Response received successfully")
            print(f"Response format: {json.dumps(data, indent=2)}")
            
            # Validate response format
            if "status" in data and "reply" in data:
                print("✅ Response format is correct")
                if data["status"] == "success":
                    print("✅ Status is 'success'")
                else:
                    print("❌ Status is not 'success'")
            else:
                print("❌ Response format is incorrect - missing 'status' or 'reply'")
        else:
            print(f"❌ Request failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Error connecting to API: {e}")
        return False
    
    # Test follow-up message
    try:
        print("\n2. Testing follow-up message...")
        response = requests.post(f"{base_url}/", json=test_payload_2, headers=headers, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Follow-up message handled successfully")
            print(f"Response: {json.dumps(data, indent=2)}")
        else:
            print(f"❌ Follow-up message failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Error with follow-up message: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("API Test Complete!")
    return True

if __name__ == "__main__":
    test_api()
