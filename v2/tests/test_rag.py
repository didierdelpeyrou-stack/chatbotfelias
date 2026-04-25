"""Tests du module RAG V2 — tokenizer, index inversé, retrieval avec seuil.

Ces tests vérifient les 3 fixes de l'audit RAG 2026-04-21 :
  - R1 : seuil hors_corpus → flag levé quand best_score < threshold
  - R2 : score_normalized ∈ [0, 1]
  - R4 : tokens courts / stopwords ignorés au tokenize()

KB synthétique pour tests rapides (pas besoin de charger les vraies bases).
"""
from __future__ import annotations

import pytest

from app.rag.index import FR_STOPWORDS, MIN_TOKEN_LEN, build_index, tokenize
from app.rag.retrieval import EXACT_MATCH_WEIGHT, search

# ────────────────────────── KB synthétique ──────────────────────────

def _kb_test() -> dict:
    """Mini-KB de 3 articles pour les tests."""
    return {
        "themes": [
            {
                "id": "rupture",
                "label": "Rupture du contrat de travail",
                "niveau": "rouge",
                "articles": [
                    {
                        "id": "ART_PREAVIS",
                        "question_type": "Quelle durée de préavis en cas de licenciement ?",
                        "mots_cles": ["preavis", "licenciement", "duree", "rupture", "contrat"],
                        "reponse": {"synthese": "1 mois après période d'essai..."},
                    },
                    {
                        "id": "ART_INDEMNITE",
                        "question_type": "Comment calculer l'indemnité de licenciement ?",
                        "mots_cles": ["indemnite", "licenciement", "calcul", "rupture"],
                        "reponse": {"synthese": "1/4 de mois par année..."},
                    },
                ],
            },
            {
                "id": "salaires",
                "label": "Rémunération",
                "niveau": "vert",
                "articles": [
                    {
                        "id": "ART_SMIC",
                        "question_type": "Comment calculer le salaire minimum ?",
                        "mots_cles": ["salaire", "smic", "remuneration", "calcul", "minimum"],
                        "reponse": {"synthese": "Voir grille IDCC 1261..."},
                    },
                ],
            },
        ]
    }


# ────────────────────────── Tokenizer ──────────────────────────

class TestTokenize:
    def test_lowercase(self):
        assert tokenize("LICENCIEMENT") == ["licenciement"]

    def test_split_on_punctuation(self):
        # Les points, virgules, etc. ne doivent pas faire partie du token.
        # Les accents sont conservés (le tokenizer accepte À-ÿ).
        result = tokenize("préavis, licenciement.")
        assert "préavis" in result
        assert "licenciement" in result

    def test_filtre_stopwords(self):
        # « les » et « des » sont des stopwords FR
        result = tokenize("les preavis des salariés")
        assert "les" not in result
        assert "des" not in result
        assert "preavis" in result

    def test_filtre_tokens_courts_R4(self):
        # « le » et « du » ont 2 chars → filtrés (MIN_TOKEN_LEN=3)
        result = tokenize("le préavis du contrat")
        assert "le" not in result
        assert "du" not in result
        assert "preavis" in result or "préavis" in result

    def test_chiffres_conservés(self):
        # Les chiffres ≥ 3 chars sont des tokens valides (ex. "2024", "L1234")
        result = tokenize("article 2024 L1234")
        assert "2024" in result
        assert "l1234" in result

    def test_chaine_vide(self):
        assert tokenize("") == []

    def test_uniquement_stopwords(self):
        # Que des stopwords / tokens courts → résultat vide
        assert tokenize("le la de du les des") == []

    def test_min_token_len_constante(self):
        # Doit rester accessible pour la doc & autres modules
        assert MIN_TOKEN_LEN >= 2

    def test_stopwords_constante(self):
        assert "les" in FR_STOPWORDS
        assert "des" in FR_STOPWORDS


# ────────────────────────── Index inversé ──────────────────────────

class TestBuildIndex:
    def test_index_compte_articles(self):
        idx = build_index(_kb_test())
        assert idx["n_articles"] == 3

    def test_index_contient_tokens_principaux(self):
        idx = build_index(_kb_test())
        assert "licenciement" in idx["inverted"]
        assert "salaire" in idx["inverted"]

    def test_postings_reference_bons_articles(self):
        idx = build_index(_kb_test())
        # « licenciement » apparaît dans 2 articles du theme 0
        postings = idx["inverted"]["licenciement"]
        theme_ids = {t_idx for (t_idx, _, _) in postings}
        assert theme_ids == {0}
        article_ids = {a_idx for (_, a_idx, _) in postings}
        assert article_ids == {0, 1}

    def test_idf_calcul_classique(self):
        idx = build_index(_kb_test())
        # « salaire » apparaît dans 1 article sur 3 → IDF élevé
        # « licenciement » apparaît dans 2 articles sur 3 → IDF plus faible
        assert idx["idf"]["salaire"] > idx["idf"]["licenciement"]

    def test_kb_vide(self):
        idx = build_index({"themes": []})
        assert idx["n_articles"] == 0
        assert idx["inverted"] == {}


# ────────────────────────── Retrieval — Concept ML ──────────────────────────

@pytest.fixture
def kb_with_index():
    kb = _kb_test()
    return kb, build_index(kb)


class TestSearchHappyPath:
    """Cas nominaux : question pertinente → résultats triés."""

    def test_question_precise_renvoie_top1_correct(self, kb_with_index):
        kb, idx = kb_with_index
        report = search(
            "Quelle durée de préavis pour un licenciement",
            kb, idx, threshold=0.5,
        )
        assert len(report.results) > 0
        assert report.results[0].article["id"] == "ART_PREAVIS"

    def test_top_k_respecte(self, kb_with_index):
        kb, idx = kb_with_index
        report = search("licenciement rupture", kb, idx, top_k=2, threshold=0.0)
        assert len(report.results) <= 2

    def test_question_salaire_renvoie_smic(self, kb_with_index):
        kb, idx = kb_with_index
        report = search("Comment calculer le salaire minimum SMIC", kb, idx, threshold=0.5)
        assert report.results[0].article["id"] == "ART_SMIC"


class TestSeuilHorsCorpusR1:
    """R1 : seuil de décision — concept ML clé du Sprint 2.2."""

    def test_question_hors_corpus_flag_leve(self, kb_with_index):
        kb, idx = kb_with_index
        report = search("recette quiche lorraine", kb, idx, threshold=1.5)
        assert report.hors_corpus is True
        assert report.best_score == 0.0  # aucun token ne matche

    def test_question_pertinente_flag_non_leve(self, kb_with_index):
        kb, idx = kb_with_index
        report = search("préavis licenciement durée", kb, idx, threshold=0.5)
        assert report.hors_corpus is False
        assert report.best_score >= 0.5

    def test_threshold_eleve_meme_top1_devient_hors_corpus(self, kb_with_index):
        # Avec un threshold ridiculement élevé, même la meilleure réponse passe en hors_corpus
        kb, idx = kb_with_index
        report = search("licenciement", kb, idx, threshold=10000.0)
        assert report.hors_corpus is True
        # Mais on a quand même les résultats remontés (le caller décide)
        assert len(report.results) > 0

    def test_threshold_zero_jamais_hors_corpus_si_match(self, kb_with_index):
        kb, idx = kb_with_index
        report = search("licenciement", kb, idx, threshold=0.0)
        assert report.hors_corpus is False  # car best_score > 0.0


class TestScoreNormaliseR2:
    """R2 : score_normalized ∈ [0, 1] — comparable inter-modules."""

    def test_score_normalized_dans_intervalle(self, kb_with_index):
        kb, idx = kb_with_index
        report = search("préavis licenciement", kb, idx, threshold=0.0)
        for r in report.results:
            assert 0.0 <= r.score_normalized <= 1.0

    def test_max_score_possible_calcule(self, kb_with_index):
        kb, idx = kb_with_index
        report = search("préavis licenciement", kb, idx, threshold=0.0)
        # Il y a 2 tokens utiles → max_score = 2 × 3.0 × idf
        assert report.max_score_possible > 0

    def test_score_normalized_proportionnel_au_match(self, kb_with_index):
        # Une question qui matche tous ses tokens dans 1 article → score normalisé élevé
        # Une question qui ne matche qu'un seul token → score plus bas
        kb, idx = kb_with_index
        full_match = search("préavis licenciement durée rupture", kb, idx, threshold=0.0)
        partial = search("licenciement vacances", kb, idx, threshold=0.0)
        if full_match.results and partial.results:
            assert full_match.best_score_normalized >= partial.best_score_normalized


class TestFiltreSubstringR4:
    """R4 : tokens courts / stopwords filtrés — pas de bruit."""

    def test_question_avec_stopwords_uniquement_hors_corpus(self, kb_with_index):
        kb, idx = kb_with_index
        # Que des stopwords/tokens courts → tokenize renvoie []
        report = search("le la de du les des", kb, idx)
        assert report.hors_corpus is True
        assert report.n_tokens_query == 0

    def test_n_tokens_query_apres_filtre(self, kb_with_index):
        kb, idx = kb_with_index
        # « le » filtré, « licenciement » conservé
        report = search("le licenciement", kb, idx, threshold=0.0)
        assert report.n_tokens_query == 1


class TestRapportComplet:
    """Le RetrievalReport doit être informatif pour la télémétrie."""

    def test_report_contient_threshold(self, kb_with_index):
        kb, idx = kb_with_index
        report = search("test", kb, idx, threshold=2.5)
        assert report.threshold == 2.5

    def test_report_max_score_possible_renseigne(self, kb_with_index):
        kb, idx = kb_with_index
        report = search("préavis licenciement", kb, idx)
        assert report.max_score_possible >= 0


class TestExactMatchWeight:
    """La constante d'exact match doit être documentée et accessible."""

    def test_exact_match_weight_constante(self):
        assert EXACT_MATCH_WEIGHT > 1.0  # bonus vs match faible
