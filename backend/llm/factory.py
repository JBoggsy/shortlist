import logging

from backend.llm.anthropic_provider import AnthropicProvider
from backend.llm.openai_provider import OpenAIProvider
from backend.llm.gemini_provider import GeminiProvider
from backend.llm.ollama_provider import OllamaProvider

logger = logging.getLogger(__name__)

PROVIDERS = {
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
    "gemini": GeminiProvider,
    "ollama": OllamaProvider,
}


def create_provider(name, api_key, model=None):
    """Create an LLM provider instance.

    Args:
        name: provider name ("anthropic", "openai", "gemini", "ollama")
        api_key: API key for the provider
        model: optional model override

    Returns:
        LLMProvider instance
    """
    cls = PROVIDERS.get(name)
    if not cls:
        raise ValueError(f"Unknown LLM provider: {name}. Available: {list(PROVIDERS)}")

    kwargs = {"api_key": api_key}
    if model:
        kwargs["model"] = model
    logger.info("Created LLM provider: %s (model=%s)", name, model or "default")
    return cls(**kwargs)
