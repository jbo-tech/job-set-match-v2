"""Tests pour brave_web_search (mock httpx)."""

import httpx
import pytest

from app.services.brave_search import BraveSearchError, brave_web_search


class _MockResponse:
    def __init__(self, status_code: int = 200, json_data: dict | None = None) -> None:
        self.status_code = status_code
        self._json = json_data or {}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "error", request=httpx.Request("GET", "https://x"), response=self  # type: ignore[arg-type]
            )

    def json(self) -> dict:
        return self._json


class _MockAsyncClient:
    def __init__(self, response: _MockResponse | None = None, raise_exc: Exception | None = None):
        self._response = response
        self._raise = raise_exc

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def get(self, *args, **kwargs):
        if self._raise:
            raise self._raise
        return self._response


async def test_brave_search_formats_results(monkeypatch):
    payload = {
        "web": {
            "results": [
                {"title": "Acme Corp", "description": "Leader du widget", "url": "https://acme.example"},
                {"title": "Acme Jobs", "description": "Carrières chez Acme", "url": "https://acme.example/jobs"},
            ]
        }
    }
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda *a, **kw: _MockAsyncClient(_MockResponse(200, payload)),
    )

    result = await brave_web_search("acme corp", api_key="fake-key")

    assert "Acme Corp" in result
    assert "Leader du widget" in result
    assert "https://acme.example" in result
    assert "Acme Jobs" in result


async def test_brave_search_no_results(monkeypatch):
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda *a, **kw: _MockAsyncClient(_MockResponse(200, {"web": {"results": []}})),
    )
    result = await brave_web_search("inexistant", api_key="fake-key")
    assert result == "(aucun résultat)"


async def test_brave_search_missing_api_key():
    with pytest.raises(BraveSearchError, match="non configurée"):
        await brave_web_search("test", api_key="")


async def test_brave_search_http_error(monkeypatch):
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda *a, **kw: _MockAsyncClient(raise_exc=httpx.ConnectError("boom")),
    )
    with pytest.raises(BraveSearchError, match="HTTP error"):
        await brave_web_search("test", api_key="fake-key")


async def test_brave_search_respects_count(monkeypatch):
    payload = {
        "web": {
            "results": [
                {"title": f"R{i}", "description": f"D{i}", "url": f"https://x/{i}"}
                for i in range(10)
            ]
        }
    }
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda *a, **kw: _MockAsyncClient(_MockResponse(200, payload)),
    )
    result = await brave_web_search("test", api_key="fake-key", count=3)
    # 3 lignes attendues
    assert result.count("\n") == 2
