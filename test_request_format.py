#!/usr/bin/env python3
"""
Test different request formats to find the exact expected format
"""
import requests
import json

def test_different_formats():
    base_url = "http://localhost:8000"
    api_key = "honeypot-2026-02-03"
    
    headers = {
        "x-api-key": api_key,  # lowercase header name
        "Content-Type": "application/json"
    }
    
    # Test 1: Exact format from documentation
    payload1 = {
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
    payload2 = {
        "sessionId": "test-123",
        "message": {
            "sender": "scammer",
            "text": "Test message",
            "timestamp": 1770005528731
        },
        "conversationHistory": []
    }
    
    # Test 3: Without metadata
    payload3 = {
        "sessionId": "test-456",
        "message": {
            "sender": "scammer", 
            "text": "Urgent: Verify your account now",
            "timestamp": 1770005528731
        },
        "conversationHistory": []
    }
    
    test_cases = [
        ("Exact format from docs", payload1),
        ("Minimal format", payload2), 
        ("Without metadata", payload3)
    ]
    
    for name, payload in test_cases:
        print(f"\n--- Testing: {name} ---")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        
        try:
            response = requests.post(f"{base_url}/", json=payload, headers=headers, timeout=10)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code == 200:
                print("✅ SUCCESS")
            else:
                print("❌ FAILED")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")

def test_header_variations():
    print("\n--- Testing header variations ---")
    base_url = "http://localhost:8000"
    
    payload = {
        "sessionId": "test-789",
        "message": {
            "sender": "scammer",
            "text": "Test message",
            "timestamp": 1770005528731
        },
        "conversationHistory": []
    }
    
    # Test different header key formats
    header_tests = [
        ("X-API-Key", "uppercase"),
        ("x-api-key", "lowercase"),
        ("X-Api-Key", "mixed case")
    ]
    
    for header_name, desc in header_tests:
        print(f"\nTesting {desc}: {header_name}")
        headers = {
            header_name: "honeypot-2026-02-03",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(f"{base_url}/", json=payload, headers=headers, timeout=5)
            print(f"Status: {response.status_code}")
            if response.status_code != 200:
                print(f"Error: {response.text}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    test_different_formats()
    test_header_variations()
