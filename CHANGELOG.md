# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-02-17

Initial release of Job Application Helper - a full-stack web application for tracking job applications with an AI-powered assistant.

### Added

**Core Features**
- Flask backend with SQLAlchemy and SQLite database
- React frontend with Vite and Tailwind CSS
- Job CRUD API endpoints with comprehensive job tracking
- Extended job fields: salary range, location, remote type, tags, contact info, applied date, source
- Job requirements and nice-to-haves fields (newline-separated)
- AI-powered job fit rating field (0-5 stars)
- Sortable columns in job list table
- Job detail panel with markdown rendering

**AI Assistant**
- Multi-LLM provider support: Anthropic Claude, OpenAI GPT, Google Gemini, Ollama
- LLM provider abstraction layer with factory pattern
- Agent system with iterative tool-calling loop
- Slide-out chat panel with Server-Sent Events (SSE) streaming
- Stream cancellation with stop button
- Message separation and markdown rendering in chat panel
- Live job list refresh after AI creates jobs

**Agent Tools**
- `web_search` - Search the web via Tavily API
- `job_search` - Search job boards (Adzuna and JSearch via RapidAPI)
- `scrape_url` - Fetch and parse web pages
- `create_job` - Add jobs to the database
- `list_jobs` - List and filter jobs with enhanced capabilities
- `read_user_profile` - Read user profile
- `update_user_profile` - Update user profile with extracted information

**User Profile System**
- User profile with YAML frontmatter for metadata
- Onboarding interview flow with dedicated OnboardingAgent
- Automatic profile reading on each agent turn for personalized responses
- Proactive profile updates via agent tools
- Profile panel in UI for viewing and manually editing user profile
- Separate LLM configuration for onboarding (`ONBOARDING_LLM_*` env vars)

**Infrastructure**
- Comprehensive logging system with file and console output
- Structured logging infrastructure with configurable log levels
- Dotenv support for environment variable configuration

**Documentation**
- User-focused README with screenshots and quick start guide
- Comprehensive DEVELOPMENT.md for contributors
- MIT License
- Contributing guidelines and code of conduct
- GitHub issue templates (bug report, feature request)
- GitHub pull request template
- Complete API reference and architecture documentation

### Changed
- Migrated Gemini provider from legacy SDK to `google-genai` package
- Improved chat tool ordering for better user experience
- Enhanced chat panel with better message formatting

### Fixed
- Tool ordering issues in chat interface
