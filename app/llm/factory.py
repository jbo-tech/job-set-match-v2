"""Factory for creating LLM clients based on model ID prefix."""

from __future__ import annotations

import logging

from app.llm.anthropic_client import AnthropicLLMClient
from app.llm.openai_client import OpenAILLMClient
from app.llm.protocol import LLMClient

logger = logging.getLogger(__name__)

# (prefix, provider_name, base_url override or None)
_PROVIDER_REGISTRY: list[tuple[str, str, str | None]] = [
    ("claude-", "anthropic", None),
    ("gpt-", "openai", None),
    ("o1-", "openai", None),
    ("o3-", "openai", None),
    ("o4-", "openai", None),
    ("chatgpt-", "openai", None),
    ("mistral", "mistral", "https://api.mistral.ai/v1"),
    ("deepseek", "deepseek", "https://api.deepseek.com"),
    ("groq/", "groq", "https://api.groq.com/openai/v1"),
    ("gemini", "google", "https://generativelanguage.googleapis.com/v1beta/openai/"),
]


def create_llm_client(
    model_id: str,
    api_keys: dict[str, str],
) -> LLMClient:
    """Instantiate the appropriate LLMClient for a given model_id.

    Args:
        model_id: Model identifier (e.g., "claude-sonnet-4-20250514",
                  "gpt-4o-mini", "mistral-large-latest").
        api_keys: Dict of provider → API key. Expected keys:
                  "anthropic", "openai", "mistral", "deepseek", "groq", "google".
    """
    for prefix, provider, base_url in _PROVIDER_REGISTRY:
        if not model_id.startswith(prefix):
            continue

        api_key = api_keys.get(provider, "")
        if not api_key:
            raise ValueError(
                f"Pas d'API key pour le provider '{provider}' "
                f"(modèle: {model_id}). Vérifier .env."
            )

        if provider == "anthropic":
            logger.info("LLM client Anthropic : %s", model_id)
            return AnthropicLLMClient(api_key=api_key, model=model_id)

        # Groq model IDs have the "groq/" prefix stripped for the API
        actual_model = model_id.removeprefix("groq/") if provider == "groq" else model_id
        logger.info("LLM client OpenAI-compat : %s (provider=%s)", actual_model, provider)
        return OpenAILLMClient(api_key=api_key, model=actual_model, base_url=base_url)

    raise ValueError(
        f"Provider inconnu pour le modèle '{model_id}'. "
        f"Préfixes supportés : {[p for p, _, _ in _PROVIDER_REGISTRY]}"
    )
