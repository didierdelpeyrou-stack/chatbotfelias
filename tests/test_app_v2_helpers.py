"""Tests des helpers V2 ajoutés à app.py au Sprint 0.1.

Couvre les fonctions « pure » qui calculent confidence, suggestions
liées et bornes des limites — base de l'UX V2 et du futur reranker ML.

Aucun appel réseau, aucune dépendance KB : on construit des résultats RAG
synthétiques pour tester les bornes et les cas dégénérés.
"""
from __future__ import annotations

import unittest

import app as app_module


def _fake_result(score: float, theme_label: str = "Theme test", question_type: str = "Question test ?",
                 niveau: str = "vert", liens=None, fiches=None):
    """Construit un résultat RAG synthétique au format produit par search_knowledge_base."""
    article = {
        "id": "ART_FAKE",
        "question_type": question_type,
        "mots_cles": ["test"],
        "reponse": {
            "synthese": "fake",
            "liens": liens or [],
            "sources": ["fake"],
        },
        "fiches_pratiques": fiches or [],
    }
    return {
        "score": score,
        "theme_id": "fake",
        "theme_label": theme_label,
        "niveau": niveau,
        "article": article,
    }


class TestComputeConfidence(unittest.TestCase):
    """Bornes : SCORE_HIGH=5.0, SCORE_MEDIUM=1.5."""

    def test_pas_de_resultats_label_none(self):
        c = app_module.compute_confidence([])
        self.assertEqual(c["label"], "none")
        self.assertEqual(c["score"], 0.0)
        self.assertIn("Aucune source", c["message"])

    def test_score_eleve_label_high(self):
        c = app_module.compute_confidence([_fake_result(score=87.4)])
        self.assertEqual(c["label"], "high")
        self.assertGreaterEqual(c["score"], app_module.SCORE_HIGH)

    def test_score_borderline_high(self):
        # Exactement SCORE_HIGH → high
        c = app_module.compute_confidence([_fake_result(score=app_module.SCORE_HIGH)])
        self.assertEqual(c["label"], "high")

    def test_score_intermediaire_label_medium(self):
        # Entre SCORE_MEDIUM et SCORE_HIGH (exclu)
        c = app_module.compute_confidence([_fake_result(score=3.0)])
        self.assertEqual(c["label"], "medium")

    def test_score_faible_label_low(self):
        c = app_module.compute_confidence([_fake_result(score=0.5)])
        self.assertEqual(c["label"], "low")

    def test_seuils_constantes_publiques(self):
        # Les constantes doivent rester accessibles (utilisées par benchmarks/tests futurs)
        self.assertGreater(app_module.SCORE_HIGH, app_module.SCORE_MEDIUM)
        self.assertGreater(app_module.SCORE_MEDIUM, 0)


class TestCollectRelatedSuggestions(unittest.TestCase):
    """3 suggestions max issues du top-2..top-N."""

    def test_pas_de_resultats(self):
        self.assertEqual(app_module.collect_related_suggestions([]), [])

    def test_un_seul_resultat_pas_de_suggestion(self):
        # Avec un seul résultat (le top-1), il n'y a rien à proposer comme « voir aussi »
        results = [_fake_result(score=10.0)]
        self.assertEqual(app_module.collect_related_suggestions(results), [])

    def test_skip_top_un(self):
        # Le top-1 est consommé par la réponse, on ne le propose pas
        results = [
            _fake_result(score=10.0, question_type="TOP1"),
            _fake_result(score=5.0, question_type="TOP2"),
            _fake_result(score=3.0, question_type="TOP3"),
        ]
        suggestions = app_module.collect_related_suggestions(results)
        titles = [s["title"] for s in suggestions]
        self.assertNotIn("TOP1", titles)
        self.assertIn("TOP2", titles)
        self.assertIn("TOP3", titles)

    def test_max_count_par_defaut_3(self):
        results = [_fake_result(score=10.0 - i, question_type=f"Q{i}") for i in range(10)]
        suggestions = app_module.collect_related_suggestions(results)
        self.assertEqual(len(suggestions), 3)

    def test_max_count_personnalise(self):
        results = [_fake_result(score=10.0 - i, question_type=f"Q{i}") for i in range(10)]
        suggestions = app_module.collect_related_suggestions(results, max_count=5)
        self.assertEqual(len(suggestions), 5)

    def test_dedoublonnage_par_titre(self):
        # Si plusieurs articles ont le même question_type, on n'en garde qu'un
        results = [
            _fake_result(score=10.0, question_type="TOP1"),
            _fake_result(score=8.0, question_type="DUPLICATE"),
            _fake_result(score=7.0, question_type="DUPLICATE"),  # ignoré
            _fake_result(score=6.0, question_type="UNIQUE"),
        ]
        suggestions = app_module.collect_related_suggestions(results)
        titles = [s["title"] for s in suggestions]
        self.assertEqual(titles.count("DUPLICATE"), 1)
        self.assertIn("UNIQUE", titles)

    def test_articles_sans_titre_ignores(self):
        # Article sans question_type ni title : skip silencieux
        bad_article = {
            "score": 5.0,
            "theme_id": "t",
            "theme_label": "Theme",
            "niveau": "vert",
            "article": {"id": "X", "mots_cles": [], "reponse": {}, "fiches_pratiques": []},
        }
        results = [_fake_result(score=10.0), bad_article]
        suggestions = app_module.collect_related_suggestions(results)
        # Pas de plantage, juste 0 suggestion (bad_article ignoré, top-1 skip)
        self.assertEqual(len(suggestions), 0)

    def test_theme_label_inclus(self):
        results = [
            _fake_result(score=10.0),
            _fake_result(score=5.0, theme_label="Theme spécifique", question_type="Q2"),
        ]
        suggestions = app_module.collect_related_suggestions(results)
        self.assertEqual(suggestions[0]["theme"], "Theme spécifique")


class TestCollectLinksAndFiches(unittest.TestCase):
    """Plafonds MAX_LIENS_PAR_REPONSE=6, MAX_FICHES_PAR_REPONSE=5."""

    def test_pas_de_resultats(self):
        liens, fiches = app_module.collect_links_and_fiches([])
        self.assertEqual(liens, [])
        self.assertEqual(fiches, [])

    def test_plafonnement_liens(self):
        # 10 liens uniques → on doit en récupérer max 6
        liens_input = [{"titre": f"Lien {i}", "url": f"https://example.com/{i}"} for i in range(10)]
        results = [_fake_result(score=10.0, liens=liens_input)]
        liens, _ = app_module.collect_links_and_fiches(results)
        self.assertEqual(len(liens), app_module.MAX_LIENS_PAR_REPONSE)

    def test_plafonnement_fiches(self):
        fiches_input = [{"fichier": f"f{i}.pdf", "titre": f"Fiche {i}"} for i in range(15)]
        results = [_fake_result(score=10.0, fiches=fiches_input)]
        _, fiches = app_module.collect_links_and_fiches(results)
        self.assertEqual(len(fiches), app_module.MAX_FICHES_PAR_REPONSE)

    def test_dedoublonnage_par_url(self):
        # Deux articles avec le même lien : pas de doublon dans le résultat
        lien = {"titre": "Lien A", "url": "https://same.com"}
        results = [
            _fake_result(score=10.0, liens=[lien]),
            _fake_result(score=5.0, liens=[lien, {"titre": "B", "url": "https://other.com"}]),
        ]
        liens, _ = app_module.collect_links_and_fiches(results)
        urls = [link["url"] for link in liens]
        self.assertEqual(len(urls), len(set(urls)))
        self.assertEqual(len(urls), 2)

    def test_dedoublonnage_par_fichier(self):
        fiche = {"fichier": "doublon.pdf", "titre": "X"}
        results = [
            _fake_result(score=10.0, fiches=[fiche]),
            _fake_result(score=5.0, fiches=[fiche]),
        ]
        _, fiches = app_module.collect_links_and_fiches(results)
        self.assertEqual(len(fiches), 1)

    def test_priorisation_top_articles(self):
        # Les liens du top-1 doivent être inclus en priorité
        lien_top1 = {"titre": "Top1", "url": "https://top1.com"}
        lien_top2 = {"titre": "Top2", "url": "https://top2.com"}
        results = [
            _fake_result(score=10.0, liens=[lien_top1]),
            _fake_result(score=5.0, liens=[lien_top2]),
        ]
        liens, _ = app_module.collect_links_and_fiches(results)
        self.assertEqual(liens[0]["url"], "https://top1.com")


if __name__ == "__main__":
    unittest.main()
