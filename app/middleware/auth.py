"""Middleware d'authentification par token partagé.

Le CORS seul ne protège pas le serveur (il est appliqué par le navigateur).
Ce middleware vérifie un header `X-Auth-Token` partagé entre l'extension
Firefox (storage.local) et FastAPI (.env).
"""

import hmac
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import get_settings

logger = logging.getLogger(__name__)

# Endpoints accessibles sans authentification
PUBLIC_PATHS = {"/health", "/docs", "/redoc", "/openapi.json"}


class AuthMiddleware(BaseHTTPMiddleware):
    """Vérifie le header X-Auth-Token sur chaque requête (sauf chemins publics)."""

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        if request.method == "OPTIONS":
            return await call_next(request)

        token = request.headers.get("X-Auth-Token")
        expected = get_settings().auth_token

        if not token or not hmac.compare_digest(token, expected):
            logger.warning(
                "Tentative d'accès non autorisée à %s depuis %s",
                request.url.path,
                request.client.host if request.client else "unknown",
            )
            # `error` (et non `detail`) pour une forme cohérente avec le reste
            # de l'API : le service worker du plugin lit `data.error`.
            return JSONResponse(
                status_code=401,
                content={"error": "Unauthorized"},
            )

        return await call_next(request)
