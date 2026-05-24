"""Configuration centralisée chargée depuis les variables d'environnement."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Paramètres applicatifs lus depuis .env."""

    # Obsidian — chemins détaillés dans vault_layout.yaml (§6 spec)
    obsidian_vault_path: Path

    # API keys
    anthropic_api_key: str
    brave_api_key: str = ""

    # Sécurité
    auth_token: str

    # Score gate
    score_threshold: float = 0.0

    # Modèles LLM — per-service overrides, fallback sur default_model
    default_model: str = "claude-sonnet-4-20250514"
    analysis_model: str = ""
    company_model: str = ""
    generation_model: str = ""
    max_tokens: int = 8192
    analysis_temperature: float = 0.2
    generation_temperature: float = 0.7

    # API keys providers (Anthropic est obligatoire, les autres optionnels)
    openai_api_key: str = ""
    mistral_api_key: str = ""
    deepseek_api_key: str = ""
    groq_api_key: str = ""
    google_api_key: str = ""

    # Serveur
    host: str = "127.0.0.1"
    port: int = 8000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    def resolve_model(self, service: str) -> str:
        """Resolve model_id for a service, falling back to default_model."""
        override = getattr(self, f"{service}_model", "")
        return override or self.default_model

    @property
    def api_keys(self) -> dict[str, str]:
        """Provider name → API key mapping for LLM client factory."""
        keys: dict[str, str] = {"anthropic": self.anthropic_api_key}
        for provider in ("openai", "mistral", "deepseek", "groq", "google"):
            key = getattr(self, f"{provider}_api_key", "")
            if key:
                keys[provider] = key
        return keys


@lru_cache
def get_settings() -> Settings:
    """Retourne l'instance Settings unique (cached)."""
    return Settings()
