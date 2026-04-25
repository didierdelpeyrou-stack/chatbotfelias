"""Tests du wrapper LLM V2 — prompts, ClaudeClient, retry, error mapping.

Pas d'appels réseau : on injecte un mock SDK via `sdk_client=...`.
Pour les tests d'intégration réels, voir Sprint 4 (benchmark).
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.llm.claude import (
    ClaudeAuthError,
    ClaudeClient,
    ClaudeError,
    ClaudeRateLimitError,
    ClaudeResponse,
    ClaudeServerError,
    ClaudeTimeoutError,
)
from app.llm.prompts import (
    SYSTEM_PROMPT_COMMUN,
    build_system_prompt,
    build_user_message,
)

# ────────────────────────── Helpers : faux SDK SDK Anthropic ──────────────────────────

def _fake_message(text: str = "réponse fake", input_tokens: int = 100, output_tokens: int = 50):
    """Construit un objet ressemblant à un Message Anthropic."""
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)],
        stop_reason="end_turn",
        usage=SimpleNamespace(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=0,
        ),
    )


def _fake_sdk_with_response(message_obj):
    """Construit un fake AsyncAnthropic dont .messages.create() renvoie message_obj."""
    sdk = SimpleNamespace()
    sdk.messages = SimpleNamespace()
    sdk.messages.create = AsyncMock(return_value=message_obj)
    return sdk


# ────────────────────────── Prompts ──────────────────────────

class TestPrompts:
    def test_build_system_prompt_juridique(self):
        p = build_system_prompt("juridique")
        assert "ELISFA" in p
        assert "R11" in p  # règle anti-hallucination présente
        assert "Juridique" in p

    def test_build_system_prompt_formation(self):
        p = build_system_prompt("formation")
        assert "Formation" in p
        assert "Uniformation" in p

    def test_build_system_prompt_module_inconnu_raise(self):
        with pytest.raises(ValueError):
            build_system_prompt("invalide")  # type: ignore

    def test_prompt_commun_contient_R11(self):
        # R11 est le concept ML clé : verbatim + citations + hors_corpus
        assert "verbatim" in SYSTEM_PROMPT_COMMUN.lower() or "cite" in SYSTEM_PROMPT_COMMUN.lower()
        assert "[ART_" in SYSTEM_PROMPT_COMMUN  # convention de citation

    def test_build_user_message_normal(self):
        msg = build_user_message("Quelle durée ?", "ART_01: ...", hors_corpus=False)
        assert "Quelle durée ?" in msg
        assert "ART_01" in msg
        assert "[HORS CORPUS" not in msg

    def test_build_user_message_hors_corpus(self):
        msg = build_user_message("?", "", hors_corpus=True)
        assert "[HORS CORPUS" in msg


# ────────────────────────── ClaudeClient — initialisation ──────────────────────────

class TestClaudeClientInit:
    def test_api_key_vide_rejete(self):
        with pytest.raises(ClaudeAuthError):
            ClaudeClient(api_key="")

    def test_init_avec_mock_sdk(self):
        sdk = _fake_sdk_with_response(_fake_message())
        client = ClaudeClient(api_key="test", sdk_client=sdk)
        assert client.model.startswith("claude-")

    def test_modele_personnalisable(self):
        sdk = _fake_sdk_with_response(_fake_message())
        client = ClaudeClient(api_key="test", model="claude-opus-4-7", sdk_client=sdk)
        assert client.model == "claude-opus-4-7"


# ────────────────────────── complete() ──────────────────────────

class TestComplete:
    @pytest.mark.asyncio
    async def test_complete_renvoie_text_et_tokens(self):
        sdk = _fake_sdk_with_response(_fake_message(text="bonjour", input_tokens=120, output_tokens=30))
        client = ClaudeClient(api_key="test", sdk_client=sdk)
        resp = await client.complete(system="sys", user="user")
        assert isinstance(resp, ClaudeResponse)
        assert resp.text == "bonjour"
        assert resp.input_tokens == 120
        assert resp.output_tokens == 30
        assert resp.stop_reason == "end_turn"

    @pytest.mark.asyncio
    async def test_complete_construit_system_avec_cache_ephemeral(self):
        # On vérifie que le payload système contient bien le cache_control ephemeral
        sdk = _fake_sdk_with_response(_fake_message())
        client = ClaudeClient(api_key="test", sdk_client=sdk)
        await client.complete(system="MON_PROMPT", user="user")

        # On inspecte les kwargs passés à messages.create
        call_kwargs = sdk.messages.create.await_args.kwargs
        system_blocks = call_kwargs["system"]
        assert isinstance(system_blocks, list)
        assert system_blocks[0]["text"] == "MON_PROMPT"
        assert system_blocks[0]["cache_control"]["type"] == "ephemeral"

    @pytest.mark.asyncio
    async def test_complete_max_tokens_par_defaut(self):
        sdk = _fake_sdk_with_response(_fake_message())
        client = ClaudeClient(api_key="test", sdk_client=sdk, max_tokens=1500)
        await client.complete(system="s", user="u")
        assert sdk.messages.create.await_args.kwargs["max_tokens"] == 1500

    @pytest.mark.asyncio
    async def test_complete_max_tokens_override(self):
        sdk = _fake_sdk_with_response(_fake_message())
        client = ClaudeClient(api_key="test", sdk_client=sdk, max_tokens=1500)
        await client.complete(system="s", user="u", max_tokens=500)
        assert sdk.messages.create.await_args.kwargs["max_tokens"] == 500


# ────────────────────────── Error mapping ──────────────────────────

class TestErrorMapping:
    # Note : on construit des sous-classes des erreurs SDK avec __init__ permissif,
    # car le SDK anthropic moderne exige `request`/`body` qu'on ne veut pas mocker
    # complètement. Le `_map_exception` ne lit que le `type` via isinstance.

    def _make_sdk_exception(self, anthropic_exc_class, message="x", status_code=500):
        """Construit une instance simulée d'une exception SDK pour isinstance() tests."""

        class _SimulatedErr(anthropic_exc_class):
            def __init__(self, msg):  # noqa: D401
                # On bypasse le __init__ parent pour éviter d'avoir à fournir
                # response/body/request — on n'a besoin que de l'isinstance check.
                Exception.__init__(self, msg)
                self.status_code = status_code

        return _SimulatedErr(message)

    @pytest.mark.asyncio
    async def test_auth_error_propagee(self):
        try:
            import anthropic  # type: ignore
        except ImportError:
            pytest.skip("anthropic SDK not installed")

        sdk = SimpleNamespace()
        sdk.messages = SimpleNamespace()
        sdk.messages.create = AsyncMock(
            side_effect=self._make_sdk_exception(
                anthropic.AuthenticationError, "bad key", 401
            )
        )
        client = ClaudeClient(api_key="test", sdk_client=sdk)
        with pytest.raises(ClaudeAuthError) as exc_info:
            await client.complete(system="s", user="u")
        assert exc_info.value.http_status == 401

    @pytest.mark.asyncio
    async def test_rate_limit_retry_puis_succes(self, monkeypatch):
        try:
            import anthropic  # type: ignore
        except ImportError:
            pytest.skip("anthropic SDK not installed")

        # Speed up retries pour le test
        monkeypatch.setattr(ClaudeClient, "RETRY_DELAY_BASE", 1.001)

        sdk = SimpleNamespace()
        sdk.messages = SimpleNamespace()
        sdk.messages.create = AsyncMock(side_effect=[
            self._make_sdk_exception(anthropic.RateLimitError, "slow down", 429),
            _fake_message(text="ok cette fois"),
        ])
        client = ClaudeClient(api_key="test", sdk_client=sdk)
        # Ne devrait PAS lever — le retry doit réussir
        resp = await client.complete(system="s", user="u")
        assert resp.text == "ok cette fois"
        assert sdk.messages.create.await_count == 2

    @pytest.mark.asyncio
    async def test_rate_limit_persistant_leve_erreur(self, monkeypatch):
        try:
            import anthropic  # type: ignore
        except ImportError:
            pytest.skip("anthropic SDK not installed")

        monkeypatch.setattr(ClaudeClient, "RETRY_DELAY_BASE", 1.001)
        monkeypatch.setattr(ClaudeClient, "MAX_RETRIES", 2)

        sdk = SimpleNamespace()
        sdk.messages = SimpleNamespace()
        sdk.messages.create = AsyncMock(
            side_effect=self._make_sdk_exception(
                anthropic.RateLimitError, "slow down", 429
            )
        )
        client = ClaudeClient(api_key="test", sdk_client=sdk)

        with pytest.raises(ClaudeRateLimitError):
            await client.complete(system="s", user="u")
        # Retried MAX_RETRIES fois
        assert sdk.messages.create.await_count == 2

    @pytest.mark.asyncio
    async def test_server_error_retry(self, monkeypatch):
        try:
            import anthropic  # type: ignore
        except ImportError:
            pytest.skip("anthropic SDK not installed")

        monkeypatch.setattr(ClaudeClient, "RETRY_DELAY_BASE", 1.001)

        sdk = SimpleNamespace()
        sdk.messages = SimpleNamespace()
        sdk.messages.create = AsyncMock(side_effect=[
            self._make_sdk_exception(anthropic.APIStatusError, "service down", 503),
            _fake_message(text="recover"),
        ])
        client = ClaudeClient(api_key="test", sdk_client=sdk)
        resp = await client.complete(system="s", user="u")
        assert resp.text == "recover"


# ────────────────────────── Erreurs typées ──────────────────────────

class TestErrorTypes:
    def test_http_status_par_defaut(self):
        assert ClaudeError("x").http_status == 500
        assert ClaudeAuthError("x").http_status == 401
        assert ClaudeRateLimitError("x").http_status == 429
        assert ClaudeTimeoutError("x").http_status == 504
        assert ClaudeServerError("x").http_status == 502

    def test_http_status_custom(self):
        err = ClaudeError("x", http_status=418)
        assert err.http_status == 418
