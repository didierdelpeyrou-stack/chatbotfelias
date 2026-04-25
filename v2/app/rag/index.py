"""Tokenizer + index inversé TF-IDF.

Migration propre du V1 (`_build_kb_index` dans app.py) avec :
  - Stop-words FR centralisés
  - Filtre tokens courts (R4) APPLIQUÉ AU TOKENIZER
    → bénéfice : non seulement le retrieval ignore les `le`/`de`,
      mais l'index inversé n'est pas pollué par eux.
  - IDF pré-calculé pour scoring sans recompute

Performance : O(K · M) à la requête où K=tokens question, M=postings/token.
Boot : O(N) sur N articles. Sur ELISFA : 158 articles → <100ms.
"""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from typing import Any

# Sprint 0.1 / 2.2 — filtre substring R4 :
# tokens < 3 chars sont ignorés (le/la/de/du/...) ET les stopwords FR usuels.
MIN_TOKEN_LEN = 3
FR_STOPWORDS: frozenset[str] = frozenset({
    "les", "des", "une", "aux", "que", "qui", "ses", "son", "sur", "par",
    "pas", "pour", "avec", "sans", "dans", "vers", "elle", "elles", "ils",
    "nous", "vous", "leur", "leurs", "mon", "ton", "mes", "tes", "votre",
    "notre", "nos", "vos", "est", "sont", "ait", "été", "être", "avoir",
    "fait", "tout", "tous", "toute", "toutes", "très", "peu", "plus",
    "moins", "mais", "donc", "car", "où", "quoi", "ceci", "cela", "celui",
    "celle", "ceux", "celles", "comme", "ainsi", "alors",
})


_TOKEN_RE = re.compile(r"[a-zA-ZÀ-ÿ0-9]+", flags=re.UNICODE)


def tokenize(text: str) -> list[str]:
    """Split + lowercase + filtre stop-words / tokens courts.

    Cette fonction est utilisée DEUX fois :
      1. Au boot, pour indexer chaque article
      2. À chaque requête, pour la question utilisateur

    → garantir que l'index et la requête utilisent EXACTEMENT le même
    pré-traitement, sinon scores incorrects.
    """
    if not text:
        return []
    raw = _TOKEN_RE.findall(text.lower())
    return [
        t for t in raw
        if len(t) >= MIN_TOKEN_LEN and t not in FR_STOPWORDS
    ]


def build_index(kb: dict[str, Any]) -> dict[str, Any]:
    """Construit un index inversé TF-IDF sur la KB.

    Parcourt chaque article (`question_type` + `mots_cles`) et stocke :
      - inverted[token] = [(theme_idx, article_idx, tf), ...]
      - idf[token] = log(1 + N / (1 + df))
      - n_articles : pour la normalisation

    La KB doit avoir le format V1 : `{"themes": [{"articles": [...]}]}`.
    """
    inverted: dict[str, list[tuple[int, int, float]]] = defaultdict(list)
    df: Counter[str] = Counter()
    n_articles = 0

    themes = kb.get("themes", [])
    for t_idx, theme in enumerate(themes):
        for a_idx, article in enumerate(theme.get("articles", [])):
            n_articles += 1
            # Concatène les champs textuels de l'article (titre + mots_cles)
            text_parts = [
                str(article.get("question_type", "")),
                " ".join(article.get("mots_cles", [])),
            ]
            tokens = tokenize(" ".join(text_parts))
            if not tokens:
                continue
            tf_local = Counter(tokens)
            for tok, tf in tf_local.items():
                inverted[tok].append((t_idx, a_idx, float(tf)))
            for tok in set(tokens):
                df[tok] += 1

    # IDF — formule classique avec lissage (+1 pour éviter division par 0)
    # log(1 + N / (1 + df)) → tokens rares ont un poids plus élevé
    idf: dict[str, float] = {
        tok: math.log(1.0 + n_articles / (1.0 + count))
        for tok, count in df.items()
    }

    return {
        "inverted": dict(inverted),
        "idf": idf,
        "n_articles": n_articles,
    }
