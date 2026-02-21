"""Model listing functions for each LLM provider.

These use the raw SDKs directly (not LangChain) to list available models
from each provider's API.  Extracted from the old provider classes during
the LangChain migration so the ``/api/config/models`` endpoint can still
enumerate models without depending on the deleted provider code.
"""

import logging

import requests

logger = logging.getLogger(__name__)


def list_anthropic_models(api_key: str = "", **kwargs) -> list[dict]:
    """List available Anthropic models.

    Returns:
        List of dicts with ``id`` and ``name`` keys.
    """
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    models = []
    for model in client.models.list():
        models.append({"id": model.id, "name": getattr(model, "display_name", model.id)})
    models.sort(key=lambda m: m["id"])
    return models


def list_openai_models(api_key: str = "", **kwargs) -> list[dict]:
    """List available OpenAI chat models.

    Returns:
        List of dicts with ``id`` keys.
    """
    import openai

    client = openai.OpenAI(api_key=api_key)
    chat_prefixes = ("gpt-", "o1", "o3", "o4", "chatgpt")
    models = []
    for model in client.models.list():
        if model.id.startswith(chat_prefixes):
            models.append({"id": model.id})
    models.sort(key=lambda m: m["id"])
    return models


def list_gemini_models(api_key: str = "", **kwargs) -> list[dict]:
    """List available Google Gemini models that support content generation.

    Returns:
        List of dicts with ``id`` and ``name`` keys.
    """
    from google import genai

    client = genai.Client(api_key=api_key)
    models = []
    for model in client.models.list():
        supported = [
            a.value if hasattr(a, "value") else str(a)
            for a in (model.supported_actions or [])
        ]
        if "generateContent" not in supported:
            continue
        model_id = model.name
        if model_id.startswith("models/"):
            model_id = model_id[len("models/"):]
        models.append({"id": model_id, "name": model.display_name or model_id})
    models.sort(key=lambda m: m["id"])
    return models


def list_ollama_models(api_key: str = "", **kwargs) -> list[dict]:
    """List locally available Ollama models.

    Args:
        api_key: Unused (included for uniform signature).
        **kwargs: Optional ``base_url`` (defaults to ``http://localhost:11434``).

    Returns:
        List of dicts with ``id`` keys.
    """
    base_url = kwargs.get("base_url", "http://localhost:11434").rstrip("/")
    resp = requests.get(f"{base_url}/api/tags", timeout=10)
    resp.raise_for_status()
    data = resp.json()
    models = []
    for m in data.get("models", []):
        models.append({"id": m["name"]})
    models.sort(key=lambda m: m["id"])
    return models


# Registry mapping provider names to their listing functions.
MODEL_LISTERS: dict[str, callable] = {
    "anthropic": list_anthropic_models,
    "openai": list_openai_models,
    "gemini": list_gemini_models,
    "ollama": list_ollama_models,
}


def list_models(provider_name: str, api_key: str = "", **kwargs) -> list[dict]:
    """List available models for a provider.

    Args:
        provider_name: One of ``anthropic``, ``openai``, ``gemini``, ``ollama``.
        api_key: API key (not needed for Ollama).
        **kwargs: Extra options forwarded to the provider-specific lister.

    Returns:
        List of dicts with at least an ``id`` key.

    Raises:
        ValueError: If *provider_name* is not recognised.
    """
    lister = MODEL_LISTERS.get(provider_name)
    if not lister:
        raise ValueError(f"Unknown provider: {provider_name}")
    return lister(api_key=api_key, **kwargs)
