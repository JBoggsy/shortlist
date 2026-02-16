# Job App Helper

A web app to track and manage job applications. Includes an LLM-powered AI assistant that can search for job postings, scrape URLs, and automatically add jobs to your tracker via a chat interface.

## Tech Stack

- **Backend:** Python 3.12+, Flask, Flask-SQLAlchemy, SQLite
- **Frontend:** React 19, Vite, Tailwind CSS 4
- **LLM Providers:** Anthropic, OpenAI, Google Gemini, Ollama
- **Agent Tools:** Tavily web search, BeautifulSoup web scraping
- **Package Management:** uv (Python), npm (JS)

## Project Structure

```
job_app_helper/
├── backend/
│   ├── app.py              # App factory
│   ├── config.py           # Configuration (incl. LLM settings)
│   ├── database.py         # SQLAlchemy setup
│   ├── models/
│   │   ├── job.py          # Job model
│   │   └── chat.py         # Conversation & Message models
│   ├── routes/
│   │   ├── jobs.py         # Job CRUD endpoints
│   │   └── chat.py         # Chat + SSE streaming endpoints
│   ├── llm/
│   │   ├── base.py         # LLMProvider ABC
│   │   ├── factory.py      # Provider factory
│   │   ├── anthropic_provider.py
│   │   ├── openai_provider.py
│   │   ├── gemini_provider.py
│   │   └── ollama_provider.py
│   └── agent/
│       ├── tools.py        # Tool definitions + execution
│       └── agent.py        # Agent loop with tool calling
├── frontend/
│   └── src/
│       ├── App.jsx
│       ├── api.js          # API helpers (jobs + chat)
│       ├── pages/
│       │   └── JobList.jsx
│       └── components/
│           ├── JobForm.jsx
│           └── ChatPanel.jsx
├── main.py                 # Backend entry point
└── pyproject.toml
```

## Setup

### Backend

```bash
# Install Python dependencies (requires uv)
uv sync

# Run the Flask server
uv run python main.py
```

The API will be available at `http://localhost:5000`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The dev server will be available at `http://localhost:3000` and proxies `/api` requests to the Flask backend.

## AI Assistant Configuration

The chat assistant requires an LLM provider to be configured via environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_PROVIDER` | Which provider to use: `anthropic`, `openai`, `gemini`, or `ollama` | `anthropic` |
| `LLM_API_KEY` | API key for the chosen provider (not needed for Ollama) | — |
| `LLM_MODEL` | Model override (optional — each provider has a sensible default) | — |
| `SEARCH_API_KEY` | [Tavily](https://tavily.com/) API key for the web search tool (optional) | — |

### Provider defaults

| Provider | Default Model | API Key Required |
|----------|--------------|-----------------|
| `anthropic` | `claude-sonnet-4-5-20250929` | Yes |
| `openai` | `gpt-4o` | Yes |
| `gemini` | `gemini-2.0-flash` | Yes |
| `ollama` | `llama3.1` | No (runs locally) |

### Example

```bash
export LLM_PROVIDER=anthropic
export LLM_API_KEY=sk-ant-...
export SEARCH_API_KEY=tvly-...   # optional, enables web search

uv run python main.py
```

For Ollama, make sure the Ollama server is running locally on port 11434:

```bash
export LLM_PROVIDER=ollama
export LLM_MODEL=llama3.1   # or any model you have pulled

uv run python main.py
```

## API Endpoints

### Jobs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/jobs` | List all jobs |
| POST | `/api/jobs` | Create a job |
| GET | `/api/jobs/:id` | Get a job |
| PATCH | `/api/jobs/:id` | Update a job |
| DELETE | `/api/jobs/:id` | Delete a job |

### Chat

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/chat/conversations` | List conversations |
| POST | `/api/chat/conversations` | Create conversation |
| GET | `/api/chat/conversations/:id` | Get conversation with messages |
| DELETE | `/api/chat/conversations/:id` | Delete conversation |
| POST | `/api/chat/conversations/:id/messages` | Send message (returns SSE stream) |
