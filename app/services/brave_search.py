"""Helper Brave Search — appel REST direct à l'API.

Utilisé comme implémentation du tool `brave_search` exposé à Claude par
CompanyAnalyzer (boucle tool_use).
"""

import logging

import httpx

logger = logging.getLogger(__name__)

BRAVE_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"


class BraveSearchError(RuntimeError):
    """Erreur d'appel à l'API Brave Search."""


async def brave_web_search(
    query: str,
    api_key: str,
    *,
    count: int = 5,
    timeout: float = 10.0,
) -> str:
    """Effectue une recherche web Brave et retourne les résultats formatés.

    Format de retour : texte plain avec une entrée par ligne :
        - Titre — Description (URL)
    Conçu pour être directement passé à Claude comme `tool_result`.
    """
    if not api_key:
        raise BraveSearchError("BRAVE_API_KEY non configurée")

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(
                BRAVE_ENDPOINT,
                headers={
                    "Accept": "application/json",
                    "X-Subscription-Token": api_key,
                },
                params={"q": query, "count": count, "safesearch": "off"},
            )
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, httpx.TimeoutException) as e:
        logger.warning("Brave Search échec sur '%s' : %s", query, e)
        raise BraveSearchError(f"Brave Search HTTP error : {e}") from e

    results = data.get("web", {}).get("results", [])
    if not results:
        return "(aucun résultat)"

    lines = []
    for r in results[:count]:
        title = r.get("title", "").strip()
        desc = r.get("description", "").strip()
        url = r.get("url", "").strip()
        lines.append(f"- {title} — {desc} ({url})")
    return "\n".join(lines)
