"""Helpers pour formater les articles RAG en contexte LLM (Sprint 3.2).

Les articles retrouvés par le RAG (Sprint 2.2) sont des dicts avec un schéma
hétérogène (synthese / fondement_legal / minimum_legal selon module). On les
sérialise en Markdown pour Claude, en respectant la convention R11
([ART_xxx] pour permettre la citation).
"""
from __future__ import annotations

from typing import Any

# Champs de `Reponse` à inclure dans le contexte LLM, par ordre de pertinence.
# On évite d'envoyer 3000 tokens si seuls 2-3 champs sont utiles.
_CONTEXT_FIELDS_ORDER = (
    "synthese",
    "fondement_ccn",
    "fondement_legal",
    "application",
    "vigilance",
    "minimum_legal",
    "plus_formation",
)


def format_article(rag_result: dict[str, Any]) -> str:
    """Sérialise un RAGResult.dict() en Markdown.

    Format :
        ## [ART_xxx] - Titre
        Theme: ...
        Score: 95.32 (normalized 1.00)

        **Synthèse**: ...
        **Fondement CCN**: ...
        ...
    """
    article = rag_result.get("article", {})
    art_id = article.get("id", "ART_UNKNOWN")
    titre = article.get("question_type", "(sans titre)")
    theme = rag_result.get("theme_label", "")
    score = rag_result.get("score", 0.0)
    score_norm = rag_result.get("score_normalized", 0.0)

    lines = [
        f"## [{art_id}] {titre}",
        f"_Thème : {theme} — score {score:.1f} (norm {score_norm:.2f})_",
        "",
    ]
    reponse = article.get("reponse", {})
    for field in _CONTEXT_FIELDS_ORDER:
        value = reponse.get(field)
        if value:
            label = field.replace("_", " ").capitalize()
            lines.append(f"**{label}** : {value}")
    return "\n".join(lines).strip()


def build_rag_context(rag_results: list[dict[str, Any]], *, max_articles: int = 5) -> str:
    """Concatène les top-k articles en un contexte Markdown unique.

    Args:
      rag_results: liste de RAGResult.model_dump() — déjà triée par score.
      max_articles: limite haute pour éviter de saturer le contexte Claude.

    Returns:
      Texte Markdown prêt à être injecté dans le `user message` du prompt.
    """
    if not rag_results:
        return "_(aucun article pertinent retrouvé)_"

    blocks = [format_article(r) for r in rag_results[:max_articles]]
    return "\n\n---\n\n".join(blocks)
