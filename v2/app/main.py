"""Point d'entrée FastAPI V2 — app factory + lifespan.

Usage local :
    cd v2/
    uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

Sprint 2.1 (ce sprint) — minimal :
  - FastAPI app + CORS
  - Lifespan : log de démarrage / shutdown
  - Routers : /healthz, /readyz
  - Settings via pydantic-settings

À venir :
  - Sprint 2.2 : router /api/ask + RAG seuil
  - Sprint 2.3 : KB Pydantic schema validation
  - Sprint 2.4 : LLM wrapper Anthropic
  - Sprint 3.x : Docker, Prometheus, KB hot-reload
"""
from __future__ import annotations

import logging
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api import chat, feedback, health
from app.kb.loader import KBStore
from app.llm.claude import ClaudeClient
from app.settings import get_settings


def _configure_logging(level: str) -> None:
    """Logging stdout simple (Sprint 2.1) — passera à structlog plus tard."""
    root = logging.getLogger()
    root.setLevel(level)
    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s :: %(message)s")
        )
        root.addHandler(handler)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Hooks de démarrage et d'arrêt.

    Boot :
      - Log de version + environnement
      - À venir Sprint 2.4 : init ClaudeClient, stocké dans app.state
      - À venir Sprint 3.1 : init KBStore, stocké dans app.state

    Shutdown :
      - Log final
    """
    settings = get_settings()
    log = logging.getLogger("app.main")
    log.info(
        "🚀 ELISFA V2 boot — version %s, env=%s, port=%d",
        __version__, settings.environment, settings.port,
    )
    log.info("Anthropic key configured: %s", bool(settings.anthropic_api_key))

    # Sprint 3.1 — chargement des 4 KB + index TF-IDF
    # Résolution path : settings.kb_data_dir est relatif au dossier v2/
    data_dir = Path(__file__).resolve().parent.parent / settings.kb_data_dir.lstrip("./")
    if not data_dir.exists():
        # fallback sur le path tel quel (Docker monte /app/data en absolu)
        data_dir = Path(settings.kb_data_dir)
    store = KBStore(data_dir=data_dir)
    summary = await store.load_all()
    log.info("📚 KB store: %s", summary)
    app.state.kb_store = store

    # Sprint 3.2 — ClaudeClient injecté pour endpoint /api/ask
    if settings.anthropic_api_key:
        try:
            app.state.claude_client = ClaudeClient(
                api_key=settings.anthropic_api_key,
                model=settings.claude_model,
                max_tokens=settings.claude_max_tokens,
                timeout=settings.claude_timeout_seconds,
            )
            log.info("🤖 ClaudeClient initialisé (model=%s)", settings.claude_model)
        except Exception as exc:  # noqa: BLE001
            log.error("[claude] init failed: %s", exc)
            app.state.claude_client = None
    else:
        log.warning("ANTHROPIC_API_KEY absent — /api/ask sera dégradé (503)")
        app.state.claude_client = None

    yield  # ← ici l'app tourne et sert les requêtes

    log.info("👋 ELISFA V2 shutdown")


def create_app() -> FastAPI:
    """App factory — testable et explicite.

    Préférer create_app() à un FastAPI() global :
      - permet aux tests d'instancier une app fraîche par fixture
      - empêche les effets de bord à l'import
    """
    settings = get_settings()
    _configure_logging(settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description="V2 du chatbot ELISFA — refonte FastAPI/Pydantic.",
        lifespan=lifespan,
    )

    # CORS — ouvert en dev, à restreindre en prod (Sprint 2.4)
    allowed_origins = ["*"] if settings.environment == "development" else [
        "https://felias-reseau-eli2026.duckdns.org",
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(health.router)
    app.include_router(chat.router)
    app.include_router(feedback.router)

    # Endpoint root informatif (utile pour valider le déploiement)
    @app.get("/", summary="Root")
    async def root() -> dict:
        return {
            "name": settings.app_name,
            "version": __version__,
            "docs": "/docs",
            "health": "/healthz",
            "ready": "/readyz",
        }

    return app


# Instance applicative pour uvicorn / gunicorn
app = create_app()
