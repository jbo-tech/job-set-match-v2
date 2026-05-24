"""Tests pour resolve_model_pricing (exact match, prefix, fallback)."""

import json

import pytest

from app.utils import pricing as pricing_module
from app.utils.pricing import FALLBACK_PRICING, resolve_model_pricing


@pytest.fixture(autouse=True)
def _reset_db(monkeypatch):
    """Réinitialise le cache global de la DB pricing entre chaque test."""
    monkeypatch.setattr(pricing_module, "_db", None)


@pytest.fixture()
def pricing_file(tmp_path):
    """Crée un pricing.json temporaire avec quelques modèles."""
    data = {
        "claude-sonnet-4-20250514": {
            "input_cost_per_token": 3e-06,
            "output_cost_per_token": 15e-06,
            "cache_read_input_token_cost": 3e-07,
            "cache_creation_input_token_cost": 3.75e-06,
        },
        "claude-opus-4-20250514": {
            "input_cost_per_token": 15e-06,
            "output_cost_per_token": 75e-06,
            "cache_read_input_token_cost": 1.5e-06,
            "cache_creation_input_token_cost": 18.75e-06,
        },
        "claude-3-5-sonnet-20241022": {
            "input_cost_per_token": 3e-06,
            "output_cost_per_token": 15e-06,
        },
    }
    path = tmp_path / "pricing.json"
    path.write_text(json.dumps(data))
    return path


def test_exact_match(pricing_file):
    result = resolve_model_pricing("claude-sonnet-4-20250514", pricing_file)
    assert result["input"] == 3e-06
    assert result["output"] == 15e-06


def test_prefix_match_model_id_shorter(pricing_file):
    result = resolve_model_pricing("claude-sonnet-4", pricing_file)
    assert result["input"] == 3e-06


def test_prefix_match_picks_longest(pricing_file):
    result = resolve_model_pricing("claude-opus-4", pricing_file)
    assert result["output"] == 75e-06


def test_no_cross_model_match(pricing_file):
    """Un modèle inconnu ne doit pas matcher par sous-chaîne arbitraire."""
    result = resolve_model_pricing("gpt-4", pricing_file)
    assert result == FALLBACK_PRICING


def test_no_match_returns_fallback(pricing_file):
    result = resolve_model_pricing("totally-unknown-model", pricing_file)
    assert result["input"] == FALLBACK_PRICING["input"]
    assert result["output"] == FALLBACK_PRICING["output"]


def test_missing_file_returns_fallback(tmp_path):
    result = resolve_model_pricing("claude-sonnet-4", tmp_path / "nope.json")
    assert result == FALLBACK_PRICING
