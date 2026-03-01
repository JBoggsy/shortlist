# Fixed Pipeline Agent Design

A programmatic pipeline architecture that replaces the monolithic ReAct loop
with **structured routing + micro-agents**. Instead of giving a single LLM
free-form access to all tools and hoping it reasons its way to the right
sequence of actions, the orchestrator classifies user intent, extracts
structured parameters, and then executes a **deterministic pipeline** for
each request type — invoking small, focused LLM calls ("micro-agents") only
at the specific steps that genuinely require natural-language reasoning.

---

## Why This Design?

The `default` monolithic ReAct agent works but has structural weaknesses:

| Problem | Root Cause | Orchestrator Fix |
|---|---|---|
| Slow multi-step tasks | LLM reasons about what to do next on every iteration | Programmatic pipeline knows the plan; LLM only runs where needed |
| Unpredictable tool sequences | LLM may call tools in a suboptimal order or skip steps | Pipeline enforces correct ordering |
| Expensive | Every reasoning step is a full LLM call with all tools bound | Micro-agents are scoped calls with minimal context |
| Hard to debug | One opaque loop does everything | Each pipeline step has clear inputs/outputs |
| Inconsistent quality | LLM may forget to evaluate fit, resolve URLs, etc. | Pipeline guarantees each step runs |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         User Message                                │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                    ┌────────────▼─────────────┐
                    │      Routing Agent        │
                    │  (single LLM call)        │
                    │                           │
                    │  Extracts:                │
                    │   • request_type (enum)   │
                    │   • params (structured)   │
                    │   • entity_refs (IDs,     │
                    │     names, URLs)          │
                    └────────────┬─────────────┘
                                 │
                    ┌────────────▼─────────────┐
                    │   Pipeline Dispatcher     │
                    │   (pure Python switch)    │
                    └──┬────┬────┬────┬────┬───┘
                       │    │    │    │    │
              ┌────────┘    │    │    │    └────────┐
              ▼             ▼    ▼    ▼             ▼
         FIND_JOBS    RESEARCH  CRUD  PREPARE   GENERAL
         pipeline     pipeline  exec  pipeline  pipeline
              │             │    │    │             │
              ▼             ▼    ▼    ▼             ▼
         (steps with     (steps)  (DB  (steps)  (single
          micro-agents)          ops)            micro-agent)
```

### Core Principles

1. **Classify once, execute deterministically.** The Routing Agent is the only
   "creative" LLM call at the top level. After that, the pipeline for each
   request type is a fixed sequence of steps.

2. **Micro-agents are scoped.** Each micro-agent gets only the context it
   needs (not the entire tool set) and produces structured output validated
   by a Pydantic schema. This makes them cheaper, faster, and more reliable.

3. **Programmatic steps don't need LLMs.** Database queries, API calls, data
   filtering, and response formatting are pure Python. The LLM is only
   invoked for tasks that require natural-language understanding or generation.

4. **SSE streaming is preserved.** The pipeline yields the same SSE event
   dicts as the default design (`text_delta`, `tool_start`, `tool_result`,
   `done`, etc.) so the frontend works without changes.

5. **Tools are reused.** The existing `AgentTools` class from
   `backend/agent/tools/` is used for all DB and API operations. Micro-agents
   do NOT get direct tool access — the pipeline calls tools programmatically
   and passes results to micro-agents as context.

---

## Request Types

The Routing Agent classifies every user message into one of these types:

| Type | Description | Example |
|---|---|---|
| `find_jobs` | Search for jobs matching criteria | "Find remote React jobs paying $150k+" |
| `research_url` | Analyze a specific URL (job posting, company page) | "Tell me about this job: https://..." |
| `track_crud` | Create, edit, or delete a job in the tracker | "Add the Stripe job" / "Update Google to interviewing" |
| `query_jobs` | Read/filter/summarize tracked jobs | "What jobs am I interviewing for?" |
| `todo_mgmt` | Create, toggle, or list application todos | "Create a checklist for the Stripe app" |
| `profile_mgmt` | Read or update the user profile | "Add React to my skills" |
| `prepare` | Interview prep, cover letters, resume tailoring | "Help me prepare for the Google interview" |
| `compare` | Compare or rank multiple jobs | "Compare the Google and Meta offers" |
| `research` | General research (company, salary, industry) | "Research Stripe's engineering culture" |
| `general` | Career advice, app help, open-ended questions | "How should I negotiate this offer?" |
| `multi_step` | User request that chains 2+ of the above | "Find jobs, add the top 3, and create todos" |

---

## Routing Agent

A single LLM call with a structured-output schema. No tools bound.

### Input
- System prompt: routing instructions + brief summary of each request type
- User message (+ last ~3 messages of conversation history for context)

### Output (Pydantic schema)

```python
class RoutingResult(BaseModel):
    """Structured output from the Routing Agent."""
    request_type: Literal[
        "find_jobs", "research_url", "track_crud", "query_jobs",
        "todo_mgmt", "profile_mgmt", "prepare", "compare",
        "research", "general", "multi_step",
    ]
    params: dict          # Type-specific parameters (see per-pipeline schemas)
    entity_refs: list[str]  # Job names, IDs, URLs referenced by the user
    acknowledgment: str   # Brief message acknowledging the user's request
```

The `acknowledgment` field is immediately streamed as `text_delta` so the user
sees feedback before the pipeline starts executing.

### Structured Output and Fallback Strategy

The Routing Agent asks the LLM to produce JSON matching the `RoutingResult`
schema. The implementation should:

1. **Prefer native structured output** — Use LangChain's
   `model.with_structured_output(RoutingResult)` which maps to the provider's
   native JSON/function-calling mode (OpenAI JSON mode, Anthropic tool_use,
   etc.).
2. **Fallback to JSON-in-text** — If the model doesn't support structured
   output, include the schema in the system prompt and parse the JSON from
   the response text.
3. **Validate with Pydantic** — All micro-agent outputs are validated through
   Pydantic models. If validation fails, retry once with the error message
   appended, then fall back to the `general` pipeline (which is a single
   unconstrained LLM call, equivalent to the old ReAct agent with no tools).

---

## Pipeline Definitions

Each pipeline is a sequence of **steps**. Steps are either:

- **Programmatic** — pure Python (DB query, API call, data transform, template)
- **Micro-agent** — a scoped LLM call with a specific prompt and output schema

### Key: Reading Pipeline Diagrams

```
[step name]          — programmatic step (no LLM)
«Micro-Agent Name»   — LLM-powered step
──►                  — data flow
~~►                  — optional/conditional
```

---

### Pipeline 1: `find_jobs`

Find jobs matching user-specified criteria via job board APIs.

**Params schema:**
```python
class FindJobsParams(BaseModel):
    query: str                          # Core search terms
    location: str | None = None         # City, state, region
    remote_type: str | None = None      # "remote", "hybrid", "onsite"
    salary_min: int | None = None       # Minimum salary
    salary_max: int | None = None       # Maximum salary
    company_type: str | None = None     # "startup", "enterprise", etc.
    employment_type: str | None = None  # "fulltime", "contract", etc.
    date_posted: str | None = None      # "today", "3days", "week", "month"
    num_results: int = 10               # Desired number of results
```

**Steps:**

```
[load user profile + resume summary]
    │
    ▼
«Query Generator Agent»
    Input:  FindJobsParams + user profile summary
    Output: list[JobSearchInput] (1-3 query variations)
    │
    ▼
[execute job_search() for each query]  ──► raw API results
    │
    ▼
[deduplicate results by URL / company+title]
    │
    ▼
«Evaluator Agent»
    Input:  deduplicated results + user profile + resume
    Output: list[EvaluatedJob] with job_fit (0-5) + fit_reason
    │
    ▼
[filter: keep jobs with job_fit >= 3]
    │
    ▼
[for each passing job:]
    ├──► «Detail Extraction Agent» (if description is sparse)
    │       Input:  raw job data
    │       Output: structured fields (requirements, nice_to_haves, etc.)
    │
    ├──► [attempt first-party URL resolution]
    │       [scrape_url on third-party link]
    │       ~~► «URL Extractor Agent» if scraping finds employer link
    │
    └──► [call add_search_result() — emits SSE event]
    │
    ▼
«Results Summary Agent»
    Input:  all added results + search params
    Output: narrative summary for the user
    │
    ▼
[stream summary as text_delta, yield done]
```

**Micro-agents in this pipeline:**

| Agent | Input | Output Schema | Purpose |
|---|---|---|---|
| Query Generator | search params + profile | `list[JobSearchInput]` | Generate optimized API queries |
| Evaluator | job results + profile | `list[EvaluatedJob]` | Rate fit 0-5 with reasons |
| Detail Extraction | raw job data | `JobDetails` | Extract structured fields from sparse listings |
| URL Extractor | scraped page text | `{url: str}` | Find first-party URL in page content |
| Results Summary | final results + params | `str` (free text) | Narrate findings for the user |

---

### Pipeline 2: `research_url`

Analyze a URL provided by the user (job posting, company page, etc.).

**Params schema:**
```python
class ResearchUrlParams(BaseModel):
    url: str                            # The URL to research
    intent: str = "analyze"             # "analyze", "add_to_tracker", "compare_to_profile"
```

**Steps:**

```
[scrape_url(url)]  ──► raw page content
    │
    ▼
«Detail Extraction Agent»
    Input:  raw page content + URL
    Output: JobDetails (company, title, salary, requirements, etc.)
    │
    ▼
[load user profile + resume]
    │
    ▼
«Fit Evaluator Agent»
    Input:  extracted details + profile + resume
    Output: {job_fit: int, fit_reason: str, strengths: list, gaps: list}
    │
    ▼
[if intent includes adding to tracker:]
    ├──► [create_job() with extracted fields + fit score]
    └──► [emit tool_start/tool_result SSE events]
    │
    ▼
«Analysis Summary Agent»
    Input:  extracted details + fit evaluation
    Output: narrative analysis for the user
    │
    ▼
[stream summary, yield done]
```

---

### Pipeline 3: `track_crud`

Create, update, or delete jobs in the tracker. Mostly programmatic.

**Params schema:**
```python
class TrackCrudParams(BaseModel):
    action: Literal["create", "edit", "delete"]
    job_ref: str | None = None          # Job reference (name, ID, "the Google job")
    job_id: int | None = None           # Resolved job ID (if directly specified)
    fields: dict = {}                   # Fields to set/update
```

**Steps:**

```
[resolve entity: job_ref → job_id]
    │ If ambiguous (multiple matches):
    │   ~~► ask user to clarify (yield text_delta with options)
    │   ~~► (this ends the pipeline; user's next message re-enters routing)
    │
    ▼
[validate fields against Job model]
    │
    ▼
[execute tool:]
    ├── action="create" → create_job(fields)
    ├── action="edit"   → edit_job(job_id, fields)
    └── action="delete" → remove_job(job_id)
    │
    ▼
[emit tool_start + tool_result SSE events]
    │
    ▼
[template confirmation message]
    "Added [title] at [company] to your tracker."
    "Updated [company] [title]: status → interviewing."
    "Removed [company] [title] from your tracker."
    │
    ▼
[stream confirmation, yield done]
```

No micro-agents needed for straightforward CRUD. If the user's fields are
expressed in natural language that needs interpretation (e.g., "set the salary
to about 180" → `salary_min: 170000, salary_max: 190000`), the Routing Agent
handles that extraction in the `params.fields` output.

---

### Pipeline 4: `query_jobs`

Query, filter, and summarize tracked jobs.

**Params schema:**
```python
class QueryJobsParams(BaseModel):
    filters: dict = {}                  # {status: ..., company: ..., title: ...}
    question: str | None = None         # Natural-language question about jobs
    format: Literal["list", "summary", "count"] = "list"
```

**Steps:**

```
[execute list_jobs(filters)]  ──► job records
    │
    ▼
[check: is this a simple listing or a complex question?]
    │
    ├── Simple (list/count with basic filters):
    │       [format results as table/list/count using template]
    │       [stream response, yield done]
    │
    └── Complex (needs analysis — "best fit", "recommend", ranking):
            │
            ▼
        [load user profile]
            │
            ▼
        «Analysis Agent»
            Input:  job records + profile + question
            Output: narrative analysis
            │
            ▼
        [stream analysis, yield done]
```

---

### Pipeline 5: `todo_mgmt`

Manage application todos — list, create, toggle, generate.

**Params schema:**
```python
class TodoMgmtParams(BaseModel):
    action: Literal["list", "toggle", "create", "generate", "delete"]
    job_ref: str | None = None
    job_id: int | None = None
    todo_id: int | None = None
    todo_data: dict = {}                 # {title, category, description, completed}
```

**Steps:**

```
[resolve job_ref → job_id]
    │
    ▼
[branch by action:]
    │
    ├── "list":
    │       [list_job_todos(job_id)]
    │       [format as checklist, stream, done]
    │
    ├── "toggle":
    │       [edit_job_todo(job_id, todo_id, completed=True/False)]
    │       [confirm: "Marked '[title]' as done."]
    │
    ├── "create":
    │       [add_job_todo(job_id, todo_data)]
    │       [confirm: "Added todo: '[title]'"]
    │
    ├── "delete":
    │       [remove_job_todo(job_id, todo_id)]
    │       [confirm: "Removed todo: '[title]'"]
    │
    └── "generate":
            │
            ▼
        [load job record + requirements]
        [load user profile + resume]
            │
            ▼
        «Todo Generator Agent»
            Input:  job details + profile + resume
            Output: list[{title, category, description}]
            │
            ▼
        [add_job_todo() × N]
        [confirm: "Created N prep tasks for your [company] application."]
```

---

### Pipeline 6: `profile_mgmt`

Read or update the user profile.

**Params schema:**
```python
class ProfileMgmtParams(BaseModel):
    action: Literal["read", "update"]
    section: str | None = None          # Specific section to update
    content: str | None = None          # New content (if simple update)
    natural_update: str | None = None   # Free-text update needing interpretation
```

**Steps:**

```
[branch by action:]
    │
    ├── "read":
    │       [read_user_profile()]
    │       [format and present]
    │
    └── "update":
            │
            ▼
        [is this a simple section update or a complex natural-language one?]
            │
            ├── Simple (section + content both clear):
            │       [update_user_profile(section, content)]
            │       [confirm: "Updated your [section]."]
            │
            └── Complex (needs interpretation):
                    │
                    ▼
                [read_user_profile() — get current state]
                    │
                    ▼
                «Profile Update Agent»
                    Input:  current profile + user's natural-language update
                    Output: list[{section: str, content: str}] — sections to update
                    │
                    ▼
                [update_user_profile(section, content) × N]
                [confirm: "Updated [sections]."]
```

---

### Pipeline 7: `prepare`

Help the user prepare for a job application (interview prep, cover letter,
resume tailoring, question prep).

**Params schema:**
```python
class PrepareParams(BaseModel):
    prep_type: Literal["interview", "cover_letter", "resume_tailor", "questions", "general"]
    job_ref: str | None = None
    job_id: int | None = None
    specifics: str | None = None         # Additional context from the user
```

**Steps:**

```
[resolve job_ref → job_id → full Job record]
    │
    ▼
[gather context (parallel):]
    ├── Job record (details, requirements, nice_to_haves)
    ├── User profile (read_user_profile)
    ├── Resume (read_resume)
    └── Existing todos (list_job_todos)
    │
    ▼
[branch by prep_type:]
    │
    ├── "interview":
    │       «Interview Prep Agent»
    │           Input:  job + profile + resume + specifics
    │           Output: talk tracks, STAR stories, company research, tips
    │
    ├── "cover_letter":
    │       «Cover Letter Agent»
    │           Input:  job + profile + resume + specifics
    │           Output: formatted cover letter draft
    │
    ├── "resume_tailor":
    │       «Resume Tailor Agent»
    │           Input:  resume + job requirements + profile
    │           Output: list of suggested edits / emphasis changes
    │
    ├── "questions":
    │       «Question Generator Agent»
    │           Input:  job + company + role level
    │           Output: likely questions + answer frameworks
    │
    └── "general":
            «General Prep Agent»
                Input:  job + profile + resume + specifics
                Output: holistic preparation advice
    │
    ▼
[optionally generate todos from prep output:]
    ~~► add_job_todo() for each actionable prep step
    │
    ▼
[stream prep content, yield done]
```

---

### Pipeline 8: `compare`

Compare or rank multiple jobs.

**Params schema:**
```python
class CompareParams(BaseModel):
    job_refs: list[str]                  # References to jobs to compare
    job_ids: list[int] = []              # Resolved IDs
    dimensions: list[str] = []           # What to compare on (salary, fit, remote, etc.)
    mode: Literal["compare", "rank", "pros_cons"] = "compare"
```

**Steps:**

```
[resolve all job_refs → job_ids → Job records]
    │
    ▼
[load user profile]
    │
    ▼
[branch by mode:]
    │
    ├── "compare" (2+ specific jobs):
    │       «Comparison Agent»
    │           Input:  job records + profile + dimensions
    │           Output: side-by-side analysis
    │
    ├── "rank" (sort a set of jobs by criteria):
    │       «Ranking Agent»
    │           Input:  job records + profile + criteria
    │           Output: ordered list with scores + explanations
    │
    └── "pros_cons" (deep dive on 1 job):
            «Analysis Agent»
                Input:  job record + profile + resume
                Output: strengths, weaknesses, overall recommendation
    │
    ▼
[optionally update job_fit ratings on the records:]
    ~~► edit_job(job_id, job_fit=score) for each
    │
    ▼
[stream analysis, yield done]
```

---

### Pipeline 9: `research`

General research — company culture, salary data, interview processes, industry.

**Params schema:**
```python
class ResearchParams(BaseModel):
    topic: str                           # What to research
    research_type: Literal["company", "salary", "interview_process", "industry", "general"]
    company: str | None = None           # Specific company (if applicable)
    role: str | None = None              # Specific role (if applicable)
```

**Steps:**

```
«Query Generator Agent»
    Input:  research params
    Output: list[str] — 2-4 search queries
    │
    ▼
[execute web_search() and/or web_research() for each query]
    │
    ▼
[collect results]
    │
    ▼
«Research Synthesizer Agent»
    Input:  search results + original topic + user profile
    Output: narrative report with citations
    │
    ▼
[stream report, yield done]
```

---

### Pipeline 10: `general`

Catch-all for career advice, app guidance, and open-ended questions.

**Params schema:**
```python
class GeneralParams(BaseModel):
    question: str                        # The user's question
    needs_job_context: bool = False      # Whether to load job data
    needs_profile: bool = False          # Whether to load profile
    job_ref: str | None = None           # Referenced job (if any)
```

**Steps:**

```
[conditionally gather context:]
    ├── needs_job_context? → list_jobs() and/or resolve job_ref
    ├── needs_profile? → read_user_profile()
    └── (always available: conversation history)
    │
    ▼
«Advisor Agent»
    Input:  question + gathered context + conversation history
    Output: free-text advice
    │
    ▼
[stream response, yield done]
```

This is the **fallback pipeline** — it's essentially a single scoped LLM call
with relevant context. If routing fails or the request doesn't fit any
specific pipeline, it lands here.

---

### Pipeline 11: `multi_step`

Composite requests that chain multiple pipelines.

**Params schema:**
```python
class MultiStepParams(BaseModel):
    steps: list[dict]                    # Each dict has {type: str, params: dict}
    # Steps are referenced by their pipeline types above
```

**Steps:**

```
[build execution plan from steps list]
    │
    ▼
[for each step:]
    ├── [stream progress: "Step 1/3: Searching for jobs..."]
    ├── [execute sub-pipeline (reuses the other pipelines above)]
    ├── [capture outputs for downstream steps]
    │       (e.g., step 2 can reference "jobs found in step 1")
    └── [stream step completion: "Found 12 jobs, added top 3."]
    │
    ▼
[stream final summary encompassing all steps, yield done]
```

---

## Micro-Agent Inventory

Each micro-agent is a **single LLM call** with:
- A focused system prompt
- Structured input (passed as user message or context)
- Structured output validated by Pydantic (where applicable)
- No tool bindings (tools are called programmatically by the pipeline)

| Micro-Agent | Used By Pipelines | Input | Output |
|---|---|---|---|
| **Routing Agent** | (top-level) | user message + recent history | `RoutingResult` |
| **Query Generator** | find_jobs, research | search params + profile | `list[query strings]` |
| **Evaluator** | find_jobs | job results + profile | `list[EvaluatedJob]` with 0-5 fit |
| **Detail Extraction** | find_jobs, research_url | raw job data or page text | `JobDetails` structured fields |
| **URL Extractor** | find_jobs, research_url | scraped page text | `{url: str}` |
| **Results Summary** | find_jobs | final results + params | free text summary |
| **Fit Evaluator** | research_url, compare | job details + profile | fit score + strengths/gaps |
| **Analysis Summary** | research_url | extracted details + fit | free text analysis |
| **Analysis** | query_jobs, compare | jobs + profile + question | free text analysis |
| **Profile Update** | profile_mgmt | current profile + update text | `list[{section, content}]` |
| **Todo Generator** | todo_mgmt, prepare | job + profile + resume | `list[{title, category, desc}]` |
| **Interview Prep** | prepare | job + profile + resume | talk tracks, stories, tips |
| **Cover Letter** | prepare | job + profile + resume | formatted draft |
| **Resume Tailor** | prepare | resume + job reqs | suggested edits |
| **Question Generator** | prepare | job + company + level | questions + answer frameworks |
| **Comparison** | compare | jobs + profile + dimensions | side-by-side analysis |
| **Ranking** | compare | jobs + profile + criteria | ordered scored list |
| **Research Synthesizer** | research | search results + topic | narrative report w/ citations |
| **Advisor** | general | question + context | free text advice |

---

## SSE Streaming Strategy

The frontend expects the same SSE events as the default agent. The orchestrator
produces them as follows:

| SSE Event | When Emitted |
|---|---|
| `text_delta` | Routing acknowledgment; progress updates between steps; micro-agent text streamed incrementally |
| `tool_start` | Before executing any programmatic tool call (e.g., `job_search`, `create_job`) |
| `tool_result` | After a programmatic tool call completes |
| `tool_error` | If a tool call fails |
| `search_result_added` | When `add_search_result()` is called (same as default) |
| `done` | Pipeline complete — includes full accumulated text |
| `error` | Fatal pipeline error |

Micro-agents that produce long-form text (summaries, cover letters, prep
content) should be **streamed** — the pipeline uses `model.stream()` and
yields `text_delta` events as chunks arrive. Micro-agents that produce
structured output (routing, evaluation, query generation) use non-streaming
`model.invoke()` since their output must be parsed as a whole.

---

## Entity Resolution

Many pipelines need to resolve natural-language job references ("the Google
job", "my Stripe application", "job #5") to a `job_id`. This is a shared
utility, not a micro-agent:

```python
def resolve_job_ref(ref: str) -> Job | list[Job] | None:
    """Resolve a natural-language job reference to a Job record.

    Strategy:
    1. If ref is a plain integer or "#N", look up by ID.
    2. Otherwise, list_jobs(company=ref) and list_jobs(title=ref).
    3. If exactly 1 match, return it.
    4. If multiple matches, return all (caller decides: ask user or pick best).
    5. If no matches, return None.
    """
```

---

## Profile Context Loading

Several pipelines need the user profile and/or resume. To avoid redundant
reads within a single request, context is loaded once and passed through:

```python
@dataclass
class RequestContext:
    """Shared context loaded once per user request."""
    profile: str | None = None           # Raw profile markdown
    resume: dict | None = None           # Parsed resume JSON
    jobs: list[dict] | None = None       # Cached job list (if needed)

    def ensure_profile(self):
        if self.profile is None:
            self.profile = read_user_profile()["content"]

    def ensure_resume(self):
        if self.resume is None:
            self.resume = read_resume()  # may return {"error": ...}

    def ensure_jobs(self, **filters):
        if self.jobs is None:
            self.jobs = list_jobs(**filters)["jobs"]
```

---

## Proactive Profile Updates

The default agent has a rule to proactively update the user's profile when
they mention job-search-relevant information. In the orchestrator design,
this is handled as a **post-processing step** after the main pipeline
completes:

```
[main pipeline completes]
    │
    ▼
[scan user message for profile-relevant info]
    │ (lightweight keyword/pattern check, not an LLM call)
    │
    ▼ if detected:
«Profile Update Agent»
    Input:  user message + current profile
    Output: section updates (if any)
    │
    ▼
[apply updates silently — no SSE events for this]
```

This runs at the end so it doesn't delay the main response.

---

## Error Handling & Fallback

1. **Routing failure** — If the Routing Agent returns an invalid type or
   fails to parse, fall back to the `general` pipeline.

2. **Micro-agent failure** — If a micro-agent call fails (timeout, invalid
   output, rate limit), the pipeline:
   - Retries once with the error context appended
   - If still failing, skips that step and continues with degraded output
   - Reports the issue in the final summary

3. **Tool failure** — Same as the default agent: the error is captured in
   `tool_error` SSE events and the pipeline continues if possible.

4. **Full fallback** — If the pipeline dispatcher itself encounters an
   unrecoverable error, the orchestrator falls back to a single monolithic
   LLM call (equivalent to the `general` pipeline) to at least give the
   user some response.

---

## File Structure

```
backend/agent/orchestrator/
    __init__.py              # Exports OrchestratorAgent, OrchestratorOnboardingAgent,
    │                        #   OrchestratorResumeParser
    DESIGN.md                # This document
    │
    # ── Core machinery ──
    routing.py               # Routing Agent — classify + extract params
    dispatcher.py            # Pipeline dispatcher — routes type → pipeline fn
    context.py               # RequestContext — shared profile/resume/jobs cache
    entity_resolution.py     # resolve_job_ref() utility
    streaming.py             # SSE event helpers (yield_text, yield_tool, etc.)
    │
    # ── Pipelines ──
    pipelines/
        __init__.py
        find_jobs.py         # find_jobs pipeline
        research_url.py      # research_url pipeline
        track_crud.py        # track_crud pipeline (mostly programmatic)
        query_jobs.py        # query_jobs pipeline
        todo_mgmt.py         # todo_mgmt pipeline
        profile_mgmt.py      # profile_mgmt pipeline
        prepare.py           # prepare pipeline
        compare.py           # compare pipeline
        research.py          # research pipeline
        general.py           # general/fallback pipeline
        multi_step.py        # multi_step orchestrator
    │
    # ── Micro-agents ──
    micro_agents/
        __init__.py
        base.py              # BaseMicroAgent — shared invoke/stream helpers
        routing_agent.py     # Routing micro-agent prompt + schema
        query_generator.py   # Generate search queries
        evaluator.py         # Rate job fit 0-5
        detail_extractor.py  # Extract structured job details
        url_extractor.py     # Find first-party URLs
        results_summary.py   # Summarize search results
        fit_evaluator.py     # Deep fit analysis
        analysis.py          # General analysis (query_jobs, compare)
        profile_updater.py   # Interpret profile updates
        todo_generator.py    # Generate application todos
        interview_prep.py    # Interview preparation content
        cover_letter.py      # Cover letter drafts
        resume_tailor.py     # Resume tailoring suggestions
        question_generator.py # Predict interview questions
        comparison.py        # Side-by-side job comparison
        ranking.py           # Score and rank jobs
        research_synthesizer.py  # Synthesize research findings
        advisor.py           # General career advice
    │
    # ── Prompts ──
    prompts/
        __init__.py
        routing.py           # Routing agent system prompt
        pipelines.py         # Progress/confirmation message templates
        micro_agents.py      # System prompts for each micro-agent
    │
    # ── Schemas ──
    schemas/
        __init__.py
        routing.py           # RoutingResult, per-pipeline param schemas
        micro_agents.py      # Output schemas for structured micro-agents
    │
    # ── Agent classes (ABCs) ──
    agent.py                 # OrchestratorAgent — main entry point
    onboarding_agent.py      # OrchestratorOnboardingAgent (can reuse default design)
    resume_parser.py         # OrchestratorResumeParser (can reuse default design)
```

---

## What Stays the Same

- **`AgentTools`** — All existing tools are reused. The orchestrator calls
  `tools.execute(name, args)` from pipeline steps rather than letting the
  LLM decide when to call them.

- **`OnboardingAgent`** — The onboarding interview is inherently conversational
  and doesn't benefit from pipeline routing. The orchestrator can reuse the
  default design's `DefaultOnboardingAgent` (or implement a new one later).

- **`ResumeParser`** — Single-shot structured extraction. The orchestrator can
  reuse `DefaultResumeParser`.

- **SSE protocol** — Identical event types and `data` shapes.

- **Frontend** — No changes required. The orchestrator is a drop-in replacement
  from the frontend's perspective.

---

## Implementation Order

Recommended build sequence:

1. **Scaffolding** — `__init__.py`, `agent.py`, `context.py`, `streaming.py`
   with the `OrchestratorAgent` class that initially falls back to a single
   LLM call (like `general` pipeline) for everything.

2. **Routing** — `routing.py` + schemas. Once routing works, the agent can
   classify requests and dispatch to stub pipelines that just echo the
   classification.

3. **Programmatic pipelines first** — `track_crud`, `query_jobs`, `todo_mgmt`,
   `profile_mgmt` (simple read). These are mostly DB operations with template
   responses and prove out the pipeline + SSE infrastructure.

4. **find_jobs** — The flagship pipeline. Build it step by step: query
   generation → API calls → evaluation → filtering → results.

5. **research_url** — Straightforward scrape + extract + evaluate.

6. **prepare** — Micro-agents for interview prep, cover letters, etc.

7. **compare**, **research**, **general** — Lower priority, can use simpler
   implementations initially.

8. **multi_step** — Orchestrate sub-pipelines once the individual ones are solid.
