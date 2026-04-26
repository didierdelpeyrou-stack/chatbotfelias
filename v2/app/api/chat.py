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
import time
from collections.abc import AsyncIterator
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.llm.claude import ClaudeError
from app.llm.context import build_rag_context
from app.llm.modes import MODES, get_mode, get_modes_for_module
from app.llm.profiles import get_profile, list_profiles
from app.llm.prompts import build_system_prompt, build_user_message, resolve_module_for_theme
from app.metrics.prometheus import (
    record_claude_tokens,
    record_latency,
    record_rag,
    record_request,
)
from app.rag.retrieval import search, search_hybrid
from app.settings import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])

ModuleName = Literal["juridique", "formation", "rh", "gouvernance"]


# ────────────────────────── Modèles I/O ──────────────────────────

class AskRequest(BaseModel):
    """Payload entrant de POST /api/ask."""

    question: str = Field(..., min_length=1, max_length=4000)
    module: ModuleName = "juridique"
    mode: str | None = Field(
        None,
        max_length=80,
        description=(
            "ID de mode optionnel (ex. 'juridique_urgence'). Si fourni et valide,"
            " l'overlay est ajouté au system prompt. Sinon mode chat libre."
        ),
    )
    profile: str | None = Field(
        None,
        max_length=80,
        description=(
            "Sprint 4.6 F1.5 — ID de profil utilisateur optionnel (ex. 'benevole_president',"
            " 'pro_directeur'). Adapte le niveau et le ton de la réponse via un contexte"
            " ajouté au system prompt."
        ),
    )


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


def _apply_mode_overlay(system_prompt: str, mode_id: str | None, module: str) -> str:
    """Sprint 4.6 F1 : suffixe l'overlay du mode si valide pour ce module.

    Retourne le system_prompt original si mode_id absent, inconnu, ou cohérent
    avec un autre module (sécurité : un mode 'rh_urgence' ne s'applique pas
    à module='juridique').
    """
    mode = get_mode(mode_id)
    if mode is None:
        return system_prompt
    if mode["module"] != module:
        # Mode non-cohérent avec le module : on log et on ignore silencieusement
        logger.info(
            "[modes] mode %s incompatible avec module %s : ignoré",
            mode_id, module,
        )
        return system_prompt
    overlay = mode["overlay"].strip()
    return f"{system_prompt}\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n{overlay}\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"


def _apply_profile_context(system_prompt: str, profile_id: str | None) -> str:
    """Sprint 4.6 F1.5 : injecte le contexte utilisateur (qui est l'utilisateur ?).

    Le contexte adapte le niveau et le ton de la réponse (vulgarisation pour
    bénévoles, technique pour pros). N'a aucun effet si profile_id absent ou
    inconnu.
    """
    profile = get_profile(profile_id)
    if profile is None:
        return system_prompt
    ctx = profile["context"].strip()
    block = f"PROFIL DE L'UTILISATEUR\n{ctx}"
    return f"{system_prompt}\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n{block}\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"


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
    t_start = time.perf_counter()
    kb_store = getattr(request.app.state, "kb_store", None)
    claude = getattr(request.app.state, "claude_client", None)
    if kb_store is None:
        raise HTTPException(503, "KBStore non initialisé (boot incomplet)")

    # 1. RAG retrieval
    settings = get_settings()
    try:
        kb_dict, kb_index = await kb_store.get(req.module)
    except KeyError:
        record_request(module=req.module, status="error")
        raise HTTPException(404, f"Module inconnu: {req.module}") from None

    # Sprint 5.2-stack : pipeline hybride si embedder actif, sinon TF-IDF
    embedder = getattr(request.app.state, "embedder", None)
    if embedder is not None and embedder.is_active:
        report = await search_hybrid(
            req.question, kb_dict, kb_index, embedder,
            top_k=settings.rag_top_k,
            threshold=settings.rag_score_min_hors_corpus,
            alpha=settings.rag_hybrid_alpha,
            skip_embedding_threshold=settings.rag_skip_embedding_threshold,
        )
    else:
        report = search(
            req.question, kb_dict, kb_index,
            top_k=settings.rag_top_k,
            threshold=settings.rag_score_min_hors_corpus,
        )
    logger.info(
        "[rag] module=%s top_score=%.2f hors_corpus=%s n_results=%d hybrid=%s",
        req.module, report.best_score, report.hors_corpus, len(report.results),
        embedder is not None and embedder.is_active,
    )
    # Sprint 3.3 : metrics Prometheus du retrieval
    record_rag(
        module=req.module,
        best_score=report.best_score,
        hors_corpus=report.hors_corpus,
    )

    confidence = _confidence_payload(report)
    sources = _sources_payload(report)

    # 2. Hors corpus → réponse courte, pas d'appel Claude (économie tokens)
    if report.hors_corpus:
        record_request(module=req.module, status="hors_corpus")
        record_latency(module=req.module, path="/api/ask", seconds=time.perf_counter() - t_start)
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
        record_request(module=req.module, status="error")
        raise HTTPException(503, "ClaudeClient non initialisé (clé API manquante ?)")

    # Sprint 5.2-tune : routage du prompt par theme_id du top-1 article RAG.
    # Plus pertinent que le module client : un article du thème
    # `fonctions_reglementaires` mérite un prompt juridique, pas formation.
    top1_theme_id = report.results[0].theme_id if report.results else None
    effective_module = resolve_module_for_theme(top1_theme_id, fallback=req.module)
    system_prompt = build_system_prompt(effective_module)
    # Sprint 4.6 F1 : overlay de mode optionnel (urgence, analyse, rédaction, …)
    system_prompt = _apply_mode_overlay(system_prompt, req.mode, req.module)
    system_prompt = _apply_profile_context(system_prompt, req.profile)
    rag_context = build_rag_context([r.model_dump() for r in report.results])
    user_msg = build_user_message(req.question, rag_context, hors_corpus=False)

    try:
        response = await claude.complete(system=system_prompt, user=user_msg)
    except ClaudeError as e:
        logger.error("[claude] %s: %s", type(e).__name__, e)
        record_request(module=req.module, status="error")
        record_latency(module=req.module, path="/api/ask", seconds=time.perf_counter() - t_start)
        raise HTTPException(e.http_status, str(e)) from e

    # Sprint 3.3 : metrics Prometheus tokens + latence + status
    record_claude_tokens(
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
        cache_creation_tokens=response.cache_creation_tokens,
        cache_read_tokens=response.cache_read_tokens,
    )
    record_request(module=req.module, status="ok")
    record_latency(module=req.module, path="/api/ask", seconds=time.perf_counter() - t_start)

    return AskResponse(
        answer=response.text,
        module=req.module,
        hors_corpus=False,
        confidence=confidence,
        sources=sources,
        n_results=len(report.results),
    )


# ────────────────────────── Endpoint SSE (streaming) ──────────────────────────

async def _sse_stream(
    claude,
    system: str,
    user: str,
    sources: list[dict[str, Any]] | None = None,
    hors_corpus: bool = False,
) -> AsyncIterator[bytes]:
    """Wrap les chunks Claude en évents SSE (text/event-stream).

    Format : "data: <json>\n\n"
    Sequence :
      1. {"type": "sources", "sources": [...], "hors_corpus": bool} — premier event (Sprint 4.5-frontend)
      2. {"type": "delta", "text": "..."} — token par token
      3. {"type": "done"} — fin
    En cas d'erreur Claude :
      - {"type": "error", "message": "...", "http_status": N}
    """
    # Sprint 4.5-frontend : envoie sources AVANT les tokens pour que le client
    # affiche le panneau sources dès le début du streaming.
    if sources is not None:
        sources_payload = json.dumps(
            {"type": "sources", "sources": sources, "hors_corpus": hors_corpus},
            ensure_ascii=False,
        )
        yield f"data: {sources_payload}\n\n".encode()

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

    # Sprint 5.2-stack : pipeline hybride si embedder actif (cohérent /api/ask)
    embedder = getattr(request.app.state, "embedder", None)
    if embedder is not None and embedder.is_active:
        report = await search_hybrid(
            req.question, kb_dict, kb_index, embedder,
            top_k=settings.rag_top_k,
            threshold=settings.rag_score_min_hors_corpus,
            alpha=settings.rag_hybrid_alpha,
            skip_embedding_threshold=settings.rag_skip_embedding_threshold,
        )
    else:
        report = search(
            req.question, kb_dict, kb_index,
            top_k=settings.rag_top_k,
            threshold=settings.rag_score_min_hors_corpus,
        )

    # Sprint 4.5-frontend : on construit le payload sources une fois pour le réutiliser
    sources_list = _sources_payload(report)

    # Hors corpus → on émet la réponse fallback en 1 chunk + done (pas d'appel Claude)
    if report.hors_corpus:
        async def _fallback_stream():
            sources_evt = json.dumps(
                {"type": "sources", "sources": sources_list, "hors_corpus": True},
                ensure_ascii=False,
            )
            yield f"data: {sources_evt}\n\n".encode()
            payload = json.dumps({"type": "delta", "text": FALLBACK_HORS_CORPUS_TEXT})
            yield f"data: {payload}\n\n".encode()
            yield b'data: {"type": "done"}\n\n'

        return StreamingResponse(_fallback_stream(), media_type="text/event-stream")

    if claude is None:
        raise HTTPException(503, "ClaudeClient non initialisé")

    # Sprint 5.2-tune : routage par theme_id (cohérent avec /api/ask)
    top1_theme_id = report.results[0].theme_id if report.results else None
    effective_module = resolve_module_for_theme(top1_theme_id, fallback=req.module)
    system_prompt = build_system_prompt(effective_module)
    # Sprint 4.6 F1 : overlay de mode (cohérent avec /api/ask)
    system_prompt = _apply_mode_overlay(system_prompt, req.mode, req.module)
    system_prompt = _apply_profile_context(system_prompt, req.profile)
    rag_context = build_rag_context([r.model_dump() for r in report.results])
    user_msg = build_user_message(req.question, rag_context, hors_corpus=False)

    return StreamingResponse(
        _sse_stream(claude, system_prompt, user_msg, sources=sources_list, hors_corpus=False),
        media_type="text/event-stream",
    )


# ────────────────────────── Endpoint Modes (Sprint 4.6 F1) ──────────────────────────

@router.get("/api/modes", summary="Liste des modes disponibles par module")
async def list_modes(module: ModuleName | None = None) -> dict[str, Any]:
    """Retourne les modes (overlays prompt) disponibles, filtrables par module.

    Réponse : { "modes": [{id, label, icon, module, placeholder}, ...] }

    L'overlay (prompt système) n'est PAS retourné — il reste côté serveur
    pour ne pas exposer le prompt engineering.
    """
    if module:
        items = get_modes_for_module(module)
    else:
        items = list(MODES.values())

    return {
        "modes": [
            {
                "id": m["id"],
                "label": m["label"],
                "icon": m["icon"],
                "module": m["module"],
                "placeholder": m["placeholder"],
            }
            for m in items
        ],
    }


# ────────────────────────── Endpoint Profils utilisateur (Sprint 4.6 F1.5) ──────────────────────────

@router.get("/api/profiles", summary="Liste des profils utilisateur (onboarding)")
async def get_profiles_endpoint() -> dict[str, Any]:
    """Retourne les 5 profils utilisateur disponibles.

    Réponse : { "profiles": [{id, name, icon, type, modules, context_short}, ...] }

    Le `context` complet (texte injecté dans le system prompt) n'est PAS exposé —
    seul un résumé court est renvoyé pour affichage UI.
    """
    return {
        "profiles": [
            {
                "id": p["id"],
                "name": p["name"],
                "icon": p["icon"],
                "type": p["type"],
                "modules": p["modules"],
                # Premier mot de contexte tronqué : aperçu UI sans révéler le prompt
                "summary": p["context"].split(".")[0] + ".",
            }
            for p in list_profiles()
        ],
    }
