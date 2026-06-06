"""Empreinte automatique d'un prompt.

Sert à attribuer une analyse à la version de prompt qui l'a produite, sans
maintenance manuelle : l'empreinte change dès que le texte du prompt change.
"""

import hashlib


def prompt_fingerprint(text: str) -> str:
    """Identifiant court et stable d'un prompt (sha256 tronqué à 8 hex)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]
