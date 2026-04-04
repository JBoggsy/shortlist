# E2E Test Plan: Shortlist Interactive Testing

**TL;DR:** A comprehensive test plan using Peter Grosman (see [GROSMAN.md](GROSMAN.md)) as the test persona. Tests every user-facing feature from clean-slate first-time setup through advanced agent interactions. Uses Ollama as primary LLM provider and switches to Anthropic partway through to test multi-provider support.

---

## Feature Coverage Matrix

| # | Feature Area | Key Interactions Tested |
|---|---|---|
| 1 | First Launch & Health Check | Clean state detection, setup wizard auto-open, health endpoint 503 |
| 2 | Setup Wizard (Ollama) | Provider selection, model discovery, test connection, integrations |
| 3 | Onboarding Interview | Auto-start, agent greeting, profile updates via tools, completion |
| 4 | Profile Page | View filled profile, edit manually, resume upload + parsing |
| 5 | Manual Job CRUD | Add job, edit job, delete job, sort/filter table, job detail page |
| 6 | AI Chat — Job Search | Ask agent to search, SSE streaming, search results panel, add to tracker |
| 7 | AI Chat — Job Management | Create/edit/delete jobs via chat, real-time job list refresh |
| 8 | Document Editor | Cover letter creation via chat, editor toolbar, version history, Ctrl+S |
| 9 | Provider Switch (Anthropic) | Change to Anthropic in settings, test connection, chat with new provider |
| 10 | Agent Mode Switch + Advanced | Switch to micro_agents_v1, run orchestrated queries, compare jobs |
| 11 | Navigation & UI Polish | Nav active states, Help page, Home stats, chat history, toasts, resizing |
| 12 | Error Handling & Edge Cases | Invalid API key, agent error recovery, form validation, empty results |

---

## Prerequisites

**Clean state setup (run before starting):**
```bash
cd /home/boggsj/Coding/personal/job_app_helper

# Save the Anthropic API key before wiping
ANTHROPIC_KEY=$(python3 -c "import json; c=json.load(open('user_data/config.json')); print(c['llm']['api_key'])")
TAVILY_KEY=$(python3 -c "import json; c=json.load(open('user_data/config.json')); print(c['integrations']['search_api_key'])")

# Wipe user data for clean slate
rm -f user_data/app.db user_data/telemetry.db user_data/config.json user_data/user_profile.md
rm -rf user_data/resumes/*

# Note the keys for later use:
echo "Anthropic key: $ANTHROPIC_KEY"
echo "Tavily key: $TAVILY_KEY"
```

**Start the app:**
```bash
./start.sh
```
This launches backend on :5000 and frontend on :3000. Open `http://localhost:3000` in the browser.

---

## Scenario 1: First Launch & Health Check

**Goal:** Verify clean-state detection, health endpoint behavior, and setup wizard auto-trigger.

**Steps:**
1. Open `http://localhost:3000` in the browser
2. **VERIFY:** The home page loads with a yellow/orange warning banner saying the AI assistant is not configured
3. **VERIFY:** The setup wizard modal auto-opens (centered, step 1 "Welcome")
4. **VERIFY:** Navigation bar is visible behind the modal (Home, Jobs, Profile, Settings, Help links + AI Assistant button)
5. Click outside the modal or press Escape — **VERIFY:** wizard stays open (it should not be dismissible on first launch without configuring)
6. Navigate to `http://localhost:3000/jobs` — **VERIFY:** Job tracker page loads with empty state message ("No applications yet" or similar)
7. Navigate to `http://localhost:3000/settings` — **VERIFY:** Settings page loads showing unconfigured state
8. Navigate back to `http://localhost:3000` — **VERIFY:** Setup wizard re-appears

---

## Scenario 2: Setup Wizard — Ollama Provider

**Goal:** Complete setup wizard using Ollama, test model discovery and connection testing.

**Steps:**
1. From the Welcome step (step 1), click "Next" / "Get Started" to proceed
2. **Step 2 — Choose Provider:** 
   - **VERIFY:** 4 provider cards displayed (Anthropic, OpenAI, Gemini, Ollama)
   - **VERIFY:** Ollama card shows "Free" badge
   - Click the **Ollama** card
   - **VERIFY:** Ollama card highlights with blue border
   - Click "Next"
3. **Step 3 — API Key / Model:**
   - **VERIFY:** No API key field shown (Ollama doesn't need one)
   - **VERIFY:** Auto-detected Ollama models appear (list of locally installed models)
   - **NOTE:** Record which models are shown — this answers the "which Ollama models" question
   - Select or confirm a model (e.g., `qwen3.5:35b` or whatever is listed)
   - Click **"Test Connection"**
   - **VERIFY:** Elapsed time counter appears
   - **VERIFY:** Connection succeeds with green checkmark message
   - If test shows model_not_found error: **VERIFY** that the model override field auto-opens
   - Click "Next"
4. **Step 4 — Integrations:**
   - **VERIFY:** Tavily Search API Key field visible with "Recommended" badge
   - Enter the saved Tavily key: (paste from prerequisites)
   - **VERIFY:** RapidAPI Key field visible
   - Leave RapidAPI blank for now (optional)
   - Click "Next"
5. **Step 5 — Done:**
   - **VERIFY:** Success message with next-steps guidance
   - Click "Launch Onboarding" (or "Get Started")
   - **VERIFY:** Wizard closes
   - **VERIFY:** Chat panel auto-opens on the right side
   - **VERIFY:** Chat header says something like "Welcome! Let's set up your profile"

---

## Scenario 3: Onboarding Interview (as Peter Grosman)

**Goal:** Test the full onboarding interview flow — agent greeting, multi-turn conversation, profile tool calls, and completion.

**Steps:**
1. **VERIFY:** Agent sends an initial greeting message (SSE streaming — text appears token by token)
2. **VERIFY:** Tool calls may appear as collapsible cards (agent might read profile first)
3. Wait for the agent to finish its greeting and ask questions

4. **Turn 1 — Introduction:**
   Send: `"Hi, I'm Peter Grosman. I'm a recent grad from the University of Michigan — double major in Economics and Math. I'm looking for entry-level quantitative finance roles."`
   - **VERIFY:** Message appears right-aligned in chat
   - **VERIFY:** Agent responds with streaming text
   - **VERIFY:** Agent may call `update_user_profile` tool (shown as tool card)
   - **VERIFY:** Agent asks follow-up questions about preferences

5. **Turn 2 — Location & Salary:**
   Send: `"I'm based in Scarsdale, NY. Strongly prefer New York City, but also open to Chicago or Boston. Hybrid preferred. Salary expectations are $90k-$140k base."`
   - **VERIFY:** Agent calls `update_user_profile` to save location/salary preferences
   - **VERIFY:** Tool cards show tool name and result

6. **Turn 3 — Experience & Skills:**
   Send: `"I interned at Lakepoint Capital as a quant research intern — built pairs-trading signals in Python. Before that I was at Hudson Valley National Bank doing risk analytics, building PD models. My core skills are Python (NumPy, pandas, scikit-learn, statsmodels), SQL, and I know some R and MATLAB."`
   - **VERIFY:** Agent updates work experience and skills sections
   - **VERIFY:** Streaming is smooth, no hiccups or error events

7. **Turn 4 — Target Roles:**
   Send: `"I'm targeting Quantitative Analyst, Quant Researcher, Risk Analyst, or Quant Developer roles. Mainly at hedge funds, prop trading firms, and asset managers. I'm available immediately — U.S. citizen, no sponsorship needed."`
   - **VERIFY:** Agent updates fields of interest and job search goals

8. **Turn 5 — Wrap Up:**
   Send: `"I think that covers everything. I'm pretty methodical about my job search — I keep spreadsheets of everything and prefer concrete data over vague encouragement."`
   - **VERIFY:** Agent acknowledges and may wrap up onboarding
   - **VERIFY:** `onboarding_complete` event fires (chat may close or show completion message)
   - **VERIFY:** Onboarding state transitions to `true`

9. **Post-onboarding verification:**
   - Navigate to Profile page (`/profile`)
   - **VERIFY:** Profile content shows Peter's details filled in across sections (Summary, Education, Work Experience, Skills, Location Preferences, Salary Preferences, Job Search Goals)
   - **VERIFY:** Profile is rendered as markdown with proper sections

---

## Scenario 4: Profile Page & Resume Upload

**Goal:** Test profile viewing/editing and the resume upload + parsing pipeline.

**Steps:**

### 4A — Profile Editing
1. Navigate to `/profile`
2. **VERIFY:** Peter's profile is displayed with filled sections from onboarding
3. Click **"Edit Profile"** button
4. **VERIFY:** Textarea appears with markdown content
5. Add a line under "Other Notes": `"Tends to over-research companies before applying. Gets stuck in analysis paralysis sometimes."`
6. Click **"Save"**
7. **VERIFY:** Profile re-renders with the new note visible
8. Click **"Edit Profile"** again, then click **"Cancel"**
9. **VERIFY:** No changes saved, original content still shown

### 4B — Resume Upload
10. Create a test resume file (can use the plain text from GROSMAN.md saved as a .docx or .pdf)
    - For simplicity: create a file `peter_resume.txt` and rename to `.pdf` — or use an actual PDF generation tool
    - **Alternative:** If no PDF handy, test with any valid PDF file and verify the upload mechanics
11. Click **"Upload Resume"** button on Profile page
12. Select the resume file
13. **VERIFY:** Upload succeeds, filename appears
14. **VERIFY:** "AI is analyzing..." spinner appears during LLM parsing
15. Wait for parsing to complete
16. **VERIFY:** "Structured" view shows parsed sections (Contact, Experience, Education, Skills)
17. Toggle to **"Raw Text"** view
18. **VERIFY:** Raw extracted text is displayed
19. Toggle back to **"Structured"** view
20. Click **"Delete"** button on resume
21. **VERIFY:** Resume is removed, upload button reappears

---

## Scenario 5: Manual Job CRUD

**Goal:** Test all manual job tracking interactions — add, view, edit, sort, delete.

**Steps:**

### 5A — Create Jobs Manually
1. Navigate to `/jobs`
2. **VERIFY:** Empty state message shown
3. Click **"Add Job"** button
4. Fill in the form:
   - Company: `Two Sigma`
   - Title: `Junior Quantitative Researcher`
   - URL: `https://twosigma.com/careers` 
   - Status: `Saved`
   - Salary Min: `120000`, Max: `150000`
   - Location: `New York, NY`
   - Remote Type: `Hybrid`
   - Tags: `quant, hedge fund, NYC`
   - Job Fit: 4 stars
   - Requirements: `Python proficiency\nStatistics background\nBS in quantitative field`
   - Notes: `Found this on their careers page. Very competitive.`
5. Click **"Add Job"** / Submit
6. **VERIFY:** Job appears in the table with correct status badge and details
7. Add a second job:
   - Company: `Citadel Securities`
   - Title: `Quantitative Research Analyst`
   - Status: `Applied`
   - Salary Min: `130000`, Max: `160000`
   - Location: `Chicago, IL`
   - Remote Type: `Onsite`
   - Applied Date: `2026-03-25`
   - Tags: `quant, prop trading, Chicago`
   - Job Fit: 5 stars
8. Add a third job:
   - Company: `Goldman Sachs`
   - Title: `Risk Analyst — Strats`
   - Status: `Interviewing`
   - Salary Min: `95000`, Max: `125000`
   - Location: `New York, NY`
   - Remote Type: `Hybrid`
   - Tags: `risk, investment bank, NYC`
   - Job Fit: 3 stars

### 5B — Table Sorting
9. Click the **"Company"** column header — **VERIFY:** rows sort alphabetically (Citadel, Goldman, Two Sigma)
10. Click again — **VERIFY:** reverse alphabetical sort
11. Click the **"Status"** column — **VERIFY:** sorting changes to status-based ordering
12. Click the **"Fit"** column — **VERIFY:** jobs sort by star rating

### 5C — Job Detail & Edit
13. Click the **Two Sigma** row
14. **VERIFY:** Navigates to `/jobs/1` (or whichever ID)
15. **VERIFY:** All fields displayed correctly: title, company, status, salary range, location, remote type, tags, requirements, notes, fit stars
16. **VERIFY:** Documents section shows "Cover Letter" and "Tailored Resume" links
17. **VERIFY:** Application Steps section shows empty / "No steps yet"
18. Click **"Edit"** button
19. Change Status from `Saved` to `Applied`, set Applied Date to today (`2026-04-03`)
20. Click **"Save Changes"**
21. **VERIFY:** Status badge updates to "Applied", applied date shown

### 5D — Application Todos
22. In the Application Steps section, click **"Add Step"**
23. Fill: Title: `Tailor resume for role`, Category: `document`
24. Submit — **VERIFY:** Todo appears with document icon
25. Add another: Title: `Research Two Sigma's investment strategies`, Category: `question`
26. Add another: Title: `Prepare for probability brainteaser questions`, Category: `assessment`
27. **VERIFY:** Progress bar shows 0/3 completed
28. Check the first todo (click checkbox)
29. **VERIFY:** Progress updates to 1/3 completed, todo shows as checked
30. Delete the second todo — **VERIFY:** Removed, progress shows 1/2

### 5E — Delete Job
31. Navigate back to `/jobs`
32. Click delete on the **Goldman Sachs** row
33. **VERIFY:** Confirmation dialog appears
34. Confirm delete
35. **VERIFY:** Job removed from table, only 2 jobs remain

---

## Scenario 6: AI Chat — Job Search

**Goal:** Test the AI chat for job searching, SSE streaming, search results panel, and adding results to the tracker.

**Steps:**
1. Click **"AI Assistant"** button in the navigation bar
2. **VERIFY:** Chat panel slides in from the right
3. **VERIFY:** Previous onboarding conversation may appear, or "New Chat" is available
4. Click **"New Chat"** to start a fresh conversation

5. **Message 1 — Job Search Request:**
   Send: `"Can you find quantitative analyst openings in New York? I'm mostly interested in hedge funds and prop trading firms, entry-level. Salary range ideally $100k+."`
   - **VERIFY:** Agent responds with streaming text
   - **VERIFY:** Agent calls `web_search` or `job_search` tool (tool cards appear with status)
   - **VERIFY:** If Tavily search is used, tool result shows search results
   - **VERIFY:** Agent may call `add_search_result` — search results panel opens to the right
   - **VERIFY:** Result cards appear with star ratings, company names, job titles
   - **VERIFY:** Each card is expandable with fit reason and description

6. **Interact with Search Results:**
   - Click a result card to expand it
   - **VERIFY:** Details visible (description, requirements, fit reason)
   - **VERIFY:** "Add to Tracker" button visible on untracked results
   - Click **"Add to Tracker"** on one result
   - **VERIFY:** Button changes to "Added" with checkmark
   - **VERIFY:** Job list refreshes (if Jobs page were open, it would show the new job)

7. **Message 2 — Follow-up:**
   Send: `"What's the difference between a quant analyst and a quant developer? I want to make sure I'm applying to the right roles given my background."`
   - **VERIFY:** Agent responds conversationally (no tool calls needed for this question)
   - **VERIFY:** Response references Peter's profile (skills, experience) since agent reads profile

8. **Chat History:**
   - Click **"History"** in chat header
   - **VERIFY:** Conversation list shows the current conversation and the onboarding conversation
   - Click the onboarding conversation
   - **VERIFY:** Previous onboarding messages load
   - Click back to the current conversation
   - **VERIFY:** Search conversation messages preserved

9. **Close and Reopen:**
   - Close the chat panel (X button)
   - **VERIFY:** Panel slides out
   - Click **"AI Assistant"** again
   - **VERIFY:** Panel reopens with same conversation loaded
   - Search results panel should also restore if results exist

---

## Scenario 7: AI Chat — Job Management via Agent

**Goal:** Test creating, editing, and deleting jobs through the chat agent, verifying real-time UI updates.

**Steps:**
1. Open chat panel, start a **New Chat**

2. **Create Job via Chat:**
   Send: `"Add that Two Sigma posting we were looking at. Junior Quantitative Researcher in NYC, salary range $120k-$150k, hybrid. URL is https://twosigma.com/careers/jr-quant-researcher."`
   - **VERIFY:** Agent calls `create_job` tool
   - **VERIFY:** Tool card shows the creation details
   - **VERIFY:** Agent confirms job was added
   - Navigate to `/jobs` — **VERIFY:** New job appears in the table (may be duplicate of manual one — that's fine for testing)

3. **Edit Job via Chat:**
   Send: `"I just applied to that Citadel Securities role. Can you update its status to Applied and set the applied date to today?"`
   - **VERIFY:** Agent calls `list_jobs` to find the job, then `edit_job` to update it
   - **VERIFY:** Tool cards show both calls
   - Navigate to Job Tracker — **VERIFY:** Citadel status updated to "Applied"

4. **Add Todos via Chat:**
   Send: `"For the Citadel role, can you add some prep steps? I need to: review probability theory, practice coding interview questions in Python, and research Citadel's market making strategies."`
   - **VERIFY:** Agent calls `add_job_todo` multiple times
   - Navigate to Job Detail for Citadel — **VERIFY:** Todos appear in the Application Steps section

5. **Delete Job via Chat:**
   Send: `"Actually, remove the Goldman Sachs Risk Analyst job if it's still there. I decided that role isn't a good fit."`
   - **VERIFY:** Agent calls `list_jobs` to find it, then `remove_job`
   - **VERIFY:** If Goldman was already deleted in Scenario 5, agent should say it's not found
   - Navigate to `/jobs` — **VERIFY:** Job removed (or was already gone)

6. **List Jobs Query:**
   Send: `"What jobs do I have saved right now? Give me a summary."`
   - **VERIFY:** Agent calls `list_jobs` and summarizes the results conversationally

---

## Scenario 8: Document Editor — Cover Letter

**Goal:** Test cover letter creation via agent, the document editor page, toolbar, and version history.

**Steps:**

### 8A — Agent Creates Cover Letter
1. Open Chat Panel, start a **New Chat**
2. Send: `"Can you write a cover letter for the Two Sigma Junior Quantitative Researcher position? Focus on my pairs trading experience at Lakepoint and my stochastic processes coursework."`
   - **VERIFY:** Agent calls `read_user_profile` to get Peter's background
   - **VERIFY:** Agent calls `get_job_document` and/or `list_jobs` to find the job
   - **VERIFY:** Agent calls `save_job_document` with the cover letter content
   - **VERIFY:** `document_saved` SSE event fires
   - **VERIFY:** Agent confirms the cover letter was saved

### 8B — Document Editor Page
3. Navigate to the **Two Sigma** job detail page (`/jobs/:id`)
4. Click the **"Cover Letter"** link in the Documents section
5. **VERIFY:** Document Editor page loads at `/jobs/:id/documents/cover_letter`
6. **VERIFY:** Cover letter content from the agent appears in the Tiptap editor
7. **VERIFY:** Version history sidebar shows v1 with creation date
8. **VERIFY:** "v1" badge visible in top bar

### 8C — Editor Toolbar
9. Select a paragraph of text in the editor
10. Click **Bold** button — **VERIFY:** Selected text becomes bold
11. Click **Italic** button — **VERIFY:** Selected text becomes italic
12. Place cursor on a new line, click **H2** — **VERIFY:** Line becomes an H2 heading
13. Type some text, click **Bullet List** — **VERIFY:** Bulleted list starts
14. Click **Undo** — **VERIFY:** Last action undone
15. Click **Redo** — **VERIFY:** Action restored
16. Add a blockquote — **VERIFY:** Blockquote formatting applied
17. Insert a horizontal rule — **VERIFY:** HR appears

### 8D — Save & Version History
18. Make edits to the cover letter (change a sentence or paragraph)
19. **VERIFY:** "Unsaved changes" indicator appears in top bar
20. **VERIFY:** Save button becomes enabled
21. Press **Ctrl+S**
22. **VERIFY:** Document saves, "Unsaved changes" disappears
23. **VERIFY:** Version history sidebar now shows v2 (with today's date)
24. Click **v1** in the history sidebar
25. **VERIFY:** Editor shows the original v1 content (read-only)
26. **VERIFY:** "Restore" button visible on v1
27. Click **"Restore"** on v1
28. **VERIFY:** Original content restored as new version (v3)
29. Click **"Copy Text"** button
30. **VERIFY:** "Copied!" feedback appears, clipboard contains plain text version

### 8E — Real-time Agent Update
31. Open Chat Panel alongside the Document Editor (chat overlays)
32. Send: `"Can you revise the cover letter for Two Sigma? Make the opening paragraph more confident and add a sentence about my Monte Carlo simulation experience."`
   - **VERIFY:** Agent calls `get_job_document`, then `save_job_document` with updated content
   - **VERIFY:** `document_saved` event fires
   - **VERIFY:** Document Editor auto-refreshes with the new content (no manual reload needed)
   - **VERIFY:** Version history updates to show the new version

---

## Scenario 9: Provider Switch — Anthropic

**Goal:** Test switching LLM providers mid-session, validating settings save and new provider connectivity.

**Steps:**
1. Navigate to `/settings`
2. **VERIFY:** Current config shows Ollama as provider with the selected model

### 9A — Change Provider
3. Change **Provider** dropdown from Ollama to **Anthropic**
4. **VERIFY:** API Key field appears (it was hidden for Ollama)
5. Enter the Anthropic API key (saved from prerequisites)
6. **VERIFY:** Model dropdown shows/allows selection (or leave blank for default)
7. Click **"Test Connection"**
8. **VERIFY:** Elapsed time counter appears
9. **VERIFY:** Connection succeeds with green checkmark
10. Click **"Save Settings"**
11. **VERIFY:** Success message appears (toast or inline)

### 9B — Health Check Update
12. Navigate to `/` (Home)
13. **VERIFY:** Yellow warning banner is gone (LLM is now configured with Anthropic)
14. **VERIFY:** Dashboard shows correct stats

### 9C — Chat with Anthropic
15. Open Chat Panel, start a **New Chat**
16. Send: `"I'm a little worried my programming skills aren't strong enough for the more engineering-heavy roles. I've mostly used Python for data analysis, not production systems. What do you think?"`
   - **VERIFY:** Agent responds (now using Anthropic model)
   - **VERIFY:** Streaming works with Anthropic provider
   - **VERIFY:** Response is contextually aware (reads Peter's profile)
   - **VERIFY:** Response quality may differ from Ollama — note any differences

17. Send: `"Can you help me prep for the Citadel interview? I've heard they focus heavily on probability and brainteasers."`
   - **VERIFY:** Agent may use web_search for interview prep info
   - **VERIFY:** Tool calls work correctly with Anthropic
   - **VERIFY:** Agent references Peter's coursework (probability, stochastic processes)

### 9D — Message Feedback
18. On the agent's response, click **thumbs up** button
19. **VERIFY:** Feedback icon changes to indicate positive feedback
20. On a different message, click **thumbs down**
21. **VERIFY:** Feedback icon changes to indicate negative feedback

---

## Scenario 10: Agent Mode Switch & Advanced Features

**Goal:** Test switching agent designs, orchestrated mode queries, and complex multi-job reasoning.

**Steps:**

### 10A — Switch to Micro Agents V1
1. Navigate to `/settings`
2. Find the **Agent Mode** / **Agent Design** dropdown
3. Change from `default` to `micro_agents_v1` (or `orchestrated`)
4. Click **"Save Settings"**
5. **VERIFY:** Settings save successfully

### 10B — Orchestrated Job Search
6. Open Chat Panel, start a **New Chat**
7. Send: `"Search for entry-level quantitative researcher positions at prop trading firms in NYC and Chicago. Also look for risk analyst roles at investment banks in NYC. I want to compare the best options."`
   - **VERIFY:** Agent decomposes this into multiple workflows (micro agents approach)
   - **VERIFY:** Multiple tool calls may execute (possibly in parallel)
   - **VERIFY:** Search results panel populates with results from both searches
   - **VERIFY:** Agent provides a comparative summary

### 10C — Multi-Job Comparison
8. Send: `"Which of the jobs in my tracker is the best fit for me? Consider my quant research internship, my coursework in stochastic processes, and my preference for NYC."`
   - **VERIFY:** Agent calls `list_jobs` and possibly `read_user_profile`
   - **VERIFY:** Agent provides a structured comparison with reasoning
   - **VERIFY:** References specific jobs by name with fit analysis

### 10D — Profile Auto-Update
9. Send: `"Oh, I forgot to mention — I also know C++ basics. I took a one-term course. And I'm particularly interested in systematic trading strategies."`
   - **VERIFY:** Agent proactively calls `update_user_profile` to add C++ to skills and systematic trading to interests
   - Navigate to `/profile` — **VERIFY:** Profile reflects the updates

### 10E — Switch Back to Default
10. Navigate to `/settings`
11. Change Agent Design back to `default`
12. Save
13. Open Chat, new conversation
14. Send: `"What's my current job search status? How many applications do I have in each stage?"`
    - **VERIFY:** Default agent works correctly after switching back
    - **VERIFY:** Agent summarizes job tracker state accurately

---

## Scenario 11: Navigation & UI Polish

**Goal:** Verify navigation, edge cases, empty states, and general UI quality.

**Steps:**
1. **Nav bar active states:** Click through each nav link (Home, Jobs, Profile, Settings, Help)
   - **VERIFY:** Active page is highlighted in the nav bar
   - **VERIFY:** Each page loads without errors

2. **Help Page:** Navigate to `/help`
   - **VERIFY:** All sections render (Getting Started, Job Tracking, AI Chat, API Keys, Troubleshooting)
   - **VERIFY:** Links open in new tabs (right-click or Ctrl+click)

3. **Home Page stats:** Navigate to `/`
   - **VERIFY:** Job stats cards show correct counts (Total, Applied, Interviewing, Offers)
   - **VERIFY:** Recent jobs section shows most recently added/modified jobs
   - **VERIFY:** Quick actions work (Add Job link, Open AI Assistant button)

4. **Chat History management:**
   - Open Chat Panel
   - Click History — **VERIFY:** Multiple conversations listed with titles
   - Delete a conversation — **VERIFY:** Confirmation, then removed from list
   - **VERIFY:** Remaining conversations persist

5. **Conversation titles:** 
   - **VERIFY:** Conversation titles are derived from the first user message (truncated to ~100 chars)

6. **Toast notifications:**
   - Trigger an error (e.g., try to save settings with an invalid API key)
   - **VERIFY:** Toast appears with error message
   - **VERIFY:** Toast has collapsible technical details
   - **VERIFY:** Toast can be dismissed

7. **Chat resizing:**
   - With chat open, hover over the left edge of the chat panel
   - **VERIFY:** Cursor changes to resize cursor
   - Drag to resize — **VERIFY:** Panel width changes

---

## Scenario 12: Error Handling & Edge Cases

**Goal:** Test error conditions, boundary cases, and recovery.

**Steps:**

### 12A — Invalid Configuration
1. Navigate to `/settings`
2. Change provider to Anthropic, enter an invalid API key: `sk-invalid-key-12345`
3. Click **"Test Connection"**
4. **VERIFY:** Error message appears with `auth_error` type
5. **VERIFY:** Error message is user-friendly (not a raw stack trace)
6. Change back to valid key and verify connection works again

### 12B — Agent Error Recovery
7. Open chat, start a new conversation
8. If Ollama is selected and you stop the Ollama service: send a message
   - **VERIFY:** Error SSE event fires, error toast shown
   - **VERIFY:** Chat remains functional (not stuck in loading state)
   - Restart Ollama, send another message — **VERIFY:** Recovery works

### 12C — Form Validation
9. Navigate to `/jobs`, click "Add Job"
10. Try to submit with empty Company and Title
11. **VERIFY:** Validation error shown (required fields)
12. Enter Company only, try submit — **VERIFY:** Title still required
13. Fill both and submit — **VERIFY:** Success

### 12D — Empty Searches
14. Open chat, send: `"Search for underwater basket weaving instructor positions in Antarctica"`
    - **VERIFY:** Agent handles gracefully (no results or "no matching jobs found")
    - **VERIFY:** No crash or stuck state

---

## Verification Checklist (Cross-Cutting)

Throughout all scenarios, verify:

- [ ] **SSE Streaming:** Text appears token-by-token, not in chunks
- [ ] **Tool Cards:** Tool calls show name, arguments, status (running → completed/error)
- [ ] **Real-time Refresh:** Job list updates when agent modifies jobs (without page reload)
- [ ] **Document Refresh:** Editor updates when agent saves documents
- [ ] **Search Panel:** Opens automatically on first `search_result_added`, accumulates results
- [ ] **Navigation:** No broken links, back button works, deep links work
- [ ] **Loading States:** Spinners appear during async operations, buttons disable while processing
- [ ] **Empty States:** Graceful messages when no data exists
- [ ] **Error States:** User-friendly error messages, no raw tracebacks in UI
- [ ] **Responsive Layout:** Chat panel doesn't break page layout
- [ ] **Profile Integration:** Agent references Peter's profile in responses
- [ ] **Keyboard Shortcuts:** Ctrl+S saves in editor
- [ ] **Provider Switching:** Both Ollama and Anthropic work without server restart
