"""LiteLLM model factory.

Builds LiteLLM model identifiers and provides a thin config wrapper
for passing to litellm.completion().
"""

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Default models per provider
DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-5-20250929",
    "openai": "gpt-4o",
    "gemini": "gemini-2.0-flash",
    "ollama": "llama3.1",
}


@dataclass
class LLMConfig:
    """Configuration passed to litellm.completion() calls."""
    model: str
    api_key: str = ""
    api_base: str | None = None
    max_tokens: int = 4096
    extra_kwargs: dict = field(default_factory=dict)


def create_llm_config(
    provider_name: str, api_key: str, model: str = ""
) -> LLMConfig:
    """Create an LLMConfig for the given provider.

    Args:
        provider_name: One of "anthropic", "openai", "gemini", "ollama"
        api_key: API key for the provider (ignored for Ollama)
        model: Optional model override; each provider has a sensible default

    Returns:
        An LLMConfig dataclass with the litellm model string and credentials.

    Raises:
        ValueError: If provider_name is not recognized
    """
    resolved_model = model or DEFAULT_MODELS.get(provider_name, "")

    if provider_name == "anthropic":
        litellm_model = f"anthropic/{resolved_model}"
    elif provider_name == "openai":
        litellm_model = f"openai/{resolved_model}"
    elif provider_name == "gemini":
        litellm_model = f"gemini/{resolved_model}"
    elif provider_name == "ollama":
        litellm_model = f"ollama_chat/{resolved_model}"
    else:
        available = list(DEFAULT_MODELS.keys())
        raise ValueError(
            f"Unknown LLM provider: {provider_name}. Available: {available}"
        )

    config = LLMConfig(
        model=litellm_model,
        api_key=api_key,
        api_base="http://localhost:11434" if provider_name == "ollama" else None,
    )

    logger.info(
        "Created LLM config: %s (model=%s)",
        provider_name,
        litellm_model,
    )
    return config
