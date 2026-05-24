"""Tests pour CompanyAnalyzer (mock LLMClient + brave_search + doc_loader)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.llm.protocol import LLMResponse, ToolCall, Usage
from app.services import company_analyzer as ca_module
from app.services.company_analyzer import CompanyAnalyzer


@pytest.fixture(autouse=True)
def _stub_log_usage(monkeypatch):
    monkeypatch.setattr(ca_module, "log_usage", lambda *a, **kw: 0.0)


def _doc_loader() -> MagicMock:
    loader = MagicMock()
    loader.build_system_blocks.return_value = [{"type": "text", "text": "system"}]
    loader.build_system_text.return_value = "system"
    return loader


def _client() -> MagicMock:
    client = MagicMock()
    client.model_id = "claude-test"
    client.complete = AsyncMock()
    client.complete_with_tools = AsyncMock()
    client.format_assistant_message = MagicMock(return_value={"role": "assistant", "content": []})
    client.format_tool_results = MagicMock(return_value=[{"role": "user", "content": []}])
    return client


def _text_response(text: str) -> LLMResponse:
    return LLMResponse(
        text=text,
        usage=Usage(input_tokens=10, output_tokens=20),
        model="claude-test",
        stop_reason="end_turn",
    )


def _tool_response(query: str, tool_id: str = "tool_1") -> LLMResponse:
    return LLMResponse(
        text="",
        tool_calls=[ToolCall(id=tool_id, name="brave_search", arguments={"query": query})],
        usage=Usage(input_tokens=10, output_tokens=20),
        model="claude-test",
        stop_reason="tool_use",
    )


async def test_returns_none_if_company_empty():
    c = _client()
    analyzer = CompanyAnalyzer(c, _doc_loader(), brave_api_key="brave-fake")
    assert await analyzer.analyze("") is None
    assert await analyzer.analyze("   ") is None
    c.complete_with_tools.assert_not_called()


async def test_returns_none_if_brave_key_missing():
    c = _client()
    analyzer = CompanyAnalyzer(c, _doc_loader(), brave_api_key="")
    assert await analyzer.analyze("Acme") is None
    c.complete_with_tools.assert_not_called()


async def test_immediate_text_response():
    c = _client()
    c.complete_with_tools.return_value = _text_response("# Rapport Acme\nContenu markdown.")

    analyzer = CompanyAnalyzer(c, _doc_loader(), brave_api_key="brave-fake")
    result = await analyzer.analyze("Acme")

    assert result is not None
    assert "Rapport Acme" in result
    assert c.complete_with_tools.await_count == 1


async def test_tool_use_loop(monkeypatch):
    brave_mock = AsyncMock(return_value="- Acme — Leader (https://acme.example)")
    monkeypatch.setattr(ca_module, "brave_web_search", brave_mock)

    c = _client()
    c.complete_with_tools.side_effect = [
        _tool_response("Acme entreprise"),
        _text_response("# Rapport final"),
    ]

    analyzer = CompanyAnalyzer(c, _doc_loader(), brave_api_key="brave-fake")
    result = await analyzer.analyze("Acme")

    assert result == "# Rapport final"
    assert brave_mock.await_count == 1
    assert c.complete_with_tools.await_count == 2


async def test_brave_error_passes_error_back(monkeypatch):
    from app.services.brave_search import BraveSearchError

    brave_mock = AsyncMock(side_effect=BraveSearchError("offline"))
    monkeypatch.setattr(ca_module, "brave_web_search", brave_mock)

    c = _client()
    c.complete_with_tools.side_effect = [
        _tool_response("Acme"),
        _text_response("Rapport partiel"),
    ]

    analyzer = CompanyAnalyzer(c, _doc_loader(), brave_api_key="brave-fake")
    result = await analyzer.analyze("Acme")
    assert result == "Rapport partiel"


async def test_max_iterations_forces_final_report(monkeypatch):
    brave_mock = AsyncMock(return_value="- result")
    monkeypatch.setattr(ca_module, "brave_web_search", brave_mock)

    c = _client()
    c.complete_with_tools.side_effect = [_tool_response("query")] * ca_module.MAX_TOOL_ITERATIONS
    c.complete.return_value = _text_response("Rapport forcé")

    analyzer = CompanyAnalyzer(c, _doc_loader(), brave_api_key="brave-fake")
    result = await analyzer.analyze("Acme")

    assert result == "Rapport forcé"
    assert c.complete_with_tools.await_count == ca_module.MAX_TOOL_ITERATIONS
    assert c.complete.await_count == 1


async def test_exception_returns_none():
    c = _client()
    c.complete_with_tools.side_effect = RuntimeError("API down")

    analyzer = CompanyAnalyzer(c, _doc_loader(), brave_api_key="brave-fake")
    assert await analyzer.analyze("Acme") is None


async def test_system_blocks_passed():
    c = _client()
    c.complete_with_tools.return_value = _text_response("# Rapport")

    loader = _doc_loader()
    analyzer = CompanyAnalyzer(c, loader, brave_api_key="brave-fake")
    await analyzer.analyze("Acme")

    loader.build_system_blocks.assert_called_once()
    loader.build_system_text.assert_called_once()
    call_kwargs = c.complete_with_tools.call_args.kwargs
    assert call_kwargs["system_blocks"] == [{"type": "text", "text": "system"}]
    assert call_kwargs["system"] == "system"
