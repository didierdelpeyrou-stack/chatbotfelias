"""Endpoints feedback V2 (Sprint 4.3).

POST /api/feedback        → enregistre un 👍/👎 dans logs/feedback.jsonl
GET  /api/feedback/stats  → agrégat global (volume + ratio par module)

Compat V1 : même payload accepté que `app.py:/api/feedback` V1, donc
le bouton 👍/👎 du frontend SPA fonctionne contre V1 ou V2 sans modif.
"""
from __future__ import annotations

import logging
from collections import defaultdict

from fastapi import APIRouter, HTTPException

from app.feedback.logger import append_feedback, read_all_feedbacks
from app.feedback.schema import FeedbackRequest, FeedbackStats

logger = logging.getLogger(__name__)
router = APIRouter(tags=["feedback"])


@router.post("/api/feedback", summary="Enregistre un feedback 👍/👎")
async def post_feedback(req: FeedbackRequest) -> dict[str, str]:
    """Persiste un rating utilisateur dans logs/feedback.jsonl.

    Retourne un payload minimal `{"status": "ok"}` (compat V1).
    """
    try:
        entry = await append_feedback(req)
    except OSError as exc:
        logger.error("[feedback] append failed: %s", exc)
        raise HTTPException(500, "Échec écriture feedback") from exc
    logger.info(
        "[feedback] module=%s rating=%+d hash=%s",
        entry.module, entry.rating, entry.question_hash,
    )
    return {"status": "ok"}


@router.get("/api/feedback/stats", response_model=FeedbackStats, summary="Stats agrégées")
async def get_feedback_stats() -> FeedbackStats:
    """Renvoie l'agrégat global. Lecture full-scan du JSONL.

    Pas d'auth pour l'instant (V2 dev) — Sprint 4.4 ajoutera un token
    admin avant exposition staging publique.
    """
    entries = read_all_feedbacks()
    total = len(entries)
    up = sum(1 for e in entries if e.get("rating") == 1)
    down = sum(1 for e in entries if e.get("rating") == -1)

    by_module: dict[str, dict[str, int]] = defaultdict(lambda: {"up": 0, "down": 0})
    for e in entries:
        mod = e.get("module") or "inconnu"
        if e.get("rating") == 1:
            by_module[mod]["up"] += 1
        elif e.get("rating") == -1:
            by_module[mod]["down"] += 1

    rated = up + down
    success_rate = round(up / rated * 100, 1) if rated else 0.0

    return FeedbackStats(
        total=total,
        up=up,
        down=down,
        by_module=dict(by_module),
        success_rate=success_rate,
    )
