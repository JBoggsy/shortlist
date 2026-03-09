# micro_agents_v1 — TODO

Items are grouped by priority.  "Needs implementing" items are blockers
for correctness; "improvements" items are quality-of-life or
architectural refinements.

---

## Needs Implementing (blockers)

### Stub workflows — `raise NotImplementedError`

These are registered in the workflow registry and will be selected by
the mapper, but immediately crash the pipeline when dispatched.  Until
they exist the executor's top-level `try/except` swallows the error and
returns a generic `error` SSE event, which is confusing for users.

- [x] **`WriteCoverLetterWorkflow`** (`workflows/write_cover_letter.py`) — implemented structured single-shot drafting (job resolution, profile/resume context, outline+narrative, parallel section drafting, unification, polish, and versioned save)

- [x] **`SpecializeResumeWorkflow`** (`workflows/specialize_resume.py`) — implemented structured single-shot specialization (job resolution, job-specific resume fallback, per-section critique + revision, unification pass, claim validation against profile/request, versioned save)

- [x] **`PrepInterviewWorkflow`** (`workflows/prep_interview.py`) — implemented structured parallel prep guide (job resolution, planning analysis, parallel generation of company brief + behavioural questions + technical questions + gap mitigation + interviewer questions, assembly into unified guide with day-of checklist)

### Stub agents — `raise NotImplementedError`

- [x] **`MicroAgentsV1OnboardingAgent`** (`onboarding_agent.py`) — implemented as DSPy `ReAct` module with `OnboardingTurnSig` signature; restricted to profile/resume tools, structured section tracking, `is_complete` output field for completion detection

- [x] **`MicroAgentsV1ResumeParser`** (`resume_parser.py`) — implemented as a 3-stage pipeline: `SectionSegmenter` → three parallel extractors (contact, experience/education, skills) → `ResumeAssembler` with LLM-based skill gap-filling; stages live in `resume_stages/`

---

## Improvements / Refinements

### Critical

- [x] **Update `CLAUDE.md`** — updated to reflect the `resume_stages/` pipeline implementation.

- [x] **Flush `_pending_events` during streaming** — `agent.py` now yields and clears `_pending_events` after the executor returns, so `search_result_added` events reach the UI.

- [x] **Graceful fallback for `NotImplementedError` in workflows** — executor now catches `NotImplementedError` per-workflow and returns a clean `WorkflowResult(success=False)` instead of crashing the pipeline.

- [x] **Clear `_pending_events` on error in `OnboardingAgent`** — added `finally: self._pending_events.clear()` in `run()`.

- [x] **Resume parser should degrade gracefully on partial extractor failure** — each extractor failure is now caught and logged; empty fallback output is used so the other extractors' results are preserved.

- [x] **`ValidateClaimsSig` receives a truncated resume as its source of truth** — added `_load_full_user_context()` that returns un-truncated resume; validation step now uses it instead of the truncated `user_context`.

- [x] **Parsed resume JSON fed to plain-text section parser** — added `_parsed_resume_to_text()` that converts parsed resume dict to structured plain text with section headings; `_load_resume_text()` now uses it instead of `json.dumps()`.

### Architecture

- [x] **`MicroAgentsV1Agent` is not a `dspy.Module`** — Added combined `_AgentModuleMeta` metaclass to `base.py` enabling dual ABC + `dspy.Module` inheritance; all three top-level agents now call `dspy.Module.__init__()` and expose sub-modules via `named_sub_modules()` / `named_parameters()`

- [x] **Pass workflow descriptions to `WorkflowMapper`** — mapper now receives JSON with `name`, `description`, and `outputs` fields via `available_workflows_with_metadata()`; each workflow class declares an `OUTPUTS` dict; output schemas also surfaced in `DeferredParamExtractor` context and `ResultCollator` result formatting

- [x] **Pass conversation context to workflows** — `agent.py` now injects the last 10 messages as `conversation_context` into each workflow assignment's `params` dict before dispatch, enabling `JobResolver` and `SearchResultResolver` to handle relative references.

- [x] **Extract shared `_load_job_context` / `_load_user_context` helpers** — extracted `load_job_context()` and `load_user_context()` free functions into `_dspy_utils.py`; replaced per-workflow copies in `write_cover_letter.py`, `specialize_resume.py`, `prep_interview.py`, and `edit_cover_letter.py`; fixed `edit_cover_letter.py` missing `int(job_id)` error handling and hardcoded constants; `_load_full_user_context()` replaced with `load_user_context(tools, max_chars=None)`.

- [x] **Deduplicate `ResumeSection` model** — `ResumeSection(title, content)` is now the shared base in `section_segmenter.py`; `SegmentedResumeSection` extends it with `section_type` + `heading` (auto-populates `title` from `heading`); `specialize_resume.py` imports from `resume_stages` instead of defining its own copy.

- [x] **Add `try/except ValueError` around `int(job_id)` casts** — all three `_load_job_context()` implementations now catch `ValueError`/`TypeError` and fall through to resolver-based lookup.

- [x] **Replace magic numbers with named constants** — `_RESUME_CONTEXT_MAX_CHARS = 3000` and `_JOB_RESOLVER_MIN_CONFIDENCE = 0.3` defined at module level in each workflow file.

- [x] **Fix `Optional` type hint on `ResumeAssembler.__init__`** — updated to `Optional["LLMConfig"] = None`.

- [x] **Remove unused imports from workflow files** — removed `json` from `onboarding_agent.py`; removed `AgentTools` from `write_cover_letter.py`, `specialize_resume.py`, and `prep_interview.py`.

- [x] **Remove dead-code double-guard in `WriteCoverLetterWorkflow`** — removed the unreachable `if not sections:` check.

### User experience

- [x] **Suppress verbose pipeline internals from chat output** — replaced "Planning approach…" / raw outcome list / "Mapping to workflows…" / full `WorkflowAssignment` dumps / "Summarising results…" with a single "Thinking…" indicator; detailed output moved to `logger.debug()`; executor now shows concise step labels ("Step 1/3: …") instead of workflow names and params.

- [x] **`GeneralWorkflow` is a black box** — `build_dspy_tools` now accepts an optional `event_queue` to emit `tool_start`/`tool_result` SSE events; `run_dspy_module_streaming()` helper runs the DSPy module in a background thread while draining events in real-time. Applied to all three ReAct call sites: `GeneralWorkflow`, `PrepInterviewWorkflow` company brief (with parallel event draining), and `MicroAgentsV1OnboardingAgent`.

- [x] **`PrepInterviewWorkflow` company brief now uses live web research** — replaced `ChainOfThought(CompanyBriefSig)` with a `dspy.ReAct` module that has access to `web_search` and `scrape_url` tools; the brief is now grounded in current web data rather than LLM training data alone.

- [x] **Narrow `_PLACEHOLDER_RE` misses many real unfilled profile sections** — defined canonical `SECTION_PLACEHOLDER` constant and `is_section_unfilled()` helper in `user_profile.py`; standardised `DEFAULT_PROFILE_TEMPLATE` to use the same placeholder for all sections; `onboarding_agent.py` now uses the helper instead of a regex; legacy placeholders from older templates are still recognised.

- [x] **Result collation doesn't stream token-by-token** — replaced DSPy `ChainOfThought` with `litellm.completion(stream=True)` so the final response streams token-by-token via SSE `text_delta` events.

### Performance / correctness

- [x] **Cache `list_jobs` within a pipeline run** — added `_CachedTools` proxy in `workflow_executor.py` that caches `list_jobs`, `read_user_profile`, and `read_resume` results per pipeline run; automatically invalidates on mutating tool calls.

- [x] **Verify thread safety of `dspy.context` in parallel analysis** — confirmed safe: `dspy.context()` uses `contextvars.ContextVar` (`thread_local_overrides`) which is inherently thread-safe. Each thread gets its own copy of the context overrides.

- [x] **Harden `build_dspy_tools` kwargs-unwrap heuristic** — now checks whether the tool has a genuine `kwargs` parameter before unwrapping; also verifies the value is a `dict` to avoid false positives.
