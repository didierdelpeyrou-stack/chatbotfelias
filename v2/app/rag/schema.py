"""Schémas Pydantic du module RAG.

On expose des objets typés (vs dicts) pour :
  - autodoc Swagger (Sprint 3.2)
  - garantir le contrat API
  - faciliter les tests
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class RAGResult(BaseModel):
    """Un article retrouvé par le RAG, avec ses métadonnées de scoring."""

    score: float = Field(..., description="Score TF-IDF brut")
    score_normalized: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Score normalisé sur [0, 1] — comparable inter-modules (R2)",
    )
    theme_id: str
    theme_label: str
    niveau: Literal["vert", "orange", "rouge"] = "vert"
    article: dict[str, Any] = Field(..., description="Article complet (id, mots_cles, reponse, ...)")


class RetrievalReport(BaseModel):
    """Bilan d'une recherche RAG — utilisé pour la télémétrie et le debug.

    Contient les résultats top-k ET les métadonnées de décision (seuil
    franchi ou pas, max_score_possible utilisé pour la normalisation).
    """

    results: list[RAGResult] = Field(default_factory=list)
    hors_corpus: bool = Field(
        ...,
        description="True si le best_score < SCORE_MIN_HORS_CORPUS (R1)",
    )
    best_score: float = 0.0
    best_score_normalized: float = 0.0
    threshold: float = Field(..., description="Seuil hors_corpus appliqué")
    max_score_possible: float = Field(
        ...,
        description="Score théorique max utilisé pour la normalisation (R2)",
    )
    n_tokens_query: int = 0
    n_tokens_filtered: int = Field(
        0, description="Tokens ignorés par le filtre substring (R4)"
    )
