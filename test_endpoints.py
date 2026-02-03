#!/usr/bin/env python3
"""
Test different endpoint paths that the hackathon might expect
"""
import requests
import json

def test_all_endpoints():
    base_url = "http://localhost:8000"
    api_key = "honeypot-2026-02-03"
    
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }
    
    payload = {
        "sessionId": "test-endpoint",
        "message": {
            "sender": "scammer",
            "text": "Test message for endpoint testing"
        }
    }
    
    # List of possible endpoints the hackathon might expect
    endpoints = [
        "/",           # Root
        "/api",        # API base
        "/detect",     # Detect endpoint
        "/honeypot",   # Honeypot endpoint
        "/api/detect", # API with detect
        "/api/honeypot", # API with honeypot
        "/hackathon",  # Hackathon endpoint
        "/webhook",    # Webhook endpoint
    ]
    
    print("Testing different endpoint paths...")
    
    for endpoint in endpoints:
        print(f"\n--- Testing {endpoint} ---")
        try:
            response = requests.post(f"{base_url}{endpoint}", json=payload, headers=headers, timeout=5)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            
            if response.status_code == 200:
                print("✅ SUCCESS - This endpoint works!")
            elif response.status_code == 404:
                print("❌ NOT FOUND - Endpoint doesn't exist")
            elif response.status_code == 422:
                print("❌ VALIDATION ERROR - Schema mismatch")
            else:
                print(f"❌ ERROR {response.status_code}")
                
        except Exception as e:
            print(f"❌ CONNECTION ERROR: {e}")

def test_health_endpoint():
    print("\n--- Testing health endpoint ---")
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        print(f"Health check status: {response.status_code}")
        print(f"Health response: {response.text}")
    except Exception as e:
        print(f"Health check failed: {e}")

if __name__ == "__main__":
    test_health_endpoint()
    test_all_endpoints()
