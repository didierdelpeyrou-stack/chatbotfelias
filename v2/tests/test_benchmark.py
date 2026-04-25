"""Tests du corpus benchmark + de l'évaluateur rule-based (Sprint 4.1).

On teste :
  - Validité du corpus (50 questions, distribution conforme)
  - Évaluateur sur des cas connus (correct, partial, hallucinated, refus, etc.)
"""
from __future__ import annotations

from app.benchmark.evaluate import (
    evaluate_answer,
    find_forbidden,
    find_keywords,
    load_corpus,
    looks_like_refusal,
    summarize,
)
from app.benchmark.schema import BenchmarkQuestion, EvalResult

# ────────────────────────── Corpus ──────────────────────────

class TestCorpus:
    def test_corpus_charge_et_valide(self):
        c = load_corpus()
        assert c.n_questions == 50

    def test_distribution_par_module_conforme_metadata(self):
        c = load_corpus()
        counts = {}
        for q in c.questions:
            counts[q.module] = counts.get(q.module, 0) + 1
        assert counts == {"juridique": 20, "formation": 10, "rh": 10, "gouvernance": 10}

    def test_ids_uniques(self):
        c = load_corpus()
        ids = [q.id for q in c.questions]
        assert len(ids) == len(set(ids)), "Les IDs Q01..Q50 doivent être uniques"

    def test_questions_non_vides(self):
        c = load_corpus()
        for q in c.questions:
            assert len(q.question) >= 3, f"{q.id}: question trop courte"

    def test_hors_corpus_vague_et_hors_sujet(self):
        c = load_corpus()
        # Toutes les questions vague/hors_sujet doivent avoir expected_hors_corpus=True
        for q in c.questions:
            if q.expected_type in ("vague", "hors_sujet"):
                assert q.expected_hors_corpus is True, \
                    f"{q.id} ({q.expected_type}) doit avoir expected_hors_corpus=True"

    def test_precise_doit_repondre(self):
        c = load_corpus()
        # Les questions précises doivent attendre une réponse (pas un refus)
        for q in c.questions:
            if q.expected_type == "precise":
                assert q.expected_hors_corpus is False, \
                    f"{q.id} (precise) doit avoir expected_hors_corpus=False"

    def test_by_module_filter(self):
        c = load_corpus()
        juridique = c.by_module("juridique")
        assert len(juridique) == 20
        assert all(q.module == "juridique" for q in juridique)


# ────────────────────────── Helpers ──────────────────────────

class TestHelpers:
    def test_looks_like_refusal_detecte_refus_v2(self):
        v2_fallback = "Je n'ai pas d'information fiable dans la base ELISFA."
        assert looks_like_refusal(v2_fallback) is True

    def test_looks_like_refusal_detecte_refus_v1_humour(self):
        # V1 est plus convivial mais le résultat est le même : refus
        v1_quiche = "Ha ha ! Je suis l'assistant juridique, pas un chef cuisinier."
        assert looks_like_refusal(v1_quiche) is True

    def test_looks_like_refusal_false_sur_vraie_reponse(self):
        good = "Sous la CCN ALISFA, le préavis est de 1 mois après la période d'essai."
        assert looks_like_refusal(good) is False

    def test_looks_like_refusal_chaine_vide(self):
        assert looks_like_refusal("") is True

    def test_find_keywords_insensible_a_la_casse(self):
        assert find_keywords("Le PRÉAVIS est de 2 MOIS", ["préavis", "2 mois"]) == ["préavis", "2 mois"]

    def test_find_keywords_keyword_absent(self):
        assert find_keywords("Le préavis est court", ["6 mois"]) == []

    def test_find_forbidden_match_phrase(self):
        # Détecte les phrases interdites = signal d'hallucination
        assert find_forbidden("La réponse contient prime d'ancienneté", ["prime d'ancienneté"]) == ["prime d'ancienneté"]


# ────────────────────────── Évaluation par cas ──────────────────────────

def _q(*, expected_hors_corpus=False, correct_keywords=None, forbidden_phrases=None,
       module="juridique", expected_type="precise", qid="Q01") -> BenchmarkQuestion:
    """Helper pour construire des BenchmarkQuestion compactes en test."""
    return BenchmarkQuestion(
        id=qid, module=module, expected_type=expected_type,
        question="placeholder question pour test",
        expected_hors_corpus=expected_hors_corpus,
        correct_keywords=correct_keywords or [],
        forbidden_phrases=forbidden_phrases or [],
    )


class TestEvaluateAnswer:
    def test_correct_quand_tous_keywords_presents(self):
        q = _q(correct_keywords=["1 mois", "2 mois", "ancienneté"])
        answer = "Préavis : 1 mois après l'essai, 2 mois si 2 ans d'ancienneté."
        r = evaluate_answer(q, answer)
        assert r.category == "correct"
        assert len(r.keywords_matched) == 3

    def test_partial_quand_quelques_keywords(self):
        q = _q(correct_keywords=["1 mois", "2 mois", "ancienneté"])
        answer = "Le préavis est de 1 mois."  # manque 2 mois + ancienneté
        r = evaluate_answer(q, answer)
        assert r.category == "partial"
        assert "1 mois" in r.keywords_matched
        assert "2 mois" in r.keywords_missing

    def test_incorrect_quand_aucun_keyword(self):
        q = _q(correct_keywords=["1 mois"])
        answer = "Réponse vague sans contenu utile."
        r = evaluate_answer(q, answer)
        assert r.category == "incorrect"

    def test_hallucinated_quand_phrase_interdite(self):
        q = _q(correct_keywords=["1 mois"], forbidden_phrases=["prime d'ancienneté"])
        answer = "Préavis 1 mois et prime d'ancienneté de 2%."  # piège
        r = evaluate_answer(q, answer)
        assert r.category == "hallucinated"
        assert "prime d'ancienneté" in r.forbidden_found

    def test_hors_corpus_ok_quand_refus_attendu(self):
        q = _q(expected_hors_corpus=True, expected_type="vague", qid="Q13")
        answer = "Je n'ai pas d'information fiable, pouvez-vous préciser votre question ?"
        r = evaluate_answer(q, answer)
        assert r.category == "hors_corpus_ok"

    def test_false_response_quand_repond_au_lieu_de_refuser(self):
        q = _q(expected_hors_corpus=True, expected_type="vague", qid="Q13")
        answer = "Voici la procédure complète à suivre étape par étape..."
        r = evaluate_answer(q, answer)
        assert r.category == "false_response"

    def test_hallucinated_meme_sur_question_vague(self):
        # Pire cas : V1 invente un fait sur une question vague
        q = _q(
            expected_hors_corpus=True, expected_type="hors_sujet", qid="Q18",
            forbidden_phrases=["pâte brisée", "lardons"],
        )
        answer = "La quiche lorraine se prépare avec une pâte brisée et des lardons."
        r = evaluate_answer(q, answer)
        assert r.category == "hallucinated"

    def test_false_refuse_quand_devait_repondre(self):
        q = _q(correct_keywords=["IDCC", "1261"])
        answer = "Je n'ai pas d'information sur cette question."
        r = evaluate_answer(q, answer)
        assert r.category == "false_refuse"

    def test_correct_par_defaut_si_pas_de_keywords(self):
        # Pour les modules avec KB pauvre, on peut accepter sans contrainte stricte
        q = _q(correct_keywords=[])  # pas de keywords définis
        answer = "Voici quelques pistes : recruter, former, organiser des AG."
        r = evaluate_answer(q, answer)
        assert r.category == "correct"


# ────────────────────────── Synthèse ──────────────────────────

class TestSummarize:
    def test_synthese_calcule_categories_et_modules(self):
        results = [
            EvalResult(question_id="Q01", module="juridique", category="correct"),
            EvalResult(question_id="Q02", module="juridique", category="partial"),
            EvalResult(question_id="Q21", module="formation", category="correct"),
            EvalResult(question_id="Q40", module="rh", category="hors_corpus_ok"),
        ]
        s = summarize(results)
        assert s["total"] == 4
        assert s["by_category"]["correct"] == 2
        assert s["by_module"]["juridique"]["correct"] == 1
        # success_rate = (correct + hors_corpus_ok) / total = 3/4 = 75%
        assert s["success_rate"] == 75.0

    def test_synthese_corpus_vide(self):
        s = summarize([])
        assert s["total"] == 0
        assert s["success_rate"] == 0.0
