"""Tests des métriques Prometheus V2 (Sprint 3.3).

On teste :
  - Helpers d'enregistrement (record_*)
  - Endpoint GET /metrics (format text/plain Prometheus)
  - Intégration : un POST /api/ask augmente les compteurs
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.llm.claude import ClaudeClient
from app.metrics.prometheus import (
    REGISTRY,
    record_claude_tokens,
    record_latency,
    record_rag,
    record_request,
    render_metrics,
)

# ────────────────────────── Helpers ──────────────────────────

def _fake_claude_message(text: str = "ok"):
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)],
        stop_reason="end_turn",
        usage=SimpleNamespace(
            input_tokens=150, output_tokens=50,
            cache_creation_input_tokens=0, cache_read_input_tokens=0,
        ),
    )


def _make_fake_claude_client(text: str = "réponse mockée"):
    sdk = SimpleNamespace()
    sdk.messages = SimpleNamespace()
    sdk.messages.create = AsyncMock(return_value=_fake_claude_message(text))
    return ClaudeClient(api_key="test-fake", sdk_client=sdk)


# ────────────────────────── render_metrics() ──────────────────────────

class TestRenderMetrics:
    def test_format_prometheus_text(self):
        body, content_type = render_metrics()
        assert isinstance(body, bytes)
        # Format Prometheus standard
        assert "text/plain" in content_type
        # Au minimum, les noms de nos 5 métriques sont dans la sortie
        text = body.decode()
        assert "elisfa_v2_requests_total" in text
        assert "elisfa_v2_rag_score" in text
        assert "elisfa_v2_request_latency_seconds" in text
        assert "elisfa_v2_claude_tokens_total" in text


# ────────────────────────── Helpers d'enregistrement ──────────────────────────

class TestHelpers:
    def test_record_request_incremente_counter(self):
        # Snapshot du compteur avant/après
        before = render_metrics()[0].decode()
        record_request(module="juridique", status="ok")
        after = render_metrics()[0].decode()
        # Le label couple (juridique, ok) doit apparaître
        assert 'module="juridique"' in after
        assert 'status="ok"' in after
        # Les bytes doivent avoir changé
        assert before != after

    def test_record_rag_observe_score_et_increment_hors_corpus(self):
        record_rag(module="rh", best_score=0.0, hors_corpus=True)
        record_rag(module="rh", best_score=10.5, hors_corpus=False)
        text = render_metrics()[0].decode()
        # Histogram a un bucket spécifique pour les scores
        assert "elisfa_v2_rag_score_bucket" in text
        # Le compteur hors_corpus doit avoir une entrée pour rh
        assert 'elisfa_v2_rag_hors_corpus_total{module="rh"}' in text

    def test_record_latency_observation(self):
        record_latency(module="juridique", path="/api/ask", seconds=2.5)
        text = render_metrics()[0].decode()
        assert "elisfa_v2_request_latency_seconds" in text

    def test_record_claude_tokens_par_type(self):
        record_claude_tokens(input_tokens=200, output_tokens=80)
        record_claude_tokens(cache_read_tokens=5000)
        text = render_metrics()[0].decode()
        assert 'type="input"' in text
        assert 'type="output"' in text
        assert 'type="cache_read"' in text

    def test_record_claude_tokens_zero_ne_logue_pas(self):
        # Si tous les tokens sont 0, on ne crée pas de séries vides
        # (test négatif : pas de plantage, pas d'incrément faux)
        record_claude_tokens()  # no-op valide
        # Pas d'assertion forte — ce test vérifie juste qu'on ne crashe pas


# ────────────────────────── Endpoint /metrics ──────────────────────────

@pytest.fixture
def client(monkeypatch):
    """App fraîche avec ClaudeClient mocké, comme test_chat_endpoint."""
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
    monkeypatch.setenv("KB_DATA_DIR", "../data")

    from app import settings as settings_module
    settings_module.get_settings.cache_clear()

    from app.main import create_app
    app = create_app()
    with TestClient(app) as c:
        app.state.claude_client = _make_fake_claude_client("ok")
        yield c


class TestEndpointMetrics:
    def test_endpoint_metrics_renvoie_format_prometheus(self, client):
        r = client.get("/metrics")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/plain")
        body = r.text
        assert "elisfa_v2_requests_total" in body

    def test_metric_incremente_apres_ask(self, client):
        # 1. Snapshot initial
        before = client.get("/metrics").text

        # 2. Appel /api/ask qui devrait incrémenter le counter
        r = client.post("/api/ask", json={
            "question": "préavis licenciement",
            "module": "juridique",
        })
        assert r.status_code == 200

        # 3. Vérifier que le counter a bougé
        after = client.get("/metrics").text
        # On doit avoir une entrée juridique/ok ou juridique/hors_corpus
        # (selon le score retourné par la KB réelle)
        assert before != after
        # Au moins une trace de "juridique" dans les requests_total
        assert 'elisfa_v2_requests_total{module="juridique"' in after

    def test_metric_rag_score_observed(self, client):
        client.post("/api/ask", json={"question": "préavis", "module": "juridique"})
        body = client.get("/metrics").text
        # Histogram du score doit avoir reçu au moins une observation
        assert 'elisfa_v2_rag_score_count{module="juridique"}' in body

    def test_metric_hors_corpus_track_fallback(self, client):
        # Question hors corpus → flag levé → counter doit s'incrémenter
        client.post("/api/ask", json={"question": "recette quiche", "module": "rh"})
        body = client.get("/metrics").text
        # Selon la calibration, peut être hors_corpus=True
        # On vérifie juste que le compteur existe maintenant
        assert "elisfa_v2_rag_hors_corpus_total" in body


# ────────────────────────── Intégrité du registre ──────────────────────────

class TestRegistry:
    def test_registre_contient_les_5_metriques(self):
        # On parse les noms via render
        text = render_metrics()[0].decode()
        expected = [
            "elisfa_v2_requests_total",
            "elisfa_v2_rag_score",
            "elisfa_v2_rag_hors_corpus_total",
            "elisfa_v2_request_latency_seconds",
            "elisfa_v2_claude_tokens_total",
        ]
        for name in expected:
            assert name in text, f"Metric {name} absente du registre"

    def test_registry_isole_du_default(self):
        # On utilise un CollectorRegistry dédié, pas le default global
        # → essentiel pour éviter les DuplicatedTimeSeriesError en pytest
        assert REGISTRY is not None
        # Le registre est un CollectorRegistry, pas le default
        from prometheus_client import REGISTRY as DEFAULT_REGISTRY
        assert REGISTRY is not DEFAULT_REGISTRY
