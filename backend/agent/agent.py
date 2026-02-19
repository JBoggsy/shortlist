import json
import logging
import re

from backend.llm.base import LLMProvider
from backend.agent.tools import TOOL_DEFINITIONS, AgentTools
from backend.agent.user_profile import read_profile, set_onboarded
from backend.resume_parser import get_saved_resume, save_parsed_resume

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a helpful job search assistant. You help users find, research, and track job applications.

You have access to tools that let you:
- Search dedicated job board APIs (Adzuna, JSearch) for real job listings
- Search the web for general information, company research, etc.
- Scrape job posting URLs to extract details
- Add jobs to the user's tracker
- List and search jobs already being tracked (filter by status, company, title, or URL)
- Read and update a persistent user profile document

## User Profile

You maintain a user profile document that stores information about the user relevant to their job search. This profile persists across conversations.

**Reading the profile:** The current profile is provided below. You can also use the `read_user_profile` tool to get the latest version at any time (e.g., after you've updated it).

**Updating the profile:** When the user shares information about themselves — education, work experience, skills, fields of interest, salary preferences, location preferences, remote work preferences, career goals, or any other job-search-relevant details — you MUST update the profile using the `update_user_profile` tool. Always read the current profile first, merge in the new information, and write back the complete updated document. Never discard existing information unless the user explicitly corrects it.

**Referencing the profile:** When evaluating whether a job is a good fit for the user, always consider the user's profile. Compare the job's requirements, location, salary, remote policy, and other attributes against the user's preferences and qualifications. Proactively mention how well a job matches (or doesn't match) the user's profile.

**Proactive extraction:** Pay close attention to what the user says in conversation. Even if the user isn't explicitly updating their profile, extract relevant information. For example:
- "I have 5 years of Python experience" → update Skills & Expertise
- "I'm looking for remote roles in the $120k-$150k range" → update Salary Preferences and Remote Work Preferences
- "I just graduated with a CS degree from MIT" → update Education
- "I used to work at Google as a senior engineer" → update Work Experience

### Current User Profile
{user_profile}

### Resume

The user may have uploaded a resume (PDF or DOCX). Use the `read_resume` tool to access the full parsed text when you need detailed information about the user's qualifications, work history, or skills — especially when evaluating job fit or helping with application preparation.

Resume status: {resume_status}

## Job Search Behavior

When the user asks you to find jobs, search for them, extract the relevant details (company, title, location, salary, remote type, requirements, nice-to-haves, etc.), and offer to add them to the tracker. When scraping a URL, extract as much structured information as possible including requirements and nice-to-have qualifications.

Before adding a new job, check if it's already in the tracker by searching for the company name or URL to avoid duplicates.

When adding a job, always set the `job_fit` field (0-5) based on how well the job matches the user's profile. 5 = excellent fit, 0 = poor fit. Consider requirements match, salary alignment, location/remote preferences, and career goals.

Be concise and helpful. After adding jobs, confirm what was added and note how well the job matches the user's profile."""

MAX_ITERATIONS = 25


class Agent:
    def __init__(self, provider: LLMProvider, search_api_key="",
                 adzuna_app_id="", adzuna_app_key="", adzuna_country="us",
                 jsearch_api_key=""):
        self.provider = provider
        self.tools = AgentTools(
            search_api_key=search_api_key,
            adzuna_app_id=adzuna_app_id,
            adzuna_app_key=adzuna_app_key,
            adzuna_country=adzuna_country,
            jsearch_api_key=jsearch_api_key,
        )

    def run(self, messages):
        """Run the agent loop, yielding SSE event dicts.

        Yields dicts with 'event' and 'data' keys:
            - text_delta: {"content": "..."}
            - tool_start: {"id": "...", "name": "...", "arguments": {...}}
            - tool_result: {"id": "...", "name": "...", "result": {...}}
            - tool_error: {"id": "...", "name": "...", "error": "..."}
            - done: {"content": "full accumulated text"}
            - error: {"message": "..."}
        """
        working_messages = [dict(m) for m in messages]
        full_text = ""

        # Inject current user profile into the system prompt
        user_profile = read_profile()
        resume_info = get_saved_resume()
        resume_status = f"Uploaded — {resume_info['filename']}" if resume_info else "No resume uploaded"
        system_prompt = SYSTEM_PROMPT.format(user_profile=user_profile, resume_status=resume_status)

        logger.info("Agent run started — %d messages in history", len(working_messages))

        for iteration in range(MAX_ITERATIONS):
            logger.info("Agent iteration %d/%d (messages: %d)", iteration + 1, MAX_ITERATIONS, len(working_messages))
            text_accum = ""
            tool_calls = []
            iteration_started = False

            for chunk in self.provider.stream_with_tools(
                working_messages, TOOL_DEFINITIONS, system_prompt
            ):
                if chunk.type == "text":
                    # Add newline separation between text from different iterations
                    if not iteration_started and full_text:
                        separator = "\n\n"
                        text_accum += separator
                        full_text += separator
                        yield {"event": "text_delta", "data": {"content": separator}}
                    iteration_started = True
                    text_accum += chunk.content
                    full_text += chunk.content
                    yield {"event": "text_delta", "data": {"content": chunk.content}}

                elif chunk.type == "tool_calls":
                    tool_calls = chunk.tool_calls

                elif chunk.type == "error":
                    logger.error("LLM stream error: %s", chunk.content)
                    yield {"event": "error", "data": {"message": chunk.content}}
                    return

            if not tool_calls:
                logger.info("Agent done — %d iterations, %d chars of text", iteration + 1, len(full_text))
                yield {"event": "done", "data": {"content": full_text}}
                return

            # Build assistant message content blocks
            content_blocks = []
            if text_accum:
                content_blocks.append({"type": "text", "text": text_accum})
            for tc in tool_calls:
                content_blocks.append({
                    "type": "tool_use",
                    "id": tc.id,
                    "name": tc.name,
                    "input": tc.arguments,
                })
            working_messages.append({"role": "assistant", "content": content_blocks})

            # Execute tools and collect results
            tool_result_blocks = []
            for tc in tool_calls:
                logger.info("Tool call: %s — args: %s", tc.name, json.dumps(tc.arguments, default=str))
                yield {
                    "event": "tool_start",
                    "data": {"id": tc.id, "name": tc.name, "arguments": tc.arguments},
                }
                result = self.tools.execute(tc.name, tc.arguments)
                if "error" in result:
                    logger.warning("Tool error: %s — %s", tc.name, result["error"])
                    yield {
                        "event": "tool_error",
                        "data": {"id": tc.id, "name": tc.name, "error": result["error"]},
                    }
                else:
                    result_json = json.dumps(result, default=str)
                    logger.info("Tool result: %s — %d chars", tc.name, len(result_json))
                    logger.debug("Tool result full: %s — %s", tc.name, result_json)
                    yield {
                        "event": "tool_result",
                        "data": {"id": tc.id, "name": tc.name, "result": result},
                    }
                tool_result_blocks.append({
                    "type": "tool_result",
                    "tool_use_id": tc.id,
                    "content": json.dumps(result),
                })

            working_messages.append({"role": "user", "content": tool_result_blocks})

        logger.warning("Agent hit max iterations (%d)", MAX_ITERATIONS)
        yield {"event": "error", "data": {"message": "Max iterations reached"}}


# ---------------------------------------------------------------------------
# Onboarding agent
# ---------------------------------------------------------------------------

# Only profile-related tools are available during onboarding
ONBOARDING_TOOL_DEFINITIONS = [
    td for td in TOOL_DEFINITIONS
    if td["name"] in ("read_user_profile", "update_user_profile")
]

ONBOARDING_SYSTEM_PROMPT = """You are a friendly onboarding assistant for a job search application. Your goal is to learn about the user so the app can help them find the best jobs.

You have access to tools to read and update the user's profile document. The current profile is shown below.

### Current User Profile
{user_profile}

## First Message (when conversation history is empty)

If there are no prior messages in the conversation, check whether the user's profile above already contains real (non-placeholder) information.

### Brand-new user (profile is all placeholder / default content)
Start with an introductory message that:
1. Welcomes the user to the app.
2. Briefly explains the onboarding process: "I'll ask you a series of questions about your background, skills, and job preferences. This usually takes just a few minutes. Your answers will help me find jobs that are the best fit for you."
3. Encourages the user to give detailed, full-sentence answers. Frame it positively — something like: "Think of this like talking to a career consultant. The more detail you share, the better I can match you with relevant jobs. For example, instead of just 'Python', you might say 'I have 5 years of professional Python experience building web APIs and data pipelines.'"
4. Ends with your first question — ask about their current role or professional background (e.g. "To start, could you tell me about your current or most recent job title and what you do?").

### Returning user (profile already has some real content)
The user started onboarding before but didn't finish. In this case:
1. Welcome them back briefly (e.g. "Welcome back! I see we got started on your profile last time.").
2. Briefly summarize what you already know about them based on the profile content.
3. Skip any sections that already have real content — do NOT re-ask those questions.
4. Ask about the NEXT missing section that still has placeholder content (e.g. "_Not yet provided_").
5. Do NOT repeat the full onboarding explanation or encourage detailed answers again — get straight to the next question.

## Ongoing Conversation

After the first message, follow this process:

1. **Ask about ONE topic at a time.** Pick the most important missing piece of information and ask about it. Topics include:
   - Current job title / role and years of experience
   - Work experience (companies, roles, durations, highlights)
   - Education (degrees, institutions, fields of study)
   - Technical and professional skills & expertise
   - Fields / industries of interest
   - Salary range preferences
   - Location preferences (city, state, willing to relocate?)
   - Remote work preferences (remote, hybrid, onsite)
   - Job search goals (what kind of role are you looking for? what matters most?)
   - Anything else relevant (visa status, availability, etc.)
2. **After each answer**, use the `update_user_profile` tool to save the information. Condense and summarize verbose answers into concise bullet points. Always read the current profile first (it's in the system prompt, or use `read_user_profile`), merge the new info, and write back the full document.
3. **Ask relevant follow-up questions** if the answer is vague or there's a natural follow-up. For example, if they say "I'm a software engineer", ask about specific technologies, seniority level, etc.
4. **When all sections are filled**, ask: "Is there anything else you'd like me to know about your job search?" Process their answer if they have one.
5. **When done**, thank the user and let them know their profile is saved. End your final message with the exact marker `[ONBOARDING_COMPLETE]` (this signals the system to mark onboarding as done — the user will not see this marker).

## Guidelines
- Be conversational and encouraging, not robotic.
- Ask only 1-2 questions per message to avoid overwhelming the user.
- Keep your messages concise.
- Always update the profile after receiving information — don't wait until the end.
- Write a brief Summary section once you have enough context.
- Do NOT ask about topics that already have real (non-placeholder) content in the profile."""

ONBOARDING_MAX_ITERATIONS = 6


class OnboardingAgent:
    """Agent that runs the onboarding interview to populate the user profile."""

    def __init__(self, provider: LLMProvider):
        self.provider = provider
        self.tools = AgentTools(search_api_key="")

    def run(self, messages):
        """Same streaming interface as Agent.run()."""
        working_messages = [dict(m) for m in messages]
        full_text = ""

        user_profile = read_profile()
        system_prompt = ONBOARDING_SYSTEM_PROMPT.format(user_profile=user_profile)

        logger.info("OnboardingAgent run started — %d messages in history", len(working_messages))

        for iteration in range(ONBOARDING_MAX_ITERATIONS):
            logger.info("Onboarding iteration %d/%d", iteration + 1, ONBOARDING_MAX_ITERATIONS)
            text_accum = ""
            tool_calls = []
            iteration_started = False

            for chunk in self.provider.stream_with_tools(
                working_messages, ONBOARDING_TOOL_DEFINITIONS, system_prompt
            ):
                if chunk.type == "text":
                    if not iteration_started and full_text:
                        separator = "\n\n"
                        text_accum += separator
                        full_text += separator
                        yield {"event": "text_delta", "data": {"content": separator}}
                    iteration_started = True
                    text_accum += chunk.content
                    full_text += chunk.content
                    yield {"event": "text_delta", "data": {"content": chunk.content}}

                elif chunk.type == "tool_calls":
                    tool_calls = chunk.tool_calls

                elif chunk.type == "error":
                    yield {"event": "error", "data": {"message": chunk.content}}
                    return

            if not tool_calls:
                # Check if onboarding is complete
                if "[ONBOARDING_COMPLETE]" in full_text:
                    logger.info("Onboarding complete — marking user as onboarded")
                    set_onboarded(True)
                    # Strip the marker from the text sent to the user
                    clean_text = full_text.replace("[ONBOARDING_COMPLETE]", "").rstrip()
                    yield {"event": "onboarding_complete", "data": {}}
                    yield {"event": "done", "data": {"content": clean_text}}
                else:
                    yield {"event": "done", "data": {"content": full_text}}
                return

            # Build assistant message content blocks
            content_blocks = []
            if text_accum:
                content_blocks.append({"type": "text", "text": text_accum})
            for tc in tool_calls:
                content_blocks.append({
                    "type": "tool_use",
                    "id": tc.id,
                    "name": tc.name,
                    "input": tc.arguments,
                })
            working_messages.append({"role": "assistant", "content": content_blocks})

            # Execute tools
            tool_result_blocks = []
            for tc in tool_calls:
                logger.info("Onboarding tool call: %s — args: %s", tc.name, json.dumps(tc.arguments, default=str))
                yield {
                    "event": "tool_start",
                    "data": {"id": tc.id, "name": tc.name, "arguments": tc.arguments},
                }
                result = self.tools.execute(tc.name, tc.arguments)
                if "error" in result:
                    yield {
                        "event": "tool_error",
                        "data": {"id": tc.id, "name": tc.name, "error": result["error"]},
                    }
                else:
                    yield {
                        "event": "tool_result",
                        "data": {"id": tc.id, "name": tc.name, "result": result},
                    }
                tool_result_blocks.append({
                    "type": "tool_result",
                    "tool_use_id": tc.id,
                    "content": json.dumps(result),
                })

            working_messages.append({"role": "user", "content": tool_result_blocks})

            # Re-read profile for next iteration (it may have been updated by tools)
            user_profile = read_profile()
            system_prompt = ONBOARDING_SYSTEM_PROMPT.format(user_profile=user_profile)

        yield {"event": "done", "data": {"content": full_text}}


# ---------------------------------------------------------------------------
# Resume parsing agent
# ---------------------------------------------------------------------------

RESUME_PARSING_SYSTEM_PROMPT = """You are a resume parsing specialist. Your job is to take raw text extracted from a PDF or DOCX resume and produce clean, structured JSON.

The raw text often has formatting artifacts from PDF extraction: weird spacing, broken lines, garbled characters, merged words, misplaced headers, duplicated content, etc. You must intelligently clean and restructure this content.

## Output Format

Return ONLY valid JSON (no markdown fences, no explanation) with this structure:

{
  "contact_info": {
    "name": "Full Name",
    "email": "email@example.com",
    "phone": "+1-555-123-4567",
    "location": "City, State",
    "linkedin": "linkedin.com/in/...",
    "github": "github.com/...",
    "website": "..."
  },
  "summary": "A brief professional summary or objective if present in the resume.",
  "work_experience": [
    {
      "company": "Company Name",
      "title": "Job Title",
      "location": "City, State",
      "start_date": "Jan 2020",
      "end_date": "Present",
      "highlights": [
        "Key accomplishment or responsibility",
        "Another highlight"
      ]
    }
  ],
  "education": [
    {
      "institution": "University Name",
      "degree": "Bachelor of Science in Computer Science",
      "location": "City, State",
      "start_date": "2016",
      "end_date": "2020",
      "details": ["GPA: 3.8", "Honors: Magna Cum Laude"]
    }
  ],
  "skills": {
    "languages": ["Python", "JavaScript"],
    "frameworks": ["React", "Flask"],
    "tools": ["Docker", "Git"],
    "other": ["Project Management", "Agile"]
  },
  "certifications": [
    {
      "name": "AWS Solutions Architect",
      "issuer": "Amazon Web Services",
      "date": "2023"
    }
  ],
  "projects": [
    {
      "name": "Project Name",
      "description": "Brief description",
      "technologies": ["Tech1", "Tech2"],
      "url": "..."
    }
  ],
  "publications": [
    {
      "title": "Paper Title",
      "venue": "Conference/Journal",
      "date": "2023",
      "url": "..."
    }
  ],
  "awards": [
    {
      "name": "Award Name",
      "issuer": "Organization",
      "date": "2023"
    }
  ],
  "languages": [
    {
      "language": "English",
      "proficiency": "Native"
    }
  ],
  "volunteer": [
    {
      "organization": "Org Name",
      "role": "Volunteer Role",
      "start_date": "2020",
      "end_date": "2021",
      "description": "..."
    }
  ]
}

## Rules

1. Only include sections that have data in the resume. Omit empty sections entirely (don't include empty arrays).
2. For skills, group them logically. If the resume doesn't categorize them, do your best to sort them into languages, frameworks, tools, and other.
3. Fix obvious OCR/extraction errors: merged words ("PythonDeveloper" → "Python Developer"), garbled characters, broken lines that should be joined.
4. Normalize dates to a consistent format (e.g., "Jan 2020", "2020", "Jan 2020 - Present").
5. Preserve all meaningful content — don't drop information, just restructure it.
6. If something is ambiguous, make your best judgment rather than omitting it.
7. Return ONLY the JSON object. No preamble, no explanation, no markdown code fences."""


RESUME_PARSING_MAX_ITERATIONS = 3


class ResumeParsingAgent:
    """Agent that uses an LLM to clean up and structure raw resume text into JSON."""

    def __init__(self, provider: LLMProvider):
        self.provider = provider

    def parse(self, raw_text: str) -> dict:
        """Parse raw resume text into structured JSON.

        Args:
            raw_text: The raw text extracted from a PDF/DOCX resume.

        Returns:
            Structured resume data as a dictionary.

        Raises:
            RuntimeError: If the LLM fails to produce valid JSON.
        """
        messages = [
            {"role": "user", "content": f"Parse the following raw resume text into structured JSON:\n\n{raw_text}"}
        ]

        logger.info("ResumeParsingAgent: starting parse (%d chars of raw text)", len(raw_text))

        full_text = ""
        for chunk in self.provider.stream_with_tools(
            messages, [], RESUME_PARSING_SYSTEM_PROMPT
        ):
            if chunk.type == "text":
                full_text += chunk.content
            elif chunk.type == "error":
                logger.error("LLM error during resume parsing: %s", chunk.content)
                raise RuntimeError(f"LLM error: {chunk.content}")

        logger.info("ResumeParsingAgent: received %d chars of response", len(full_text))

        # Try to extract JSON from the response (LLM may wrap it in markdown fences)
        parsed = self._extract_json(full_text)
        if parsed is None:
            logger.error("ResumeParsingAgent: failed to parse JSON from LLM response")
            raise RuntimeError("LLM did not return valid JSON. Please try again.")

        # Save the parsed result
        save_parsed_resume(parsed)
        logger.info("ResumeParsingAgent: successfully parsed and saved structured resume")
        return parsed

    @staticmethod
    def _extract_json(text: str) -> dict | None:
        """Extract a JSON object from LLM output, handling markdown fences."""
        text = text.strip()

        # Try to find JSON in markdown code fences
        fence_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
        if fence_match:
            text = fence_match.group(1).strip()

        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to find the first { ... } block
        brace_match = re.search(r'\{.*\}', text, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group())
            except json.JSONDecodeError:
                pass

        return None
