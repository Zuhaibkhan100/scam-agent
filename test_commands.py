#!/usr/bin/env python3
"""
Test commands for your scam detection API
Run this to test both local and deployed endpoints
"""

import requests
import json
import time

# Configuration
LOCAL_URL = "http://localhost:8000/"
RENDER_URL = "https://scam-agent.onrender.com/"
API_KEY = "honeypot-2026-02-03"

# Test payload
payload = {
    "sessionId": "test-session-123",
    "message": {
        "sender": "scammer", 
        "text": "Your bank account will be blocked today. Verify immediately."
    }
}

def test_endpoint(url, name):
    print(f"\n{'='*50}")
    print(f"Testing {name}: {url}")
    print(f"{'='*50}")
    
    headers = {
        "x-api-key": API_KEY,
        "Content-Type": "application/json"
    }
    
    start_time = time.time()
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        elapsed = time.time() - start_time
        
        print(f"✅ Status: {response.status_code}")
        print(f"⏱️  Time: {elapsed:.2f} seconds")
        
        if response.status_code == 200:
            data = response.json()
            print(f"📝 Response: {json.dumps(data, indent=2)}")
        else:
            print(f"❌ Error Response: {response.text}")
            
    except requests.exceptions.Timeout:
        print(f"❌ TIMEOUT after 30 seconds")
    except Exception as e:
        print(f"❌ ERROR: {e}")

def main():
    print("🧪 API Testing Script")
    print("Make sure your local server is running on http://localhost:8000")
    
    # Test local endpoint
    test_endpoint(LOCAL_URL, "Local Server")
    
    # Test deployed endpoint (first call - may be slow due to cold start)
    test_endpoint(RENDER_URL, "Render Deployed (First Call)")
    
    # Test deployed endpoint again (should be faster)
    print("\n⏳ Waiting 3 seconds before second call to Render...")
    time.sleep(3)
    test_endpoint(RENDER_URL, "Render Deployed (Second Call)")

if __name__ == "__main__":
    main()
