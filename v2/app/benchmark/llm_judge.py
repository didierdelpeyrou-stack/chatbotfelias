"""LLM-judge évaluateur (Sprint 5.2-stack Phase A2).

Remplace le keyword matching rule-based par un jugement Claude Haiku 4.5.
Plus fiable : tolère les paraphrases, comprend les négations contextuelles,
mesure la complétude vs les notes de la question.

Coût : ~0.001 € par jugement avec Haiku 4.5 (300 input + 100 output tokens).
Pour un bench 70 Q × 3 runs = 210 appels = ~0.20 €.

Usage :
    from app.benchmark.llm_judge import judge_answer
    result = await judge_answer(client, question, answer)
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.benchmark.schema import BenchmarkQuestion, EvalResult
from app.llm.claude import ClaudeClient

logger = logging.getLogger(__name__)


_JUDGE_SYSTEM = """\
Tu es un évaluateur impartial de la qualité de réponses d'un chatbot juridique
spécialisé dans la branche ALISFA (action sociale, animation, formation).

Tu dois évaluer une RÉPONSE par rapport à une QUESTION + ATTENTES.
Réponds UNIQUEMENT en JSON strict, format :
{
  "category": "correct" | "partial" | "incorrect" | "hors_corpus_ok" | "false_response" | "false_refuse" | "hallucinated",
  "pertinence": 1-5,
  "exactitude": 1-5,
  "completude": 1-5,
  "rationale": "brève justification 1-2 phrases"
}

Catégories :
- "correct"        : la réponse est complète, factuelle, traite la question
- "partial"        : la réponse touche le sujet mais manque d'éléments importants
- "incorrect"      : la réponse aborde le sujet mais avec des erreurs factuelles
- "hors_corpus_ok" : la question était hors-corpus ET la réponse refuse poliment
- "false_response" : la question était hors-corpus mais la réponse essaie de répondre
- "false_refuse"   : la question méritait une réponse mais V2 refuse à tort
- "hallucinated"   : la réponse contient des faits inventés ou contraires aux attentes

Critères :
- pertinence : la réponse traite-t-elle bien la question posée ? (5 = parfaitement)
- exactitude : les faits cités correspondent-ils aux notes/keywords attendus ? (5 = parfaitement)
- completude : la réponse couvre-t-elle les points clés attendus ? (5 = parfaitement)

Sois strict mais juste : une réponse qui dit l'essentiel correct mérite "correct"
même si elle paraphrase. Une réponse qui contient une erreur factuelle est
"hallucinated" même si le reste est juste."""


def _build_user_prompt(question: BenchmarkQuestion, answer: str) -> str:
    """Compose le message utilisateur pour le juge."""
    expected_kw = ", ".join(question.correct_keywords) if question.correct_keywords else "aucun"
    forbidden = ", ".join(question.forbidden_phrases) if question.forbidden_phrases else "aucun"
    expected_type = "HORS-CORPUS (refus attendu)" if question.expected_hors_corpus else "RÉPONSE attendue"

    return f"""\
QUESTION POSÉE :
{question.question}

CONTEXTE DE LA QUESTION :
- Module : {question.module}
- Type attendu : {expected_type}
- Sujet attendu : {question.expected_topic_hint}
- Keywords attendus dans la réponse : {expected_kw}
- Phrases interdites (signe d'erreur) : {forbidden}
- Notes additionnelles : {question.notes}

RÉPONSE FOURNIE PAR LE CHATBOT :
{answer[:2000]}

Évalue cette réponse selon les critères. JSON only."""


async def judge_answer(
    client: ClaudeClient,
    question: BenchmarkQuestion,
    answer: str,
) -> EvalResult:
    """Évalue une réponse via Claude Haiku 4.5 et retourne un EvalResult.

    Fallback en cas d'erreur : log + EvalResult catégorie "incorrect" avec note.
    """
    user_msg = _build_user_prompt(question, answer)

    try:
        response = await client.complete(system=_JUDGE_SYSTEM, user=user_msg)
        raw = response.text.strip()

        # Extraction JSON robuste : on cherche un objet JSON dans la réponse
        match = re.search(r"\{[^{]*\}", raw, re.DOTALL)
        if not match:
            raise ValueError(f"Pas de JSON trouvé dans : {raw[:200]}")
        data = json.loads(match.group(0))

        category = data.get("category", "incorrect")
        # Validation
        valid_cats = {
            "correct", "partial", "incorrect", "hors_corpus_ok",
            "false_response", "false_refuse", "hallucinated",
        }
        if category not in valid_cats:
            category = "incorrect"

        rationale = data.get("rationale", "")[:500]
        pertinence = int(data.get("pertinence", 0))
        exactitude = int(data.get("exactitude", 0))
        completude = int(data.get("completude", 0))

        return EvalResult(
            question_id=question.id,
            module=question.module,
            category=category,
            notes=(
                f"LLM-judge p={pertinence}/5 e={exactitude}/5 c={completude}/5 — "
                f"{rationale}"
            ),
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("[llm-judge] %s : %s — fallback 'incorrect'", question.id, exc)
        return EvalResult(
            question_id=question.id,
            module=question.module,
            category="incorrect",
            notes=f"LLM-judge erreur : {exc}",
        )


def stats_consensus(rule_based: list[EvalResult], llm_judge: list[EvalResult]) -> dict[str, Any]:
    """Compare les deux évaluateurs sur les mêmes questions.

    Retourne un dict avec :
    - n_total
    - n_agreement : combien de questions ont la même catégorie
    - disagreements : liste des (question_id, rule_cat, judge_cat)
    - by_category : matrice de transition rule → judge
    """
    by_id_rule = {r.question_id: r.category for r in rule_based}
    by_id_judge = {r.question_id: r.category for r in llm_judge}

    common = set(by_id_rule) & set(by_id_judge)
    n_agreement = sum(1 for qid in common if by_id_rule[qid] == by_id_judge[qid])

    disagreements = [
        {"qid": qid, "rule": by_id_rule[qid], "judge": by_id_judge[qid]}
        for qid in sorted(common)
        if by_id_rule[qid] != by_id_judge[qid]
    ]

    matrix: dict[tuple[str, str], int] = {}
    for qid in common:
        key = (by_id_rule[qid], by_id_judge[qid])
        matrix[key] = matrix.get(key, 0) + 1

    return {
        "n_total": len(common),
        "n_agreement": n_agreement,
        "agreement_rate": round(n_agreement / len(common) * 100, 1) if common else 0.0,
        "n_disagreements": len(disagreements),
        "disagreements": disagreements,
        "transition_matrix": {f"{k[0]} → {k[1]}": v for k, v in sorted(matrix.items())},
    }
