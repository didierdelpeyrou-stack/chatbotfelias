"""Healthchecks Kubernetes-ready : liveness + readiness.

Convention :
- /healthz  : liveness probe — répond 200 tant que le process tourne (light check)
- /readyz   : readiness probe — répond 200 quand l'app est prête à servir
              (KB chargée, client Claude initialisé)

Cette distinction permet à un orchestrateur (k8s, docker-compose healthcheck)
de NE PAS router de trafic vers une instance qui boot encore (KB pas chargée).
"""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app import __version__
from app.settings import get_settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Réponse minimale pour /healthz."""

    status: str
    version: str
    timestamp: str


class ReadinessResponse(BaseModel):
    """Réponse détaillée pour /readyz."""

    status: str  # "ready" | "starting" | "degraded"
    version: str
    timestamp: str
    environment: str
    checks: dict


@router.get("/healthz", response_model=HealthResponse, summary="Liveness probe")
async def healthz() -> HealthResponse:
    """Liveness — répond OK tant que le process Python tourne.

    Pas de check coûteux ici : k8s appelle ça toutes les 10s. Si on
    timeout l'app sur du RAG, on fait redémarrer pour rien.
    """
    return HealthResponse(
        status="ok",
        version=__version__,
        timestamp=datetime.now(UTC).isoformat(timespec="seconds"),
    )


@router.get("/readyz", response_model=ReadinessResponse, summary="Readiness probe")
async def readyz(request: Request) -> ReadinessResponse:
    """Readiness — l'app est-elle prête à servir du trafic ?

    Vérifie que les composants critiques sont initialisés (Sprint 2.1
    initial : settings chargés. Sprint 3.1 ajoutera KB, Sprint 2.4 LLM).
    """
    settings = get_settings()
    checks: dict[str, bool] = {
        "settings_loaded": True,  # Si on est ici, les settings sont OK
        "anthropic_key_configured": bool(settings.anthropic_api_key),
    }
    # Sprint 3.1 : checks["kb_loaded"] = bool(request.app.state.kb_store)
    # Sprint 2.4 : checks["claude_ready"] = bool(request.app.state.claude_client)

    all_ok = all(checks.values())
    return ReadinessResponse(
        status="ready" if all_ok else "starting",
        version=__version__,
        timestamp=datetime.now(UTC).isoformat(timespec="seconds"),
        environment=settings.environment,
        checks=checks,
    )
