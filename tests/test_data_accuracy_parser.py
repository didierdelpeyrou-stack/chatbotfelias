"""Tests unitaires — parseur de critères du script run_data_accuracy.

Lance :
    python3 -m pytest tests/test_data_accuracy_parser.py -v
    ou
    python3 tests/test_data_accuracy_parser.py
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from run_data_accuracy import (  # noqa: E402
    _contains,
    evaluate_criteria,
    parse_criteria,
)


class TestContainsTolerant(unittest.TestCase):
    def test_espaces_insecables(self):
        # La réponse utilise un espace insécable U+00A0, le critère un espace normal
        self.assertTrue(_contains("Le montant est 22\u00a0100 €", "22 100"))

    def test_pas_de_separateur(self):
        # Réponse sans espace, critère avec espace
        self.assertTrue(_contains("Le montant est 22100 €", "22 100"))

    def test_casse_accents(self):
        self.assertTrue(_contains("L'anciennete compte", "ancienneté"))
        self.assertTrue(_contains("RÉPONSE", "reponse"))

    def test_non_contenu(self):
        self.assertFalse(_contains("Le montant est 21 800 €", "22 100"))


class TestParseCriteriaSSC(unittest.TestCase):
    def test_ssc_simple(self):
        r = parse_criteria("La réponse doit contenir '22 100' et '2024'")
        self.assertIn("22 100", r["must_contain_all"])
        self.assertIn("2024", r["must_contain_all"])
        self.assertTrue(r["parseable"])

    def test_ssc_avec_parentheses_explicatives(self):
        # Les parenthèses explicatives ne doivent pas polluer le parsing
        r = parse_criteria(
            "La réponse doit contenir '22 100' (espaces/points acceptés) et '2024'"
        )
        self.assertIn("22 100", r["must_contain_all"])
        self.assertIn("2024", r["must_contain_all"])
        # Les mots dans les parenthèses ne doivent pas apparaître
        self.assertNotIn("espaces", r["must_contain_all"])
        self.assertNotIn("points acceptés", r["must_contain_all"])


class TestParseCriteriaMiniMaxi(unittest.TestCase):
    def test_mini_maxi_basique(self):
        r = parse_criteria("Mini 43, maxi 175")
        self.assertIn("43", r["must_contain_all"])
        self.assertIn("175", r["must_contain_all"])

    def test_mini_maxi_avec_unite(self):
        r = parse_criteria("Réponse : mini 1 pt, maxi 58 pts")
        self.assertIn("1", r["must_contain_all"])
        self.assertIn("58", r["must_contain_all"])

    def test_mini_maxi_petites_valeurs(self):
        # Vérifie que les nombres à 1 chiffre ne sont pas filtrés
        r = parse_criteria("Mini 5, maxi 154")
        self.assertIn("5", r["must_contain_all"])
        self.assertIn("154", r["must_contain_all"])


class TestParseCriteriaPointsList(unittest.TestCase):
    def test_liste_classique(self):
        r = parse_criteria("Points exacts : 0, 5, 15, 35, 55, 90, 120")
        for val in ["0", "5", "15", "35", "55", "90", "120"]:
            self.assertIn(val, r["must_contain_all"])

    def test_liste_avec_ssc_prefix(self):
        # "0/SSC" en première position ne doit pas casser le parsing
        r = parse_criteria("Points exacts : 0/SSC, 5, 15, 30, 45, 65, 80, 110")
        for val in ["5", "15", "30", "45", "65", "80", "110"]:
            self.assertIn(val, r["must_contain_all"])


class TestParseCriteriaArticles(unittest.TestCase):
    def test_article_l2251(self):
        r = parse_criteria("Réponse cite exactement L2251-1")
        self.assertIn("L2251-1", r["must_contain_all"])

    def test_article_multiple(self):
        r = parse_criteria("Réponse cite L1234-1 avec seuils 6 mois / 2 ans")
        self.assertIn("L1234-1", r["must_contain_all"])
        self.assertIn("6 mois", r["must_contain_all"])
        self.assertIn("2 ans", r["must_contain_all"])


class TestParseCriteriaNegatif(unittest.TestCase):
    def test_ne_pas_inventer_apres_exemple_positif(self):
        # La quote positive avant NE PAS doit rester positive
        r = parse_criteria(
            "Si l'article n'existe pas : le bot doit dire "
            "'je n'ai pas cette disposition' et NE PAS inventer"
        )
        # La positive ("je n") ne doit PAS être dans les négatifs
        self.assertNotIn("je n", r["must_not_contain"])


class TestEvaluateCriteria(unittest.TestCase):
    def test_ok_quand_tout_present(self):
        crit = parse_criteria("Réponse contient '22 100' et '2024'")
        verdict, _ = evaluate_criteria("Pour 2024 : 22 100 € bruts annuels.", crit)
        self.assertEqual(verdict, "OK")

    def test_ko_quand_valeur_manquante(self):
        crit = parse_criteria("Réponse contient '22 100' et '2024'")
        verdict, details = evaluate_criteria("Pour 2023 : 21 800 €.", crit)
        self.assertEqual(verdict, "KO")
        self.assertTrue(any("MANQUANT" in d for d in details))

    def test_manuel_si_critere_non_parsable(self):
        crit = parse_criteria("Réponse distingue bien les deux rôles avec exemples")
        verdict, _ = evaluate_criteria("peu importe", crit)
        self.assertEqual(verdict, "MANUEL")


class TestLoadCasesFromRealXlsx(unittest.TestCase):
    """Vérifie que le xlsx de production reste parsable au moins à 60 %."""

    def test_parsabilite_minimum(self):
        xlsx_path = Path(__file__).parent / "plan_evaluation_elisfa.xlsx"
        if not xlsx_path.exists():
            self.skipTest(f"xlsx absent : {xlsx_path}")
        from run_data_accuracy import load_cases

        cases, _wb, _ws = load_cases(xlsx_path, "2. Exactitude données")
        self.assertGreater(len(cases), 30, "Le xlsx doit contenir >30 cas")
        parseable = sum(1 for c in cases if parse_criteria(c["critere"])["parseable"])
        # Au moins 60 % des cas doivent être auto-parseables
        ratio = parseable / len(cases)
        self.assertGreaterEqual(
            ratio,
            0.60,
            f"Seulement {ratio:.0%} des critères sont auto-parseables (min : 60 %)",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
