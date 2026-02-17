# TODO

## Features

- [ ] **Add job-site search APIs (LinkedIn)**
  - Integrate LinkedIn job search API (or scraping fallback) as an agent tool
  - Allow the agent to search for jobs on LinkedIn and other job boards directly

- [ ] **Improve agent orchestration**
  - Add routes/tools for company search (research a specific company)
  - Add generic job search tool (search across multiple sources)
  - Improve how the agent leverages the user profile for personalized recommendations

- [ ] **Improve user profile updating**
  - Make the agent more sensitive to user statements that reveal preferences, skills, or constraints
  - Proactively extract and update profile info from natural conversation

- [ ] **Job suitability ranking**
  - Add an AI-generated suitability score (e.g. x/5 stars) per job
  - Store the ranking on the Job model and display it in the UI
  - Agent should auto-rate jobs based on user profile match

- [ ] **Job application preparation**
  - Add per-job preparation components (interview prep, resume tailoring, cover letter drafts)
  - Store preparation notes/materials linked to each job
  - Agent tools to generate and manage prep content
