"""Helpers de manipulation de chemins — slugify et protection path traversal."""

import re
from pathlib import Path

from slugify import slugify as _slugify

# Caractères interdits dans les noms de fichiers (Windows + Obsidian)
_UNSAFE_CHARS = str.maketrans({
    "/": "_",
    "\\": "_",
    ":": "-",
    "|": "-",
    "*": "_",
    "?": "",
    "<": "",
    ">": "",
    '"': "'",
})


def safe_slug(value: str, fallback: str = "unknown") -> str:
    """Slugifie une chaîne pour usage en nom de fichier/dossier.

    Retourne `fallback` si le résultat est vide.
    """
    result = _slugify(value, max_length=80, lowercase=False, separator="-")
    return result or fallback


def vault_slug(value: str, max_length: int = 80) -> str:
    """Slugifie pour Obsidian : préserve espaces et accents, retire les caractères FS interdits."""
    cleaned = value.translate(_UNSAFE_CHARS)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:max_length] if cleaned else "unknown"


def ensure_within(child: Path, parent: Path) -> Path:
    """Vérifie que `child` est strictement contenu dans `parent` après résolution.

    Lève ValueError si une tentative de path traversal est détectée.
    Retourne le chemin résolu.
    """
    parent_resolved = parent.resolve()
    child_resolved = child.resolve()
    try:
        child_resolved.relative_to(parent_resolved)
    except ValueError as e:
        raise ValueError(
            f"Path traversal détecté : {child} sort de {parent}"
        ) from e
    return child_resolved
