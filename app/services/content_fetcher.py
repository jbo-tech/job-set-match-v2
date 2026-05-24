"""ContentFetcher — fallback contenu (httpx + bs4) et capture PDF (Playwright).

Deux services indépendants regroupés dans une même classe car ils partagent
le même besoin (récupérer une URL) avec des sorties différentes :
- `fetch_clean_text()` : texte propre, fallback si le contenu du plugin est
  trop court (< 200 chars). HTTP simple, n'a pas accès aux pages authentifiées.
- `capture_pdf()` : PDF de la page complète via Playwright (Chromium headless).
  Pas d'accès aux sessions Firefox → pages authentifiées rendront la version
  publique ou la page de login.

Note : on appelle directement les libs Python plutôt que des serveurs MCP
externes — équivalent fonctionnel, complexité opérationnelle moindre.
"""

import asyncio
import ipaddress
import logging
import socket
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# User-Agent neutre — certains sites bloquent l'UA Python par défaut
DEFAULT_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


# --- Validation SSRF -----------------------------------------------------------


async def _validate_url(url: str) -> None:
    """Vérifie qu'une URL cible un hôte public (anti-SSRF).

    Lève ValueError si le scheme n'est pas http/https ou si l'hôte
    résout vers une adresse privée/réservée.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Scheme interdit : {parsed.scheme}")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL sans hostname")

    loop = asyncio.get_running_loop()
    try:
        infos = await loop.run_in_executor(
            None, lambda: socket.getaddrinfo(hostname, parsed.port or 80)
        )
    except socket.gaierror as e:
        raise ValueError(f"Résolution DNS impossible : {hostname}") from e

    for family, _type, _proto, _canonname, sockaddr in infos:
        addr = ipaddress.ip_address(sockaddr[0])
        if addr.is_private or addr.is_loopback or addr.is_reserved or addr.is_link_local:
            raise ValueError(
                f"Adresse interdite : {hostname} résout vers {addr}"
            )


class ContentFetcher:
    """Fallback de récupération de contenu (texte + PDF)."""

    def __init__(
        self,
        fetch_timeout: float = 15.0,
        pdf_timeout: float = 30.0,
    ) -> None:
        self.fetch_timeout = fetch_timeout
        self.pdf_timeout = pdf_timeout
        self._playwright = None
        self._browser = None

    # ----------------------------------------------------------- browser lazy

    async def _get_browser(self):
        """Retourne une instance Chromium persistante (lazy-init + crash recovery)."""
        from playwright.async_api import async_playwright

        if self._browser is not None and self._browser.is_connected():
            return self._browser

        if self._playwright is None:
            self._playwright = await async_playwright().start()

        self._browser = await self._playwright.chromium.launch(headless=True)
        return self._browser

    async def close(self) -> None:
        """Libère les ressources Playwright (appelé au shutdown)."""
        if self._browser is not None:
            try:
                await self._browser.close()
            except Exception:
                pass
            self._browser = None
        if self._playwright is not None:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None

    # ------------------------------------------------------------------ texte

    async def fetch_clean_text(self, url: str) -> str | None:
        """Récupère le texte propre d'une URL publique.

        Retourne None en cas d'échec (timeout, HTTP error, parsing, SSRF).
        Le pipeline doit alors continuer avec le contenu original du plugin.
        """
        try:
            await _validate_url(url)
        except ValueError as e:
            logger.warning("fetch_clean_text bloquée (SSRF) : %s — %s", url, e)
            return None

        try:
            async with httpx.AsyncClient(
                timeout=self.fetch_timeout,
                follow_redirects=True,
                headers={"User-Agent": DEFAULT_UA},
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                html = response.text
        except (httpx.HTTPError, httpx.TimeoutException) as e:
            logger.warning("fetch_clean_text échec sur %s : %s", url, e)
            return None

        return _extract_main_text(html)

    # -------------------------------------------------------------------- pdf

    async def capture_pdf(self, url: str) -> bytes | None:
        """Capture la page complète en PDF via Playwright (Chromium headless).

        Retourne None si Playwright n'est pas installé, en cas de timeout,
        SSRF ou d'échec navigation. Le pipeline continue sans capture.

        Prérequis : `uv run playwright install chromium`
        """
        try:
            await _validate_url(url)
        except ValueError as e:
            logger.warning("capture_pdf bloquée (SSRF) : %s — %s", url, e)
            return None

        try:
            from playwright.async_api import (
                Error as PlaywrightError,
                TimeoutError as PlaywrightTimeoutError,
            )
        except ImportError:
            logger.warning("Playwright non installé — capture PDF désactivée")
            return None

        try:
            browser = await self._get_browser()
            context = await browser.new_context(user_agent=DEFAULT_UA)
            try:
                page = await context.new_page()
                await page.goto(
                    url,
                    wait_until="networkidle",
                    timeout=self.pdf_timeout * 1000,
                )
                return await page.pdf(
                    format="A4",
                    print_background=True,
                    margin={
                        "top": "1cm",
                        "bottom": "1cm",
                        "left": "1cm",
                        "right": "1cm",
                    },
                )
            finally:
                await context.close()
        except (PlaywrightTimeoutError, PlaywrightError) as e:
            logger.warning("capture_pdf échec sur %s : %s", url, e)
            return None
        except Exception as e:  # pragma: no cover - filet de sécurité
            logger.warning("capture_pdf erreur inattendue sur %s : %s", url, e)
            return None


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------


_NOISE_TAGS = (
    "script", "style", "noscript", "nav", "header", "footer",
    "aside", "form", "dialog", "template",
)


def _extract_main_text(html: str) -> str | None:
    """Extrait le texte significatif d'une page HTML.

    Stratégie simple : retire les balises bruyantes (nav, footer, scripts...)
    puis prend `body.get_text()` avec séparateurs lisibles.
    """
    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception as e:  # pragma: no cover
        logger.warning("Parsing HTML échec : %s", e)
        return None

    for tag in soup(_NOISE_TAGS):
        tag.decompose()

    target = soup.body or soup
    text = target.get_text(separator="\n", strip=True)

    lines = [line for line in text.splitlines() if line.strip()]
    cleaned = "\n".join(lines)

    if len(cleaned) < 100:
        logger.warning("fetch_clean_text : texte extrait trop court (%d chars)", len(cleaned))
        return None

    return cleaned
