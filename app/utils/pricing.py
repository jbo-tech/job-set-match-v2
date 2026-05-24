"""Résolution du pricing modèle depuis pricing.json (vendored LiteLLM).

Cascade de résolution (identique à llm-sparring/budget.py) :
  1. Lookup exact par model_id dans pricing.json
  2. Lookup avec préfixe "claude-" canonique
  3. Fallback conservateur avec warning

Le fichier pricing.json est partagé avec le projet llm-sparring via chemin configurable.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

FALLBACK_PRICING = {
    "input": 3e-06,
    "output": 15e-06,
    "cache_read": 3e-07,
    "cache_write": 3.75e-06,
}

_db: dict | None = None


def _load_db(pricing_path: Path) -> dict:
    """Charge pricing.json et indexe par clé modèle. Coûts per-token."""
    if not pricing_path.exists():
        logger.warning("pricing.json introuvable : %s", pricing_path)
        return {}
    try:
        raw = json.loads(pricing_path.read_text())
    except Exception as e:
        logger.warning("Impossible de charger pricing.json : %s", e)
        return {}

    db = {}
    for key, entry in raw.items():
        if key == "sample_spec" or not isinstance(entry, dict):
            continue
        inp = entry.get("input_cost_per_token")
        out = entry.get("output_cost_per_token")
        if inp is None or out is None:
            continue
        db[key] = {
            "input": float(inp),
            "output": float(out),
            "cache_read": float(entry.get("cache_read_input_token_cost") or 0),
            "cache_write": float(entry.get("cache_creation_input_token_cost") or 0),
        }
    return db


def get_pricing_db(pricing_path: Path | None = None) -> dict:
    """Retourne la DB pricing (chargée une seule fois, lazy)."""
    global _db
    if _db is None:
        path = pricing_path or _default_pricing_path()
        _db = _load_db(path)
        if _db:
            logger.info("Pricing chargé : %d modèles depuis %s", len(_db), path)
    return _db


def _default_pricing_path() -> Path:
    """Chemin par défaut : pricing.json du projet sparring."""
    sparring = Path.home() / "Wip/coding/mcp/llm-sparring/pricing.json"
    if sparring.exists():
        return sparring
    return Path(__file__).resolve().parent.parent.parent / "pricing.json"


def resolve_model_pricing(model_id: str, pricing_path: Path | None = None) -> dict:
    """Résout le pricing per-token d'un modèle.

    Retourne un dict {input, output, cache_read, cache_write} en coût per-token.
    """
    db = get_pricing_db(pricing_path)

    if model_id in db:
        return db[model_id]

    candidates = [
        (k, db[k]) for k in db
        if k.startswith(model_id) or model_id.startswith(k)
    ]
    if candidates:
        best_key, best = max(candidates, key=lambda x: len(x[0]))
        logger.info("Pricing résolu par préfixe : %s → %s", model_id, best_key)
        return best

    logger.warning("Pricing introuvable pour %s, fallback conservateur", model_id)
    return dict(FALLBACK_PRICING)
