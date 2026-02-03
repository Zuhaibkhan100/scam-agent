# Agentic Honey-Pot Scam Classification API

A FastAPI-based service for detecting scams, generating victim replies, and extracting intelligence.

## Features

- **Stage-1**: AI-powered scam classification with confidence scoring
- **Stage-2**: Human-like victim agent reply generation with conversation memory
- **Stage-3**: Intelligence analysis for high-risk messages
- API key authentication
- In-memory conversation tracking

## Local Development

1. Clone the repo
2. Copy `.env.example` to `.env` and fill in values
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
5. Environment Variables:
   - `API_KEY`: Your chosen API key (e.g., `honeypot-2026-02-03`)
   - `GEMINI_API_KEY`: Your Google Gemini API key
   - Optional: `LLM_MODEL_NAME`, `LLM_COOLDOWN_SECONDS`, etc.
6. Deploy

## Testing

After deployment, use the Render URL (e.g., `https://your-app.onrender.com/detect`) in API testers like Postman:

- **Method**: POST
- **Headers**: `X-API-Key: your-api-key`
- **Body** (JSON):
  ```json
  {
    "conversation_id": "test-1",
    "text": "Urgent: Your account is blocked. Click https://fake-bank.com to verify."
  }
  ```

Health check: GET `https://your-app.onrender.com/health`

## API Endpoints

- `POST /detect`: Full scam detection pipeline
- `POST /victim_reply`: Reply generation only
- `GET /memory/{conversation_id}`: Debug conversation memory
- `GET /health`: Health check

## Security Notes

- Change default `API_KEY` in production
- Restrict CORS origins if needed
- Monitor usage to avoid LLM quota issues