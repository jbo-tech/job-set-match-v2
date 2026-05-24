"""Tests pour ContentFetcher (mock httpx + extraction HTML + SSRF)."""

import socket

import httpx
import pytest

from app.services.content_fetcher import ContentFetcher, _extract_main_text, _validate_url


# ----------------------------------------------------------------- _extract_main_text


def test_extract_strips_noise_tags():
    html = """
    <html><body>
        <nav>menu</nav>
        <header>logo</header>
        <main>
            <h1>Titre offre</h1>
            <p>Description du poste qui doit être suffisamment longue pour passer
            le seuil minimum de 100 caractères imposé par l'extracteur.</p>
        </main>
        <footer>copyright</footer>
        <script>alert('x')</script>
    </body></html>
    """
    text = _extract_main_text(html)
    assert text is not None
    assert "Titre offre" in text
    assert "Description du poste" in text
    assert "menu" not in text
    assert "logo" not in text
    assert "copyright" not in text
    assert "alert" not in text


def test_extract_returns_none_if_too_short():
    html = "<html><body><p>tiny</p></body></html>"
    assert _extract_main_text(html) is None


def test_extract_compresses_blank_lines():
    html = "<html><body><p>" + ("ligne\n\n\n\n") * 30 + "</p></body></html>"
    text = _extract_main_text(html)
    assert text is not None
    assert "\n\n\n" not in text


# ------------------------------------------------------------------ fetch_clean_text


class _MockResponse:
    def __init__(self, status_code: int, text: str) -> None:
        self.status_code = status_code
        self.text = text

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "error",
                request=httpx.Request("GET", "https://x"),
                response=self,  # type: ignore[arg-type]
            )


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


async def test_fetch_clean_text_success(monkeypatch):
    html = (
        "<html><body><main><p>"
        + "Contenu réel d'une offre d'emploi suffisamment long pour passer le seuil. " * 5
        + "</p></main></body></html>"
    )
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda *a, **kw: _MockAsyncClient(_MockResponse(200, html)),
    )
    fetcher = ContentFetcher()
    result = await fetcher.fetch_clean_text("https://example.com/job")
    assert result is not None
    assert "Contenu réel" in result


async def test_fetch_clean_text_http_error_returns_none(monkeypatch):
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda *a, **kw: _MockAsyncClient(raise_exc=httpx.ConnectError("boom")),
    )
    fetcher = ContentFetcher()
    result = await fetcher.fetch_clean_text("https://example.com")
    assert result is None


async def test_fetch_clean_text_too_short_returns_none(monkeypatch):
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda *a, **kw: _MockAsyncClient(_MockResponse(200, "<html><body>x</body></html>")),
    )
    fetcher = ContentFetcher()
    result = await fetcher.fetch_clean_text("https://example.com")
    assert result is None


# --------------------------------------------------------------------- capture_pdf


async def test_capture_pdf_returns_none_without_playwright(monkeypatch):
    """Si Playwright n'est pas installé (ou simulé absent), retourne None proprement."""
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name.startswith("playwright"):
            raise ImportError("simulated absence")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    fetcher = ContentFetcher()
    result = await fetcher.capture_pdf("https://example.com")
    assert result is None


# ---------------------------------------------------------------- SSRF validation


def _patch_dns(monkeypatch, ip: str):
    """Monkeypatch socket.getaddrinfo pour retourner une IP fixe."""
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda host, port, *a, **kw: [(socket.AF_INET, 0, 0, "", (ip, port or 80))],
    )


@pytest.mark.parametrize(
    "ip",
    ["127.0.0.1", "10.0.0.1", "192.168.1.1", "172.16.0.1", "169.254.1.1"],
)
async def test_validate_url_blocks_private_ips(monkeypatch, ip):
    _patch_dns(monkeypatch, ip)
    with pytest.raises(ValueError, match="Adresse interdite"):
        await _validate_url(f"https://evil.example.com/path")


async def test_validate_url_allows_public(monkeypatch):
    _patch_dns(monkeypatch, "93.184.216.34")
    await _validate_url("https://example.com/job")


@pytest.mark.parametrize("scheme", ["ftp", "file", "gopher"])
async def test_validate_url_blocks_non_http_scheme(scheme):
    with pytest.raises(ValueError, match="Scheme interdit"):
        await _validate_url(f"{scheme}://example.com/path")


async def test_validate_url_blocks_empty_hostname():
    with pytest.raises(ValueError):
        await _validate_url("https:///path")


async def test_fetch_blocks_private_url(monkeypatch):
    _patch_dns(monkeypatch, "127.0.0.1")
    fetcher = ContentFetcher()
    assert await fetcher.fetch_clean_text("https://evil.test/job") is None


async def test_capture_pdf_blocks_private_url(monkeypatch):
    _patch_dns(monkeypatch, "10.0.0.1")
    fetcher = ContentFetcher()
    assert await fetcher.capture_pdf("https://evil.test/job") is None


# -------------------------------------------------------- Noise tags dialog/template


def test_extract_strips_dialog_and_template():
    html = """
    <html><body>
        <dialog open>Popup contenu</dialog>
        <template><div>Template caché</div></template>
        <main>
            <p>Offre d'emploi avec suffisamment de contenu pour passer le seuil des
            cent caractères imposé par l'extracteur de texte principal.</p>
        </main>
    </body></html>
    """
    text = _extract_main_text(html)
    assert text is not None
    assert "Popup contenu" not in text
    assert "Template caché" not in text
    assert "Offre d'emploi" in text


# --------------------------------------------------------- Playwright persistence


async def test_close_when_no_browser():
    """close() est safe même sans browser initialisé."""
    fetcher = ContentFetcher()
    await fetcher.close()
    assert fetcher._browser is None
    assert fetcher._playwright is None
