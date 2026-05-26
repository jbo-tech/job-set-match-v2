"""Tests pour Pipeline — cache entité, flag refresh, flux principal."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.llm.protocol import LLMResponse, Usage
from app.models import (
    AnalysisResult,
    AnalyzeRequest,
    CareerFitAnalysis,
    CompetitiveProfile,
    JobSummary,
    ProfileMatchAssessment,
    ShouldApply,
    StrategicRecommendations,
)
from app.pipeline import Pipeline


def _make_analysis(company: str = "Acme Corp", decision: bool = False) -> AnalysisResult:
    return AnalysisResult(
        jobSummary=JobSummary(
            jobTitle="Data Engineer",
            jobCompany=company,
            jobLocation="Paris",
            jobOverview="Overview",
        ),
        careerFitAnalysis=CareerFitAnalysis(careerDevelopmentRating=8.0),
        profileMatchAssessment=ProfileMatchAssessment(matchCompatibilityRating=7.5),
        competitiveProfile=CompetitiveProfile(successProbabilityRating=7.0),
        strategicRecommendations=StrategicRecommendations(
            shouldApply=ShouldApply(decision=decision, chanceRating=5.0),
        ),
    )


def _make_request(refresh: bool = False) -> AnalyzeRequest:
    return AnalyzeRequest(
        url="https://example.com/job/1",
        title="Test Job",
        content="x" * 300,
        refresh=refresh,
    )


def _mock_llm_client() -> MagicMock:
    client = MagicMock()
    client.model_id = "claude-test"
    client.complete = AsyncMock()
    client.complete_with_tools = AsyncMock()
    client.format_assistant_message = MagicMock(return_value={"role": "assistant", "content": []})
    client.format_tool_results = MagicMock(return_value=[{"role": "user", "content": []}])
    return client


@pytest.fixture()
def pipeline(monkeypatch, app_config):
    """Pipeline avec tous les sous-services mockés."""
    settings = SimpleNamespace(
        anthropic_api_key="fake-key",
        brave_api_key="brave-fake",
        api_keys={"anthropic": "fake-key"},
    )

    monkeypatch.setattr("app.pipeline.create_llm_client", lambda model, keys: _mock_llm_client())
    monkeypatch.setattr("app.pipeline.PromptLoader", lambda vl: MagicMock(load=lambda key: f"PROMPT_{key}"))

    p = Pipeline(settings, app_config)
    p.offer_analyzer.analyze = AsyncMock(return_value=_make_analysis())
    p.content_fetcher.fetch_clean_text = AsyncMock(return_value=None)
    p.content_fetcher.capture_pdf = AsyncMock(return_value=None)
    p.company_analyzer.analyze = AsyncMock(return_value="# Rapport Acme")
    p.cover_letter_generator.generate = AsyncMock(return_value=None)
    p.outreach_generator.generate = AsyncMock(return_value=None)
    return p


async def test_company_cache_skips_analyzer(pipeline):
    companies = pipeline.obsidian_writer.companies_dir
    companies.mkdir(parents=True)
    (companies / "Acme Corp.md").write_text("# Acme Corp existant")

    response = await pipeline.run(_make_request())

    assert response.status == "success"
    pipeline.company_analyzer.analyze.assert_not_called()


async def test_company_cache_miss_calls_analyzer(pipeline):
    response = await pipeline.run(_make_request())

    assert response.status == "success"
    pipeline.company_analyzer.analyze.assert_awaited_once_with("Acme Corp")


async def test_url_cache_returns_deduplicated(pipeline):
    await pipeline.run(_make_request())

    response = await pipeline.run(_make_request())

    assert response.status == "deduplicated"


async def test_refresh_bypasses_url_cache(pipeline):
    await pipeline.run(_make_request())

    response = await pipeline.run(_make_request(refresh=True))

    assert response.status == "success"


async def test_refresh_bypasses_company_cache(pipeline):
    companies = pipeline.obsidian_writer.companies_dir
    companies.mkdir(parents=True)
    (companies / "Acme Corp.md").write_text("# Ancien rapport")

    response = await pipeline.run(_make_request(refresh=True))

    assert response.status == "success"
    pipeline.company_analyzer.analyze.assert_awaited_once()


async def test_url_cache_checked_before_analysis(pipeline):
    await pipeline.run(_make_request())
    pipeline.offer_analyzer.analyze.reset_mock()

    response = await pipeline.run(_make_request())

    assert response.status == "deduplicated"
    pipeline.offer_analyzer.analyze.assert_not_called()
