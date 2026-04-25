"""Tests de l'endpoint /api/ask + /api/ask/stream (Sprint 3.2).

On utilise le TestClient FastAPI avec lifespan complet (KBStore + ClaudeClient).
ClaudeClient utilise un fake SDK pour ne pas faire d'appels réseau.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.llm.claude import ClaudeClient

# ────────────────────────── Helpers de mock ──────────────────────────

def _fake_claude_message(text: str = "Voici la réponse."):
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)],
        stop_reason="end_turn",
        usage=SimpleNamespace(
            input_tokens=200, output_tokens=80,
            cache_creation_input_tokens=0, cache_read_input_tokens=0,
        ),
    )


def _make_fake_claude_client(response_text: str = "Réponse Claude mockée"):
    """Construit un ClaudeClient avec un fake SDK pour les tests."""
    sdk = SimpleNamespace()
    sdk.messages = SimpleNamespace()
    sdk.messages.create = AsyncMock(return_value=_fake_claude_message(response_text))
    return ClaudeClient(api_key="test-fake", sdk_client=sdk)


# ────────────────────────── Fixture client (avec mock Claude injecté) ──────────────────────────

@pytest.fixture
def client(monkeypatch, tmp_path):
    """App fraîche avec :
      - vraies KB V1 chargées (KB_DATA_DIR=../data)
      - ClaudeClient mocké (pas d'appel Anthropic réseau)
    """
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
    monkeypatch.setenv("KB_DATA_DIR", "../data")

    from app import settings as settings_module
    settings_module.get_settings.cache_clear()

    from app.main import create_app
    app = create_app()

    # On override le ClaudeClient APRÈS le lifespan boot pour injecter notre mock
    with TestClient(app) as c:
        app.state.claude_client = _make_fake_claude_client(
            "Synthèse : 1 mois de préavis après période d'essai. [ART_CCN]"
        )
        yield c


# ────────────────────────── Cas pertinent (RAG match → Claude) ──────────────────────────

class TestAskJsonOK:
    def test_question_juridique_pertinente(self, client):
        r = client.post("/api/ask", json={
            "question": "Quelle durée de préavis en cas de licenciement ?",
            "module": "juridique",
        })
        assert r.status_code == 200
        body = r.json()
        assert body["module"] == "juridique"
        assert body["hors_corpus"] is False
        assert body["confidence"]["label"] in ("high", "medium")
        assert body["confidence"]["score"] > 0
        assert body["n_results"] > 0
        assert "1 mois" in body["answer"]  # vient du mock Claude

    def test_sources_renvoyees(self, client):
        r = client.post("/api/ask", json={
            "question": "préavis licenciement",
            "module": "juridique",
        })
        body = r.json()
        assert len(body["sources"]) > 0
        assert all("id" in s for s in body["sources"])
        assert all("score" in s for s in body["sources"])


# ────────────────────────── Cas hors_corpus (pas d'appel Claude) ──────────────────────────

class TestAskHorsCorpus:
    def test_question_hors_corpus_renvoie_fallback(self, client):
        r = client.post("/api/ask", json={
            "question": "Recette de la quiche lorraine ?",
            "module": "rh",  # KB RH n'a aucun mot lié à quiche
        })
        assert r.status_code == 200
        body = r.json()
        assert body["hors_corpus"] is True
        assert "pas d'information fiable" in body["answer"].lower()
        assert body["confidence"]["label"] == "none"

    def test_stopwords_uniquement_hors_corpus(self, client):
        r = client.post("/api/ask", json={
            "question": "le la de du les des",
            "module": "juridique",
        })
        body = r.json()
        assert body["hors_corpus"] is True


# ────────────────────────── Validation Pydantic ──────────────────────────

class TestAskValidation:
    def test_question_vide_rejetee(self, client):
        r = client.post("/api/ask", json={"question": "", "module": "juridique"})
        assert r.status_code == 422

    def test_module_inconnu_rejete(self, client):
        r = client.post("/api/ask", json={"question": "test", "module": "inexistant"})
        assert r.status_code == 422

    def test_payload_manquant_rejete(self, client):
        r = client.post("/api/ask", json={})
        assert r.status_code == 422


# ────────────────────────── Streaming SSE ──────────────────────────

class TestAskStream:
    def test_stream_hors_corpus_envoie_fallback_puis_done(self, client):
        # Streaming avec une question HS — pas d'appel Claude, juste fallback
        r = client.post("/api/ask/stream", json={
            "question": "recette quiche",
            "module": "rh",
        })
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")
        body = r.text
        # On doit avoir au moins un event delta + un event done
        assert "data: " in body
        assert '"type": "delta"' in body
        assert '"type": "done"' in body
        # Le fallback doit apparaître dans les deltas
        assert "pas d'information" in body.lower() or "pôle juridique" in body.lower()


# ────────────────────────── Module spécifique : juridique ──────────────────────────

class TestModuleJuridique:
    """Sprint 3.2 cible juridique en priorité (cutover Phase 1 Sprint 7)."""

    def test_question_classification_emplois(self, client):
        r = client.post("/api/ask", json={
            "question": "Comment fonctionne la pesée des emplois ALISFA ?",
            "module": "juridique",
        })
        assert r.status_code == 200
        body = r.json()
        assert body["module"] == "juridique"
        # On doit avoir trouvé au moins quelques sources pertinentes
        assert body["n_results"] >= 1
