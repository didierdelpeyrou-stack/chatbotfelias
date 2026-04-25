"""Schémas Pydantic des KB ELISFA — niveau permissif (Sprint 2.3).

Conçu pour accepter les 4 KB V1 actuelles (juridique/formation/rh/gouvernance)
sans modification, tout en validant les invariants critiques :
  - id non vide sur chaque article et theme
  - mots_cles est une liste de strings (pas une string seule)
  - niveau ∈ {vert, orange, rouge} si présent
  - liens.url valides si présents

Les enrichissements V2 (escalade article, revision) sont **optionnels** —
ils seront rendus obligatoires Sprint 5.1 (migration KB V1→V2).
"""
from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

# Niveaux d'escalade du chatbot juridique
NiveauLiteral = Literal["vert", "orange", "rouge"]


class Lien(BaseModel):
    """Un lien externe (Légifrance, gouvernement, etc.)."""

    model_config = ConfigDict(extra="allow")

    titre: str = Field(..., min_length=1, max_length=200)
    url: HttpUrl
    type: str | None = None  # ex: "legislation", "guide", "officiel"


class FichePratique(BaseModel):
    """Une fiche pratique téléchargeable (PDF)."""

    model_config = ConfigDict(extra="allow")

    fichier: str = Field(..., min_length=1)
    titre: str | None = None
    description: str | None = None


class Revision(BaseModel):
    """Métadonnée de révision d'un article (Sprint 5.1)."""

    model_config = ConfigDict(extra="allow")

    derniere_verification: date
    verifie_par: str = Field(..., min_length=1)


class Reponse(BaseModel):
    """Contenu structuré d'une réponse — composé pour Markdown rendering.

    Tous les champs sauf `synthese` sont optionnels — les KB V1 ont des
    schémas hétérogènes (formation a `minimum_legal`, juridique a
    `fondement_ccn`, etc.).
    """

    model_config = ConfigDict(extra="allow")

    synthese: str = Field(..., min_length=1)
    fondement_legal: str | None = None
    fondement_ccn: str | None = None
    application: str | None = None
    vigilance: str | None = None
    sources: list[str] = Field(default_factory=list)
    liens: list[Lien] = Field(default_factory=list)
    # Champs spécifiques formation
    minimum_legal: str | None = None
    plus_formation: str | None = None
    # Champ d'escalade (selon niveau)
    escalade: bool | None = None
    message_escalade: str | None = None


class Article(BaseModel):
    """Un article de KB — unité atomique du RAG."""

    model_config = ConfigDict(extra="allow", str_strip_whitespace=True)

    id: str = Field(..., min_length=1, max_length=80)
    question_type: str = Field(..., min_length=1)
    mots_cles: list[str] = Field(default_factory=list)
    reponse: Reponse
    fiches_pratiques: list[FichePratique] = Field(default_factory=list)

    # Enrichissements V2 — optionnels (audit 2026-04-21)
    niveau: NiveauLiteral | None = None
    # `escalade` accepte bool (V1, simple flag) OU str (V2, message d'instruction).
    # Sprint 5.1 normalisera en {action, delai, message}.
    escalade: bool | str | None = None
    revision: Revision | None = None

    @field_validator("mots_cles")
    @classmethod
    def _mots_cles_non_vides(cls, v: list[str]) -> list[str]:
        """Refuse les listes contenant des strings vides ('' ou whitespace).

        Garantie pour le RAG : tokenize() recevra des tokens valides.
        """
        cleaned = [m.strip() for m in v if m and m.strip()]
        return cleaned


class Theme(BaseModel):
    """Un thème = groupe d'articles partageant un sujet (ex. 'Rupture du contrat')."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(..., min_length=1, max_length=80)
    label: str = Field(..., min_length=1, max_length=200)
    articles: list[Article] = Field(default_factory=list)

    # Optionnels (présents en V1 juridique/formation, absents en RH/gouvernance)
    niveau: NiveauLiteral | None = None
    chapitre: str | None = None


class KBMetadata(BaseModel):
    """Métadonnées de la KB — laissées free-form pour respecter V1.

    On VÉRIFIE simplement que `version` est présent (pour le suivi),
    le reste est libre (chaque KB a ses propres champs : extension,
    libelle, perimetre, sources_principales, etc.).
    """

    model_config = ConfigDict(extra="allow")

    version: str = Field(..., min_length=1)


class KnowledgeBase(BaseModel):
    """KB complète chargée depuis JSON."""

    model_config = ConfigDict(extra="allow")

    metadata: KBMetadata
    themes: list[Theme] = Field(default_factory=list)

    @property
    def n_articles(self) -> int:
        """Total d'articles, utile pour les logs et la télémétrie."""
        return sum(len(t.articles) for t in self.themes)

    def to_v1_dict(self) -> dict[str, Any]:
        """Sérialise en dict compatible V1 (pour l'index TF-IDF du Sprint 2.2).

        Le module `app.rag.index.build_index()` attend un dict V1, donc on
        produit ce format quand on alimente le RAG.
        """
        return {
            "metadata": self.metadata.model_dump(mode="json"),
            "themes": [t.model_dump(mode="json", exclude_none=True) for t in self.themes],
        }
