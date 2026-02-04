# Agentic Honey-Pot for Scam Detection & Intelligence Extraction

FastAPI service aligned to the hackathon requirements:
- Accepts incoming message events (with `sessionId`, `message`, `conversationHistory`, `metadata`)
- Detects scam intent
- Engages autonomously with a human-like persona (multi-turn via `conversationHistory`)
- Extracts scam intelligence (UPI IDs, links, phone numbers, bank accounts, suspicious keywords)
- Returns a minimal JSON response: `{ "status": "success", "reply": "..." }`
- Sends the mandatory final callback to the GUVI evaluation endpoint (best-effort, once per session)

**Authentication**
- Header: `x-api-key: YOUR_SECRET_API_KEY`
- Header: `Content-Type: application/json`

**Hackathon Entry Endpoints**
All of these accept the required request schema:
- `POST /`
- `POST /detect`
- `POST /honeypot`
- `POST /honeypot/message`
- `POST /hackathon/detect`

**Request Format (Input)**
```json
{
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
```

**Response Format (Output)**
```json
{
  "status": "success",
  "reply": "Why is my account being suspended?"
}
```

**Mandatory Final Result Callback**
- Endpoint: `POST https://hackathon.guvi.in/api/updateHoneyPotFinalResult`
- Content-Type: `application/json`
- Sent once per session when:
  1. Scam intent is confirmed (`scamDetected = true`)
  2. Engagement depth is sufficient (`totalMessagesExchanged >= CALLBACK_MIN_TURNS`)

Example payload:
```json
{
  "sessionId": "abc123-session-id",
  "scamDetected": true,
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
```

**Configuration (.env)**
- `API_KEY` (required): the value expected in the `x-api-key` header
- `LLM_PROVIDER` (optional): `mock` (default) or `gemini`
- `GEMINI_API_KEY` (required if `LLM_PROVIDER=gemini`)
- `LLM_MODEL_NAME` (optional): Gemini model name
- `CALLBACK_ENABLED` (optional): `true`/`false` (default: `true`)
- `CALLBACK_URL` (optional): defaults to the GUVI endpoint
- `CALLBACK_MIN_TURNS` (optional): minimum `totalMessagesExchanged` before callback (default: `2`)

**Run Locally**
```bash
pip install -r requirements.txt
uvicorn app:app --reload
```

**Deploy on Render (important)**
- Start command: `uvicorn app:app --host 0.0.0.0 --port $PORT`
- Environment vars: `API_KEY` (required), `LLM_PROVIDER` (`mock` recommended for speed), `GEMINI_API_KEY` (only if `LLM_PROVIDER=gemini`)
- If you see 30s timeouts from the evaluator, verify the service is awake (Render free tier can sleep) and that you are binding to `$PORT`.

**Quick Test**
```bash
curl -X POST http://127.0.0.1:8000/honeypot/message \
  -H "x-api-key: honeypot-2026-02-03" \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "test-1",
    "message": {"sender": "scammer", "text": "Urgent: verify your account", "timestamp": 1770005528731},
    "conversationHistory": [],
    "metadata": {"channel": "SMS", "language": "English", "locale": "IN"}
  }'
```
