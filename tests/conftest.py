"""Fixtures partagés pour pytest."""

import pytest

from app.config import AppConfig, LLMConfig, LLMModelsConfig, ServerConfig
from app.vault_layout import VaultLayout, VaultPaths


@pytest.fixture
def app_config(tmp_path):
    """AppConfig déterministe avec un vault temporaire (indépendant du filesystem hôte)."""
    vault = tmp_path / "vault"
    vault.mkdir()
    layout = VaultLayout(
        vault_root=vault,
        paths=VaultPaths(applications="04_Applications", companies="02_Companies"),
        personal_docs={},
    )
    return AppConfig(
        vault=layout,
        llm=LLMConfig(
            models=LLMModelsConfig(default="claude-test"),
            max_tokens=1024,
            temperatures={"analysis": 0.2, "generation": 0.7, "outreach": 0.5},
        ),
        server=ServerConfig(score_threshold=0),
    )
