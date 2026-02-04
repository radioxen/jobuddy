# JobBuddy — Development Diary

## Project Status: IN PROGRESS

---

## 2026-02-04 — Project Kickoff

### Decisions Made
- **Tech Stack**: Python/FastAPI backend, React/Vite/TypeScript frontend
- **AI Framework**: CrewAI (Flows + Crews pattern)
- **LLM**: OpenAI GPT-5.2 (`gpt-5.2-2025-12-11`)
- **Browser Automation**: Playwright with persistent context (headed mode)
- **Database**: SQLite via SQLAlchemy async
- **Resume Processing**: python-docx + docxtpl for DOCX manipulation
- **Real-time**: WebSocket for chat + status updates

### Architecture
- 6 AI agents: Job Searcher, Resume Matcher, Resume Tailor, Cover Letter Writer, Application Filler, Chat Agent
- CrewAI Flow orchestrates the pipeline with human-in-the-loop checkpoints
- Platform-specific form fillers for LinkedIn and Indeed
- Persistent browser sessions (user logs in once)
- Full-control chatbot via WebSocket

---

## Build Log

### Phase 1: Foundation
- [ ] Backend skeleton (FastAPI, config, database)
- [ ] SQLAlchemy models (UserProfile, JobListing, Application, ChatMessage)
- [ ] Pydantic schemas
- [ ] Resume upload + parse endpoint
- [ ] User preferences endpoints
- [ ] Frontend skeleton (React + Vite, routing, Layout)

### Phase 2: Agent Infrastructure
- [ ] CrewAI setup + agent/task YAML configs
- [ ] Search tools (Indeed + LinkedIn via Playwright)
- [ ] Job Search Crew
- [ ] Resume Matcher Crew
- [ ] Jobs API + JobList page

### Phase 3: Document Generation
- [ ] Resume Tailor agent + DOCX generation
- [ ] Cover Letter agent + DOCX generation
- [ ] Download endpoints

### Phase 4: Browser Automation
- [ ] BrowserManager (persistent Playwright context)
- [ ] LinkedIn Easy Apply form filler
- [ ] Indeed form filler
- [ ] Browser control API

### Phase 5: Orchestration
- [ ] JobApplicationFlow (CrewAI Flow)
- [ ] Human-in-the-loop checkpoints
- [ ] WebSocket status updates

### Phase 6: Chat
- [ ] Chat service (GPT + command extraction)
- [ ] WebSocket chat endpoint
- [ ] Chat frontend page
- [ ] Command execution wiring

### Phase 7: Polish
- [ ] Error handling + retry logic
- [ ] Edge cases
- [ ] Testing
