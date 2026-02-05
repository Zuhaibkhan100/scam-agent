#!/bin/bash
# curl commands for testing your API

API_KEY="honeypot-2026-03-02"
LOCAL_URL="http://localhost:8000/"
RENDER_URL="https://scam-agent.onrender.com/"

# Test payload
PAYLOAD='{
    "sessionId": "test-session-123",
    "message": {
        "sender": "scammer",
        "text": "Your bank account will be blocked today. Verify immediately."
    }
}'

echo "=== Testing Local Server ==="
curl -X POST "$LOCAL_URL" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY" \
  -d "$PAYLOAD" \
  -w "\nTime: %{time_total}s\n"

echo -e "\n=== Testing Render Deployed (First Call) ==="
curl -X POST "$RENDER_URL" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY" \
  -d "$PAYLOAD" \
  -w "\nTime: %{time_total}s\n" \
  --max-time 30

echo -e "\n=== Testing Render Deployed (Second Call) ==="
sleep 3
curl -X POST "$RENDER_URL" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY" \
  -d "$PAYLOAD" \
  -w "\nTime: %{time_total}s\n" \
  --max-time 30
