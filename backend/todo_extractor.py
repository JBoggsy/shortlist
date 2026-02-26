"""Application todo extraction — scrape a job URL and extract application steps via LLM.

Extracts the specific application requirements from a job posting (e.g., submit
resume, write cover letter, answer short-answer questions, complete assessments)
so they can be tracked as checkable todos per job.
"""

import json
import logging
import re

logger = logging.getLogger(__name__)

# Valid categories for application todos
VALID_CATEGORIES = {"document", "question", "assessment", "reference", "other"}

APPLICATION_TODO_PROMPT = """You are a job application requirements extractor. Given the raw text scraped from a job posting, identify the **specific application steps** the applicant must complete.

## Instructions
Extract ONLY concrete action items that the job posting explicitly asks applicants to do. These are things like:
- Documents to submit (resume, cover letter, portfolio, transcript, writing samples, etc.)
- Short-answer questions or essay prompts the applicant must respond to (include the FULL question text)
- Assessments or tests to complete (coding challenges, skills tests, personality assessments, etc.)
- References to provide (letters of recommendation, reference contacts, etc.)
- Any other specific application steps (e.g., "include salary expectations", "specify start date availability")

## Important Rules
- Only include items that are EXPLICITLY mentioned or clearly implied by the posting
- Do NOT invent generic steps — if the posting doesn't mention a cover letter, don't add one
- For questions/prompts, include the FULL question text in the description field
- Keep titles concise but descriptive
- Order items in the logical sequence they should be completed

## Output Format
Return a JSON array of objects. Each object has:
- "category": one of "document", "question", "assessment", "reference", "other"
- "title": short label (e.g., "Submit resume", "Cover letter", "Answer: Why this company?")
- "description": additional detail — for questions, include the full prompt text; for documents, note any specific requirements (e.g., "PDF format, max 2 pages"); leave empty string if no extra detail

Return valid JSON only — a JSON array, no markdown fences or extra text. If the posting has no specific application steps beyond a generic "apply" button, return an empty array []."""


def _extract_json_array(text):
    """Extract a JSON array from LLM output, handling markdown fences."""
    text = text.strip()
    # Try markdown fence
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()
    # Try direct parse
    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass
    # Try to find array in text
    bracket_match = re.search(r"\[.*\]", text, re.DOTALL)
    if bracket_match:
        try:
            result = json.loads(bracket_match.group())
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass
    return None


def _validate_todo(item, sort_order):
    """Validate and normalize a single todo item dict. Returns normalized dict or None."""
    if not isinstance(item, dict):
        return None
    title = (item.get("title") or "").strip()
    if not title:
        return None
    category = (item.get("category") or "other").strip().lower()
    if category not in VALID_CATEGORIES:
        category = "other"
    description = (item.get("description") or "").strip()
    return {
        "category": category,
        "title": title,
        "description": description,
        "sort_order": sort_order,
    }


def extract_application_todos(scraped_text, llm_model):
    """Extract application todo items from scraped job posting text using an LLM.

    Args:
        scraped_text: The scraped text content from the job posting page.
        llm_model: A LangChain BaseChatModel instance.

    Returns:
        List of dicts with keys: category, title, description, sort_order.
        Returns empty list on failure.
    """
    if not scraped_text or not llm_model:
        return []

    from langchain_core.messages import SystemMessage, HumanMessage

    messages = [
        SystemMessage(content=APPLICATION_TODO_PROMPT),
        HumanMessage(content=f"## Scraped Job Posting Text\n\n{scraped_text}"),
    ]

    try:
        logger.info("todo_extractor: invoking LLM (%d chars of scraped text)", len(scraped_text))
        response = llm_model.invoke(messages)
        response_text = response.content if isinstance(response.content, str) else str(response.content)
        raw_items = _extract_json_array(response_text)

        if raw_items is None:
            logger.warning("todo_extractor: LLM did not return valid JSON array")
            return []

        todos = []
        for i, item in enumerate(raw_items):
            validated = _validate_todo(item, sort_order=i)
            if validated:
                todos.append(validated)

        logger.info("todo_extractor: extracted %d application todos", len(todos))
        return todos

    except Exception as e:
        logger.error("todo_extractor: LLM extraction failed: %s", e)
        return []
