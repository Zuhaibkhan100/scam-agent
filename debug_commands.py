#!/usr/bin/env python3
"""
Generate exact curl commands for testing
"""

def generate_curl_commands():
    base_url = "http://localhost:8000"  # Change to your Render URL
    api_key = "honeypot-2026-02-03"
    
    # Test 1: Exact format from docs
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
    
    import json
    
    print("🧪 EXACT CURL COMMANDS FOR TESTING")
    print("=" * 60)
    print("Copy and paste these commands to test your API:")
    print()
    
    # Test 1: Root endpoint
    print("1. ROOT ENDPOINT (/) - Full format:")
    print(f"curl -X POST {base_url}/ \\")
    print(f"  -H \"Content-Type: application/json\" \\")
    print(f"  -H \"x-api-key: {api_key}\" \\")
    print(f"  -d '{json.dumps(payload_1)}' \\")
    print("  -w \"\\nHTTP_CODE:%{http_code}\\n\" -s")
    print()
    
    # Test 2: Detect endpoint
    print("2. DETECT ENDPOINT (/detect) - Minimal format:")
    print(f"curl -X POST {base_url}/detect \\")
    print(f"  -H \"Content-Type: application/json\" \\")
    print(f"  -H \"x-api-key: {api_key}\" \\")
    print(f"  -d '{json.dumps(payload_2)}' \\")
    print("  -w \"\\nHTTP_CODE:%{http_code}\\n\" -s")
    print()
    
    # Test 3: Uppercase header
    print("3. UPPERCASE HEADER (X-API-Key):")
    print(f"curl -X POST {base_url}/ \\")
    print(f"  -H \"Content-Type: application/json\" \\")
    print(f"  -H \"X-API-Key: {api_key}\" \\")
    print(f"  -d '{json.dumps(payload_2)}' \\")
    print("  -w \"\\nHTTP_CODE:%{http_code}\\n\" -s")
    print()
    
    print("=" * 60)
    print("📝 FOR RENDER DEPLOYMENT:")
    print("Replace localhost:8000 with your Render URL:")
    print("https://your-app-name.onrender.com")
    print()
    print("🔍 EXPECTED RESPONSES:")
    print("✅ HTTP_CODE:200")
    print('✅ Response: {"status": "success", "reply": "..."}')
    print()
    print("❌ POSSIBLE ERRORS:")
    print("HTTP_CODE:401 -> API key issue")
    print("HTTP_CODE:404 -> Endpoint not found")
    print("HTTP_CODE:422 -> Invalid request body")
    print("HTTP_CODE:500 -> Server error")

if __name__ == "__main__":
    generate_curl_commands()
