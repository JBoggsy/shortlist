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

- [ ] **Add database migration system** — The app uses `db.create_all()` which only creates tables that don't exist — it cannot alter existing tables. The moment a future release changes the schema (adds/removes/renames a column), every existing user's database breaks silently. Add Flask-Migrate (Alembic wrapper) with an initial migration before shipping so future schema changes can be applied safely.
- [ ] **Add cascade delete on SearchResult foreign keys** — `backend/models/search_result.py` defines `db.ForeignKey("conversations.id")` and `db.ForeignKey("jobs.id")` without `ondelete="CASCADE"`. Deleting a conversation or job with linked search results will raise an IntegrityError.

### Data Safety

- [ ] **Atomic config file writes** — `backend/config_manager.py` writes `config.json` with plain `open('w')`. Two concurrent Settings saves (possible if user double-clicks or browser retries) can interleave and corrupt the JSON file. Write to a temp file first, then `os.rename()` for atomic replacement.
- [ ] **Sanitize API keys from log messages** — Error paths like `logger.error(f"Failed to create LLM config: {e}")` can include API keys in the exception string if the LLM client embeds them. Sanitize exception messages before logging.

## Bugs

- [ ] **Outcome Planner over-decomposition** — for requests like "tailor my resume for X job", the OutcomePlanner produces redundant outcomes (e.g. "identify job" + "tailor resume") even though `specialize_resume` already resolves the job internally via `load_job_context()`. Causes unnecessary job search API calls, ~5 min wasted, and a confusing "Jobs Found" panel. Fix: strengthen `PlanOutcomesSig` prompt to avoid decomposition when the target workflow handles resolution internally, or teach the WorkflowMapper to recognize and skip redundant outcomes.
- [ ] **Skills section wall of text in tailored resumes** — the specialize_resume pipeline produces a Skills section as a single unformatted paragraph instead of using structured markdown with bold category labels and proper grouping (e.g. `**Languages:** Python, C++`)

## Features

- [x] **Job application preparation (phase 2)** — Document editor with Tiptap, agent co-editing via SSE, version history
- [ ] **Interview prep** — agent-assisted interview preparation workflows

## Post-Beta Improvements

- [ ] **Database indexes** — No indexes on `status`, `conversation_id`, `created_at` columns. Fine for beta volumes (hundreds of jobs), will become a problem at scale.
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
