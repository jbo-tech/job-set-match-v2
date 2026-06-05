"""Tests pour ContentFetcher (mock httpx + extraction HTML + SSRF)."""

import socket

import httpx
import pytest

from app.services.content_fetcher import (
    MAX_REDIRECTS,
    ContentFetcher,
    _extract_main_text,
    _guard_route,
    _validate_url,
)


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
    def __init__(
        self,
        status_code: int,
        text: str = "",
        *,
        is_redirect: bool = False,
        headers: dict | None = None,
    ) -> None:
        self.status_code = status_code
        self.text = text
        self.is_redirect = is_redirect
        self.headers = headers or {}

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


# ----------------------------------------------- fetch_clean_text + redirections


class _SeqMockAsyncClient:
    """Renvoie une réponse différente par appel get() et enregistre les URLs.

    Permet de simuler une chaîne de redirections (follow_redirects=False côté
    code testé : chaque saut est un get() distinct).
    """

    def __init__(self, responses):
        self._responses = list(responses)
        self.requested: list[str] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def get(self, url, *args, **kwargs):
        self.requested.append(url)
        return self._responses.pop(0)


def _patch_dns_map(monkeypatch, mapping: dict[str, str], default: str | None = None):
    """Monkeypatch getaddrinfo avec une résolution host → IP différenciée."""

    def fake(host, port, *a, **kw):
        ip = mapping.get(host, default)
        if ip is None:
            raise socket.gaierror(f"unknown host {host}")
        return [(socket.AF_INET, 0, 0, "", (ip, port or 80))]

    monkeypatch.setattr(socket, "getaddrinfo", fake)


async def test_fetch_follows_public_redirect(monkeypatch):
    """Une redirection vers un hôte public est suivie normalement."""
    _patch_dns_map(
        monkeypatch,
        {"start.example.com": "93.184.216.34", "end.example.com": "93.184.216.35"},
    )
    html = "<html><body><main><p>" + "Offre suffisamment longue. " * 10 + "</p></main></body></html>"
    client = _SeqMockAsyncClient(
        [
            _MockResponse(302, is_redirect=True, headers={"location": "https://end.example.com/job"}),
            _MockResponse(200, html),
        ]
    )
    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **kw: client)
    fetcher = ContentFetcher()
    result = await fetcher.fetch_clean_text("https://start.example.com/job")
    assert result is not None
    assert "Offre suffisamment longue" in result
    assert client.requested == [
        "https://start.example.com/job",
        "https://end.example.com/job",
    ]


async def test_fetch_blocks_redirect_to_private(monkeypatch):
    """SSRF : une redirection vers un hôte interne est bloquée AVANT la connexion."""
    _patch_dns_map(
        monkeypatch,
        {"public.example.com": "93.184.216.34", "internal.example.com": "127.0.0.1"},
    )
    client = _SeqMockAsyncClient(
        [
            _MockResponse(
                302,
                is_redirect=True,
                headers={"location": "http://internal.example.com:8000/admin"},
            ),
            _MockResponse(200, "<html><body><main>NE DOIT PAS ETRE ATTEINT</main></body></html>"),
        ]
    )
    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **kw: client)
    fetcher = ContentFetcher()
    result = await fetcher.fetch_clean_text("https://public.example.com/job")
    assert result is None
    # La cible interne n'a jamais été requêtée.
    assert client.requested == ["https://public.example.com/job"]


async def test_fetch_resolves_relative_redirect(monkeypatch):
    """Une Location relative est résolue en URL absolue avant revalidation."""
    _patch_dns_map(monkeypatch, {}, default="93.184.216.34")
    html = "<html><body><main><p>" + "Contenu valide et long. " * 10 + "</p></main></body></html>"
    client = _SeqMockAsyncClient(
        [
            _MockResponse(302, is_redirect=True, headers={"location": "/redirected"}),
            _MockResponse(200, html),
        ]
    )
    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **kw: client)
    fetcher = ContentFetcher()
    result = await fetcher.fetch_clean_text("https://example.com/start")
    assert result is not None
    assert client.requested == [
        "https://example.com/start",
        "https://example.com/redirected",
    ]


async def test_fetch_too_many_redirects_returns_none(monkeypatch):
    """Une boucle de redirections > MAX_REDIRECTS est abandonnée proprement."""
    _patch_dns_map(monkeypatch, {}, default="93.184.216.34")
    responses = [
        _MockResponse(302, is_redirect=True, headers={"location": f"https://h{i}.example.com/"})
        for i in range(MAX_REDIRECTS + 2)
    ]
    client = _SeqMockAsyncClient(responses)
    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **kw: client)
    fetcher = ContentFetcher()
    result = await fetcher.fetch_clean_text("https://h-start.example.com/")
    assert result is None
    # Requête initiale + MAX_REDIRECTS sauts, pas plus.
    assert len(client.requested) == MAX_REDIRECTS + 1


async def test_fetch_redirect_without_location_returns_none(monkeypatch):
    """Une réponse 3xx sans header Location est traitée comme un échec."""
    _patch_dns_map(monkeypatch, {}, default="93.184.216.34")
    client = _SeqMockAsyncClient([_MockResponse(302, is_redirect=True, headers={})])
    monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **kw: client)
    fetcher = ContentFetcher()
    assert await fetcher.fetch_clean_text("https://example.com/start") is None


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


# -------------------------------------------------- Playwright _guard_route (SSRF)


class _FakeRequest:
    def __init__(self, url: str, navigation: bool = True):
        self.url = url
        self._nav = navigation

    def is_navigation_request(self) -> bool:
        return self._nav


class _FakeRoute:
    def __init__(self, request: _FakeRequest):
        self.request = request
        self.aborted = False
        self.continued = False

    async def abort(self):
        self.aborted = True

    async def continue_(self):
        self.continued = True


async def test_guard_route_aborts_private_navigation(monkeypatch):
    """Navigation (redirection) vers un hôte interne : avortée."""
    _patch_dns(monkeypatch, "127.0.0.1")
    route = _FakeRoute(_FakeRequest("http://internal.test/admin"))
    await _guard_route(route)
    assert route.aborted is True
    assert route.continued is False


async def test_guard_route_allows_public_navigation(monkeypatch):
    _patch_dns(monkeypatch, "93.184.216.34")
    route = _FakeRoute(_FakeRequest("https://example.com/job"))
    await _guard_route(route)
    assert route.continued is True
    assert route.aborted is False


async def test_guard_route_skips_subresources(monkeypatch):
    """Une sous-ressource (non navigation) n'est pas revalidée → laissée passer."""
    _patch_dns(monkeypatch, "127.0.0.1")
    route = _FakeRoute(_FakeRequest("http://internal.test/img.png", navigation=False))
    await _guard_route(route)
    assert route.continued is True
    assert route.aborted is False


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
