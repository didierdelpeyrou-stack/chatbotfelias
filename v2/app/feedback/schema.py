"""Schémas Pydantic du module feedback (Sprint 4.3).

Validation stricte côté API :
  - rating ∈ {-1, +1} (binary thumbs)
  - longueurs bornées (anti-DoS)
  - module = un des 4 modules connus

Privacy : on ne stocke jamais le User-Agent complet ni d'IP.
La question est conservée tronquée pour analyse (déjà publique côté UI).
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ModuleName = Literal["juridique", "formation", "rh", "gouvernance"]
Rating = Literal[-1, 1]  # -1 = 👎, 1 = 👍


class FeedbackRequest(BaseModel):
    """Payload entrant POST /api/feedback.

    Compat V1 : on accepte les mêmes champs que `app.py:/api/feedback` V1
    pour pouvoir réutiliser le bouton 👍/👎 du frontend tel quel.
    """

    model_config = ConfigDict(extra="ignore")  # ignore champs V1 non portés

    rating: Rating
    question: str = Field(..., min_length=1, max_length=2000)
    answer: str = Field(..., min_length=1, max_length=8000)
    module: ModuleName
    comment: str | None = Field(default=None, max_length=2000)
    question_hash: str | None = Field(default=None, max_length=32)
    confidence_label: str | None = Field(default=None, max_length=16)
    confidence_score: float | None = None


class FeedbackEntry(BaseModel):
    """Ce qu'on persiste réellement dans logs/feedback.jsonl.

    Diffère de FeedbackRequest : on ajoute timestamp + hash question
    (calculé serveur-side si non fourni) + on tronque les champs longs.
    """

    timestamp: str
    rating: Rating
    module: ModuleName
    question: str
    question_hash: str
    answer: str
    comment: str | None = None
    confidence_label: str | None = None
    confidence_score: float | None = None

    @classmethod
    def from_request(cls, req: FeedbackRequest, question_hash: str) -> FeedbackEntry:
        """Construit l'entrée à logger à partir du payload validé."""
        return cls(
            timestamp=datetime.now(UTC).isoformat(timespec="seconds"),
            rating=req.rating,
            module=req.module,
            question=req.question[:2000],
            question_hash=question_hash,
            answer=req.answer[:8000],
            comment=(req.comment or None) and req.comment[:2000],
            confidence_label=req.confidence_label,
            confidence_score=req.confidence_score,
        )


class FeedbackStats(BaseModel):
    """Réponse de GET /api/feedback/stats.

    Agrégat simple par module. Pas de PII : on ne renvoie ni question
    ni commentaire individuel — uniquement les compteurs.
    """

    total: int
    up: int
    down: int
    by_module: dict[str, dict[str, int]]
    success_rate: float  # up / (up + down) * 100, arrondi à 1 décimale
