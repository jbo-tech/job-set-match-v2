"""Tests du middleware d'authentification : forme d'erreur et garde de token."""

from types import SimpleNamespace

import pytest
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from app.middleware.auth import AuthMiddleware


@pytest.fixture
def client(monkeypatch):
    """App minimale protégée par AuthMiddleware ; token attendu = 'secret'."""
    monkeypatch.setattr(
        "app.middleware.auth.get_settings",
        lambda: SimpleNamespace(auth_token="secret"),
    )

    async def protected(request):
        return JSONResponse({"status": "ok"})

    app = Starlette(routes=[Route("/protected", protected, methods=["GET"])])
    app.add_middleware(AuthMiddleware)
    return TestClient(app)


def test_missing_token_returns_error_key(client):
    """401 expose `error` (cohérent avec l'API), jamais `detail`."""
    response = client.get("/protected")
    assert response.status_code == 401
    body = response.json()
    assert "error" in body
    assert "detail" not in body


def test_wrong_token_rejected(client):
    response = client.get("/protected", headers={"X-Auth-Token": "wrong"})
    assert response.status_code == 401


def test_valid_token_passes(client):
    response = client.get("/protected", headers={"X-Auth-Token": "secret"})
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
