"""Endpoint /api/ask — pipeline RAG + Claude (Sprint 3.2).

Deux modes :
  - POST /api/ask        → JSON one-shot (utile pour benchmark Sprint 4)
  - POST /api/ask/stream → SSE token par token (UX fluide)

Pipeline interne (cf. concept ML "End-to-end RAG pipeline") :
  1. Validation de la requête (Pydantic)
  2. RAG retrieval avec seuil hors_corpus (Sprint 2.2)
  3. Si hors_corpus → réponse fallback courte, pas d'appel Claude (économie)
  4. Sinon → construction du contexte Markdown + appel Claude
  5. Logs structurés à chaque étape (compatible Sprint 0.4)
"""
from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.llm.claude import ClaudeError
from app.llm.context import build_rag_context
from app.llm.prompts import build_system_prompt, build_user_message
from app.rag.retrieval import search
from app.settings import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])

ModuleName = Literal["juridique", "formation", "rh", "gouvernance"]


# ────────────────────────── Modèles I/O ──────────────────────────

class AskRequest(BaseModel):
    """Payload entrant de POST /api/ask."""

    question: str = Field(..., min_length=1, max_length=4000)
    module: ModuleName = "juridique"


class AskResponse(BaseModel):
    """Réponse JSON one-shot — utile pour benchmark + tests."""

    answer: str
    module: str
    hors_corpus: bool
    confidence: dict[str, Any]   # {label, score, score_normalized, threshold}
    sources: list[dict[str, Any]] = Field(default_factory=list)
    n_results: int = 0


# ────────────────────────── Réponse fallback hors_corpus ──────────────────────────

FALLBACK_HORS_CORPUS_TEXT = (
    "Je n'ai pas d'information fiable dans la base ELISFA pour répondre précisément "
    "à cette question. Pour un avis personnalisé, contactez le pôle juridique ELISFA "
    "(rdv-juriste@elisfa.fr) ou demandez un appel de 15 minutes via le formulaire."
)


def _confidence_payload(report) -> dict[str, Any]:
    """Construit le dict de confidence à renvoyer (compat UX V1)."""
    if report.best_score >= 5.0:
        label = "high"
    elif report.best_score >= report.threshold:
        label = "medium"
    elif report.best_score > 0:
        label = "low"
    else:
        label = "none"
    return {
        "label": label,
        "score": report.best_score,
        "score_normalized": report.best_score_normalized,
        "threshold": report.threshold,
        "hors_corpus": report.hors_corpus,
    }


def _sources_payload(report) -> list[dict[str, Any]]:
    """Réduit chaque RAGResult à des champs utilisables côté UI."""
    return [
        {
            "id": r.article.get("id"),
            "title": r.article.get("question_type"),
            "theme_label": r.theme_label,
            "score": r.score,
            "score_normalized": r.score_normalized,
        }
        for r in report.results
    ]


# ────────────────────────── Endpoint JSON (one-shot) ──────────────────────────

@router.post("/api/ask", response_model=AskResponse, summary="Pose une question (JSON)")
async def ask(req: AskRequest, request: Request) -> AskResponse:
    """Pipeline RAG + Claude → réponse JSON complète.

    Utile pour :
      - tests automatisés (benchmark Sprint 4)
      - clients qui ne supportent pas SSE
    """
    kb_store = getattr(request.app.state, "kb_store", None)
    claude = getattr(request.app.state, "claude_client", None)
    if kb_store is None:
        raise HTTPException(503, "KBStore non initialisé (boot incomplet)")

    # 1. RAG retrieval
    settings = get_settings()
    try:
        kb_dict, kb_index = await kb_store.get(req.module)
    except KeyError:
        raise HTTPException(404, f"Module inconnu: {req.module}") from None

    report = search(
        req.question, kb_dict, kb_index,
        top_k=settings.rag_top_k,
        threshold=settings.rag_score_min_hors_corpus,
    )
    logger.info(
        "[rag] module=%s top_score=%.2f hors_corpus=%s n_results=%d",
        req.module, report.best_score, report.hors_corpus, len(report.results),
    )

    confidence = _confidence_payload(report)
    sources = _sources_payload(report)

    # 2. Hors corpus → réponse courte, pas d'appel Claude (économie tokens)
    if report.hors_corpus:
        return AskResponse(
            answer=FALLBACK_HORS_CORPUS_TEXT,
            module=req.module,
            hors_corpus=True,
            confidence=confidence,
            sources=sources,
            n_results=len(report.results),
        )

    # 3. Cas pertinent : construction du contexte + appel Claude
    if claude is None:
        raise HTTPException(503, "ClaudeClient non initialisé (clé API manquante ?)")

    system_prompt = build_system_prompt(req.module)
    rag_context = build_rag_context([r.model_dump() for r in report.results])
    user_msg = build_user_message(req.question, rag_context, hors_corpus=False)

    try:
        response = await claude.complete(system=system_prompt, user=user_msg)
    except ClaudeError as e:
        logger.error("[claude] %s: %s", type(e).__name__, e)
        raise HTTPException(e.http_status, str(e)) from e

    return AskResponse(
        answer=response.text,
        module=req.module,
        hors_corpus=False,
        confidence=confidence,
        sources=sources,
        n_results=len(report.results),
    )


# ────────────────────────── Endpoint SSE (streaming) ──────────────────────────

async def _sse_stream(claude, system: str, user: str) -> AsyncIterator[bytes]:
    """Wrap les chunks Claude en évents SSE (text/event-stream).

    Format : "data: <json>\n\n"
    Chaque event contient {"type": "delta", "text": "..."}.
    Final event : {"type": "done"}.
    """
    try:
        async for chunk in claude.stream(system=system, user=user):
            payload = json.dumps({"type": "delta", "text": chunk}, ensure_ascii=False)
            yield f"data: {payload}\n\n".encode()
    except ClaudeError as e:
        # On envoie l'erreur sous forme d'event SSE — le client doit la traiter
        err_payload = json.dumps({"type": "error", "message": str(e), "http_status": e.http_status})
        yield f"data: {err_payload}\n\n".encode()
        return
    yield b'data: {"type": "done"}\n\n'


@router.post("/api/ask/stream", summary="Pose une question (SSE streaming)")
async def ask_stream(req: AskRequest, request: Request) -> StreamingResponse:
    """Variante streaming — token par token via Server-Sent Events.

    Premier token visible <1s vs 8-12s en mode JSON. Pour le frontend,
    parser chaque ligne `data: ...` jusqu'à recevoir `{"type": "done"}`.
    """
    kb_store = getattr(request.app.state, "kb_store", None)
    claude = getattr(request.app.state, "claude_client", None)
    if kb_store is None:
        raise HTTPException(503, "KBStore non initialisé")

    settings = get_settings()
    try:
        kb_dict, kb_index = await kb_store.get(req.module)
    except KeyError:
        raise HTTPException(404, f"Module inconnu: {req.module}") from None

    report = search(
        req.question, kb_dict, kb_index,
        top_k=settings.rag_top_k,
        threshold=settings.rag_score_min_hors_corpus,
    )

    # Hors corpus → on émet la réponse fallback en 1 chunk + done (pas d'appel Claude)
    if report.hors_corpus:
        async def _fallback_stream():
            payload = json.dumps({"type": "delta", "text": FALLBACK_HORS_CORPUS_TEXT})
            yield f"data: {payload}\n\n".encode()
            yield b'data: {"type": "done"}\n\n'

        return StreamingResponse(_fallback_stream(), media_type="text/event-stream")

    if claude is None:
        raise HTTPException(503, "ClaudeClient non initialisé")

    system_prompt = build_system_prompt(req.module)
    rag_context = build_rag_context([r.model_dump() for r in report.results])
    user_msg = build_user_message(req.question, rag_context, hors_corpus=False)

    return StreamingResponse(
        _sse_stream(claude, system_prompt, user_msg),
        media_type="text/event-stream",
    )
