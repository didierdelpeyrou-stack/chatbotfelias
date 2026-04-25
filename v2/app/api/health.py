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

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel

from app import __version__
from app.metrics.prometheus import render_metrics
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
    # Sprint 3.1 — KB store chargé et au moins 1 base disponible
    kb_store = getattr(request.app.state, "kb_store", None)
    checks["kb_loaded"] = bool(kb_store and kb_store.stats())
    # Sprint 3.2 : checks["claude_ready"] = bool(request.app.state.claude_client)

    all_ok = all(checks.values())
    return ReadinessResponse(
        status="ready" if all_ok else "starting",
        version=__version__,
        timestamp=datetime.now(UTC).isoformat(timespec="seconds"),
        environment=settings.environment,
        checks=checks,
    )


@router.get("/metrics", summary="Prometheus metrics (text/plain)")
async def metrics() -> Response:
    """Expose les 5 métriques Prometheus V2 en format text/plain.

    Scraper Prometheus côté infra → indiquer ce path dans `prometheus.yml`.
    """
    body, content_type = render_metrics()
    return Response(content=body, media_type=content_type)
