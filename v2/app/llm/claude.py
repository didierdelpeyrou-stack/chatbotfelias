"""Wrapper async pour l'API Claude (Anthropic SDK).

Encapsule :
  - Client `AsyncAnthropic` (réutilisé entre requêtes)
  - Prompt caching ephemeral (5 min TTL) sur le system prompt
  - Retry exponential sur 429 (rate limit) et 5xx (server error)
  - Mapping des erreurs SDK vers des `ClaudeError` typées (HTTP status)
  - Mode `complete()` (one-shot) ET `stream()` (token par token, Sprint 3.2)

Pourquoi async :
  → FastAPI native async → 1000+ requêtes simultanées sur 1 process
  → Sprint 4 (benchmark) : 50 questions en parallèle au lieu de séquentiel.
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

# Le SDK est importé paresseusement pour permettre les tests sans clé Anthropic.
# from anthropic import AsyncAnthropic — fait dans __init__

logger = logging.getLogger(__name__)


# ── Erreurs typées (HTTP status pour FastAPI) ──

class ClaudeError(RuntimeError):
    """Erreur Claude — porte un http_status pour propagation vers le client API."""

    http_status: int = 500

    def __init__(self, message: str, *, http_status: int | None = None):
        super().__init__(message)
        # Si http_status n'est pas fourni, on hérite de l'attribut de classe
        # (les sous-classes définissent http_status = 401, 429, etc.).
        if http_status is not None:
            self.http_status = http_status


class ClaudeAuthError(ClaudeError):
    http_status = 401


class ClaudeRateLimitError(ClaudeError):
    http_status = 429


class ClaudeTimeoutError(ClaudeError):
    http_status = 504


class ClaudeServerError(ClaudeError):
    http_status = 502


# ── Réponse structurée ──

@dataclass
class ClaudeResponse:
    """Résultat d'un appel Claude non-streaming.

    Champs documentés pour faciliter le logging structuré (Sprint 0.4 V2).
    """
    text: str
    model: str
    stop_reason: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0


# ── Client wrappé ──

class ClaudeClient:
    """Client async pour Claude — réutilisable, retries, prompt caching.

    Usage typique :
        client = ClaudeClient(api_key=..., model="claude-haiku-4-5-20251001")
        response = await client.complete(system="...", user="...", max_tokens=2000)
        # ou en streaming :
        async for chunk in client.stream(system="...", user="..."):
            print(chunk, end="", flush=True)
    """

    DEFAULT_MAX_TOKENS = 2000
    DEFAULT_TIMEOUT = 60.0
    MAX_RETRIES = 3
    RETRY_DELAY_BASE = 2.0  # backoff exponentiel : 2, 4, 8s

    def __init__(
        self,
        api_key: str,
        model: str = "claude-haiku-4-5-20251001",
        *,
        timeout: float = DEFAULT_TIMEOUT,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        sdk_client: Any | None = None,  # injection pour tests
    ):
        if not api_key:
            raise ClaudeAuthError("ANTHROPIC_API_KEY est vide ou absent.")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.max_tokens = max_tokens

        if sdk_client is not None:
            # Permet aux tests d'injecter un mock
            self._client = sdk_client
        else:
            try:
                from anthropic import AsyncAnthropic  # type: ignore
            except ImportError as exc:  # pragma: no cover (dépendance déclarée)
                raise ClaudeError(
                    "Le package `anthropic` n'est pas installé. `pip install anthropic`."
                ) from exc
            self._client = AsyncAnthropic(api_key=api_key, timeout=timeout)

    @staticmethod
    def _build_system_blocks(system: str) -> list[dict[str, Any]]:
        """Construit les blocs système avec cache_control ephemeral.

        Le cache_control permet à Claude de réutiliser le system prompt
        entre requêtes (TTL 5 min) → -40% latence + -90% coût input.
        """
        return [
            {
                "type": "text",
                "text": system,
                "cache_control": {"type": "ephemeral"},
            }
        ]

    @classmethod
    def _map_exception(cls, exc: Exception) -> ClaudeError:
        """Map une exception SDK Anthropic → notre `ClaudeError` typée."""
        # Import paresseux pour ne pas exiger anthropic en tests offline
        try:
            import anthropic  # type: ignore
        except ImportError:  # pragma: no cover
            return ClaudeError(str(exc))

        if isinstance(exc, anthropic.AuthenticationError):
            return ClaudeAuthError(f"Authentication error: {exc}")
        if isinstance(exc, anthropic.RateLimitError):
            return ClaudeRateLimitError(f"Rate limit exceeded: {exc}")
        if isinstance(exc, anthropic.APITimeoutError):
            return ClaudeTimeoutError(f"Claude API timeout: {exc}")
        if isinstance(exc, anthropic.APIStatusError):
            status = getattr(exc, "status_code", 500)
            if status >= 500:
                return ClaudeServerError(f"Claude server error {status}: {exc}")
            return ClaudeError(f"Claude API error {status}: {exc}", http_status=status)
        return ClaudeError(f"Unexpected Claude error: {type(exc).__name__}: {exc}")

    async def _retry(self, coro_factory):
        """Exécute la coroutine avec retry exponentiel sur les erreurs transitoires.

        coro_factory : callable qui renvoie une coroutine fraîche à chaque tentative
                       (on ne peut pas await deux fois la même coro).
        """
        last_err: ClaudeError | None = None
        for attempt in range(self.MAX_RETRIES):
            try:
                return await coro_factory()
            except Exception as exc:  # noqa: BLE001
                err = self._map_exception(exc)
                last_err = err
                # Retry uniquement sur transient (rate limit, server, timeout)
                if not isinstance(err, ClaudeRateLimitError | ClaudeServerError | ClaudeTimeoutError):
                    raise err from exc
                if attempt == self.MAX_RETRIES - 1:
                    raise err from exc
                delay = self.RETRY_DELAY_BASE ** (attempt + 1)
                logger.warning(
                    "Claude transient error (attempt %d/%d), retry in %.1fs: %s",
                    attempt + 1, self.MAX_RETRIES, delay, err,
                )
                await asyncio.sleep(delay)
        # Sécurité : ne devrait jamais arriver
        raise last_err or ClaudeError("Retry loop exited unexpectedly")

    async def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int | None = None,
    ) -> ClaudeResponse:
        """Appel one-shot (non-streaming). Retourne la réponse complète.

        Usage : pour le mode batch (benchmark) ou si l'UI ne supporte pas SSE.
        """
        async def _call():
            return await self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens or self.max_tokens,
                system=self._build_system_blocks(system),
                messages=[{"role": "user", "content": user}],
            )

        msg = await self._retry(_call)

        # Extraction du texte (Claude peut renvoyer plusieurs blocs)
        text_blocks = [
            getattr(b, "text", "") for b in msg.content
            if getattr(b, "type", None) == "text"
        ]
        text = "\n\n".join(t for t in text_blocks if t) or ""

        usage = getattr(msg, "usage", None)
        return ClaudeResponse(
            text=text,
            model=self.model,
            stop_reason=getattr(msg, "stop_reason", None),
            input_tokens=getattr(usage, "input_tokens", 0) or 0,
            output_tokens=getattr(usage, "output_tokens", 0) or 0,
            cache_creation_tokens=getattr(usage, "cache_creation_input_tokens", 0) or 0,
            cache_read_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
        )

    async def stream(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        """Streaming token par token. Yield des strings au fur et à mesure.

        Pour Sprint 3.2 (endpoint SSE). Latence perçue divisée par ~10.
        """
        async with self._client.messages.stream(
            model=self.model,
            max_tokens=max_tokens or self.max_tokens,
            system=self._build_system_blocks(system),
            messages=[{"role": "user", "content": user}],
        ) as stream:
            async for text_delta in stream.text_stream:
                yield text_delta
