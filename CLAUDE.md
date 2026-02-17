# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Job application helper — a web app to track and manage job applications. Users can add, edit, and delete job applications and track their status through the hiring pipeline. Includes an LLM-powered AI assistant that can research job postings, scrape URLs, search the web, and automatically add jobs to the database via a chat interface.

## Tech Stack

- **Backend:** Python 3.12+, Flask, Flask-SQLAlchemy, SQLite
- **LLM providers:** Anthropic, OpenAI, Google Gemini, Ollama (configurable via env vars)
- **Agent tools:** Tavily search API, BeautifulSoup web scraping
- **Frontend:** React 19, Vite, Tailwind CSS 4
- **Package management:** uv (Python), npm (JS)

## Key Commands

### Backend
- `uv sync` — install Python dependencies
- `uv run python main.py` — start Flask dev server (port 5000)

### Frontend
- `cd frontend && npm install` — install JS dependencies
- `cd frontend && npm run dev` — start Vite dev server (port 3000)
- `cd frontend && npm run build` — production build (use to verify changes compile)

## Project Structure

### Backend
- `main.py` — entry point, runs Flask server
- `backend/app.py` — Flask app factory (`create_app`)
- `backend/config.py` — app configuration
- `backend/database.py` — SQLAlchemy `db` instance
- `backend/models/job.py` — `Job` model (fields: `id`, `company`, `title`, `url`, `status`, `notes`, `salary_min`, `salary_max`, `location`, `remote_type`, `tags`, `contact_name`, `contact_email`, `applied_date`, `source`, `job_fit`, `created_at`, `updated_at`)
- `backend/routes/jobs.py` — CRUD blueprint (`jobs_bp` at `/api/jobs`)
- `backend/routes/chat.py` — Chat blueprint (`chat_bp` at `/api/chat`) with SSE streaming
- `backend/models/chat.py` — `Conversation` and `Message` models for chat persistence
- `backend/llm/base.py` — `LLMProvider` ABC, `StreamChunk`, `ToolCall` dataclasses
- `backend/llm/anthropic_provider.py` — Anthropic Claude provider
- `backend/llm/openai_provider.py` — OpenAI GPT provider
- `backend/llm/gemini_provider.py` — Google Gemini provider
- `backend/llm/ollama_provider.py` — Ollama local model provider
- `backend/llm/factory.py` — `create_provider()` factory function
- `backend/agent/tools.py` — `AgentTools` class + `TOOL_DEFINITIONS` (web_search, job_search, scrape_url, create_job, list_jobs, read_user_profile, update_user_profile)
- `backend/agent/agent.py` — `Agent` class with iterative tool-calling loop; `OnboardingAgent` for user profile interview; injects user profile into system prompt
- `backend/agent/user_profile.py` — User profile markdown file management with YAML frontmatter (onboarded flag), read/write/onboarding helpers
- `backend/routes/profile.py` — Profile blueprint (`profile_bp` at `/api/profile`)

### Frontend
- `frontend/vite.config.js` — Vite config (React plugin, Tailwind CSS plugin, API proxy)
- `frontend/src/main.jsx` — React entry point
- `frontend/src/index.css` — Tailwind CSS base import
- `frontend/src/App.jsx` — App shell with header, layout, and onboarding auto-start
- `frontend/src/api.js` — API helper (`fetchJobs`, `createJob`, `updateJob`, `deleteJob`, chat functions, `streamMessage`, `fetchProfile`, `updateProfile`, onboarding functions)
- `frontend/src/pages/JobList.jsx` — Main dashboard: job table with status badges, add/edit/delete
- `frontend/src/components/JobForm.jsx` — Reusable form for creating and editing jobs
- `frontend/src/components/ChatPanel.jsx` — Slide-out AI assistant chat panel with SSE streaming
- `frontend/src/components/ProfilePanel.jsx` — Slide-out user profile viewer/editor panel

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/jobs` | List all jobs (newest first) |
| POST | `/api/jobs` | Create job (`company`, `title` required) |
| GET | `/api/jobs/:id` | Get single job |
| PATCH | `/api/jobs/:id` | Update job (partial) |
| DELETE | `/api/jobs/:id` | Delete job |
| GET | `/api/chat/conversations` | List conversations (newest first) |
| POST | `/api/chat/conversations` | Create conversation |
| GET | `/api/chat/conversations/:id` | Get conversation with messages |
| DELETE | `/api/chat/conversations/:id` | Delete conversation |
| POST | `/api/chat/conversations/:id/messages` | Send message, returns SSE stream |
| GET | `/api/profile` | Get user profile markdown content |
| PUT | `/api/profile` | Update user profile markdown content |
| GET | `/api/profile/onboarding-status` | Check if user has been onboarded |
| POST | `/api/profile/onboarding-status` | Set onboarding status |
| POST | `/api/chat/onboarding/conversations` | Create onboarding conversation |
| POST | `/api/chat/onboarding/conversations/:id/messages` | Send onboarding message, returns SSE stream |
| POST | `/api/chat/onboarding/kick` | Start onboarding (agent greeting), returns SSE stream |

Job statuses: `saved`, `applied`, `interviewing`, `offer`, `rejected`
Remote types: `onsite`, `hybrid`, `remote` (or `null`)

Optional job fields: `salary_min` (int), `salary_max` (int), `location` (string), `remote_type` (string), `tags` (comma-separated string), `contact_name` (string), `contact_email` (string), `applied_date` (ISO date string), `source` (string), `job_fit` (int, 0-5 star rating), `requirements` (text, newline-separated), `nice_to_haves` (text, newline-separated)

### LLM Chat Configuration (env vars)
- `LLM_PROVIDER` — provider name: `anthropic` (default), `openai`, `gemini`, `ollama`
- `LLM_API_KEY` — API key for the chosen provider
- `LLM_MODEL` — optional model override (each provider has a sensible default)
- `SEARCH_API_KEY` — Tavily API key for web search tool
- `ADZUNA_APP_ID` — Adzuna API application ID (for job search)
- `ADZUNA_APP_KEY` — Adzuna API application key (for job search)
- `ADZUNA_COUNTRY` — Adzuna country code (default: `us`)
- `JSEARCH_API_KEY` — RapidAPI key for JSearch API (for job search); preferred over Adzuna when both are configured

### Onboarding LLM Configuration (env vars)
- `ONBOARDING_LLM_PROVIDER` — optional, defaults to `LLM_PROVIDER`
- `ONBOARDING_LLM_API_KEY` — optional, defaults to `LLM_API_KEY`
- `ONBOARDING_LLM_MODEL` — optional, defaults to `LLM_MODEL` (use a cheaper model to save costs)

### SSE Event Types (chat streaming)
- `text_delta` — `{"content": "..."}` — incremental text from the LLM
- `tool_start` — `{"id": "...", "name": "...", "arguments": {...}}` — tool execution starting
- `tool_result` — `{"id": "...", "name": "...", "result": {...}}` — tool completed successfully
- `tool_error` — `{"id": "...", "name": "...", "error": "..."}` — tool execution failed
- `done` — `{"content": "full text"}` — agent finished
- `onboarding_complete` — `{}` — onboarding interview finished (only in onboarding flow)
- `error` — `{"message": "..."}` — fatal error

## Conventions

- Backend API routes are prefixed with `/api/`
- Frontend Vite dev server proxies `/api` to Flask at `localhost:5000`
- SQLite database file is `app.db` in the project root (gitignored)
- User profile file is `user_profile.md` in the project root (gitignored, auto-created with default template)
- The AI agent reads the user profile on every turn and injects it into the system prompt
- The agent proactively extracts job-search-relevant info from user messages and updates the profile via the `update_user_profile` tool
- Users can also view and manually edit their profile via the Profile panel in the UI
- User profile uses YAML frontmatter for metadata (`onboarded: true/false`); body is markdown
- On first visit, the app auto-opens the chat in onboarding mode to interview the user and fill their profile
- Onboarding uses a separate LLM config (`ONBOARDING_LLM_*`) so a cheaper model can be used
- Frontend pages live in `frontend/src/pages/`, reusable components in `frontend/src/components/`
- API helper functions in `frontend/src/api.js` — all backend calls go through this module
- **Live job list refresh:** `ChatPanel` has a `JOB_MUTATING_TOOLS` set that tracks which agent tools modify job data (currently `create_job`). When a `tool_result` SSE event fires for one of these tools, the panel calls `onJobsChanged()` which bumps a `jobsVersion` counter in `App`, causing `JobList` to re-fetch. **When adding a new agent tool that creates, updates, or deletes jobs, add its name to `JOB_MUTATING_TOOLS` in `frontend/src/components/ChatPanel.jsx`.**

## Best Practices

### General
- Keep changes focused — one feature or fix per commit
- Run `cd frontend && npm run build` to verify frontend changes compile before committing
- Prefer editing existing files over creating new ones to avoid file bloat

### Backend (Python)
- Follow PEP 8 style conventions
- Use Flask blueprints for new route groups; register them in `backend/app.py`
- Add new models in `backend/models/` and import them in `backend/models/__init__.py`
- Use SQLAlchemy model methods (e.g., `to_dict()`) to serialize responses — keep route handlers thin
- Validate required fields in route handlers before creating/updating records

### Frontend (React/JS)
- Use functional components with hooks (`useState`, `useEffect`)
- Place page-level components in `frontend/src/pages/`, shared UI in `frontend/src/components/`
- All API calls go through `frontend/src/api.js` — never call `fetch` directly in components
- Use Tailwind CSS utility classes for styling — no separate CSS files per component
- Keep components focused: if a component grows beyond ~150 lines, consider extracting subcomponents

## Documentation

After making changes, update this file (`CLAUDE.md`) to reflect:
- New or modified files in the project structure section
- New API endpoints or changes to existing ones
- New commands, dependencies, or conventions
- Any architectural decisions that future contributors should know about

Keeping this file accurate ensures Claude Code (and human developers) can work with the codebase effectively.
