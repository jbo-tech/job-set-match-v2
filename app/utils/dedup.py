"""Déduplication d'URLs sur une fenêtre glissante.

Empêche les analyses multiples sur la même offre dans une courte fenêtre
(double-clic accidentel, bug du plugin) qui coûteraient des appels API
redondants.
"""

import time


class UrlDeduplicator:
    """Cache TTL en mémoire pour ignorer les URLs récemment vues."""

    def __init__(self, window_seconds: int = 30) -> None:
        self.window = window_seconds
        self._cache: dict[str, float] = {}

    def is_duplicate(self, url: str) -> bool:
        """Retourne True si l'URL a déjà été vue dans la fenêtre.

        Si False, l'URL est enregistrée pour les prochains appels.
        """
        now = time.monotonic()
        # Nettoyage des entrées expirées
        expired = [k for k, ts in self._cache.items() if now - ts > self.window]
        for k in expired:
            del self._cache[k]

        if url in self._cache:
            return True

        self._cache[url] = now
        return False

    def clear(self) -> None:
        """Vide le cache (utile en tests)."""
        self._cache.clear()
