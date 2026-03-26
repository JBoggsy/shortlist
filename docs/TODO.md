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

## Bugs

- [ ] **Outcome Planner over-decomposition** — for requests like "tailor my resume for X job", the OutcomePlanner produces redundant outcomes (e.g. "identify job" + "tailor resume") even though `specialize_resume` already resolves the job internally via `load_job_context()`. Causes unnecessary job search API calls, ~5 min wasted, and a confusing "Jobs Found" panel. Fix: strengthen `PlanOutcomesSig` prompt to avoid decomposition when the target workflow handles resolution internally, or teach the WorkflowMapper to recognize and skip redundant outcomes.
- [ ] **Skills section wall of text in tailored resumes** — the specialize_resume pipeline produces a Skills section as a single unformatted paragraph instead of using structured markdown with bold category labels and proper grouping (e.g. `**Languages:** Python, C++`)

## UX Improvements

- [ ] **Test Connection needs timeout feedback** — testing a large Ollama model shows only "Testing..." with no spinner, elapsed timer, or timeout for 45+ seconds; users may think the app is frozen. Add an elapsed time counter or a "this may take a while for large models" note.
- [ ] **Setup wizard scroll indicator too subtle** — step 4 (integrations) has scrollable content with Tavily and RapidAPI sections, but the scroll indicator is a tiny triangle at the edge; users may miss the RapidAPI section entirely. Consider a more prominent scroll cue or auto-scroll hint.
- [ ] **"AI Assistant not configured" banner stale behind wizard** — the yellow warning banner stays visible behind the setup wizard modal and doesn't refresh after config is saved until the page reloads. Dashboard should re-fetch health status after the wizard completes.
- [ ] **Chat panel backdrop blocks navigation bar** — when the chat panel is open, a semi-transparent overlay blocks clicks on the navigation bar; users must close chat to navigate to another page. Consider allowing nav clicks through the overlay, or narrowing the overlay to only cover the main content area.
- [ ] **Setup wizard Ollama instructions reference unavailable model** — step 3 tells users to "Run `ollama pull llama3.2`" but the default model may not be installed; users with other models must discover the "Advanced: model override" dropdown themselves. Consider auto-selecting the first available model or highlighting the dropdown when the default model is missing.
- [ ] **Agent apologizes multiple times on parallel tool call failure** — when parallel tool calls fail and retry, the agent emits multiple apology messages in rapid succession ("You're absolutely right, I apologize..."), giving an unprofessional impression. This is a symptom of #1 but could also be mitigated with prompt tuning to avoid repetitive apologies.

## Features

- [x] **Job application preparation (phase 2)** — Document editor with Tiptap, agent co-editing via SSE, version history
- [ ] **Interview prep** — agent-assisted interview preparation workflows

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
