#!/usr/bin/env python3
"""
Debug script to test exact schema validation
"""
import json
from pydantic import ValidationError
from models.hackathon_schemas import HackathonRequest, HackathonResponse

def test_schema_validation():
    print("Testing HackathonRequest schema validation...")
    
    # Test with exact format from documentation
    test_payload = {
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
        # Test schema validation
        request = HackathonRequest(**test_payload)
        print("✅ Schema validation passed")
        print(f"Session ID: {request.sessionId}")
        print(f"Message sender: {request.message.sender}")
        print(f"Message text: {request.message.text}")
        print(f"Conversation history length: {len(request.conversationHistory)}")
        
        # Test response format
        response = HackathonResponse(status="success", reply="Test reply")
        print("✅ Response schema valid")
        print(f"Response: {response.model_dump()}")
        
        return True
        
    except ValidationError as e:
        print("❌ Schema validation failed:")
        print(json.dumps(e.errors(), indent=2))
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_minimal_payload():
    print("\nTesting minimal payload...")
    
    # Test with minimal required fields
    minimal_payload = {
        "sessionId": "test-123",
        "message": {
            "sender": "scammer", 
            "text": "Test message"
        }
    }
    
    try:
        request = HackathonRequest(**minimal_payload)
        print("✅ Minimal payload validation passed")
        return True
    except ValidationError as e:
        print("❌ Minimal payload failed:")
        print(json.dumps(e.errors(), indent=2))
        return False

if __name__ == "__main__":
    test_schema_validation()
    test_minimal_payload()
