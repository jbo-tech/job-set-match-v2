"""Chargement des prompts depuis le vault Obsidian.

Source de vérité : config.yaml > vault.prompts.
Chaque prompt est un fichier Markdown dans le vault. Le loader lit le contenu,
strip le frontmatter YAML et les blocs de code englobants, et retourne le texte
brut. Fallback sur les constantes Python (app/prompts/) si le fichier n'existe pas.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from app.vault_layout import VaultLayout

logger = logging.getLogger(__name__)


def _strip_frontmatter(text: str) -> str:
    """Retire le frontmatter YAML (--- ... ---) en tête de fichier."""
    return re.sub(r"\A---\s*\n.*?\n---\s*\n", "", text, count=1, flags=re.DOTALL)


def _strip_outer_code_fence(text: str) -> str:
    """Retire un éventuel bloc de code englobant (```...```)."""
    stripped = text.strip()
    match = re.match(
        r"^```[^\n]*\n(.*)\n```\s*$", stripped, re.DOTALL,
    )
    return match.group(1) if match else stripped


def _strip_heading(text: str) -> str:
    """Retire le premier heading Markdown (# ...) s'il est en première ligne."""
    stripped = text.lstrip()
    if stripped.startswith("#"):
        _, _, rest = stripped.partition("\n")
        return rest.lstrip()
    return text


def _clean_prompt(raw: str) -> str:
    """Pipeline de nettoyage : frontmatter → heading → code fence → strip."""
    text = _strip_frontmatter(raw)
    text = _strip_heading(text)
    text = _strip_outer_code_fence(text)
    return text.strip()


class PromptLoader:
    """Charge les prompts depuis le vault, avec fallback Python."""

    def __init__(self, vault_layout: VaultLayout) -> None:
        self.vault_layout = vault_layout
        self._cache: dict[str, str] = {}

    def load(self, key: str) -> str:
        """Retourne le prompt pour `key` (analysis, company, generation).

        Ordre : cache mémoire → fichier vault → constante Python (fallback).
        """
        if key in self._cache:
            return self._cache[key]

        prompt = self._load_from_vault(key)
        if prompt is None:
            prompt = self._load_fallback(key)

        self._cache[key] = prompt
        return prompt

    def _load_from_vault(self, key: str) -> str | None:
        """Tente de charger le prompt depuis le vault."""
        if key not in self.vault_layout.prompts:
            return None

        path = self.vault_layout.resolve_prompt(key)
        if not path.exists():
            logger.warning("Prompt vault manquant : %s", path)
            return None

        raw = path.read_text(encoding="utf-8")
        prompt = _clean_prompt(raw)
        if not prompt:
            logger.warning("Prompt vault vide après nettoyage : %s", path)
            return None

        logger.info("Prompt '%s' chargé depuis le vault (%d chars)", key, len(prompt))
        return prompt

    def _load_fallback(self, key: str) -> str:
        """Charge depuis les constantes Python (app/prompts/)."""
        from app.prompts import (
            ANALYSIS_PROMPT,
            COMPANY_PROMPT,
            GENERATION_PROMPT,
            OUTREACH_PROMPT,
        )

        fallbacks = {
            "analysis": ANALYSIS_PROMPT,
            "company": COMPANY_PROMPT,
            "generation": GENERATION_PROMPT,
            "outreach": OUTREACH_PROMPT,
        }
        if key not in fallbacks:
            raise KeyError(f"Prompt inconnu et pas de fallback : {key}")

        logger.info("Prompt '%s' : fallback sur constante Python", key)
        return fallbacks[key]

    def invalidate(self, key: str | None = None) -> None:
        """Vide le cache (tout ou une clé spécifique)."""
        if key:
            self._cache.pop(key, None)
        else:
            self._cache.clear()
