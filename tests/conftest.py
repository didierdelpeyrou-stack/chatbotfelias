"""Fixtures partagées pour pytest.

Contient :
  - ``flask_client`` : Flask test client avec Anthropic stubbé (pas d'appels
    réseau réels pendant les tests).
  - ``fake_anthropic`` : stub de l'API Claude qui renvoie des réponses
    déterministes — permet de tester /api/ask sans clé API ni latence.
  - ``temp_kb_file`` : fichier JSON temporaire pour tester le cache KB.
  - ``admin_credentials`` : configure ADMIN_PASS_HASH pour les tests admin.

Ces fixtures sont chargées automatiquement par pytest pour tous les fichiers
``test_*.py`` dans ``tests/``. L'ajout de ce conftest ne casse aucun test
existant (unittest/TestCase) : pytest les détecte et les exécute tels quels.

Usage type
----------
    def test_ask_returns_200(flask_client, fake_anthropic):
        resp = flask_client.post("/api/ask",
            json={"question": "Bonjour", "module": "juridique"})
        assert resp.status_code == 200
        assert "answer" in resp.get_json()
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# Ajoute le répertoire parent au PYTHONPATH pour que les imports `from
# validation import ...` fonctionnent depuis n'importe quel test, même
# quand pytest est lancé depuis ``tests/`` directement.
_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


# ──────────────────────── Config env par défaut pour les tests ────────────────────────

@pytest.fixture(scope="session", autouse=True)
def _test_env(tmp_path_factory):
    """Variables d'environnement minimales pour tous les tests.

    ``autouse=True`` : appliqué automatiquement à TOUS les tests. Évite
    qu'un test oublie de stubber ANTHROPIC_API_KEY et finisse par taper
    l'API réelle (facture + dépendance réseau).

    ``scope="session"`` : configuré une fois, partagé par tous les tests.
    """
    # Clé API factice — nos tests stubbent l'appel, mais le module app.py
    # refuse de démarrer sans la variable.
    os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")
    # Modèle non utilisé (stubbé) mais requis par config.py
    os.environ.setdefault("CLAUDE_MODEL", "claude-haiku-4-5-20251001")
    # Pas d'admin par défaut (certains tests configurent eux-mêmes)
    os.environ.pop("ADMIN_PASS", None)
    os.environ.pop("ADMIN_PASS_HASH", None)
    # Rate limiting haut pour ne pas être bloqué par une rafale de tests
    os.environ["RATE_LIMIT_PER_MINUTE"] = "10000"
    os.environ["RATE_LIMIT_PER_HOUR"] = "100000"
    # Pas de Sentry en tests
    os.environ.pop("SENTRY_DSN", None)
    yield
    # Pas de cleanup explicite : pytest restaure tout en fin de session.


# ──────────────────────── Stub Anthropic ────────────────────────

class _FakeAnthropicResponse:
    """Réponse Claude factice — mime la structure minimale de la vraie."""

    def __init__(self, text: str = "Réponse simulée", stop_reason: str = "end_turn"):
        class _TextBlock:
            type = "text"
            def __init__(self, t): self.text = t
        self.content = [_TextBlock(text)]
        self.stop_reason = stop_reason
        # Usage : le code tire cache_read_input_tokens pour les métriques.
        self.usage = MagicMock(
            input_tokens=100,
            output_tokens=50,
            cache_read_input_tokens=0,
            cache_creation_input_tokens=0,
        )


@pytest.fixture
def fake_anthropic():
    """Patch ``anthropic.Anthropic.messages.create`` pour renvoyer une réponse stub.

    Empêche tout appel réseau pendant les tests d'endpoint. Chaque test
    peut récupérer le mock pour vérifier les arguments passés à Claude
    (par ex. le system prompt, les outils déclarés, etc.).
    """
    # On patche à la source : dans le module app.py, ``anthropic.Anthropic``
    # est instancié. On remplace donc sa méthode ``messages.create``.
    with patch("anthropic.Anthropic") as mock_client_class:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _FakeAnthropicResponse()
        mock_client_class.return_value = mock_client
        yield mock_client


# ──────────────────────── Flask test client ────────────────────────

@pytest.fixture
def flask_app(fake_anthropic):
    """Retourne l'app Flask avec les stubs en place.

    Note : on importe ``app`` APRÈS avoir patché anthropic, sinon le client
    réel est instancié au module-load de app.py. ``scope="function"`` pour
    que chaque test reparte d'un état propre (rate limiter, caches).
    """
    # Force re-import pour que le patch anthropic s'applique.
    if "app" in sys.modules:
        del sys.modules["app"]
    import app as app_module  # noqa: E402

    app_module.app.config["TESTING"] = True
    yield app_module.app


@pytest.fixture
def flask_client(flask_app):
    """Client de test Flask prêt à l'emploi."""
    with flask_app.test_client() as client:
        yield client


@pytest.fixture
def admin_client(flask_app):
    """Client Flask avec ADMIN_PASS_HASH configuré pour tester les routes admin."""
    from security import hash_password

    # Génère un hash pour "test-admin-pass" et l'injecte
    test_hash = hash_password("test-admin-pass", rounds=4)  # 4 rounds = rapide en CI

    # On patche les globales à la volée (plus simple que re-importer)
    import app as app_module
    original_hash = app_module.ADMIN_PASS_HASH
    app_module.ADMIN_PASS_HASH = test_hash
    try:
        with flask_app.test_client() as client:
            # Fournit aussi le couple user/pass pour les tests qui l'utilisent
            client._admin_auth = ("admin", "test-admin-pass")
            yield client
    finally:
        app_module.ADMIN_PASS_HASH = original_hash


# ──────────────────────── Helpers pour les tests de KB ────────────────────────

@pytest.fixture
def temp_kb_file(tmp_path):
    """Crée un fichier JSON temporaire pour tester ``FileBackedCache``.

    Retourne un tuple ``(path, write_fn)`` — write_fn permet de réécrire
    le fichier en updatant le mtime (utile pour tester l'invalidation).
    """
    path = tmp_path / "fake_kb.json"
    path.write_text(json.dumps({"themes": [], "v": 1}), encoding="utf-8")

    def _write(data: dict, *, sleep: float = 1.1) -> None:
        """Écrit data dans path, avec un sleep pour dépasser le check_interval
        par défaut de FileBackedCache (1.0 s)."""
        import time
        time.sleep(sleep)
        path.write_text(json.dumps(data), encoding="utf-8")

    return path, _write


# ──────────────────────── Capture des logs ────────────────────────

@pytest.fixture
def captured_logs(caplog):
    """Alias documenté de ``caplog`` avec niveau INFO par défaut."""
    import logging
    caplog.set_level(logging.INFO)
    return caplog
