"""Tests du script de migration KB V1 → V2 (Sprint 5.1).

On teste :
  - enrich_article : ajout des 3 champs sans toucher au reste, idempotence
  - migrate_kb : enrichissement complet d'une mini-KB + stats correctes
  - validate_v2 : KB enrichie passe le schéma Pydantic V2
  - heritage du niveau depuis le thème (juridique) vs défaut "vert"
"""
from __future__ import annotations

# Le script vit dans v2/scripts/, pas en package — on importe via import dynamique.
import importlib.util
import sys
from datetime import date
from pathlib import Path

from app.kb.schema import KnowledgeBase

SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "migrate_kb_v1_v2.py"
spec = importlib.util.spec_from_file_location("_migrate", SCRIPT_PATH)
_migrate = importlib.util.module_from_spec(spec)
sys.modules["_migrate"] = _migrate
spec.loader.exec_module(_migrate)


TODAY = date(2026, 4, 25)


# ────────────────────────── enrich_article ──────────────────────────

class TestEnrichArticle:
    def _bare_article(self) -> dict:
        return {
            "id": "ART_001",
            "question_type": "Préavis",
            "mots_cles": ["préavis"],
            "reponse": {"synthese": "1 mois.", "sources": ["CCN art. 4"]},
        }

    def test_ajoute_les_3_champs_quand_absents(self):
        art = self._bare_article()
        added = _migrate.enrich_article(art, theme_niveau="orange", today=TODAY)
        assert art["niveau"] == "orange"
        assert art["escalade"] is False
        assert art["revision"]["derniere_verification"] == "2026-04-25"
        assert art["revision"]["verifie_par"] == _migrate.MIGRATION_AUTHOR
        assert set(added.keys()) == {"niveau", "escalade", "revision"}

    def test_niveau_par_defaut_vert_si_theme_vide(self):
        art = self._bare_article()
        _migrate.enrich_article(art, theme_niveau=None, today=TODAY)
        assert art["niveau"] == "vert"

    def test_idempotent_si_deja_enrichi(self):
        art = self._bare_article()
        art["niveau"] = "rouge"
        art["escalade"] = True
        art["revision"] = {"derniere_verification": "2025-01-15", "verifie_par": "Juriste X"}
        added = _migrate.enrich_article(art, theme_niveau="orange", today=TODAY)
        assert added == {}, "Aucun champ ne doit être ré-écrit"
        assert art["niveau"] == "rouge"  # préserve V1
        assert art["escalade"] is True
        assert art["revision"]["verifie_par"] == "Juriste X"

    def test_preserve_escalade_v1_string(self):
        # Cas spec V2 : escalade peut être un string d'instruction
        art = self._bare_article()
        art["escalade"] = "Contacter immédiatement le pôle juridique."
        _migrate.enrich_article(art, theme_niveau="rouge", today=TODAY)
        assert art["escalade"] == "Contacter immédiatement le pôle juridique."

    def test_ne_touche_pas_au_contenu_metier(self):
        art = self._bare_article()
        _migrate.enrich_article(art, theme_niveau="vert", today=TODAY)
        assert art["id"] == "ART_001"
        assert art["question_type"] == "Préavis"
        assert art["mots_cles"] == ["préavis"]
        assert art["reponse"]["synthese"] == "1 mois."


# ────────────────────────── migrate_kb ──────────────────────────

class TestMigrateKB:
    def _mini_kb(self) -> dict:
        """Mini-KB juridique avec 1 thème vert + 1 thème rouge, 2 articles chacun."""
        return {
            "metadata": {"version": "1.0.0", "module": "juridique"},
            "themes": [
                {
                    "id": "th_contrat",
                    "label": "Contrat",
                    "niveau": "vert",
                    "articles": [
                        {
                            "id": "contrat-01",
                            "question_type": "Période d'essai",
                            "mots_cles": ["essai"],
                            "reponse": {"synthese": "2 mois.", "sources": ["art. 4"]},
                        },
                        {
                            "id": "contrat-02",
                            "question_type": "Préavis",
                            "mots_cles": ["préavis"],
                            "reponse": {"synthese": "1 mois.", "sources": ["art. 5"]},
                        },
                    ],
                },
                {
                    "id": "th_disc",
                    "label": "Discipline",
                    "niveau": "rouge",
                    "articles": [
                        {
                            "id": "disc-01",
                            "question_type": "Faute grave",
                            "mots_cles": ["faute"],
                            "reponse": {"synthese": "Sanction.", "sources": ["art. 9"]},
                            "escalade": True,
                        },
                    ],
                },
            ],
        }

    def test_migration_enrichit_tous_les_articles(self):
        kb, stats = _migrate.migrate_kb(self._mini_kb(), TODAY)
        assert stats["articles_total"] == 3
        # 3 articles × 3 champs ajoutés (escalade, niveau, revision pour 2 ; juste niveau+revision pour disc-01 qui a déjà escalade)
        assert stats["enrichments_added"]["niveau"] == 3
        assert stats["enrichments_added"]["revision"] == 3
        assert stats["enrichments_added"]["escalade"] == 2  # disc-01 préservé

    def test_distribution_niveaux_correcte(self):
        _, stats = _migrate.migrate_kb(self._mini_kb(), TODAY)
        # Les articles héritent du niveau de leur thème
        assert stats["niveaux_distribution"] == {"vert": 2, "rouge": 1}

    def test_validation_v2_passe_apres_migration(self):
        kb_dict, _ = _migrate.migrate_kb(self._mini_kb(), TODAY)
        # Doit valider sans raise
        kb = KnowledgeBase.model_validate(kb_dict)
        assert kb.n_articles == 3
        # Tous les articles ont les 3 champs requis
        for theme in kb.themes:
            for art in theme.articles:
                assert art.niveau is not None
                assert art.escalade is not None
                assert art.revision is not None
                assert art.revision.derniere_verification == TODAY

    def test_idempotence_run_2_fois(self):
        kb1 = self._mini_kb()
        _migrate.migrate_kb(kb1, TODAY)
        # 2e passe sur la même KB déjà enrichie
        _, stats2 = _migrate.migrate_kb(kb1, TODAY)
        # Aucun enrichissement nouveau attendu
        assert sum(stats2["enrichments_added"].values()) == 0


# ────────────────────────── validate_v2 ──────────────────────────

class TestValidateV2:
    def test_kb_correcte_passe(self):
        kb = {
            "metadata": {"version": "1.0"},
            "themes": [{
                "id": "t1", "label": "T", "articles": [{
                    "id": "A1", "question_type": "Q",
                    "mots_cles": ["k"],
                    "reponse": {"synthese": "S"},
                    "niveau": "vert",
                    "escalade": False,
                    "revision": {"derniere_verification": "2026-04-25", "verifie_par": "X"},
                }],
            }],
        }
        # Ne raise pas
        _migrate.validate_v2(kb, "test.json")

    def test_kb_invalide_raise(self):
        kb = {
            "metadata": {"version": "1.0"},
            "themes": [{
                "id": "t1", "label": "T", "articles": [{
                    # `id` manquant → ValidationError
                    "question_type": "Q",
                    "mots_cles": ["k"],
                    "reponse": {"synthese": "S"},
                }],
            }],
        }
        import pytest
        with pytest.raises(SystemExit):
            _migrate.validate_v2(kb, "test.json")
