# Agentic Honey-Pot Scam Classification API

A FastAPI-based service for detecting scams, generating victim replies, and extracting intelligence. **GUVI-compliant** with mandatory callback for evaluation.

## Architecture

This system is a **stateless agent node** orchestrated by GUVI:
- GUVI controls the conversation lifecycle
- GUVI sends `conversationHistory` with each request
- Your system classifies, replies, extracts intelligence, and sends a final callback
- No internal session management required

## Features

- **Stage-1**: AI-powered scam classification with confidence scoring
- **Stage-2**: Human-like victim agent reply generation
- **Stage-3**: Intelligence extraction (URLs, UPI IDs, phone numbers, tactics)
- **Callback**: Mandatory final result submission to GUVI evaluation endpoint
- API key authentication
- Free mode: Uses heuristic classification (no paid LLM required)
- Paid mode: Optional Google Gemini integration for higher accuracy

## Local Development

1. Clone the repo
2. Copy `.env.example` to `.env`
3. Install dependencies: `pip install -r requirements.txt`
4. Run: `uvicorn app:app --reload`
5. Test with: `python chat_simulator.py` or API tools

## Deployment on Render

1. Push code to GitHub
2. Connect Render account to GitHub repo
3. Create new **Web Service**
4. Settings:
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app:app --host 0.0.0.0 --port $PORT`
5. Environment Variables (required):
   - `API_KEY`: Your chosen API key (e.g., `honeypot-2026-02-03`)
   - `LLM_PROVIDER`: `mock` (free) or `gemini` (requires GEMINI_API_KEY)
   - `CALLBACK_ENABLED`: `true`
   - `CALLBACK_MIN_TURNS`: `2` (ensures callback fires during evaluation)
6. Optional:
   - `GEMINI_API_KEY`: Your Google Gemini API key (only if using gemini provider)
   - `LLM_MODEL_NAME`: `gemini-2.5-flash-lite`
7. Deploy

## GUVI Hackathon Integration

### Submission Endpoint

Use this endpoint URL in the GUVI platform:

```
POST https://your-app.onrender.com/honeypot/message
```

### Request Format

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

### Response Format

```json
{
  "status": "success",
  "reply": "Why is my account being suspended?"
}
```

### Authentication

- Header: `X-API-Key: your-api-key`
- Content-Type: `application/json`

### Mandatory Callback

Your system automatically sends a final callback to:
```
POST https://hackathon.guvi.in/api/updateHoneyPotFinalResult
```

When:
- Scam is detected AND
- Engagement depth ≥ CALLBACK_MIN_TURNS (default: 2) AND
- Intelligence signals extracted (URLs, UPI IDs, phone numbers, etc.)

Payload:
```json
{
  "sessionId": "...",
  "scamDetected": true,
  "totalMessagesExchanged": 4,
  "extractedIntelligence": {
    "bankAccounts": [],
    "upiIds": ["scammer@upi"],
    "phishingLinks": ["http://malicious.com"],
    "phoneNumbers": ["+91XXXXXXXXXX"],
    "suspiciousKeywords": ["urgent", "verify", "blocked"]
  },
  "agentNotes": "Scam tactics: urgency, authority. Engagement depth: 4 turns."
}
```

## API Endpoints

- `POST /honeypot/message`: **GUVI submission endpoint** (stateless, callback-enabled)
- `POST /detect`: Original endpoint (backward compatible, internal memory)
- `POST /victim_reply`: Reply generation only
- `GET /memory/{conversation_id}`: Debug conversation memory (for /detect only)
- `GET /health`: Health check

## Testing Locally

Health check:
```bash
curl https://your-app.onrender.com/health
```

Test honeypot endpoint:
```bash
curl -X POST https://your-app.onrender.com/honeypot/message \
  -H "X-API-Key: honeypot-2026-02-03" \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "test-1",
    "message": {"sender": "scammer", "text": "Urgent: verify your account", "timestamp": 1770005528731},
    "conversationHistory": [],
    "metadata": {"channel": "SMS", "language": "English", "locale": "IN"}
  }'
```

## Security Notes

- Change default `API_KEY` in production
- Restrict CORS origins if needed
- Callback is sent asynchronously; failures are logged but don't block the response
- Free mode (mock provider) has no external dependencies; paid mode requires Gemini API key