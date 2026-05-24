"""Tests pour CoverLetterGenerator (mock LLMClient + DocumentLoader)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.llm.protocol import LLMResponse, Usage
from app.models import (
    AnalysisResult,
    CareerFitAnalysis,
    CompetitiveProfile,
    JobSummary,
    ProfileMatchAssessment,
    ShouldApply,
    StrategicRecommendations,
)
from app.services import cover_letter as cl_module
from app.services.cover_letter import CoverLetterError, CoverLetterGenerator


@pytest.fixture(autouse=True)
def _stub_log_usage(monkeypatch):
    monkeypatch.setattr(cl_module, "log_usage", lambda *a, **kw: 0.0)


def _doc_loader() -> MagicMock:
    loader = MagicMock()
    loader.build_system_blocks.return_value = [
        {"type": "text", "text": "SYSTEM_INSTRUCTION_STUB"},
        {
            "type": "text",
            "text": "<documents>fake cacheable docs</documents>",
            "cache_control": {"type": "ephemeral"},
        },
        {
            "type": "text",
            "text": "<documents>fake non-cacheable docs</documents>",
        },
    ]
    loader.build_system_text.return_value = (
        "SYSTEM_INSTRUCTION_STUB\n\n"
        "<documents>fake cacheable docs</documents>\n\n"
        "<documents>fake non-cacheable docs</documents>"
    )
    return loader


def _client() -> MagicMock:
    client = MagicMock()
    client.model_id = "claude-test"
    client.complete = AsyncMock()
    return client


def _analysis() -> AnalysisResult:
    return AnalysisResult(
        jobSummary=JobSummary(
            jobTitle="Data Scientist",
            jobCompany="Acme",
            jobLocation="Paris",
            jobOverview="Mission data.",
            jobPainPointsAnalysis=["pain 1"],
            jobFailureFactors=[],
        ),
        careerFitAnalysis=CareerFitAnalysis(
            careerAnalysis=["point 1"],
            careerDevelopmentRating=8,
        ),
        profileMatchAssessment=ProfileMatchAssessment(
            profileMatchAnalysis=["match 1"],
            matchCompatibilityRating=7,
        ),
        competitiveProfile=CompetitiveProfile(
            competitiveAnalysis=["compet 1"],
            successProbabilityRating=6,
        ),
        strategicRecommendations=StrategicRecommendations(
            shouldApply=ShouldApply(
                decision=True,
                explanation="Go.",
                chanceRating=7,
            ),
            keyPointsInJobOffer=["kp"],
            matchingPointsWithProfile=["mp"],
            keyWordsToUse=["python"],
            preparationSteps="prep",
            interviewFocusAreas="focus",
        ),
    )


def _text_response(text: str) -> LLMResponse:
    return LLMResponse(
        text=text,
        usage=Usage(input_tokens=100, output_tokens=250),
        model="claude-test",
        stop_reason="end_turn",
    )


async def test_generate_returns_letter_text():
    c = _client()
    c.complete.return_value = _text_response(
        "Madame, Monsieur,\nVoici ma lettre de motivation.\nCordialement,"
    )

    gen = CoverLetterGenerator(c, _doc_loader())
    letter = await gen.generate(_analysis(), "Contenu de l'offre")

    assert "Madame, Monsieur" in letter
    assert "Cordialement" in letter
    c.complete.assert_called_once()


async def test_generate_passes_docs_and_analysis():
    c = _client()
    c.complete.return_value = _text_response("Lettre.")

    loader = _doc_loader()
    gen = CoverLetterGenerator(c, loader)
    await gen.generate(_analysis(), "Offre Data Scientist chez Acme")

    loader.build_system_blocks.assert_called_once()
    loader.build_system_text.assert_called_once()

    call = c.complete.call_args
    assert call.kwargs["temperature"] == 0.7
    system_blocks = call.kwargs["system_blocks"]
    assert len(system_blocks) == 3
    assert system_blocks[1]["cache_control"] == {"type": "ephemeral"}
    assert "cacheable docs" in system_blocks[1]["text"]
    assert "cache_control" not in system_blocks[2]

    user_content = call.kwargs["messages"][0]["content"]
    assert "Offre Data Scientist chez Acme" in user_content
    assert "Data Scientist" in user_content
    assert "Acme" in user_content


async def test_generate_raises_on_empty_response():
    c = _client()
    c.complete.return_value = LLMResponse(
        text="",
        usage=Usage(),
        model="claude-test",
        stop_reason="end_turn",
    )

    gen = CoverLetterGenerator(c, _doc_loader())
    with pytest.raises(CoverLetterError, match="vide"):
        await gen.generate(_analysis(), "Offre")


async def test_generate_strips_whitespace():
    c = _client()
    c.complete.return_value = _text_response("\n\n  Lettre avec espaces  \n\n")

    gen = CoverLetterGenerator(c, _doc_loader())
    letter = await gen.generate(_analysis(), "Offre")
    assert letter == "Lettre avec espaces"
