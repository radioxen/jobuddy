# JobBuddy — Development Diary

## Project Status: MVP COMPLETE — READY FOR TESTING

---

## 2026-02-04 — Project Kickoff & Full MVP Build

### Decisions Made
- **Tech Stack**: Python/FastAPI backend, React/Vite/TypeScript frontend
- **AI Framework**: CrewAI 1.9.3 (installed, custom orchestration flow using direct OpenAI calls)
- **LLM**: OpenAI GPT-5.2 (`gpt-5.2-2025-12-11`)
- **Browser Automation**: Playwright 1.58 with persistent context (headed mode)
- **Database**: SQLite via SQLAlchemy async (aiosqlite)
- **Resume Processing**: python-docx + docxtpl for DOCX manipulation
- **Real-time**: WebSocket for chat + status updates
- **Python**: 3.13.9 (3.14 not compatible with CrewAI)

### Architecture
- 6 AI agents: Job Searcher, Resume Matcher, Resume Tailor, Cover Letter Writer, Application Filler, Chat Agent
- Custom orchestration flow (job_application_flow.py) with human-in-the-loop checkpoints
- Platform-specific form fillers for LinkedIn (Easy Apply) and Indeed
- Persistent browser sessions (user logs in once, cookies persist)
- Full-control chatbot via WebSocket (GPT-powered with command extraction)

---

## Build Log

### Phase 1: Foundation — COMPLETE
- [x] Backend skeleton (FastAPI, config, database) — `app/main.py`, `app/config.py`, `app/database.py`
- [x] SQLAlchemy models — `app/models/` (UserProfile, JobListing, Application, ChatMessage)
- [x] Pydantic schemas — `app/schemas/` (user, job, application, chat)
- [x] Resume upload + parse endpoint — `app/api/v1/users.py` (POST /upload-resume)
- [x] User preferences endpoints — `app/api/v1/users.py` (GET/PUT /preferences)
- [x] Frontend skeleton — React + Vite + TypeScript, routing, Layout with sidebar

### Phase 2: Agent Infrastructure — COMPLETE
- [x] CrewAI setup + agent/task YAML configs — `app/agents/config/`
- [x] Search services (Indeed + LinkedIn via Playwright) — `app/services/job_search.py`
- [x] Resume Matcher (GPT-based scoring) — `app/agents/flows/job_application_flow.py`
- [x] Jobs API — `app/api/v1/jobs.py` (search, list, approve, reject, batch)
- [x] JobList page — `frontend/src/pages/JobList.tsx`

### Phase 3: Document Generation — COMPLETE
- [x] Resume Tailor service + DOCX generation — `app/services/resume_tailor.py`
- [x] Cover Letter writer + DOCX generation — `app/services/cover_letter_writer.py`
- [x] Download endpoints — `app/api/v1/applications.py`

### Phase 4: Browser Automation — COMPLETE
- [x] BrowserManager (persistent Playwright context) — `app/services/browser_manager.py`
- [x] LinkedIn Easy Apply form filler — `app/services/form_filler.py`
- [x] Indeed form filler — `app/services/form_filler.py`
- [x] Browser control API — `app/api/v1/browser.py`

### Phase 5: Orchestration — COMPLETE
- [x] JobApplicationFlow — `app/agents/flows/job_application_flow.py`
- [x] Human-in-the-loop checkpoints (approve jobs → prepare docs → fill forms → user submits)
- [x] WebSocket real-time status updates — `app/services/websocket_manager.py`

### Phase 6: Chat — COMPLETE
- [x] Chat service (GPT + command extraction) — `app/services/chat_service.py`
- [x] WebSocket chat endpoint — `app/api/v1/chat.py`
- [x] Chat frontend page — `frontend/src/pages/Chat.tsx`
- [x] Command execution wiring (all actions: search, approve, prepare, fill, preferences)

### Phase 7: Verification — COMPLETE
- [x] Backend starts (uvicorn): health check returns `{"status":"healthy","version":"0.1.0"}`
- [x] Frontend TypeScript: 0 errors
- [x] Frontend Vite build: ✓ 1637 modules, 240KB gzip bundle
- [x] All dependencies installed (CrewAI 1.9.3, Playwright 1.58, FastAPI 0.128)

---

## Issues Resolved
1. **Python 3.14 incompatible with CrewAI** — Fixed by using Python 3.13.9 venv
2. **setuptools build backend** — Changed from `_legacy:_Backend` to `build_meta`
3. **setuptools package discovery** — Added `[tool.setuptools.packages.find]` config
4. **TypeScript NodeJS namespace** — Changed `NodeJS.Timeout` to `ReturnType<typeof setTimeout>`

---

## How to Run

### Backend
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd frontend
npm run dev
```

### First-Time Setup
1. Start backend + frontend
2. Open http://localhost:5173
3. Upload your DOCX resume on the Dashboard
4. Set job search preferences (titles, locations, remote preference)
5. Click "Start Browser" → log into LinkedIn and Indeed manually
6. Click "Start Job Search" or use the Chat to say "start searching"
7. Review and approve jobs in the Jobs tab
8. Click "Prepare All Docs" in Applications tab
9. Click "Fill Form" for each application
10. Review in the Playwright browser and manually click Submit

---

## File Count Summary
- Backend Python files: ~27
- Frontend TypeScript files: ~12
- Config files: ~8
- Total: ~47 files

---

## 2026-02-05 — RAG Integration & Pipeline Tracking

### New Features Added

#### RAG (Retrieval Augmented Generation) Service
- **File**: `app/services/rag_service.py`
- Loads documents from `/documents` folder (resume, portfolio, etc.)
- Intelligent chunking with section detection
- GPT-powered context extraction for each job application
- Provides relevant portfolio projects and experience for tailoring

#### Pipeline Tracker
- **File**: `app/agents/flows/job_application_flow.py` (updated)
- Added `PipelineTracker` class for recursive job status tracking
- Status flow: `discovered → scored → approved → docs_prepared → form_filled → submitted`
- Methods: `get_pipeline_status()`, `advance_job_status()`, `get_stalled_jobs()`

#### Enhanced Document Generation
- Resume tailor and cover letter writer now accept `additional_context` parameter
- RAG context automatically injected during document preparation
- Portfolio highlights used during job scoring for better matching

### Bug Fixes
1. **Browser context stale state** — BrowserManager now detects closed context and reinitializes
2. **RAG directory path** — Fixed from "document" to "documents"

### Documents Added
- `documents/DetailedResume.docx` — User's detailed resume (88KB)
- `documents/DataBadger Portfolio.docx` — Company portfolio (92KB)

### Testing Status
- [x] Backend starts successfully
- [x] Frontend loads with all pages working
- [x] Resume uploaded and parsed via GPT
- [x] RAG service loads both documents (46 chunks total)
- [x] Browser manager starts Playwright successfully
- [ ] LinkedIn login (user action required)
- [ ] Indeed login (user action required)
- [ ] Full job search flow
- [ ] Document preparation with RAG context
- [ ] Form filling automation
