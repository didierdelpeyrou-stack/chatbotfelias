"""Recherche RAG avec seuil hors_corpus (R1) et score normalisé (R2).

Cœur du fix V2 : on n'oblige plus le LLM à inventer une réponse à partir
d'articles non pertinents.

Pipeline :
  1. tokenize(question) — applique aussi le filtre substring R4
  2. lookup dans inverted index → accumule scores TF·IDF par article
  3. tri décroissant → top-K
  4. normalisation (R2) : score / max_score_possible
  5. seuil (R1) : si best_score < threshold → flag hors_corpus

Le caller décide quoi faire avec hors_corpus (renvoyer une réponse
fallback, escalader vers humain, etc.) — la logique RAG ne décide PAS,
elle SIGNALE.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.rag.index import tokenize
from app.rag.schema import RAGResult, RetrievalReport

# Bonus appliqué quand un token de la question matche EXACTEMENT un token de l'article
# (vs un substring). Calqué sur V1 (`+ 3.0 * tf * idf`).
EXACT_MATCH_WEIGHT = 3.0


def _max_score_possible(tokens: list[str], idf: dict[str, float]) -> float:
    """Score théorique maximal : si chaque token matche exactement avec tf=1.

    Sert à la normalisation R2 : score_normalized ∈ [0, 1].
    Si la question contient des tokens INCONNUS de l'index, ils contribuent 0.
    """
    return sum(EXACT_MATCH_WEIGHT * 1.0 * idf.get(tok, 0.0) for tok in tokens)


def search(
    question: str,
    kb: dict[str, Any],
    kb_index: dict[str, Any],
    *,
    top_k: int = 5,
    threshold: float = 1.5,
) -> RetrievalReport:
    """Recherche TF-IDF avec seuil hors_corpus.

    Args:
      question: requête utilisateur brute.
      kb: KB au format V1 ({"themes": [{"id", "label", "articles": [...]}]}).
      kb_index: index produit par `build_index(kb)`.
      top_k: max d'articles à retourner si on n'est pas hors corpus.
      threshold: score minimum pour considérer le top-1 comme pertinent (R1).

    Returns:
      RetrievalReport avec results triés + flags de décision.
    """
    inverted: dict[str, list[tuple[int, int, float]]] = kb_index.get("inverted", {})
    idf: dict[str, float] = kb_index.get("idf", {})

    # 1. Tokenize (R4 appliqué dans tokenize() : filtre substring + stopwords)
    raw_tokens = tokenize(question)
    n_filtered = len([t for t in question.split() if t.lower() not in raw_tokens])

    if not raw_tokens:
        # Tous les tokens ont été filtrés (question = "le la de" par ex)
        return RetrievalReport(
            results=[],
            hors_corpus=True,
            best_score=0.0,
            best_score_normalized=0.0,
            threshold=threshold,
            max_score_possible=0.0,
            n_tokens_query=0,
            n_tokens_filtered=n_filtered,
        )

    # 2. Lookup + scoring TF-IDF
    scores: dict[tuple[int, int], float] = defaultdict(float)
    for qtok in raw_tokens:
        # Match exact : (theme_idx, article_idx, tf) du token tel quel
        for t_idx, a_idx, tf in inverted.get(qtok, []):
            scores[(t_idx, a_idx)] += EXACT_MATCH_WEIGHT * tf * idf.get(qtok, 0.0)

    # 3. Tri + top-k
    if not scores:
        return RetrievalReport(
            results=[],
            hors_corpus=True,
            best_score=0.0,
            best_score_normalized=0.0,
            threshold=threshold,
            max_score_possible=_max_score_possible(raw_tokens, idf),
            n_tokens_query=len(raw_tokens),
            n_tokens_filtered=n_filtered,
        )

    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:top_k]

    # 4. Normalisation (R2)
    max_possible = _max_score_possible(raw_tokens, idf)
    best_raw_score = ranked[0][1]
    best_normalized = best_raw_score / max_possible if max_possible > 0 else 0.0
    # Cap à 1.0 (peut dépasser si plusieurs tokens matchent le même article)
    best_normalized = min(1.0, best_normalized)

    # 5. Construction des RAGResult
    themes = kb.get("themes", [])
    results: list[RAGResult] = []
    for (t_idx, a_idx), score in ranked:
        theme = themes[t_idx]
        article = theme["articles"][a_idx]
        norm = min(1.0, score / max_possible) if max_possible > 0 else 0.0
        results.append(RAGResult(
            score=float(score),
            score_normalized=float(norm),
            theme_id=str(theme.get("id", f"theme_{t_idx}")),
            theme_label=str(theme.get("label", "Inconnu")),
            niveau=theme.get("niveau", "vert"),
            article=article,
        ))

    # 6. Seuil hors_corpus (R1)
    hors_corpus = best_raw_score < threshold

    return RetrievalReport(
        results=results,
        hors_corpus=hors_corpus,
        best_score=float(best_raw_score),
        best_score_normalized=float(best_normalized),
        threshold=threshold,
        max_score_possible=float(max_possible),
        n_tokens_query=len(raw_tokens),
        n_tokens_filtered=n_filtered,
    )
