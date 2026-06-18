"""Configuration centralisée — secrets via .env, métier via config.yaml."""

from functools import lru_cache
from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.vault_layout import VaultLayout

_CENTRAL_KEYS = Path.home() / ".config" / "llm-provider-keys" / "providers.env"
_LOCAL_ENV = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_CENTRAL_KEYS)
load_dotenv(_LOCAL_ENV, override=True)


class LLMModelsConfig(BaseModel):
    """Mapping modèles par service."""

    default: str = "claude-sonnet-4-20250514"
    analysis: str = ""
    company: str = ""
    generation: str = ""
    outreach: str = ""

    def resolve(self, service: str) -> str:
        """Retourne le modèle pour un service, fallback sur default."""
        override = getattr(self, service, "")
        return override or self.default


class LLMConfig(BaseModel):
    """Paramètres LLM (modèles, températures, limites)."""

    models: LLMModelsConfig = Field(default_factory=LLMModelsConfig)
    temperatures: dict[str, float] = Field(
        default_factory=lambda: {
            "analysis": 0.2,
            "generation": 0.7,
            "outreach": 0.5,
        }
    )
    max_tokens: int = 8192
    # Outreach = sorties courtes (accroche + email) → budget tokens réduit.
    max_tokens_outreach: int = 4096


class ServerConfig(BaseModel):
    """Paramètres serveur et métier."""

    score_threshold: float = 0.0
    host: str = "127.0.0.1"
    port: int = 8000


_PACKAGE_ROOT = Path(__file__).resolve().parent.parent
_CONFIG_DIR = Path.home() / ".config" / "jobset-match"


class AppConfig(BaseModel):
    """Configuration métier unique lue depuis ~/.config/jobset-match/config.yaml."""

    vault: VaultLayout
    llm: LLMConfig = Field(default_factory=LLMConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)


class Settings(BaseSettings):
    """Paramètres secrets lus depuis .env."""

    # API keys (Anthropic obligatoire, les autres optionnels)
    anthropic_api_key: str
    brave_api_key: str = ""

    # Sécurité
    auth_token: str

    # Providers optionnels
    openai_api_key: str = ""
    mistral_api_key: str = ""
    deepseek_api_key: str = ""
    groq_api_key: str = ""
    google_api_key: str = ""

    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

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


def load_app_config(yaml_path: Path | str | None = None) -> AppConfig:
    """Charge et valide config.yaml depuis ~/.config/jobset-match/."""
    if yaml_path is None:
        path = _CONFIG_DIR / "config.yaml"
    else:
        path = Path(yaml_path)
    if not path.exists():
        raise FileNotFoundError(
            f"config.yaml introuvable : {path.resolve()}\n"
            f"Run install.sh or copy config.example.yaml to {_CONFIG_DIR}/config.yaml"
        )
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if raw is None:
        raise ValueError(f"config.yaml vide : {path.resolve()}")
    return AppConfig(**raw)


@lru_cache
def get_app_config(yaml_path: Path | str | None = None) -> AppConfig:
    """Retourne l'instance AppConfig unique (cached)."""
    return load_app_config(yaml_path)
