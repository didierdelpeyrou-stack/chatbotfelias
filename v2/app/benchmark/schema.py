"""Schémas Pydantic du corpus benchmark + des résultats d'évaluation.

Toute la rigueur de la "double-blind eval" repose sur la qualité des
annotations : un corpus mal annoté → un benchmark sans valeur.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ModuleName = Literal["juridique", "formation", "rh", "gouvernance"]
QuestionType = Literal["precise", "vague", "hors_sujet"]


class BenchmarkQuestion(BaseModel):
    """Une question du corpus, annotée pour la référence (ground truth)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str = Field(..., pattern=r"^Q\d{2,3}$")
    module: ModuleName
    expected_type: QuestionType
    question: str = Field(..., min_length=3, max_length=400)

    # Annotations ground truth
    expected_hors_corpus: bool = Field(
        ...,
        description="True si on attend que le système refuse honnêtement (hors_sujet ou question trop vague pour répondre)",
    )
    expected_topic_hint: str | None = Field(
        None,
        description="Theme RAG attendu si la question est précise (utile pour debug, pas pour scoring strict)",
    )
    correct_keywords: list[str] = Field(
        default_factory=list,
        description="Mots-clés DEVANT apparaître dans une bonne réponse (insensible à la casse). Vide pour hors_sujet/vague.",
    )
    forbidden_phrases: list[str] = Field(
        default_factory=list,
        description="Phrases qui révèlent une hallucination (ex: 'article L9999' qui n'existe pas)",
    )
    notes: str | None = Field(
        None,
        description="Annotation libre — pourquoi cette question est dans le corpus, où chercher la bonne réponse, etc.",
    )


class BenchmarkCorpus(BaseModel):
    """Le corpus complet (chargé depuis corpus.json)."""

    model_config = ConfigDict(extra="forbid")

    metadata: dict
    questions: list[BenchmarkQuestion]

    @property
    def n_questions(self) -> int:
        return len(self.questions)

    def by_module(self, module: ModuleName) -> list[BenchmarkQuestion]:
        return [q for q in self.questions if q.module == module]


# ────────────────────────── Résultat d'une évaluation ──────────────────────────

EvalCategory = Literal[
    "correct",       # bons keywords présents, pas de phrase interdite
    "partial",       # quelques keywords mais incomplet
    "hors_corpus_ok",  # le système a refusé sur question hors_sujet/vague (correct)
    "false_refuse",  # le système a refusé alors qu'il aurait dû répondre
    "false_response",  # le système a répondu alors qu'il aurait dû refuser
    "hallucinated",  # phrase interdite détectée (info inventée)
    "incorrect",     # ne correspond à rien d'attendu
]


class EvalResult(BaseModel):
    """Résultat d'une évaluation rule-based d'une réponse."""

    model_config = ConfigDict(extra="forbid")

    question_id: str
    module: str
    category: EvalCategory
    keywords_matched: list[str] = Field(default_factory=list)
    keywords_missing: list[str] = Field(default_factory=list)
    forbidden_found: list[str] = Field(default_factory=list)
    notes: str | None = None
