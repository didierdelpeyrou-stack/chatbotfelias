"""Tests du scaffold FastAPI V2 — /healthz, /readyz, /, /docs.

Sprint 2.1 — vérifications minimales :
  - L'app démarre sans erreur (lifespan OK)
  - Les endpoints health renvoient des codes/payloads attendus
  - /docs (Swagger) est accessible (preuve que FastAPI fonctionne)
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch) -> TestClient:
    """App fraîche par test — settings clear pour éviter les effets de bord."""
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")

    # Reset le cache lru sur get_settings (sinon les monkeypatch ne prennent pas)
    from app import settings as settings_module
    settings_module.get_settings.cache_clear()

    from app.main import create_app
    app = create_app()
    return TestClient(app)


class TestRoot:
    def test_root_renvoie_200_avec_metadata(self, client: TestClient):
        r = client.get("/")
        assert r.status_code == 200
        body = r.json()
        assert body["name"] == "Chatbot ELISFA V2"
        assert body["version"].startswith("2.")
        assert body["docs"] == "/docs"


class TestHealthz:
    def test_renvoie_200(self, client: TestClient):
        r = client.get("/healthz")
        assert r.status_code == 200

    def test_payload_status_ok(self, client: TestClient):
        body = client.get("/healthz").json()
        assert body["status"] == "ok"
        assert "version" in body
        assert "timestamp" in body

    def test_timestamp_iso(self, client: TestClient):
        body = client.get("/healthz").json()
        # Format ISO 8601 attendu : 2026-XX-XXTXX:XX:XX...
        assert "T" in body["timestamp"]


class TestReadyz:
    def test_ready_quand_clef_anthropic_configuree(self, client: TestClient):
        body = client.get("/readyz").json()
        assert body["status"] == "ready"
        assert body["checks"]["settings_loaded"] is True
        assert body["checks"]["anthropic_key_configured"] is True

    def test_starting_quand_clef_anthropic_absente(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "")
        from app import settings as settings_module
        settings_module.get_settings.cache_clear()

        from app.main import create_app
        app = create_app()
        with TestClient(app) as c:
            body = c.get("/readyz").json()
            assert body["status"] == "starting"
            assert body["checks"]["anthropic_key_configured"] is False

    def test_environment_renvoye(self, client: TestClient):
        body = client.get("/readyz").json()
        assert body["environment"] == "development"


class TestSwaggerDocs:
    def test_docs_accessible(self, client: TestClient):
        # FastAPI auto-génère /docs (Swagger UI)
        r = client.get("/docs")
        assert r.status_code == 200
        assert "swagger" in r.text.lower() or "openapi" in r.text.lower()

    def test_openapi_json_accessible(self, client: TestClient):
        r = client.get("/openapi.json")
        assert r.status_code == 200
        spec = r.json()
        # Les 3 endpoints qu'on a définis doivent être présents
        assert "/healthz" in spec["paths"]
        assert "/readyz" in spec["paths"]
        assert "/" in spec["paths"]


class TestLifespan:
    def test_app_demarre_sans_erreur(self, client: TestClient):
        # Si on est ici, c'est que lifespan a tourné sans crasher
        # (TestClient utilise le lifespan automatiquement)
        r = client.get("/healthz")
        assert r.status_code == 200
