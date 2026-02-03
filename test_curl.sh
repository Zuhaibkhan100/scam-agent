#!/bin/bash

echo "🧪 DIRECT CURL TESTS"
echo "===================="

API_KEY="honeypot-2026-02-03"
BASE_URL="http://localhost:8000"

# Test 1: Exact hackathon format (first message)
echo -e "\n1. Testing exact hackathon format (first message)..."
curl -X POST "$BASE_URL/" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY" \
  -d '{
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
  }' \
  -w "\nHTTP_CODE:%{http_code}\nRESPONSE_TIME:%{time_total}s\n" \
  -s

echo -e "\n" 

# Test 2: With /detect endpoint
echo -e "\n2. Testing /detect endpoint..."
curl -X POST "$BASE_URL/detect" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY" \
  -d '{
    "sessionId": "test-detect",
    "message": {
      "sender": "scammer",
      "text": "Share your UPI ID now"
    }
  }' \
  -w "\nHTTP_CODE:%{http_code}\nRESPONSE_TIME:%{time_total}s\n" \
  -s

echo -e "\n"

# Test 3: With uppercase header
echo -e "\n3. Testing with X-API-Key (uppercase)..."
curl -X POST "$BASE_URL/" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "sessionId": "test-uppercase",
    "message": {
      "sender": "scammer",
      "text": "Urgent: Verify account"
    }
  }' \
  -w "\nHTTP_CODE:%{http_code}\nRESPONSE_TIME:%{time_total}s\n" \
  -s

echo -e "\n"

# Test 4: Follow-up message format
echo -e "\n4. Testing follow-up message format..."
curl -X POST "$BASE_URL/" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY" \
  -d '{
    "sessionId": "follow-up-test",
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
  }' \
  -w "\nHTTP_CODE:%{http_code}\nRESPONSE_TIME:%{time_total}s\n" \
  -s

echo -e "\n===================="
echo "✅ Curl tests completed"
