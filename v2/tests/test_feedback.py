"""Tests du module feedback (Sprint 4.3).

Couverture :
  - Validation Pydantic (rating ∈ {-1, 1}, longueurs)
  - Logger asynchrone (write JSONL, lecture, hash)
  - Endpoint POST /api/feedback (200, 422, compat V1)
  - Endpoint GET /api/feedback/stats (vide, peuplé, par module)
  - Compat V1 : payload V1 doit passer la validation (extra="ignore")
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.feedback.logger import (
    append_feedback,
    hash_question,
    read_all_feedbacks,
)
from app.feedback.schema import FeedbackEntry, FeedbackRequest

# ────────────────────────── Schéma ──────────────────────────

class TestFeedbackRequest:
    def test_payload_minimal_valide(self):
        r = FeedbackRequest(
            rating=1, question="Quel préavis ?", answer="1 mois.", module="juridique"
        )
        assert r.rating == 1
        assert r.module == "juridique"

    def test_rating_invalide(self):
        with pytest.raises(ValueError):
            FeedbackRequest(rating=0, question="q", answer="a", module="juridique")

    def test_rating_negatif_un_ok(self):
        r = FeedbackRequest(rating=-1, question="q", answer="a", module="juridique")
        assert r.rating == -1

    def test_module_invalide(self):
        with pytest.raises(ValueError):
            FeedbackRequest(rating=1, question="q", answer="a", module="inconnu")

    def test_question_vide_rejetee(self):
        with pytest.raises(ValueError):
            FeedbackRequest(rating=1, question="", answer="a", module="juridique")

    def test_compat_v1_champs_extra_ignores(self):
        # V1 envoie des champs supplémentaires : function, sources, profile, context...
        r = FeedbackRequest.model_validate({
            "rating": 1,
            "question": "Quel préavis ?",
            "answer": "1 mois.",
            "module": "juridique",
            "function": "ask",
            "sources": [{"id": "ART_001"}],
            "profile": "salarie",
            "context": {"ua": "..."},
            "user_agent": "Mozilla/5.0",
        })
        # Les champs extra sont silencieusement ignorés (pas d'erreur)
        assert r.rating == 1
        assert not hasattr(r, "function")

    def test_comment_trop_long_rejete(self):
        # Pydantic max_length=2000 → payload > 2000 doit être rejeté à la validation
        with pytest.raises(ValueError):
            FeedbackRequest(
                rating=-1, question="q", answer="a", module="juridique",
                comment="x" * 5000,
            )

    def test_comment_2000_exactement_accepte(self):
        # Exactement à la limite : ok, pas de tronquage perdu
        req = FeedbackRequest(
            rating=-1, question="q", answer="a", module="juridique",
            comment="x" * 2000,
        )
        entry = FeedbackEntry.from_request(req, question_hash="abc")
        assert len(entry.comment) == 2000


# ────────────────────────── Hash ──────────────────────────

class TestHash:
    def test_hash_question_stable(self):
        h1 = hash_question("Quelle est la période d'essai ?")
        h2 = hash_question("Quelle est la période d'essai ?")
        assert h1 == h2
        assert len(h1) == 12

    def test_hash_question_different(self):
        assert hash_question("question A") != hash_question("question B")

    def test_hash_question_vide(self):
        assert hash_question("") == ""


# ────────────────────────── Logger ──────────────────────────

class TestLogger:
    def test_append_feedback_ecrit_jsonl(self, tmp_path: Path, monkeypatch):
        log_file = tmp_path / "feedback.jsonl"
        monkeypatch.setenv("ELISFA_FEEDBACK_LOG", str(log_file))

        req = FeedbackRequest(
            rating=1, question="Préavis ?", answer="1 mois.", module="juridique"
        )
        entry = asyncio.run(append_feedback(req))

        assert log_file.exists()
        lines = log_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1
        loaded = json.loads(lines[0])
        assert loaded["rating"] == 1
        assert loaded["module"] == "juridique"
        assert loaded["question_hash"] == entry.question_hash
        assert loaded["question"] == "Préavis ?"
        assert "timestamp" in loaded

    def test_append_plusieurs_feedbacks(self, tmp_path: Path, monkeypatch):
        log_file = tmp_path / "feedback.jsonl"
        monkeypatch.setenv("ELISFA_FEEDBACK_LOG", str(log_file))

        for rating in (1, -1, 1):
            req = FeedbackRequest(
                rating=rating, question="Q", answer="A", module="juridique"
            )
            asyncio.run(append_feedback(req))

        entries = read_all_feedbacks()
        assert len(entries) == 3
        assert [e["rating"] for e in entries] == [1, -1, 1]

    def test_read_all_fichier_absent(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("ELISFA_FEEDBACK_LOG", str(tmp_path / "absent.jsonl"))
        assert read_all_feedbacks() == []

    def test_read_all_skip_lignes_malformees(self, tmp_path: Path, monkeypatch):
        log_file = tmp_path / "feedback.jsonl"
        log_file.write_text(
            '{"rating": 1, "module": "juridique"}\n'
            'pas du json\n'
            '{"rating": -1, "module": "rh"}\n',
            encoding="utf-8",
        )
        monkeypatch.setenv("ELISFA_FEEDBACK_LOG", str(log_file))
        entries = read_all_feedbacks()
        assert len(entries) == 2  # ligne malformée skippée


# ────────────────────────── Endpoints ──────────────────────────

@pytest.fixture
def client(monkeypatch, tmp_path: Path):
    """App fraîche avec FEEDBACK_LOG isolé en tmp_path."""
    log_file = tmp_path / "feedback.jsonl"
    monkeypatch.setenv("ELISFA_FEEDBACK_LOG", str(log_file))
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
    monkeypatch.setenv("KB_DATA_DIR", "../data")

    from app import settings as settings_module
    settings_module.get_settings.cache_clear()

    from app.main import create_app
    app = create_app()
    with TestClient(app) as c:
        yield c


class TestPostFeedback:
    def test_post_feedback_minimal_ok(self, client: TestClient):
        r = client.post(
            "/api/feedback",
            json={
                "rating": 1,
                "question": "Quel préavis ?",
                "answer": "1 mois.",
                "module": "juridique",
            },
        )
        assert r.status_code == 200, r.text
        assert r.json() == {"status": "ok"}

    def test_post_feedback_rating_zero_rejete(self, client: TestClient):
        r = client.post(
            "/api/feedback",
            json={"rating": 0, "question": "q", "answer": "a", "module": "juridique"},
        )
        assert r.status_code == 422

    def test_post_feedback_module_inconnu_rejete(self, client: TestClient):
        r = client.post(
            "/api/feedback",
            json={"rating": 1, "question": "q", "answer": "a", "module": "WTF"},
        )
        assert r.status_code == 422

    def test_post_feedback_question_vide_rejetee(self, client: TestClient):
        r = client.post(
            "/api/feedback",
            json={"rating": 1, "question": "", "answer": "a", "module": "juridique"},
        )
        assert r.status_code == 422

    def test_post_feedback_avec_commentaire_negatif(self, client: TestClient, tmp_path):
        r = client.post(
            "/api/feedback",
            json={
                "rating": -1,
                "question": "Question floue",
                "answer": "Réponse hors-sujet",
                "module": "rh",
                "comment": "La réponse ne correspond pas à ma question",
            },
        )
        assert r.status_code == 200
        # Vérifie que le JSONL a bien capturé le commentaire
        entries = read_all_feedbacks()
        assert any(e["comment"] == "La réponse ne correspond pas à ma question" for e in entries)

    def test_post_feedback_compat_v1_champs_extra(self, client: TestClient):
        # Frontend V1 envoie des champs en plus → V2 doit les ignorer sans 422
        r = client.post(
            "/api/feedback",
            json={
                "rating": 1,
                "question": "q",
                "answer": "a",
                "module": "juridique",
                "function": "ask",
                "sources": [{"id": "ART_001", "score": 5.2}],
                "profile": "salarie",
                "user_agent": "Mozilla/5.0 ...",
            },
        )
        assert r.status_code == 200


class TestGetFeedbackStats:
    def test_stats_vide(self, client: TestClient):
        r = client.get("/api/feedback/stats")
        assert r.status_code == 200
        body = r.json()
        assert body == {
            "total": 0, "up": 0, "down": 0, "by_module": {}, "success_rate": 0.0,
        }

    def test_stats_apres_feedbacks_mixtes(self, client: TestClient):
        # 3 👍 juridique + 1 👎 rh
        for _ in range(3):
            client.post(
                "/api/feedback",
                json={"rating": 1, "question": "q", "answer": "a", "module": "juridique"},
            )
        client.post(
            "/api/feedback",
            json={"rating": -1, "question": "q", "answer": "a", "module": "rh"},
        )

        r = client.get("/api/feedback/stats")
        body = r.json()
        assert body["total"] == 4
        assert body["up"] == 3
        assert body["down"] == 1
        assert body["success_rate"] == 75.0
        assert body["by_module"]["juridique"] == {"up": 3, "down": 0}
        assert body["by_module"]["rh"] == {"up": 0, "down": 1}
