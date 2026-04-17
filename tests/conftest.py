"""Fixtures partagées pour pytest.

Contient :
  - ``flask_client`` : Flask test client avec Anthropic stubbé (pas d'appels
    réseau réels pendant les tests).
  - ``fake_anthropic`` : stub de l'API Claude qui renvoie une réponse
    déterministe — permet de tester /api/ask sans clé API ni latence.
  - ``fake_anthropic_factory`` : variante paramétrable quand on a besoin
    de faire varier la réponse (stop_reason, tool_use, erreur, etc.).
  - ``admin_client`` : Flask client avec ADMIN_PASS_HASH configuré.

Ces fixtures sont chargées automatiquement par pytest pour tous les fichiers
``test_*.py`` dans ``tests/``. L'ajout de ce conftest ne casse aucun test
existant (unittest/TestCase) : pytest les détecte et les exécute tels quels.

Notes de robustesse
-------------------
Historique : ce conftest contenait une fixture ``temp_kb_file`` et
``captured_logs`` qui n'étaient appelées nulle part ("dead fixtures").
Elles ont été supprimées — elles ne faisaient qu'ajouter des lignes à
maintenir et trompaient la doc.

Le cleanup env vars se fait via ``_restore_env_per_test`` (autouse,
scope="function") : si un test fait ``os.environ["X"] = ...``, la valeur
originale est restaurée en teardown — évite les leaks entre tests.

Usage type
----------
    def test_ask_returns_200(flask_client, fake_anthropic):
        resp = flask_client.post("/api/ask",
            json={"question": "Bonjour", "module": "juridique"})
        assert resp.status_code == 200
        assert "answer" in resp.get_json()
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest


# Ajoute le répertoire parent au PYTHONPATH pour que les imports `from
# validation import ...` fonctionnent depuis n'importe quel test, même
# quand pytest est lancé depuis ``tests/`` directement.
_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


# ──────────────────────── Config env par défaut pour les tests ────────────────────────

# Clés env que ``_test_env`` définit — on les retient pour pouvoir
# restaurer leur état initial en fin de session ET pour contrôler quelles
# clés le cleanup par-test doit surveiller.
_TEST_MANAGED_ENV_KEYS = (
    "ANTHROPIC_API_KEY",
    "CLAUDE_MODEL",
    "ADMIN_PASS",
    "ADMIN_PASS_HASH",
    "RATE_LIMIT_PER_MINUTE",
    "RATE_LIMIT_PER_HOUR",
    "SENTRY_DSN",
)


@pytest.fixture(scope="session", autouse=True)
def _test_env():
    """Variables d'environnement minimales pour tous les tests.

    ``autouse=True`` : appliqué automatiquement à TOUS les tests. Évite
    qu'un test oublie de stubber ANTHROPIC_API_KEY et finisse par taper
    l'API réelle (facture + dépendance réseau).

    ``scope="session"`` : configuré une fois, partagé par tous les tests.

    La restauration complète de l'env en fin de session garantit qu'on ne
    pollue pas l'environnement du process parent (utile quand pytest
    tourne dans un shell interactif : ``python -m pytest`` puis
    ``python -c 'import os; print(os.environ["ADMIN_PASS_HASH"])'``).
    """
    snapshot = {k: os.environ.get(k) for k in _TEST_MANAGED_ENV_KEYS}

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

    # Restaure l'état initial (évite la pollution du shell parent).
    for k, v in snapshot.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


@pytest.fixture(autouse=True)
def _restore_env_per_test():
    """Restaure les variables d'environnement mutées par un test.

    Autouse + scope function : snapshot de l'env avant le test, puis
    restauration en teardown. Évite qu'un test qui fait
    ``os.environ["ADMIN_PASS_HASH"] = "xxx"`` pollue le test suivant.

    Stratégie : snapshot complet (dict(os.environ)) — plus fiable qu'une
    liste de clés watchées, et l'overhead est < 0.1 ms par test.
    """
    snapshot = dict(os.environ)
    try:
        yield
    finally:
        # Supprime les clés ajoutées par le test…
        for k in list(os.environ.keys()):
            if k not in snapshot:
                os.environ.pop(k, None)
        # …et remet les valeurs mutées.
        for k, v in snapshot.items():
            if os.environ.get(k) != v:
                os.environ[k] = v


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


def _make_anthropic_mock(response: Optional[_FakeAnthropicResponse] = None) -> MagicMock:
    """Construit un mock du client Anthropic avec une réponse configurable."""
    mock_client = MagicMock()
    mock_client.messages.create.return_value = response or _FakeAnthropicResponse()
    return mock_client


@pytest.fixture
def fake_anthropic():
    """Patch ``anthropic.Anthropic.messages.create`` pour renvoyer une réponse stub.

    Empêche tout appel réseau pendant les tests d'endpoint. Chaque test
    peut récupérer le mock pour vérifier les arguments passés à Claude
    (par ex. le system prompt, les outils déclarés, etc.) :

        def test_foo(flask_client, fake_anthropic):
            flask_client.post("/api/ask", json={...})
            call_args = fake_anthropic.messages.create.call_args
            assert call_args.kwargs["model"].startswith("claude-")
    """
    with patch("anthropic.Anthropic") as mock_client_class:
        mock_client = _make_anthropic_mock()
        mock_client_class.return_value = mock_client
        yield mock_client


@pytest.fixture
def fake_anthropic_factory():
    """Variante de ``fake_anthropic`` paramétrable.

    Permet de configurer la réponse (texte, stop_reason) avant d'utiliser
    le client Flask. Utile pour tester des cas de bord (réponse vide,
    tool_use, max_tokens atteint, etc.) :

        def test_cas_limite(flask_client, fake_anthropic_factory):
            mock = fake_anthropic_factory(text="", stop_reason="max_tokens")
            resp = flask_client.post("/api/ask", json={"question": "x"})
            # ... assertions
    """
    mocks_created = []

    with patch("anthropic.Anthropic") as mock_client_class:
        def _factory(text: str = "Réponse simulée",
                     stop_reason: str = "end_turn") -> MagicMock:
            resp = _FakeAnthropicResponse(text=text, stop_reason=stop_reason)
            mock_client = _make_anthropic_mock(response=resp)
            mocks_created.append(mock_client)
            mock_client_class.return_value = mock_client
            return mock_client

        # Ping par défaut avant qu'un test n'appelle _factory explicitement.
        mock_client_class.return_value = _make_anthropic_mock()
        yield _factory


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


# Credentials admin partagés (évite le pattern privé ``client._admin_auth``).
ADMIN_TEST_USER = "admin"
ADMIN_TEST_PASSWORD = "test-admin-pass"


@pytest.fixture
def admin_credentials():
    """Tuple ``(username, password)`` des credentials admin de test.

    À utiliser dans les tests qui veulent construire leur en-tête Basic
    Auth sans dépendre d'un attribut privé du client Flask.
    """
    return (ADMIN_TEST_USER, ADMIN_TEST_PASSWORD)


@pytest.fixture
def admin_client(flask_app, monkeypatch):
    """Client Flask avec ADMIN_PASS_HASH configuré pour tester les routes admin.

    ``monkeypatch`` assure la restauration de la valeur initiale même en
    cas d'exception (vs. notre try/finally précédent qui n'était pas
    à 100 % safe contre les KeyboardInterrupt).

    Note sur la rétrocompatibilité : on expose toujours ``client._admin_auth``
    pour les tests existants, mais la fixture ``admin_credentials`` est
    préférable pour les nouveaux tests.
    """
    from security import hash_password

    # Génère un hash pour le mdp de test et l'injecte via monkeypatch.
    test_hash = hash_password(ADMIN_TEST_PASSWORD, rounds=4)  # 4 rounds = rapide en CI

    import app as app_module
    monkeypatch.setattr(app_module, "ADMIN_PASS_HASH", test_hash)

    with flask_app.test_client() as client:
        # Rétrocompat : ancien attribut privé encore utilisé par quelques tests.
        client._admin_auth = (ADMIN_TEST_USER, ADMIN_TEST_PASSWORD)  # noqa: SLF001
        yield client


# ──────────────────────── Helpers HTTP partagés ────────────────────────

def _basic_auth_header(user: str, pwd: str) -> dict:
    """Construit l'en-tête HTTP Basic Auth — helper pour les tests admin."""
    import base64
    token = base64.b64encode(f"{user}:{pwd}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {token}"}


@pytest.fixture
def basic_auth_header():
    """Fixture-factory pour construire un header Basic Auth sans boilerplate."""
    return _basic_auth_header
