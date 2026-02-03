#!/usr/bin/env python3
"""
Comprehensive curl test to match hackathon platform exactly
"""
import subprocess
import json
import time

def run_curl_test(test_name, url, payload, headers):
    """Run curl command and return response"""
    print(f"\n{'='*60}")
    print(f"TEST: {test_name}")
    print(f"URL: {url}")
    print(f"HEADERS: {headers}")
    print(f"PAYLOAD:")
    print(json.dumps(payload, indent=2))
    print("-"*60)
    
    # Build curl command
    curl_cmd = [
        'curl', '-X', 'POST',
        url,
        '-H', f'Content-Type: application/json',
        '-H', f'x-api-key: {headers["x-api-key"]}',
        '-d', json.dumps(payload),
        '-w', '\\n\\nHTTP_CODE:%{{http_code}}\\nRESPONSE_TIME:%{{time_total}}',
        '-s'
    ]
    
    try:
        result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=10)
        
        # Parse response
        output = result.stdout.strip()
        if 'HTTP_CODE:' in output:
            parts = output.split('HTTP_CODE:')
            response_body = parts[0].strip()
            metadata = parts[1].strip()
            
            http_code = metadata.split('RESPONSE_TIME:')[0]
            response_time = metadata.split('RESPONSE_TIME:')[1]
            
            print(f"HTTP STATUS: {http_code}")
            print(f"RESPONSE TIME: {response_time}s")
            print(f"RESPONSE BODY:")
            print(response_body)
            
            return {
                'status_code': int(http_code),
                'response_body': response_body,
                'response_time': float(response_time),
                'success': int(http_code) == 200
            }
        else:
            print(f"RAW OUTPUT: {output}")
            return {'success': False, 'error': 'Parse error'}
            
    except subprocess.TimeoutExpired:
        print("❌ TIMEOUT - Request took too long")
        return {'success': False, 'error': 'timeout'}
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return {'success': False, 'error': str(e)}

def main():
    base_url = "http://localhost:8000"
    api_key = "honeypot-2026-02-03"
    
    headers = {"x-api-key": api_key}
    
    # Test 1: Exact format from hackathon docs (first message)
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
    
    # Test 2: Follow-up message format
    payload_2 = {
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
    
    # Test 3: Minimal payload
    payload_3 = {
        "sessionId": "minimal-test",
        "message": {
            "sender": "scammer",
            "text": "Urgent: Act now"
        }
    }
    
    # Test different header formats
    header_variants = [
        {"x-api-key": api_key, "name": "lowercase x-api-key"},
        {"X-API-Key": api_key, "name": "uppercase X-API-Key"},
        {"X-Api-Key": api_key, "name": "mixed case X-Api-Key"}
    ]
    
    # Test different endpoints
    endpoints = [
        {"path": "/", "name": "root endpoint"},
        {"path": "/detect", "name": "detect endpoint"},
        {"path": "/honeypot", "name": "honeypot endpoint"}
    ]
    
    print("🧪 COMPREHENSIVE CURL TESTING")
    print("This simulates exactly what the hackathon platform sends")
    
    results = []
    
    # Test combinations
    for endpoint in endpoints:
        url = f"{base_url}{endpoint['path']}"
        
        for header_variant in header_variants:
            # Test with payload 1
            result = run_curl_test(
                f"{endpoint['name']} - {header_variant['name']} - First Message",
                url,
                payload_1,
                header_variant
            )
            results.append(result)
            
            # Small delay between requests
            time.sleep(0.5)
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 SUMMARY")
    print(f"{'='*60}")
    
    successful_tests = sum(1 for r in results if r.get('success', False))
    total_tests = len(results)
    
    print(f"Successful tests: {successful_tests}/{total_tests}")
    
    if successful_tests > 0:
        print("\n✅ WORKING CONFIGURATIONS:")
        for i, result in enumerate(results):
            if result.get('success'):
                print(f"  Test {i+1}: SUCCESS")
    else:
        print("\n❌ NO WORKING CONFIGURATIONS FOUND")
        print("Check if server is running: python -m uvicorn app:app --host 0.0.0.0 --port 8000")
    
    # Show any error patterns
    error_codes = {}
    for result in results:
        if not result.get('success') and 'status_code' in result:
            code = result['status_code']
            error_codes[code] = error_codes.get(code, 0) + 1
    
    if error_codes:
        print(f"\n🔍 ERROR PATTERNS:")
        for code, count in error_codes.items():
            print(f"  HTTP {code}: {count} times")

if __name__ == "__main__":
    main()
