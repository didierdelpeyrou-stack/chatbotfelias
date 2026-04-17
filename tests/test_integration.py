"""Tests d'intégration e2e via Flask test_client (fix 12).

Couvre les parcours complets en mockant uniquement les I/O externes :
  - Anthropic (stubbed via ``fake_anthropic`` fixture dans conftest.py)
  - SMTP / webhooks (patches locaux au test)
  - Fichiers de persistence RDV / Appels / Feedback (tmp_path)

Les tests vérifient le CONTRAT HTTP public :
  - /api/ask         : happy path 200, validation 400, oversize 413, vide 400
  - /api/rdv         : validation 400 (email invalide), happy 200
  - /api/appel       : validation 400, happy 200
  - /api/email-juriste : happy 200
  - /api/feedback    : rating invalide 400, rating OK 200
  - /api/health      : shape de la réponse, toujours 200
  - /api/openapi.yaml / .json : YAML/JSON
  - /api/reload      : 401 sans auth, 200 avec admin_client
  - /api/knowledge   : 401 sans auth, 200 avec admin_client
  - CORS             : headers présents sur OPTIONS

Exécution :
    pytest tests/test_integration.py -v
    pytest tests/test_integration.py -v -m integration
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest


pytestmark = pytest.mark.integration


# ──────────────────────── helpers ────────────────────────

def _assert_json(resp):
    """Raccourci : extrait et retourne le JSON ou échoue avec un message clair."""
    assert resp.is_json, f"réponse non-JSON ({resp.status_code}): {resp.data[:200]!r}"
    return resp.get_json()


@pytest.fixture
def isolated_storage(tmp_path, flask_app):
    """Redirige les écritures disque (RDV / Appels / Emails / Feedback) vers
    un répertoire temporaire pour que les tests ne polluent pas les vrais
    fichiers de prod.
    """
    import app as app_module

    # Sauvegarde des chemins originaux
    orig_rdv = app_module.RDV_FILE
    orig_emails = app_module.EMAILS_FILE
    orig_appels = app_module.APPELS_FILE
    orig_log_dir = app_module.LOG_DIR

    app_module.RDV_FILE = tmp_path / "rdv.json"
    app_module.EMAILS_FILE = tmp_path / "emails.json"
    app_module.APPELS_FILE = tmp_path / "appels.json"
    app_module.LOG_DIR = tmp_path  # feedback.jsonl sera écrit ici
    try:
        yield tmp_path
    finally:
        app_module.RDV_FILE = orig_rdv
        app_module.EMAILS_FILE = orig_emails
        app_module.APPELS_FILE = orig_appels
        app_module.LOG_DIR = orig_log_dir


@pytest.fixture
def no_side_effects():
    """Désactive les envois email/webhook pour ne pas leak en tests.

    ``return_value=True`` : certains handlers réinjectent la valeur de retour
    dans la réponse JSON (ex. ``email_sent`` dans /api/email-juriste) — un
    MagicMock n'est pas JSON-sérialisable, d'où le True explicite.
    """
    with patch("app.send_email_notification", return_value=True), \
         patch("app.send_webhook_notification", return_value=True):
        yield


# ══════════════════════════════════════════════
#                /api/health
# ══════════════════════════════════════════════

class TestHealth:
    def test_health_returns_200(self, flask_client):
        resp = flask_client.get("/api/health")
        assert resp.status_code == 200
        data = _assert_json(resp)
        assert data["status"] == "ok"
        assert "timestamp" in data
        assert "model" in data
        assert "themes_count" in data
        assert isinstance(data["themes_count"], int)

    def test_health_inclut_metriques_claude(self, flask_client):
        """La clé `claude_metrics` doit exister pour le monitoring."""
        resp = flask_client.get("/api/health")
        data = _assert_json(resp)
        assert "claude_metrics" in data
        # Shape attendue : un dict avec au minimum un compteur
        assert isinstance(data["claude_metrics"], dict)


# ══════════════════════════════════════════════
#                /api/ask
# ══════════════════════════════════════════════

class TestAskEndpoint:
    def test_happy_path_200(self, flask_client, fake_anthropic):
        """Requête valide → 200 avec answer + métadonnées."""
        resp = flask_client.post("/api/ask", json={
            "question": "Quelle est la durée légale du travail ?",
            "module": "juridique",
        })
        assert resp.status_code == 200
        data = _assert_json(resp)
        assert "answer" in data
        assert data["answer"]  # non-vide
        assert data["module"] == "juridique"
        assert "mode" in data
        # Le stub Anthropic a bien été appelé une fois
        assert fake_anthropic.messages.create.called

    def test_payload_non_json_rejette_400(self, flask_client):
        resp = flask_client.post("/api/ask", data="pas du json",
                                 content_type="text/plain")
        assert resp.status_code == 400
        assert "error" in _assert_json(resp)

    def test_payload_liste_rejette_400(self, flask_client):
        """Une liste n'est pas un dict → 400 propre (pas de 500)."""
        resp = flask_client.post("/api/ask", json=[1, 2, 3])
        assert resp.status_code == 400

    def test_question_et_document_vides_rejette_400(self, flask_client):
        """Aucun contenu exploitable → 400 'Veuillez poser une question'."""
        resp = flask_client.post("/api/ask", json={"question": "",
                                                    "module": "juridique"})
        assert resp.status_code == 400
        assert "question" in _assert_json(resp)["error"].lower() \
            or "veuillez" in _assert_json(resp)["error"].lower()

    def test_module_inconnu_tombe_sur_juridique(self, flask_client, fake_anthropic):
        """Module exotique → fallback silencieux sur 'juridique'."""
        resp = flask_client.post("/api/ask", json={
            "question": "test",
            "module": "module_inexistant_xyz",
        })
        assert resp.status_code == 200
        data = _assert_json(resp)
        assert data["module"] == "juridique"

    def test_question_trop_longue_413(self, flask_client):
        """Question au-delà de MAX_QUESTION_CHARS (5000) → 413."""
        resp = flask_client.post("/api/ask", json={
            "question": "x" * 10_000,
            "module": "juridique",
        })
        # Pydantic rejette à 5000 avec 400, legacy rejette à 5000 avec 413
        assert resp.status_code in (400, 413)
        assert "error" in _assert_json(resp)

    def test_history_depasse_cap_tronque_silencieusement(self, flask_client, fake_anthropic):
        """50 messages d'historique → modèle en accepte 20, pas de 400."""
        history = [{"role": "user", "content": f"m{i}"} for i in range(50)]
        resp = flask_client.post("/api/ask", json={
            "question": "suite",
            "history": history,
            "module": "juridique",
        })
        assert resp.status_code == 200

    def test_extras_ignores(self, flask_client, fake_anthropic):
        """Champs inconnus (feature_flag_v2, etc.) → ignorés, pas de 400."""
        resp = flask_client.post("/api/ask", json={
            "question": "test",
            "feature_flag_v2": True,
            "future_field": [1, 2, 3],
        })
        assert resp.status_code == 200


# ══════════════════════════════════════════════
#                /api/rdv
# ══════════════════════════════════════════════

class TestRdvEndpoint:
    VALID = {
        "nom": "Jean Dupont",
        "email": "jean@exemple.fr",
        "telephone": "0612345678",
        "sujet": "Question sur un CDD",
    }

    def test_happy_path_200(self, flask_client, isolated_storage, no_side_effects):
        resp = flask_client.post("/api/rdv", json=self.VALID)
        assert resp.status_code == 200
        data = _assert_json(resp)
        assert data["status"] == "ok"
        assert "rdv_id" in data
        # Le fichier de persistence doit exister
        assert (isolated_storage / "rdv.json").exists()
        rdvs = json.loads((isolated_storage / "rdv.json").read_text())
        assert len(rdvs) == 1
        assert rdvs[0]["nom"] == "Jean Dupont"

    def test_email_invalide_400(self, flask_client):
        bad = {**self.VALID, "email": "pas-un-email"}
        resp = flask_client.post("/api/rdv", json=bad)
        assert resp.status_code == 400
        assert "email" in _assert_json(resp)["error"].lower()

    def test_telephone_trop_court_400(self, flask_client):
        bad = {**self.VALID, "telephone": "12"}
        resp = flask_client.post("/api/rdv", json=bad)
        assert resp.status_code == 400

    def test_nom_vide_400(self, flask_client):
        bad = {**self.VALID, "nom": ""}
        resp = flask_client.post("/api/rdv", json=bad)
        assert resp.status_code == 400

    def test_payload_vide_400(self, flask_client):
        resp = flask_client.post("/api/rdv", json={})
        assert resp.status_code == 400


# ══════════════════════════════════════════════
#                /api/appel
# ══════════════════════════════════════════════

class TestAppelEndpoint:
    VALID = {
        "nom": "Marie Durand",
        "email": "marie@crea.fr",
        "telephone": "0698765432",
        "motif": "orientation",
        "date": "2026-12-01",
        "heure": "10:30",
    }

    def test_happy_path_200(self, flask_client, isolated_storage, no_side_effects):
        resp = flask_client.post("/api/appel", json=self.VALID)
        assert resp.status_code == 200
        data = _assert_json(resp)
        assert data["status"] == "ok"
        assert "appel_id" in data

    def test_motif_vide_400(self, flask_client):
        bad = {**self.VALID, "motif": ""}
        resp = flask_client.post("/api/appel", json=bad)
        assert resp.status_code == 400

    def test_email_invalide_400(self, flask_client):
        bad = {**self.VALID, "email": "bad"}
        resp = flask_client.post("/api/appel", json=bad)
        assert resp.status_code == 400

    def test_date_manquante_400(self, flask_client):
        """Pydantic accepte date=None mais le handler exige non vide."""
        bad = {k: v for k, v in self.VALID.items() if k != "date"}
        resp = flask_client.post("/api/appel", json=bad)
        assert resp.status_code == 400


# ══════════════════════════════════════════════
#                /api/email-juriste
# ══════════════════════════════════════════════

class TestEmailJuristeEndpoint:
    VALID = {
        "nom": "Pierre Martin",
        "email": "pierre@elisfa.fr",
        "telephone": "0612345678",
        "theme_guide": "contrat_travail",
        "reponses": {"type_contrat": "CDI", "anciennete": "3 ans"},
    }

    def test_happy_path_200(self, flask_client, isolated_storage, no_side_effects):
        resp = flask_client.post("/api/email-juriste", json=self.VALID)
        assert resp.status_code == 200
        data = _assert_json(resp)
        assert data.get("status") == "ok"

    def test_reponses_vide_400(self, flask_client):
        bad = {**self.VALID, "reponses": {}}
        resp = flask_client.post("/api/email-juriste", json=bad)
        assert resp.status_code == 400


# ══════════════════════════════════════════════
#                /api/feedback
# ══════════════════════════════════════════════

class TestFeedbackEndpoint:
    def test_rating_plus_un_ok(self, flask_client, isolated_storage):
        resp = flask_client.post("/api/feedback", json={
            "rating": 1,
            "comment": "Super réponse",
            "question": "Q?",
            "answer": "A.",
        })
        assert resp.status_code == 200
        assert _assert_json(resp)["status"] == "ok"
        # La ligne est bien écrite dans feedback.jsonl
        fb_file = isolated_storage / "feedback.jsonl"
        assert fb_file.exists()
        lines = fb_file.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["rating"] == 1

    def test_rating_moins_un_ok(self, flask_client, isolated_storage):
        resp = flask_client.post("/api/feedback", json={"rating": -1})
        assert resp.status_code == 200

    def test_rating_zero_400(self, flask_client):
        resp = flask_client.post("/api/feedback", json={"rating": 0})
        assert resp.status_code == 400

    def test_rating_hors_plage_400(self, flask_client):
        resp = flask_client.post("/api/feedback", json={"rating": 42})
        assert resp.status_code == 400

    def test_rating_manquant_400(self, flask_client):
        resp = flask_client.post("/api/feedback", json={})
        assert resp.status_code == 400


# ══════════════════════════════════════════════
#                Admin endpoints
# ══════════════════════════════════════════════

class TestAdminEndpoints:
    def test_reload_sans_auth_401(self, flask_client):
        """Sans credentials, /api/reload doit retourner 401."""
        resp = flask_client.post("/api/reload")
        assert resp.status_code == 401
        # Basic auth challenge présent
        assert "WWW-Authenticate" in resp.headers

    def test_knowledge_sans_auth_401(self, flask_client):
        resp = flask_client.get("/api/knowledge")
        assert resp.status_code == 401

    def test_rdv_list_sans_auth_401(self, flask_client):
        resp = flask_client.get("/api/rdv")
        assert resp.status_code == 401

    def test_reload_avec_auth_200(self, admin_client):
        """Avec admin_client fixture (bcrypt hash configuré) → 200."""
        username, password = admin_client._admin_auth
        resp = admin_client.post("/api/reload", headers=_basic_auth(username, password))
        assert resp.status_code == 200
        data = _assert_json(resp)
        assert data["status"] == "ok"
        assert "themes" in data

    def test_knowledge_avec_auth_200(self, admin_client):
        username, password = admin_client._admin_auth
        resp = admin_client.get("/api/knowledge", headers=_basic_auth(username, password))
        assert resp.status_code == 200
        data = _assert_json(resp)
        # La KB exposée a une clé "themes"
        assert "themes" in data

    def test_auth_mauvais_mdp_401(self, admin_client):
        resp = admin_client.post("/api/reload", headers=_basic_auth("admin", "WRONG"))
        assert resp.status_code == 401

    def test_auth_mauvais_user_401(self, admin_client):
        _username, password = admin_client._admin_auth
        resp = admin_client.post("/api/reload", headers=_basic_auth("hacker", password))
        assert resp.status_code == 401


def _basic_auth(user: str, pwd: str) -> dict:
    """Construit l'en-tête HTTP Basic Auth."""
    import base64
    token = base64.b64encode(f"{user}:{pwd}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {token}"}


# ══════════════════════════════════════════════
#                OpenAPI / Swagger
# ══════════════════════════════════════════════

class TestOpenAPIEndpoints:
    def test_openapi_yaml_200(self, flask_client):
        resp = flask_client.get("/api/openapi.yaml")
        # 200 si le fichier docs/openapi.yaml existe, 404 sinon
        assert resp.status_code in (200, 404)
        if resp.status_code == 200:
            assert b"openapi" in resp.data.lower()

    def test_openapi_json_200(self, flask_client):
        resp = flask_client.get("/api/openapi.json")
        # 200 si le fichier + pyyaml présents, 404/501 sinon
        assert resp.status_code in (200, 404, 501)
        if resp.status_code == 200:
            data = _assert_json(resp)
            assert "openapi" in data
            assert "paths" in data


# ══════════════════════════════════════════════
#                CORS
# ══════════════════════════════════════════════

class TestCORS:
    def test_cors_preflight_options(self, flask_client):
        """OPTIONS sur /api/ask depuis un origin autorisé → headers CORS."""
        resp = flask_client.options(
            "/api/ask",
            headers={
                "Origin": "http://localhost:5000",
                "Access-Control-Request-Method": "POST",
            },
        )
        # Flask-CORS répond 200 (ou 204) sur le preflight
        assert resp.status_code in (200, 204)
        # L'en-tête doit être présent
        assert "Access-Control-Allow-Origin" in resp.headers

    def test_cors_headers_sur_get(self, flask_client):
        """Un GET simple depuis origin autorisé → header Allow-Origin."""
        resp = flask_client.get("/api/health",
                                 headers={"Origin": "http://localhost:5000"})
        assert resp.status_code == 200
        assert resp.headers.get("Access-Control-Allow-Origin") == "http://localhost:5000"


# ══════════════════════════════════════════════
#                Handlers d'erreurs
# ══════════════════════════════════════════════

class TestErrorHandlers:
    def test_404_sur_route_inconnue(self, flask_client):
        resp = flask_client.get("/api/route-qui-nexiste-pas")
        assert resp.status_code == 404

    def test_405_sur_methode_incorrecte(self, flask_client):
        """GET /api/ask → 405 (seul POST autorisé)."""
        resp = flask_client.get("/api/ask")
        assert resp.status_code == 405


# ══════════════════════════════════════════════
#                Parcours complet (scénario réel)
# ══════════════════════════════════════════════

class TestParcoursComplet:
    """Simule un usage utilisateur de bout en bout."""

    def test_ask_puis_feedback(self, flask_client, isolated_storage, fake_anthropic):
        """1) poser une question 2) feedback positif sur la réponse."""
        # 1. Question
        r1 = flask_client.post("/api/ask", json={
            "question": "Qu'est-ce qu'un CDI ?",
            "module": "juridique",
        })
        assert r1.status_code == 200
        answer = r1.get_json()["answer"]
        assert answer

        # 2. Feedback positif
        r2 = flask_client.post("/api/feedback", json={
            "rating": 1,
            "question": "Qu'est-ce qu'un CDI ?",
            "answer": answer,
            "module": "juridique",
        })
        assert r2.status_code == 200

        # Vérifie la persistence feedback
        fb_lines = (isolated_storage / "feedback.jsonl").read_text().strip().splitlines()
        assert len(fb_lines) == 1

    def test_rdv_creation_puis_liste_admin(
        self, admin_client, isolated_storage, no_side_effects,
    ):
        """Un utilisateur crée un RDV puis l'admin le voit dans la liste."""
        username, password = admin_client._admin_auth
        auth_headers = _basic_auth(username, password)

        # 1. Création RDV (pas d'auth requise)
        r1 = admin_client.post("/api/rdv", json={
            "nom": "Jean Dupont",
            "email": "jean@test.fr",
            "telephone": "0612345678",
            "sujet": "Rupture conventionnelle",
        })
        assert r1.status_code == 200
        rdv_id = r1.get_json()["rdv_id"]

        # 2. Liste admin
        r2 = admin_client.get("/api/rdv", headers=auth_headers)
        assert r2.status_code == 200
        rdvs = r2.get_json()
        assert isinstance(rdvs, list)
        assert any(r["id"] == rdv_id for r in rdvs)
