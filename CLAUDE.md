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
- `backend/models/job.py` — `Job` model (fields: `id`, `company`, `title`, `url`, `status`, `notes`, `salary_min`, `salary_max`, `location`, `remote_type`, `tags`, `contact_name`, `contact_email`, `applied_date`, `source`, `created_at`, `updated_at`)
- `backend/routes/jobs.py` — CRUD blueprint (`jobs_bp` at `/api/jobs`)
- `backend/routes/chat.py` — Chat blueprint (`chat_bp` at `/api/chat`) with SSE streaming
- `backend/models/chat.py` — `Conversation` and `Message` models for chat persistence
- `backend/llm/base.py` — `LLMProvider` ABC, `StreamChunk`, `ToolCall` dataclasses
- `backend/llm/anthropic_provider.py` — Anthropic Claude provider
- `backend/llm/openai_provider.py` — OpenAI GPT provider
- `backend/llm/gemini_provider.py` — Google Gemini provider
- `backend/llm/ollama_provider.py` — Ollama local model provider
- `backend/llm/factory.py` — `create_provider()` factory function
- `backend/agent/tools.py` — `AgentTools` class + `TOOL_DEFINITIONS` (search_jobs, scrape_url, create_job, list_jobs)
- `backend/agent/agent.py` — `Agent` class with iterative tool-calling loop

### Frontend
- `frontend/vite.config.js` — Vite config (React plugin, Tailwind CSS plugin, API proxy)
- `frontend/src/main.jsx` — React entry point
- `frontend/src/index.css` — Tailwind CSS base import
- `frontend/src/App.jsx` — App shell with header and layout
- `frontend/src/api.js` — API helper (`fetchJobs`, `createJob`, `updateJob`, `deleteJob`, chat functions, `streamMessage`)
- `frontend/src/pages/JobList.jsx` — Main dashboard: job table with status badges, add/edit/delete
- `frontend/src/components/JobForm.jsx` — Reusable form for creating and editing jobs
- `frontend/src/components/ChatPanel.jsx` — Slide-out AI assistant chat panel with SSE streaming

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

Job statuses: `saved`, `applied`, `interviewing`, `offer`, `rejected`
Remote types: `onsite`, `hybrid`, `remote` (or `null`)

Optional job fields: `salary_min` (int), `salary_max` (int), `location` (string), `remote_type` (string), `tags` (comma-separated string), `contact_name` (string), `contact_email` (string), `applied_date` (ISO date string), `source` (string), `requirements` (text, newline-separated), `nice_to_haves` (text, newline-separated)

### LLM Chat Configuration (env vars)
- `LLM_PROVIDER` — provider name: `anthropic` (default), `openai`, `gemini`, `ollama`
- `LLM_API_KEY` — API key for the chosen provider
- `LLM_MODEL` — optional model override (each provider has a sensible default)
- `SEARCH_API_KEY` — Tavily API key for web search tool

### SSE Event Types (chat streaming)
- `text_delta` — `{"content": "..."}` — incremental text from the LLM
- `tool_start` — `{"id": "...", "name": "...", "arguments": {...}}` — tool execution starting
- `tool_result` — `{"id": "...", "name": "...", "result": {...}}` — tool completed successfully
- `tool_error` — `{"id": "...", "name": "...", "error": "..."}` — tool execution failed
- `done` — `{"content": "full text"}` — agent finished
- `error` — `{"message": "..."}` — fatal error

## Conventions

- Backend API routes are prefixed with `/api/`
- Frontend Vite dev server proxies `/api` to Flask at `localhost:5000`
- SQLite database file is `app.db` in the project root (gitignored)
- Frontend pages live in `frontend/src/pages/`, reusable components in `frontend/src/components/`
- API helper functions in `frontend/src/api.js` — all backend calls go through this module

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
