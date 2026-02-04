# JobBuddy

Multi-agent AI job application assistant with a FastAPI backend, Playwright automation, and a React (Vite) frontend.

## Features
- Resume upload + GPT-based parsing
- Job search across Indeed and LinkedIn (Playwright)
- Job scoring, approvals, and application tracking
- Document generation (tailored resume + cover letter)
- Real-time status updates via WebSocket

## Tech Stack
- Backend: FastAPI, SQLAlchemy (async), SQLite
- Frontend: React + Vite
- Automation: Playwright
- LLM: OpenAI API

## Quick Start

### 1. Configure Environment
Copy the example env file and fill in your keys:
```bash
cp .env.example .env
```

### 2. Backend
From the repo root:
```bash
cd backend
python -m pip install -e .
python -m playwright install
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend
```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173/`.

## WebSocket
The frontend uses `/api/v1/ws/chat` for real-time updates. The Vite dev server proxies `/api` to `http://localhost:8000`.

## Notes
- The backend runs in single-user mode for now.
- Playwright requires a local browser install (`python -m playwright install`).
- The LLM features require `OPENAI_API_KEY` to be set.
