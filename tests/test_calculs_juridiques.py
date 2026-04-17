"""Tests unitaires — utils/calculs_juridiques.py

Lance :
    python3 -m pytest tests/test_calculs_juridiques.py -v
    ou
    python3 tests/test_calculs_juridiques.py
"""

import sys
import unittest
from datetime import date
from pathlib import Path

# Permet d'exécuter le fichier directement (python tests/test_calculs_juridiques.py)
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.calculs_juridiques import (  # noqa: E402
    calcul_anciennete,
    dispatch_calcul,
    indemnite_licenciement,
    preavis_licenciement,
    salaire_minimum_alisfa,
)


class TestAnciennete(unittest.TestCase):
    def test_un_an_pile(self):
        r = calcul_anciennete("2024-01-15", "2025-01-15")
        self.assertEqual(r["annees"], 1)
        self.assertEqual(r["mois"], 0)
        self.assertEqual(r["jours"], 0)

    def test_fraction_annee(self):
        r = calcul_anciennete("2020-06-01", "2025-09-15")
        self.assertEqual(r["annees"], 5)
        self.assertEqual(r["mois"], 3)
        self.assertEqual(r["jours"], 14)

    def test_annee_bissextile(self):
        # 29 février 2020 → 28 février 2021 = 365 jours
        r = calcul_anciennete("2020-02-29", "2021-02-28")
        self.assertEqual(r["annees"], 0)
        self.assertEqual(r["mois"], 11)
        # 29 jours (mois de février) - 1 jour = 28 jours ; dépend du mode choisi
        self.assertEqual(r["total_jours"], 365)

    def test_format_francais(self):
        r = calcul_anciennete("01/06/2020", "15/09/2025")
        self.assertEqual(r["annees"], 5)
        self.assertEqual(r["mois"], 3)

    def test_date_fin_defaut_aujourdhui(self):
        r = calcul_anciennete("2020-01-01")
        # On vérifie juste que ça ne crashe pas et que l'ancienneté est > 0
        self.assertGreater(r["annees"], 0)
        self.assertEqual(r["date_fin"], date.today().isoformat())

    def test_date_fin_avant_debut_erreur(self):
        with self.assertRaises(ValueError):
            calcul_anciennete("2025-01-01", "2020-01-01")

    def test_format_invalide(self):
        with self.assertRaises(ValueError):
            calcul_anciennete("pas une date")

    def test_total_jours(self):
        r = calcul_anciennete("2024-01-01", "2024-01-31")
        self.assertEqual(r["total_jours"], 30)

    def test_total_mois(self):
        r = calcul_anciennete("2024-01-01", "2026-03-01")
        # 2 ans 2 mois = 26 mois
        self.assertEqual(r["total_mois"], 26)

    def test_bascule_mois_jours_negatifs(self):
        # 15 mars 2024 → 10 avril 2024 : les jours passent de 10-15 = -5
        # → mois -= 1, jours += 31 (mars) = 26 jours
        r = calcul_anciennete("2024-03-15", "2024-04-10")
        self.assertEqual(r["annees"], 0)
        self.assertEqual(r["mois"], 0)
        self.assertEqual(r["jours"], 26)


class TestPreavis(unittest.TestCase):
    def test_cadre_plus_de_2_ans(self):
        r = preavis_licenciement(anciennete_mois=36, statut="cadre")
        # Code : 2 mois, CCN : 3 mois → retenu : 3 (CCN + favorable)
        self.assertEqual(r["resultat"], 3)
        self.assertIn("CCN", r["fondement_retenu"])

    def test_employe_moins_de_2_ans(self):
        r = preavis_licenciement(anciennete_mois=12, statut="employe")
        # Code : 1 mois, CCN : 1 mois → retenu : 1 (identiques)
        self.assertEqual(r["resultat"], 1)

    def test_employe_plus_de_2_ans(self):
        r = preavis_licenciement(anciennete_mois=30, statut="employe")
        # Code : 2 mois, CCN : 2 mois → retenu : 2
        self.assertEqual(r["resultat"], 2)

    def test_cadre_moins_de_2_ans(self):
        r = preavis_licenciement(anciennete_mois=12, statut="cadre")
        # Code : 1 mois, CCN cadre : 2 mois → retenu : 2 (CCN + favorable)
        self.assertEqual(r["resultat"], 2)
        self.assertIn("CCN", r["fondement_retenu"])

    def test_moins_6_mois_usage_local(self):
        r = preavis_licenciement(anciennete_mois=3, statut="employe")
        # Code : None (usage local), CCN : 1 mois → retenu : 1
        self.assertEqual(r["resultat"], 1)
        self.assertIsNone(r["preavis_legal_mois"])

    def test_anciennete_negative_erreur(self):
        with self.assertRaises(ValueError):
            preavis_licenciement(anciennete_mois=-1)

    def test_statut_inconnu(self):
        with self.assertRaises(ValueError):
            preavis_licenciement(anciennete_mois=12, statut="patron")

    def test_unite_mois(self):
        r = preavis_licenciement(anciennete_mois=24)
        self.assertEqual(r["unite"], "mois")


class TestIndemniteLicenciement(unittest.TestCase):
    def test_non_eligible_moins_8_mois(self):
        r = indemnite_licenciement(salaire_mensuel_brut=2000, anciennete_annees=0.5)
        self.assertFalse(r["eligible"])
        self.assertEqual(r["montant"], 0.0)

    def test_cinq_ans(self):
        # 5 ans × 2000 € × 1/4 = 2500 €
        r = indemnite_licenciement(salaire_mensuel_brut=2000, anciennete_annees=5)
        self.assertTrue(r["eligible"])
        self.assertEqual(r["montant"], 2500.0)

    def test_dix_ans_pile(self):
        # 10 ans × 2000 € × 1/4 = 5000 €
        r = indemnite_licenciement(salaire_mensuel_brut=2000, anciennete_annees=10)
        self.assertEqual(r["montant"], 5000.0)

    def test_quinze_ans(self):
        # 10 × 2000 × 1/4 + 5 × 2000 × 1/3 = 5000 + 3333.33 = 8333.33
        r = indemnite_licenciement(salaire_mensuel_brut=2000, anciennete_annees=15)
        self.assertAlmostEqual(r["montant"], 8333.33, places=2)

    def test_fraction_annee(self):
        # 2.5 ans × 3000 × 1/4 = 1875
        r = indemnite_licenciement(salaire_mensuel_brut=3000, anciennete_annees=2.5)
        self.assertEqual(r["montant"], 1875.0)

    def test_seuil_exact_8_mois(self):
        # Pile 8 mois = 8/12 ans ≈ 0.6667 → éligible
        r = indemnite_licenciement(salaire_mensuel_brut=2000, anciennete_annees=8 / 12)
        self.assertTrue(r["eligible"])

    def test_salaire_negatif_erreur(self):
        with self.assertRaises(ValueError):
            indemnite_licenciement(salaire_mensuel_brut=-100, anciennete_annees=5)

    def test_anciennete_negative_erreur(self):
        with self.assertRaises(ValueError):
            indemnite_licenciement(salaire_mensuel_brut=2000, anciennete_annees=-1)


class TestSalaireMinimumAlisfa(unittest.TestCase):
    def test_calcul_basique(self):
        r = salaire_minimum_alisfa(coefficient=300, valeur_point=6.77)
        self.assertEqual(r["salaire_mensuel_brut"], round(300 * 6.77, 2))
        self.assertEqual(r["coefficient"], 300)

    def test_valeur_point_par_defaut(self):
        r = salaire_minimum_alisfa(coefficient=300)
        self.assertIsNotNone(r["valeur_point"])
        self.assertGreater(r["salaire_mensuel_brut"], 0)

    def test_coefficient_negatif(self):
        with self.assertRaises(ValueError):
            salaire_minimum_alisfa(coefficient=-10)


class TestDispatcher(unittest.TestCase):
    def test_appel_valide(self):
        r = dispatch_calcul("calcul_anciennete", date_debut="2020-01-01", date_fin="2025-01-01")
        self.assertEqual(r["annees"], 5)

    def test_calculateur_inconnu(self):
        r = dispatch_calcul("pas_un_calcul_reel")
        self.assertIn("erreur", r)
        self.assertIn("disponibles", r)

    def test_parametre_manquant(self):
        # calcul_anciennete requiert date_debut
        r = dispatch_calcul("calcul_anciennete")
        self.assertIn("erreur", r)

    def test_mauvais_type_parametre(self):
        r = dispatch_calcul("calcul_anciennete", date_debut="pas une date")
        self.assertIn("erreur", r)


if __name__ == "__main__":
    unittest.main(verbosity=2)
