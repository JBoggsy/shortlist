# Agent Designs

This directory contains the agent framework for Shortlist. The application uses
a pluggable **design/strategy** pattern — each agent design is a self-contained
sub-package that implements the three abstract base classes defined in `base.py`.

The active design is selected via the `agent.design` config key (or
`AGENT_DESIGN` env var) and defaults to `"default"`.

---

## Creating a New Agent Design

### 1. Create the sub-package

Add a new folder under `backend/agent/` named after your design in
**snake_case**:

```
backend/agent/my_design/
    __init__.py
```

### 2. Implement the three required classes

Your `__init__.py` must export exactly three classes, named using the
**PascalCase** form of the folder name:

| Folder name   | Required exports                                                  |
|---------------|-------------------------------------------------------------------|
| `my_design`   | `MyDesignAgent`, `MyDesignOnboardingAgent`, `MyDesignResumeParser`|
| `default`     | `DefaultAgent`, `DefaultOnboardingAgent`, `DefaultResumeParser`   |
| `react_agent` | `ReactAgentAgent`, `ReactAgentOnboardingAgent`, `ReactAgentResumeParser` |

Each class must extend the corresponding ABC from `base.py`:

```python
# backend/agent/my_design/__init__.py

from backend.agent.base import Agent, OnboardingAgent, ResumeParser

class MyDesignAgent(Agent):
    def __init__(self, model, search_api_key="", adzuna_app_id="",
                 adzuna_app_key="", adzuna_country="us",
                 jsearch_api_key="", conversation_id=None):
        self.model = model
        # ... store other args ...

    def run(self, messages):
        # Yield SSE event dicts — see base.py for the full protocol
        yield {"event": "text_delta", "data": {"content": "Hello!"}}
        yield {"event": "done", "data": {"content": "Hello!"}}


class MyDesignOnboardingAgent(OnboardingAgent):
    def __init__(self, model):
        self.model = model

    def run(self, messages):
        # Same SSE protocol as Agent.run(), plus "onboarding_complete"
        yield {"event": "text_delta", "data": {"content": "Welcome!"}}
        yield {"event": "onboarding_complete", "data": {}}
        yield {"event": "done", "data": {"content": "Welcome!"}}


class MyDesignResumeParser(ResumeParser):
    def __init__(self, model):
        self.model = model

    def parse(self, raw_text):
        # Return structured resume data as a dict
        return {"name": "...", "experience": []}
```

#### ABC reference

| ABC               | Constructor args                                                                 | Abstract method          |
|-------------------|----------------------------------------------------------------------------------|--------------------------|
| `Agent`           | `model`, `search_api_key`, `adzuna_app_id`, `adzuna_app_key`, `adzuna_country`, `jsearch_api_key`, `conversation_id` | `run(messages) → Generator[dict]` |
| `OnboardingAgent` | `model`                                                                          | `run(messages) → Generator[dict]` |
| `ResumeParser`    | `model`                                                                          | `parse(raw_text) → dict`          |

See `base.py` docstrings for the full SSE event protocol that `run()` must yield.

### 3. Use shared tools

Agent tools live in `backend/agent/tools/` and are available to all designs.
Call `get_tool_definitions()` to retrieve tool metadata and `execute(name, args)`
to run a tool. Your design is responsible for adapting tool definitions to
whatever format your LLM framework expects (e.g. OpenAI function-calling
schema, Anthropic tool-use blocks, etc.).

### 4. Activate your design

Set the config value — either in `config.json`:

```json
{
  "agent": {
    "design": "my_design"
  }
}
```

or via the environment variable:

```bash
export AGENT_DESIGN=my_design
```

The application must be restarted for a design change to take effect (the
classes are resolved at import time).

---

## Extant Designs

| Design name | Folder                   | Description                                  |
|-------------|--------------------------|----------------------------------------------|
| `default`   | `backend/agent/default/` | Monolithic ReAct loop (reason → act → observe). Each agent streams a tool-calling loop powered by LangChain `bind_tools`. This is the simplest possible design and the default. |

### `default` — Monolithic ReAct Loop

**Files:**

| File                  | Class                      | Description                              |
|-----------------------|----------------------------|------------------------------------------|
| `agent.py`            | `DefaultAgent`             | Main chat agent — multi-turn ReAct loop with all tools |
| `onboarding_agent.py` | `DefaultOnboardingAgent`   | Onboarding interview — ReAct loop, emits `[ONBOARDING_COMPLETE]` marker |
| `resume_parser.py`    | `DefaultResumeParser`      | Single-shot LLM call — parses raw text to structured JSON, no tools |
| `prompts.py`          | —                          | System prompt templates for all three agents |

**How it works:**

1. The agent converts all `AgentTools` definitions to LangChain `StructuredTool`
   objects and calls `model.bind_tools(tools)`.
2. On each `run()` call, it builds a message list (system prompt + conversation
   history) and enters a loop (max 15 iterations).
3. Each iteration streams the LLM response, yielding `text_delta` SSE events.
4. If the response includes tool calls, they are executed via `AgentTools.execute()`,
   results are appended as `ToolMessage`s, and the loop continues.
5. When the LLM responds without tool calls, the loop exits and a `done` event
   is yielded.
