#!/usr/bin/env python3
"""
Test the correct Render endpoints
"""
import requests
import json

def test_render_endpoints():
    base_url = "https://scam-agent.onrender.com"
    api_key = "honeypot-2026-02-03"
    
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key
    }
    
    payload = {
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
    
    endpoints_to_test = [
        "/",
        "/detect",
        "/honeypot",
        "/honeypot/message",
        "/hackathon/detect",
    ]
    
    print("🌍 TESTING RENDER ENDPOINTS")
    print("=" * 50)
    
    for endpoint in endpoints_to_test:
        url = f"{base_url}{endpoint}"
        print(f"\n🔍 Testing: {url}")
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            print(f"✅ Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Response: {json.dumps(data, indent=2)}")
                print("🎯 THIS ENDPOINT WORKS!")
            else:
                print(f"❌ Error: {response.text}")
                
        except requests.exceptions.Timeout:
            print("❌ Timeout - Server might be starting up")
        except requests.exceptions.ConnectionError:
            print("❌ Connection Error - Server might be down")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print(f"\n📋 CORRECT URLS TO USE ON HACKATHON WEBSITE:")
    print(f"1. https://scam-agent.onrender.com/")
    print(f"2. https://scam-agent.onrender.com/honeypot/message")
    print(f"3. https://scam-agent.onrender.com/detect")

if __name__ == "__main__":
    test_render_endpoints()
