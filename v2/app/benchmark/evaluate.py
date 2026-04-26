"""Évaluateur rule-based des réponses du benchmark.

Stratégie :
  1. Décision selon `expected_hors_corpus` :
     - Si attendu hors_corpus ET réponse refuse → hors_corpus_ok ✅
     - Si attendu hors_corpus ET réponse répond → false_response ❌
     - Si attendu réponse ET refuse → false_refuse ❌
  2. Sinon, comparer aux `correct_keywords` (fuzzy match insensible casse) :
     - Tous trouvés ET aucun forbidden → correct ✅
     - Quelques uns trouvés → partial 🟡
     - Aucun → incorrect ❌
  3. forbidden_phrases trouvées → hallucinated ❌

Pour Sprint 4.2, on pourra remplacer ce scoring rule-based par un
évaluateur LLM (Claude lit la réponse et juge), mais commencer simple.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from app.benchmark.schema import BenchmarkCorpus, BenchmarkQuestion, EvalResult

logger = logging.getLogger(__name__)


# ────────────────────────── Détection de refus ──────────────────────────

# Phrases typiques d'un refus honnête (V2) — utilisées pour détecter
# qu'une réponse est une mention "hors_corpus" plutôt qu'une vraie réponse.
REFUSAL_MARKERS = (
    "pas d'information fiable",
    "je n'ai pas",
    "n'ai pas d'information",
    "ne dispose pas",
    "hors corpus",
    "hors-sujet",
    "pas spécialisé",
    "pas de mon périmètre",
    "domaine de la cuisine",  # cas edge V1
    "chef cuisinier",
    "préciser votre question",
    "me donnez pas assez de détails",
)


def looks_like_refusal(answer: str) -> bool:
    """Heuristique : la réponse est-elle un refus / demande de précision ?

    On regarde les 500 premiers caractères — Claude commence souvent par
    "Je n'ai pas d'information..." quand il refuse.
    """
    if not answer:
        return True
    head = answer[:500].lower()
    return any(marker in head for marker in REFUSAL_MARKERS)


# ────────────────────────── Match keywords ──────────────────────────

def _normalize(text: str) -> str:
    """Lowercase + collapse whitespace pour matching robuste."""
    return re.sub(r"\s+", " ", text.lower()).strip()


def find_keywords(answer: str, keywords: list[str]) -> list[str]:
    """Retourne les keywords présents dans answer (insensible à la casse)."""
    norm = _normalize(answer)
    return [k for k in keywords if _normalize(k) in norm]


# Marqueurs de négation/inversion qui INVALIDENT un match forbidden_phrase.
# Si l'un de ces marqueurs apparaît dans les NEGATION_LOOKBACK_CHARS caractères
# précédant la forbidden_phrase, on considère le contexte comme négation
# (ex : "il ne faut **pas ignorer**" — "ignorer" est forbidden mais ici nié).
NEGATION_MARKERS = (
    "ne pas",
    "ne jamais",
    "il ne faut pas",
    "il faut éviter",
    "il faut eviter",
    "à éviter",
    "a eviter",
    "erreurs fréquentes",
    "erreurs frequentes",
    "erreurs à éviter",
    "erreurs a eviter",
    "pièges",
    "pieges",
    "non bloquant",
    "non bloquante",
    "à proscrire",
    "a proscrire",
    "interdit",
    "danger",
    "risque",
)

NEGATION_LOOKBACK_CHARS = 80

# Marqueurs immédiatement précédents (≤ 5 caractères) qui inversent le sens.
# Exemple : "**non obligatoire**" → "non " précède "obligatoire" → forbidden inversée.
IMMEDIATE_NEGATION_PREFIXES = (
    "non ",
    "pas ",
    "sans ",
    "aucun ",
    "aucune ",
    "jamais ",
    "ni ",
)


def find_forbidden(answer: str, forbidden: list[str]) -> list[str]:
    """Retourne les phrases interdites trouvées (signal d'hallucination).

    Filtre les **faux positifs contextuels** : si la forbidden_phrase est
    précédée immédiatement par une négation directe (« non », « pas »,
    « sans », ...) ou apparaît dans un contexte de négation
    (« il ne faut pas », « erreurs à éviter », ...) dans les
    NEGATION_LOOKBACK_CHARS caractères précédents, on ne la compte pas.
    """
    norm = _normalize(answer)
    found: list[str] = []
    for p in forbidden:
        np = _normalize(p)
        idx = norm.find(np)
        while idx >= 0:
            # 1) Négation immédiate (1-7 caractères avant)
            prefix = norm[max(0, idx - 7):idx]
            if any(prefix.endswith(m) for m in IMMEDIATE_NEGATION_PREFIXES):
                idx = norm.find(np, idx + len(np))
                continue
            # 2) Marqueur de négation dans le contexte large précédent
            context = norm[max(0, idx - NEGATION_LOOKBACK_CHARS):idx]
            if any(m in context for m in NEGATION_MARKERS):
                idx = norm.find(np, idx + len(np))
                continue
            # Match valide
            found.append(p)
            break
    return found


# ────────────────────────── Évaluation principale ──────────────────────────

def evaluate_answer(question: BenchmarkQuestion, answer: str) -> EvalResult:
    """Évalue une réponse selon les règles annotées dans la question.

    Retourne un EvalResult avec catégorie + détails.
    """
    refused = looks_like_refusal(answer)

    # Cas 1 : on attendait un refus (vague ou hors_sujet)
    if question.expected_hors_corpus:
        if refused:
            return EvalResult(
                question_id=question.id,
                module=question.module,
                category="hors_corpus_ok",
                notes="Refus correct sur question hors_corpus.",
            )
        # La réponse est substantielle alors qu'elle aurait dû refuser
        # → on vérifie quand même les forbidden (pire cas : hallucination)
        forbidden_found = find_forbidden(answer, question.forbidden_phrases)
        if forbidden_found:
            return EvalResult(
                question_id=question.id,
                module=question.module,
                category="hallucinated",
                forbidden_found=forbidden_found,
                notes="Aurait dû refuser ET a fabriqué de l'info.",
            )
        return EvalResult(
            question_id=question.id,
            module=question.module,
            category="false_response",
            notes="Aurait dû refuser mais a tenté de répondre.",
        )

    # Cas 2 : on attendait une réponse substantielle
    if refused:
        return EvalResult(
            question_id=question.id,
            module=question.module,
            category="false_refuse",
            keywords_missing=question.correct_keywords,
            notes="Aurait dû répondre mais a refusé (V2 trop strict ?).",
        )

    # Réponse donnée — vérifier keywords + forbidden
    kw_matched = find_keywords(answer, question.correct_keywords)
    kw_missing = [k for k in question.correct_keywords if k not in kw_matched]
    forbidden_found = find_forbidden(answer, question.forbidden_phrases)

    if forbidden_found:
        return EvalResult(
            question_id=question.id,
            module=question.module,
            category="hallucinated",
            keywords_matched=kw_matched,
            keywords_missing=kw_missing,
            forbidden_found=forbidden_found,
            notes="Phrase interdite détectée.",
        )

    # Si pas de keywords définis, on accepte par défaut (low confidence)
    if not question.correct_keywords:
        return EvalResult(
            question_id=question.id,
            module=question.module,
            category="correct",
            notes="Pas de keywords stricts — réponse acceptée par défaut.",
        )

    if len(kw_matched) == len(question.correct_keywords):
        return EvalResult(
            question_id=question.id,
            module=question.module,
            category="correct",
            keywords_matched=kw_matched,
        )
    if kw_matched:
        return EvalResult(
            question_id=question.id,
            module=question.module,
            category="partial",
            keywords_matched=kw_matched,
            keywords_missing=kw_missing,
        )
    return EvalResult(
        question_id=question.id,
        module=question.module,
        category="incorrect",
        keywords_missing=kw_missing,
    )


# ────────────────────────── Chargement corpus ──────────────────────────

_CORPUS_PATH = Path(__file__).parent / "corpus.json"


def load_corpus(path: Path | None = None) -> BenchmarkCorpus:
    """Charge et valide le corpus depuis JSON."""
    p = path or _CORPUS_PATH
    with open(p, encoding="utf-8") as f:
        data = json.load(f)
    return BenchmarkCorpus.model_validate(data)


# ────────────────────────── Synthèse ──────────────────────────

def summarize(results: list[EvalResult]) -> dict[str, Any]:
    """Aggrège les résultats pour un rapport markdown."""
    by_category: dict[str, int] = {}
    by_module: dict[str, dict[str, int]] = {}
    for r in results:
        by_category[r.category] = by_category.get(r.category, 0) + 1
        by_module.setdefault(r.module, {})
        by_module[r.module][r.category] = by_module[r.module].get(r.category, 0) + 1
    n = len(results)
    return {
        "total": n,
        "by_category": by_category,
        "by_module": by_module,
        "success_rate": round(
            (by_category.get("correct", 0) + by_category.get("hors_corpus_ok", 0)) / n * 100, 1,
        ) if n else 0.0,
    }
