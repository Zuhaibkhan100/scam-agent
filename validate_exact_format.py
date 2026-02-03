#!/usr/bin/env python3
"""
Validate exact format without server - test schema and response format
"""
import json
from models.hackathon_schemas import HackathonRequest, HackathonResponse

def test_exact_hackathon_format():
    print("🔍 TESTING EXACT HACKATHON FORMAT VALIDATION")
    print("=" * 60)
    
    # Test 1: Exact format from documentation (First Message)
    print("\n1. Testing First Message Format:")
    first_message_payload = {
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
    
    try:
        request = HackathonRequest(**first_message_payload)
        print("✅ First message format - VALID")
        print(f"   Session ID: {request.sessionId}")
        print(f"   Sender: {request.message.sender}")
        print(f"   Text: {request.message.text}")
        print(f"   History length: {len(request.conversationHistory)}")
    except Exception as e:
        print(f"❌ First message format - INVALID: {e}")
    
    # Test 2: Follow-up Message Format
    print("\n2. Testing Follow-up Message Format:")
    followup_payload = {
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
    
    try:
        request = HackathonRequest(**followup_payload)
        print("✅ Follow-up message format - VALID")
        print(f"   Session ID: {request.sessionId}")
        print(f"   History length: {len(request.conversationHistory)}")
        for i, msg in enumerate(request.conversationHistory):
            print(f"   History {i+1}: {msg.sender} -> {msg.text[:30]}...")
    except Exception as e:
        print(f"❌ Follow-up message format - INVALID: {e}")
    
    # Test 3: Response Format
    print("\n3. Testing Response Format:")
    try:
        response = HackathonResponse(
            status="success",
            reply="Why is my account being suspended?"
        )
        print("✅ Response format - VALID")
        response_dict = response.model_dump()
        print(f"   Response: {json.dumps(response_dict, indent=2)}")
        
        # Check if it matches expected format exactly
        expected_keys = {"status", "reply"}
        actual_keys = set(response_dict.keys())
        if actual_keys == expected_keys:
            print("✅ Response has exactly the required fields")
        else:
            print(f"❌ Response fields mismatch. Expected: {expected_keys}, Got: {actual_keys}")
            
    except Exception as e:
        print(f"❌ Response format - INVALID: {e}")
    
    # Test 4: Edge Cases
    print("\n4. Testing Edge Cases:")
    
    # Minimal payload
    minimal_payload = {
        "sessionId": "test-123",
        "message": {
            "sender": "scammer",
            "text": "Test"
        }
    }
    
    try:
        request = HackathonRequest(**minimal_payload)
        print("✅ Minimal payload - VALID")
    except Exception as e:
        print(f"❌ Minimal payload - INVALID: {e}")
    
    # Invalid sender
    invalid_sender_payload = {
        "sessionId": "test-456",
        "message": {
            "sender": "invalid",  # Should be "scammer" or "user"
            "text": "Test"
        }
    }
    
    try:
        request = HackathonRequest(**invalid_sender_payload)
        print("❌ Invalid sender - Should have failed but didn't!")
    except Exception as e:
        print("✅ Invalid sender - Correctly rejected")

def test_callback_format():
    print("\n" + "=" * 60)
    print("🔍 TESTING CALLBACK PAYLOAD FORMAT")
    print("=" * 60)
    
    callback_payload = {
        "sessionId": "abc123-session-id",
        "scamDetected": True,
        "totalMessagesExchanged": 18,
        "extractedIntelligence": {
            "bankAccounts": ["XXXX-XXXX-XXXX"],
            "upiIds": ["scammer@upi"],
            "phishingLinks": ["http://malicious-link.example"],
            "phoneNumbers": ["+91XXXXXXXXXX"],
            "suspiciousKeywords": ["urgent", "verify now", "account blocked"]
        },
        "agentNotes": "Scammer used urgency tactics and payment redirection"
    }
    
    # Check required fields
    required_fields = ["sessionId", "scamDetected", "totalMessagesExchanged", "extractedIntelligence", "agentNotes"]
    required_intel_fields = ["bankAccounts", "upiIds", "phishingLinks", "phoneNumbers", "suspiciousKeywords"]
    
    print("\nChecking callback payload structure:")
    
    for field in required_fields:
        if field in callback_payload:
            print(f"✅ {field} - Present")
        else:
            print(f"❌ {field} - Missing")
    
    intel = callback_payload.get("extractedIntelligence", {})
    for field in required_intel_fields:
        if field in intel:
            print(f"✅ extractedIntelligence.{field} - Present")
        else:
            print(f"❌ extractedIntelligence.{field} - Missing")
    
    print(f"\nCallback payload format: {json.dumps(callback_payload, indent=2)}")

if __name__ == "__main__":
    test_exact_hackathon_format()
    test_callback_format()
    
    print("\n" + "=" * 60)
    print("📋 SUMMARY")
    print("=" * 60)
    print("If all tests above show ✅ VALID, then your schema is correct.")
    print("The INVALID_REQUEST_BODY error is likely due to:")
    print("1. Wrong endpoint URL on hackathon website")
    print("2. Server not running/deployed properly")
    print("3. API key mismatch")
    print("4. Network/firewall issues")
