"""Recherche RAG avec seuil hors_corpus (R1) et score normalisé (R2).

Cœur du fix V2 : on n'oblige plus le LLM à inventer une réponse à partir
d'articles non pertinents.

Pipeline TF-IDF (legacy, conservé pour fallback) :
  1. tokenize(question) — applique aussi le filtre substring R4
  2. lookup dans inverted index → accumule scores TF·IDF par article
  3. tri décroissant → top-K
  4. normalisation (R2) : score / max_score_possible
  5. seuil (R1) : si best_score < threshold → flag hors_corpus

Pipeline HYBRIDE (Sprint 5.2-stack — quand embedder actif) :
  1. TF-IDF retrieve top-K élargi (top_k * 2)
  2. Si tfidf_normalized top-1 > rag_skip_embedding_threshold : skip embeddings
     (économie latence, ~30% des requêtes typiquement)
  3. Sinon : embedding question + cosine sim avec articles top-K élargis
  4. Score final hybride : α · tfidf_norm + (1-α) · cosine_sim
  5. Re-rank et tronque à top_k final

Le caller décide quoi faire avec hors_corpus (renvoyer une réponse
fallback, escalader vers humain, etc.) — la logique RAG ne décide PAS,
elle SIGNALE.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

import numpy as np

from app.rag.embeddings import Embedder, cosine_similarity_batch
from app.rag.index import tokenize
from app.rag.schema import RAGResult, RetrievalReport

logger = logging.getLogger(__name__)

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
    # NOTE Sprint 5.2-bench : un fix "ratio score/tokens" a été testé pour
    # détecter les questions vagues type "améliorer ma structure" mais
    # créait 23% de faux HC sur les questions valides courtes. Le rule-based
    # RAG ne peut pas distinguer fiablement Q70 vague (ratio 3.96) de Q33
    # valide (ratio 4.02). Délégué à Claude au stade génération.

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


# ───────────────────── Pipeline HYBRIDE (Sprint 5.2-stack) ─────────────────────


async def search_hybrid(
    question: str,
    kb: dict[str, Any],
    kb_index: dict[str, Any],
    embedder: Embedder,
    *,
    top_k: int = 5,
    threshold: float = 1.5,
    alpha: float = 0.5,
    skip_embedding_threshold: float = 0.85,
    rerank_pool_size: int = 10,
) -> RetrievalReport:
    """Recherche RAG hybride TF-IDF + embeddings sémantiques.

    Args:
      question: requête utilisateur brute.
      kb: KB au format V1 ({"themes": [...]}).
      kb_index: index TF-IDF (build_index) + 'embeddings' (np.ndarray) + 'flat_ids'.
      embedder: VoyageEmbedder ou NoOpEmbedder. Si is_active=False → fallback TF-IDF.
      top_k: max d'articles dans le résultat final.
      threshold: seuil score brut TF-IDF pour hors_corpus.
      alpha: pondération hybride (1.0 = TF-IDF seul, 0.0 = embeddings seuls).
      skip_embedding_threshold: si tfidf_norm top-1 > seuil, skip embeddings.
      rerank_pool_size: nb candidats TF-IDF à re-ranker via embeddings.

    Returns:
      RetrievalReport avec scores hybrides.
    """
    # 1. TF-IDF avec pool élargi (pour avoir des candidats à re-ranker)
    tfidf_report = search(
        question, kb, kb_index, top_k=rerank_pool_size, threshold=threshold,
    )

    # Si pas d'embedder actif OU hors_corpus : retourner directement TF-IDF
    if not embedder.is_active or tfidf_report.hors_corpus or not tfidf_report.results:
        # Tronquer à top_k final si on avait demandé un pool plus large
        if len(tfidf_report.results) > top_k:
            tfidf_report = RetrievalReport(
                results=tfidf_report.results[:top_k],
                hors_corpus=tfidf_report.hors_corpus,
                best_score=tfidf_report.best_score,
                best_score_normalized=tfidf_report.best_score_normalized,
                threshold=tfidf_report.threshold,
                max_score_possible=tfidf_report.max_score_possible,
                n_tokens_query=tfidf_report.n_tokens_query,
                n_tokens_filtered=tfidf_report.n_tokens_filtered,
            )
        return tfidf_report

    # 2. Skip embeddings si confiance TF-IDF déjà très haute (gain latence)
    if tfidf_report.best_score_normalized >= skip_embedding_threshold:
        logger.debug(
            "[rag.hybrid] skip embeddings (tfidf_norm=%.3f >= %.2f)",
            tfidf_report.best_score_normalized, skip_embedding_threshold,
        )
        results = tfidf_report.results[:top_k]
        return RetrievalReport(
            results=results,
            hors_corpus=tfidf_report.hors_corpus,
            best_score=tfidf_report.best_score,
            best_score_normalized=tfidf_report.best_score_normalized,
            threshold=tfidf_report.threshold,
            max_score_possible=tfidf_report.max_score_possible,
            n_tokens_query=tfidf_report.n_tokens_query,
            n_tokens_filtered=tfidf_report.n_tokens_filtered,
        )

    # 3. Embeddings sémantiques + re-rank
    doc_embeddings: np.ndarray | None = kb_index.get("embeddings")
    flat_ids: list[tuple[int, int]] | None = kb_index.get("flat_ids")
    if doc_embeddings is None or flat_ids is None:
        logger.warning("[rag.hybrid] kb_index sans embeddings → fallback TF-IDF")
        return tfidf_report._replace(results=tfidf_report.results[:top_k]) \
            if hasattr(tfidf_report, '_replace') else tfidf_report

    try:
        query_vec = await embedder.embed_query(question)
    except Exception as exc:
        logger.warning("[rag.hybrid] embed_query failed (%s) → fallback TF-IDF", exc)
        return RetrievalReport(
            results=tfidf_report.results[:top_k],
            hors_corpus=tfidf_report.hors_corpus,
            best_score=tfidf_report.best_score,
            best_score_normalized=tfidf_report.best_score_normalized,
            threshold=tfidf_report.threshold,
            max_score_possible=tfidf_report.max_score_possible,
            n_tokens_query=tfidf_report.n_tokens_query,
            n_tokens_filtered=tfidf_report.n_tokens_filtered,
        )

    # 4. Re-rank : retrouver les indices plats des candidats TF-IDF
    flat_index_map = {tuple(fid): i for i, fid in enumerate(flat_ids)}
    theme_idx_by_id: dict[str, int] = {}
    for ti, theme in enumerate(kb.get("themes", [])):
        theme_idx_by_id[theme.get("id", f"theme_{ti}")] = ti

    cand_flat = []
    for r in tfidf_report.results:
        ti = theme_idx_by_id.get(r.theme_id)
        if ti is None:
            continue
        articles = kb["themes"][ti]["articles"]
        ai = next(
            (i for i, a in enumerate(articles) if a.get("id") == r.article.get("id")),
            None,
        )
        if ai is None:
            continue
        flat_idx = flat_index_map.get((ti, ai))
        if flat_idx is not None:
            cand_flat.append(flat_idx)

    if not cand_flat:
        # Pas de mapping → fallback TF-IDF
        return RetrievalReport(
            results=tfidf_report.results[:top_k],
            hors_corpus=tfidf_report.hors_corpus,
            best_score=tfidf_report.best_score,
            best_score_normalized=tfidf_report.best_score_normalized,
            threshold=tfidf_report.threshold,
            max_score_possible=tfidf_report.max_score_possible,
            n_tokens_query=tfidf_report.n_tokens_query,
            n_tokens_filtered=tfidf_report.n_tokens_filtered,
        )

    cand_doc_vecs = doc_embeddings[cand_flat]
    cosine_sims = cosine_similarity_batch(query_vec, cand_doc_vecs)
    # Normaliser cosine [-1, 1] → [0, 1] pour combinaison hybride
    cosine_norm = (cosine_sims + 1.0) / 2.0

    # 5. Score hybride
    rescored = []
    for r, cos in zip(tfidf_report.results, cosine_norm, strict=True):
        hybrid = alpha * r.score_normalized + (1 - alpha) * float(cos)
        # On préserve le score TF-IDF brut, mais on remplace score_normalized
        # par le score hybride pour le re-ranking
        rescored.append((hybrid, float(cos), r))

    rescored.sort(key=lambda x: x[0], reverse=True)
    top = rescored[:top_k]

    new_results = []
    for hybrid_score, _cos, r in top:
        new_results.append(RAGResult(
            score=r.score,
            score_normalized=hybrid_score,  # ← score hybride en clé de tri
            theme_id=r.theme_id,
            theme_label=r.theme_label,
            niveau=r.niveau,
            article=r.article,
        ))

    return RetrievalReport(
        results=new_results,
        hors_corpus=tfidf_report.hors_corpus,
        best_score=tfidf_report.best_score,
        best_score_normalized=top[0][0] if top else 0.0,
        threshold=threshold,
        max_score_possible=tfidf_report.max_score_possible,
        n_tokens_query=tfidf_report.n_tokens_query,
        n_tokens_filtered=tfidf_report.n_tokens_filtered,
    )
