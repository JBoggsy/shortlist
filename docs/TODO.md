# TODO

## Completed

- [x] Make tool use errors less scary (v0.5.0)
- [x] Improve onboarding intro message (v0.5.0)
- [x] Clarify API key requirements (v0.5.0)
- [x] Simplify API key acquisition — first-time setup wizard with inline how-to guides (v0.6.0)
- [x] Onboarding resumption checks profile — tri-state status in profile frontmatter (v0.7.0)
- [x] User-friendly error notifications — toast system with error classification (v0.7.1)
- [x] Resizable panels — drag-to-resize with localStorage persistence (v0.7.3)
- [x] Direct download links in README and releases
- [x] Integration keys step in setup wizard (Tavily, JSearch)
- [x] Resume uploading and parsing — PDF/DOCX upload with AI agent access (v0.7.0)
- [x] AI resume parsing agent — structured JSON extraction from resumes (v0.7.1)
- [x] Auto-update system — Tauri updater with download progress banner (v0.5.0)
- [x] Dedicated visual interface for job search results (v0.9.0)
- [x] Job search sub-agent for better result coverage (v0.9.0)
- [x] Main agent delegates job searches to specialized sub-agent via `run_job_search` tool (v0.9.0)
- [x] Setup wizard UX polish — connection timer/timeout feedback, stronger integrations scroll cue, Ollama model auto-detection, and live health refresh after setup
- [x] Chat/error UX polish — navigation remains clickable with chat open, and agent failure messaging avoids repeated apologies

## Must-Fix Before Beta

### Backend Error Handling

- [x] Add global Flask error handler, wrap profile routes, protect chat streaming generators, validate jobs POST fields (v0.12.2)

### Input Validation

- [x] Add type and range checks on job fields — centralized `backend/validation.py` with reusable validators; applied to all job, document, and todo routes; DRY'd up agent tool constants (v0.12.1)

### Database Integrity

- [x] Add database migration system (Flask-Migrate/Alembic) with initial baseline and FK cascade migration; auto-detects and upgrades pre-existing databases on startup (v0.12.2)
- [x] Add cascade delete on SearchResult foreign keys, Message FK cascade, SQLite FK enforcement pragma, and ORM relationship for Conversation → SearchResult (v0.12.2)

### Data Safety

- [x] Atomic config file writes, sanitize API keys from log messages (v0.12.3)

## Must-Fix Before Beta (Round 2)

- [x] Database migration recovery from corrupted state — detect version-stamp-with-no-tables and reset before running migrations (v0.12.4)
- [x] **README download links updated to v0.12.1** (v0.12.1)
- [x] **React Error Boundary** — wraps `<Routes>` for graceful fallback on rendering errors (v0.12.4)
- [x] **Setup wizard Ollama model auto-selection** — was picking first model alphabetically (no tool support); now uses ranked `default_model` from providers endpoint (v0.12.4)
- [x] **Ollama preferred model list** — added `qwen3.5`, reordered to avoid vision model false matches (v0.12.4)
- [x] **Playwright E2E test suite fully operational** — all 43 tests pass (39 passed, 4 skipped for missing Anthropic key); fixed timeouts, model auto-detection, onboarding resets, and assertion leniency (v0.12.4)

## Bugs

- [ ] **Outcome Planner over-decomposition** — for requests like "tailor my resume for X job", the OutcomePlanner produces redundant outcomes (e.g. "identify job" + "tailor resume") even though `specialize_resume` already resolves the job internally via `load_job_context()`. Causes unnecessary job search API calls, ~5 min wasted, and a confusing "Jobs Found" panel. Fix: strengthen `PlanOutcomesSig` prompt to avoid decomposition when the target workflow handles resolution internally, or teach the WorkflowMapper to recognize and skip redundant outcomes.
- [x] Skills section wall of text in tailored resumes (v0.12.5)
- [x] Stale `handleKeyDown` in DocumentEditorPage (v0.12.5)

## Features

- [x] Job application preparation (phase 2) — document editor with Tiptap, agent co-editing, version history (v0.11.1)
- [ ] **Interview prep** — agent-assisted interview preparation workflows

## Post-Beta Improvements

- [x] Database indexes on frequently queried columns (v0.12.5)
- [ ] **Search results pagination** — No pagination on search results panel or job list. Fine for beta, needed if users accumulate hundreds of results.
- [ ] **Rate limiting** — No rate limiting on any endpoint. Acceptable for a desktop/local app, needed before any hosted deployment.

## Desktop App

- [ ] **Native OS Integration**
  - System tray icon with quick actions
  - Native notifications for job status changes
  - Native file picker for resume upload
  - OS-specific menu bar integration

- [ ] **Desktop-Specific Features**
  - Offline mode (work without internet, sync later)
  - Multiple workspace/profile support
  - Data import/export (JSON, CSV)
  - Backup and restore functionality
