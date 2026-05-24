"""Tests pour OutreachGenerator (mock LLMClient + DocumentLoader)."""

import json
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
from app.services import outreach_generator as og_module
from app.services.outreach_generator import OutreachError, OutreachGenerator


@pytest.fixture(autouse=True)
def _stub_log_usage(monkeypatch):
    monkeypatch.setattr(og_module, "log_usage", lambda *a, **kw: 0.0)


def _doc_loader() -> MagicMock:
    loader = MagicMock()
    loader.build_system_blocks.return_value = [
        {"type": "text", "text": "SYSTEM"},
    ]
    loader.build_system_text.return_value = "SYSTEM"
    return loader


def _client() -> MagicMock:
    client = MagicMock()
    client.model_id = "claude-test"
    client.complete = AsyncMock()
    return client


def _analysis() -> AnalysisResult:
    return AnalysisResult(
        jobSummary=JobSummary(
            jobTitle="Data Engineer",
            jobCompany="Acme",
            jobLocation="Paris",
            jobOverview="Mission data.",
        ),
        careerFitAnalysis=CareerFitAnalysis(careerDevelopmentRating=8),
        profileMatchAssessment=ProfileMatchAssessment(matchCompatibilityRating=7),
        competitiveProfile=CompetitiveProfile(successProbabilityRating=6),
        strategicRecommendations=StrategicRecommendations(
            shouldApply=ShouldApply(decision=True, chanceRating=7),
        ),
    )


_VALID_JSON = json.dumps({
    "accroche_linkedin": "Bonjour, votre travail sur la data chez Acme m'intéresse.",
    "email_introduction": {
        "objet": "Candidature Data Engineer — profil transformation digitale",
        "corps": "Bonjour,\n\nJe me permets de vous contacter...",
    },
    "suggestions_cv": {
        "mots_cles": ["Python", "ETL", "dbt"],
        "experiences_a_valoriser": ["Direction pôle 13 experts"],
        "competences_a_mettre_en_avant": ["Gestion de projet agile"],
        "ajustements_recommandes": ["Ajouter section compétences data"],
    },
})


def _text_response(text: str) -> LLMResponse:
    return LLMResponse(
        text=text,
        usage=Usage(input_tokens=100, output_tokens=200),
        model="claude-test",
        stop_reason="end_turn",
    )


async def test_generate_returns_outreach_result():
    c = _client()
    c.complete.return_value = _text_response(_VALID_JSON)

    gen = OutreachGenerator(c, _doc_loader(), prompt="PROMPT")
    result = await gen.generate(_analysis(), "Contenu offre")

    assert result.accroche_linkedin == "Bonjour, votre travail sur la data chez Acme m'intéresse."
    assert result.email_introduction.objet == "Candidature Data Engineer — profil transformation digitale"
    assert "Python" in result.suggestions_cv.mots_cles
    c.complete.assert_called_once()


async def test_generate_passes_docs_and_analysis():
    c = _client()
    c.complete.return_value = _text_response(_VALID_JSON)

    loader = _doc_loader()
    gen = OutreachGenerator(c, loader, prompt="PROMPT_TEST")
    await gen.generate(_analysis(), "Offre Data Engineer chez Acme")

    loader.build_system_blocks.assert_called_once()
    loader.build_system_text.assert_called_once()

    call = c.complete.call_args
    user_content = call.kwargs["messages"][0]["content"]
    assert "Offre Data Engineer chez Acme" in user_content
    assert "PROMPT_TEST" in user_content


async def test_generate_raises_on_empty_response():
    c = _client()
    c.complete.return_value = LLMResponse(
        text="",
        usage=Usage(),
        model="claude-test",
        stop_reason="end_turn",
    )

    gen = OutreachGenerator(c, _doc_loader(), prompt="P")
    with pytest.raises(OutreachError, match="vide"):
        await gen.generate(_analysis(), "Offre")


async def test_generate_raises_on_invalid_json():
    c = _client()
    c.complete.return_value = _text_response("Pas du JSON du tout")

    gen = OutreachGenerator(c, _doc_loader(), prompt="P")
    with pytest.raises(OutreachError, match="parsable"):
        await gen.generate(_analysis(), "Offre")


async def test_generate_extracts_json_from_code_fence():
    wrapped = f"Voici le résultat :\n```json\n{_VALID_JSON}\n```"
    c = _client()
    c.complete.return_value = _text_response(wrapped)

    gen = OutreachGenerator(c, _doc_loader(), prompt="P")
    result = await gen.generate(_analysis(), "Offre")

    assert result.accroche_linkedin != ""
    assert len(result.suggestions_cv.mots_cles) > 0


async def test_generate_handles_partial_result():
    partial = json.dumps({
        "accroche_linkedin": "Hello",
        "email_introduction": {"objet": "", "corps": ""},
        "suggestions_cv": {},
    })
    c = _client()
    c.complete.return_value = _text_response(partial)

    gen = OutreachGenerator(c, _doc_loader(), prompt="P")
    result = await gen.generate(_analysis(), "Offre")

    assert result.accroche_linkedin == "Hello"
    assert result.suggestions_cv.mots_cles == []
