"""Chargement et validation de vault_layout.yaml.

Externalise la structure du vault Obsidian (chemins, docs perso) hors du code.
Voir APP_INTEGRATION_SPEC.md §6 pour le contrat.
"""

from __future__ import annotations

import glob
import logging
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, model_validator
from typing_extensions import Self

logger = logging.getLogger(__name__)

# Caractères qui déclenchent une résolution glob
_GLOB_CHARS = ("*", "?", "[")


class PersonalDoc(BaseModel):
    """Un document perso (fichier unique ou pattern glob)."""

    path: str
    cache: bool = True


class VaultPaths(BaseModel):
    """Chemins relatifs des dossiers structurants du vault."""

    applications: str = "04_Applications"
    companies: str = "02_Companies"
    archive: str = "04_Applications/_Archive_V1"


class VaultLayout(BaseModel):
    """Représentation typée de vault_layout.yaml."""

    vault_root: Path
    paths: VaultPaths = Field(default_factory=VaultPaths)
    personal_docs: dict[str, PersonalDoc]
    prompts: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_vault_root_exists(self) -> Self:
        if not self.vault_root.exists():
            raise ValueError(f"vault_root introuvable : {self.vault_root}")
        if not self.vault_root.is_dir():
            raise ValueError(f"vault_root n'est pas un dossier : {self.vault_root}")
        return self

    def resolve_doc(self, key: str) -> list[Path]:
        """Résout un doc perso en liste de Path absolus.

        - Si `path` ne contient pas de wildcards : retourne [vault_root / path]
          (sans vérifier l'existence — c'est au caller de gérer).
        - Si `path` contient `*`, `?` ou `[` : résolution glob, retourne la
          liste triée des matches (vide si aucun).
        """
        if key not in self.personal_docs:
            raise KeyError(f"Doc perso inconnu : {key}")

        doc = self.personal_docs[key]
        full_pattern = str(self.vault_root / doc.path)

        if any(c in doc.path for c in _GLOB_CHARS):
            matches = sorted(Path(p) for p in glob.glob(full_pattern))
            if not matches:
                logger.warning(
                    "Aucun fichier ne matche le glob pour '%s' : %s", key, full_pattern
                )
            return matches

        return [self.vault_root / doc.path]


    def resolve_prompt(self, key: str) -> Path:
        """Retourne le chemin absolu d'un prompt vault."""
        if key not in self.prompts:
            raise KeyError(f"Prompt inconnu : {key}")
        return self.vault_root / self.prompts[key]


def load_vault_layout(yaml_path: Path | str = "vault_layout.yaml") -> VaultLayout:
    """Charge et valide vault_layout.yaml depuis le disque."""
    path = Path(yaml_path)
    if not path.exists():
        raise FileNotFoundError(f"vault_layout.yaml introuvable : {path.resolve()}")

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if raw is None:
        raise ValueError(f"vault_layout.yaml vide : {path.resolve()}")

    return VaultLayout(**raw)


@lru_cache
def get_vault_layout() -> VaultLayout:
    """Instance VaultLayout unique (cached) lue depuis vault_layout.yaml à la racine."""
    return load_vault_layout()
