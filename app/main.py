"""Application FastAPI — point d'entrée + endpoint /analyze + mode CLI."""

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_app_config, get_settings
from app.middleware.auth import AuthMiddleware
from app.models import AnalyzeRequest, AnalyzeResponse
from app.pipeline import Pipeline
from app.utils.dedup import UrlDeduplicator
from app.utils.token_logger import get_stats

# --- Logging ----------------------------------------------------------------
_log_path = Path(__file__).resolve().parent.parent / "jobsetmatch.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        RotatingFileHandler(
            _log_path, maxBytes=5_000_000, backupCount=3, encoding="utf-8"
        ),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("jobsetmatch")


# État partagé (initialisé au démarrage)
_pipeline: Pipeline | None = None
_dedup = UrlDeduplicator(window_seconds=30)
_semaphore: asyncio.Semaphore | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialisation au démarrage et nettoyage à l'arrêt."""
    global _pipeline, _semaphore
    settings = get_settings()
    app_config = get_app_config()
    logger.info("Démarrage de l'app — vault=%s", app_config.vault.vault_root)
    _pipeline = Pipeline(settings)
    _semaphore = asyncio.Semaphore(1)
    yield
    if _pipeline is not None:
        await _pipeline.content_fetcher.close()
    logger.info("Arrêt de l'app")


app = FastAPI(
    title="Job Set & Match V2",
    description="Outil personnel de veille emploi — Firefox → Claude → Obsidian",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — restreint aux extensions Firefox (en complément du token auth)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^moz-extension://.*$",
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Content-Type", "X-Auth-Token"],
)

# Auth token (vérifié sur chaque requête sauf /health, /docs)
app.add_middleware(AuthMiddleware)


# --- Endpoints --------------------------------------------------------------


@app.get("/health")
async def health() -> dict[str, str]:
    """Endpoint de santé (sans auth)."""
    return {"status": "ok"}


@app.get("/stats")
async def stats():
    """Statistiques de consommation de tokens (session courante)."""
    s = get_stats()
    return {
        "input_tokens": s.input_tokens,
        "output_tokens": s.output_tokens,
        "cache_creation_tokens": s.cache_creation_tokens,
        "cache_read_tokens": s.cache_read_tokens,
        "cost_usd": round(s.cost_usd, 6),
        "calls": s.calls,
        "by_operation": s.by_operation,
    }


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    """Analyse une offre d'emploi reçue depuis l'extension Firefox."""
    url_str = str(request.url)

    # Déduplication (bypass si refresh)
    if not request.refresh and _dedup.is_duplicate(url_str):
        logger.info("URL dupliquée ignorée : %s", url_str)
        return AnalyzeResponse(status="deduplicated")

    # Une seule analyse à la fois
    if _semaphore is None or _pipeline is None:
        raise RuntimeError("App non initialisée")
    async with _semaphore:
        return await _pipeline.run(request)


# --- Mode CLI ---------------------------------------------------------------


MAX_CLI_CONTENT = 50_000


async def _cli_main(
    url: str,
    content_path: str | None,
    *,
    refresh: bool = False,
    temperature: float | None = None,
) -> None:
    """Mode CLI : exécute le pipeline sur une URL et un fichier texte local.

    Usage :
        uv run python -m app.main https://example.com/offre [chemin/offre.txt] [--refresh] [--temperature 0.5]
        echo "contenu offre" | uv run python -m app.main https://example.com/offre
    """
    settings = get_settings()
    app_config = get_app_config()
    if temperature is not None:
        app_config = app_config.model_copy(deep=True)
        app_config.llm.temperatures["generation"] = temperature
    pipeline = Pipeline(settings, app_config)

    if content_path:
        from pathlib import Path

        content = Path(content_path).read_text(encoding="utf-8")
    else:
        content = sys.stdin.read()

    if len(content) > MAX_CLI_CONTENT:
        print(
            f"Avertissement : contenu tronqué à {MAX_CLI_CONTENT} caractères "
            f"(original : {len(content)})",
            file=sys.stderr,
        )
        content = content[:MAX_CLI_CONTENT]

    if not content.strip():
        print("Erreur : aucun contenu fourni (stdin ou argument fichier)", file=sys.stderr)
        sys.exit(1)

    request = AnalyzeRequest(url=url, title="CLI test", content=content, refresh=refresh)
    response = await pipeline.run(request)
    print(response.model_dump_json(indent=2))


if __name__ == "__main__":
    refresh_flag = False
    temperature_flag: float | None = None
    positional: list[str] = []
    raw_args = sys.argv[1:]
    i = 0
    while i < len(raw_args):
        if raw_args[i] == "--refresh":
            refresh_flag = True
        elif raw_args[i] == "--temperature" and i + 1 < len(raw_args):
            temperature_flag = float(raw_args[i + 1])
            i += 1
        else:
            positional.append(raw_args[i])
        i += 1

    if len(positional) < 1:
        print(
            "Usage : python -m app.main <URL> [chemin/offre.txt] [--refresh] [--temperature 0.5]",
            file=sys.stderr,
        )
        sys.exit(1)
    url_arg = positional[0]
    content_arg = positional[1] if len(positional) > 1 else None
    asyncio.run(
        _cli_main(url_arg, content_arg, refresh=refresh_flag, temperature=temperature_flag)
    )
