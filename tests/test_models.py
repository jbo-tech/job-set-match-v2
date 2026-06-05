"""Tests des bornes de validation sur les schémas Pydantic."""

import pytest
from pydantic import ValidationError

from app.models import AnalyzeRequest

# Doit rester aligné sur AnalyzeRequest.content (max_length) et MAX_CLI_CONTENT.
MAX_CONTENT = 50_000


def test_content_rejected_above_max_length():
    """Un payload `content` au-delà de la borne est refusé (anti-coût LLM)."""
    with pytest.raises(ValidationError):
        AnalyzeRequest(
            url="https://example.com/job",
            title="Titre",
            content="x" * (MAX_CONTENT + 1),
        )


def test_content_accepted_at_max_length():
    req = AnalyzeRequest(
        url="https://example.com/job",
        title="Titre",
        content="x" * MAX_CONTENT,
    )
    assert len(req.content) == MAX_CONTENT
