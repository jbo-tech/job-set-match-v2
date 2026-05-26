"""Suivi des tokens consommés par les appels Claude.

Loggue chaque appel API avec input/output tokens et coût estimé.
Maintient un compteur en mémoire pour la session courante.
"""

import logging
from dataclasses import dataclass, field
from threading import Lock

from app.config import get_app_config
from app.utils.pricing import resolve_model_pricing

logger = logging.getLogger(__name__)


@dataclass
class TokenStats:
    """Cumulatif des tokens consommés sur la session."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    cost_usd: float = 0.0
    calls: int = 0
    by_operation: dict[str, dict[str, float]] = field(default_factory=dict)


_stats = TokenStats()
# threading.Lock intentionnel : les opérations protégées sont purement synchrones
# (arithmétique sur compteurs), et le module peut être appelé depuis le CLI (sync).
_lock = Lock()


def log_usage(usage, operation: str, model_id: str | None = None) -> float:
    """Loggue l'usage d'un appel LLM et retourne le coût estimé en USD.

    `usage` peut être un objet Anthropic Usage, un LLMResponse Usage,
    ou tout objet avec les attributs token count.
    `model_id` est le modèle réel utilisé (fallback sur config.yaml default).
    """
    if model_id is None:
        model_id = get_app_config().llm.models.default
    pricing = resolve_model_pricing(model_id)

    in_tokens = getattr(usage, "input_tokens", 0)
    out_tokens = getattr(usage, "output_tokens", 0)
    cache_create = getattr(usage, "cache_creation_input_tokens", 0) or 0
    cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0

    cost = (
        in_tokens * pricing["input"]
        + out_tokens * pricing["output"]
        + cache_create * pricing["cache_write"]
        + cache_read * pricing["cache_read"]
    )

    with _lock:
        _stats.input_tokens += in_tokens
        _stats.output_tokens += out_tokens
        _stats.cache_creation_tokens += cache_create
        _stats.cache_read_tokens += cache_read
        _stats.cost_usd += cost
        _stats.calls += 1
        op_stats = _stats.by_operation.setdefault(
            operation,
            {"input": 0, "output": 0, "cache_create": 0, "cache_read": 0, "cost": 0.0, "calls": 0},
        )
        op_stats["input"] += in_tokens
        op_stats["output"] += out_tokens
        op_stats["cache_create"] += cache_create
        op_stats["cache_read"] += cache_read
        op_stats["cost"] += cost
        op_stats["calls"] += 1

    logger.info(
        "[%s] tokens in=%d out=%d cache_create=%d cache_read=%d coût=$%.4f (cumul: $%.4f)",
        operation,
        in_tokens,
        out_tokens,
        cache_create,
        cache_read,
        cost,
        _stats.cost_usd,
    )
    return cost


def get_stats() -> TokenStats:
    """Retourne le cumul de la session courante."""
    with _lock:
        return TokenStats(
            input_tokens=_stats.input_tokens,
            output_tokens=_stats.output_tokens,
            cache_creation_tokens=_stats.cache_creation_tokens,
            cache_read_tokens=_stats.cache_read_tokens,
            cost_usd=_stats.cost_usd,
            calls=_stats.calls,
            by_operation={k: dict(v) for k, v in _stats.by_operation.items()},
        )


def reset_stats() -> None:
    """Réinitialise le compteur (utile en tests)."""
    with _lock:
        _stats.input_tokens = 0
        _stats.output_tokens = 0
        _stats.cache_creation_tokens = 0
        _stats.cache_read_tokens = 0
        _stats.cost_usd = 0.0
        _stats.calls = 0
        _stats.by_operation.clear()
