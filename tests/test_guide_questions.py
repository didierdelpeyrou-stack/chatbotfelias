"""Tests unitaires — utils/guide_questions.py

Lance :
    python3 -m pytest tests/test_guide_questions.py -v
    ou
    python3 tests/test_guide_questions.py
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.guide_questions import (  # noqa: E402
    WIZARD_HINTS_JURIDIQUE,
    get_wizard_hints,
    list_themes,
)


# Les libellés EXACTS utilisés comme options du step `theme` dans le
# wizard juridique côté frontend (templates/index.html, WIZARDS.juridique).
# Attention aux apostrophes typographiques (U+2019) utilisées côté HTML.
WIZARD_JURIDIQUE_THEMES = [
    "Discipline / sanction",
    "Rupture du contrat",
    "Inaptitude / santé au travail",
    "Temps de travail / congés",
    "Rémunération / classification",
    "CSE / représentants",
    "Modification du contrat",
    "Contentieux Prud\u2019hommes",
    "Autre",
]


class TestWizardHintsParity(unittest.TestCase):
    """La banque de hints doit couvrir exactement les thèmes du wizard."""

    def test_tous_les_themes_wizard_ont_des_hints(self):
        for theme in WIZARD_JURIDIQUE_THEMES:
            with self.subTest(theme=theme):
                hints = get_wizard_hints(theme)
                self.assertGreater(
                    len(hints),
                    0,
                    f"Aucun hint pour le thème '{theme}' (vérifier la typographie des clés)",
                )

    def test_pas_de_cles_orphelines(self):
        orphelines = [k for k in list_themes() if k not in WIZARD_JURIDIQUE_THEMES]
        self.assertEqual(
            orphelines,
            [],
            f"Clés non rattachées à un thème du wizard : {orphelines}",
        )

    def test_au_moins_4_hints_par_theme(self):
        # Règle éditoriale : chaque thème expose au moins 4 questions-pistes.
        for theme, hints in WIZARD_HINTS_JURIDIQUE.items():
            with self.subTest(theme=theme):
                self.assertGreaterEqual(
                    len(hints), 4, f"Thème '{theme}' en dessous du minimum de 4 hints"
                )

    def test_thème_inconnu_renvoie_liste_vide(self):
        self.assertEqual(get_wizard_hints("Thème qui n'existe pas"), [])

    def test_list_themes_coherent_avec_dict(self):
        self.assertEqual(set(list_themes()), set(WIZARD_HINTS_JURIDIQUE.keys()))


class TestHintsContenu(unittest.TestCase):
    def test_hints_sont_des_strings_non_vides(self):
        for theme, hints in WIZARD_HINTS_JURIDIQUE.items():
            for i, h in enumerate(hints):
                with self.subTest(theme=theme, i=i):
                    self.assertIsInstance(h, str)
                    self.assertGreater(len(h.strip()), 10, f"Hint trop court : '{h}'")

    def test_hints_posent_des_questions(self):
        # Règle éditoriale : les hints sont des questions (finissent par ?).
        for theme, hints in WIZARD_HINTS_JURIDIQUE.items():
            for h in hints:
                with self.subTest(theme=theme, hint=h[:40]):
                    self.assertTrue(
                        h.rstrip().endswith("?"),
                        f"Hint non interrogatif : '{h}'",
                    )


if __name__ == "__main__":
    unittest.main(verbosity=2)
