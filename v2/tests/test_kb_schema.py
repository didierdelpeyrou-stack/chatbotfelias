"""Tests des schémas KB Pydantic + validation des 4 KB V1 réelles.

Niveau de rigueur — Sprint 2.3 :
  - Schéma permissif accepte les KB V1 telles quelles (niveau theme optional, etc.)
  - Mais valide les invariants critiques (id non vide, mots_cles list[str], niveau ∈ enum)
  - Test bonus : les 4 KB réelles V1 valident toutes
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.kb.schema import (
    Article,
    FichePratique,
    KBMetadata,
    KnowledgeBase,
    Lien,
    Reponse,
    Revision,
    Theme,
)
from app.kb.validators import KBValidationError, validate_kb_dict, validate_kb_file

# ────────────────────────── Article ──────────────────────────

class TestArticle:
    def test_article_minimal_valide(self):
        art = Article(
            id="ART_001",
            question_type="Test ?",
            mots_cles=["test"],
            reponse=Reponse(synthese="ok"),
        )
        assert art.id == "ART_001"
        assert art.niveau is None  # optionnel

    def test_id_vide_rejete(self):
        with pytest.raises(ValidationError):
            Article(
                id="",
                question_type="Q",
                mots_cles=["m"],
                reponse=Reponse(synthese="s"),
            )

    def test_question_type_vide_rejete(self):
        with pytest.raises(ValidationError):
            Article(
                id="A",
                question_type="",
                mots_cles=["m"],
                reponse=Reponse(synthese="s"),
            )

    def test_mots_cles_string_rejete(self):
        # mots_cles doit être une LISTE, pas une string seule (bug typique)
        with pytest.raises(ValidationError):
            Article.model_validate({
                "id": "A",
                "question_type": "Q",
                "mots_cles": "rupture",  # ← string au lieu de list
                "reponse": {"synthese": "s"},
            })

    def test_mots_cles_strings_vides_filtres(self):
        # Les strings vides ou whitespace sont silencieusement filtrés (pas une erreur)
        art = Article(
            id="A",
            question_type="Q",
            mots_cles=["valide", "", "  ", "encore"],
            reponse=Reponse(synthese="s"),
        )
        assert art.mots_cles == ["valide", "encore"]

    def test_niveau_invalide_rejete(self):
        with pytest.raises(ValidationError):
            Article.model_validate({
                "id": "A",
                "question_type": "Q",
                "mots_cles": [],
                "reponse": {"synthese": "s"},
                "niveau": "jaune",  # n'existe pas
            })

    def test_niveau_rouge_accepte(self):
        art = Article(
            id="A",
            question_type="Q",
            mots_cles=[],
            reponse=Reponse(synthese="s"),
            niveau="rouge",
        )
        assert art.niveau == "rouge"

    def test_extra_fields_acceptes(self):
        # extra="allow" — un champ inattendu ne fait pas planter la validation (compat V1)
        # et est conservé tel quel (Pydantic le stocke en model_extra)
        art = Article.model_validate({
            "id": "A",
            "question_type": "Q",
            "mots_cles": [],
            "reponse": {"synthese": "s"},
            "champ_inconnu_v3": "futur",
        })
        # L'objet existe sans erreur — c'est l'essentiel pour la compat V1
        assert art.id == "A"
        # Le champ extra est conservé dans model_extra
        assert art.model_extra is not None
        assert art.model_extra.get("champ_inconnu_v3") == "futur"


# ────────────────────────── Reponse ──────────────────────────

class TestReponse:
    def test_synthese_obligatoire(self):
        with pytest.raises(ValidationError):
            Reponse()  # synthese requis

    def test_synthese_seule_suffit(self):
        r = Reponse(synthese="ok")
        assert r.fondement_legal is None
        assert r.sources == []
        assert r.liens == []


# ────────────────────────── Lien ──────────────────────────

class TestLien:
    def test_lien_minimal(self):
        link = Lien(titre="Légifrance", url="https://www.legifrance.gouv.fr")
        assert str(link.url).startswith("https://")

    def test_url_invalide_rejete(self):
        with pytest.raises(ValidationError):
            Lien(titre="X", url="pas une url")

    def test_titre_vide_rejete(self):
        with pytest.raises(ValidationError):
            Lien(titre="", url="https://example.com")


# ────────────────────────── FichePratique ──────────────────────────

class TestFichePratique:
    def test_fichier_obligatoire(self):
        with pytest.raises(ValidationError):
            FichePratique()

    def test_fichier_minimal(self):
        fp = FichePratique(fichier="rupture.pdf")
        assert fp.titre is None  # optionnel


# ────────────────────────── Theme ──────────────────────────

class TestTheme:
    def test_theme_minimal(self):
        t = Theme(id="rupture", label="Rupture du contrat")
        assert t.articles == []
        assert t.niveau is None  # optionnel

    def test_theme_avec_niveau_rouge(self):
        t = Theme(id="x", label="X", niveau="rouge")
        assert t.niveau == "rouge"


# ────────────────────────── Revision ──────────────────────────

class TestRevision:
    def test_revision_complete(self):
        rev = Revision(derniere_verification="2026-04-21", verifie_par="ddelpeyrou")
        assert rev.verifie_par == "ddelpeyrou"

    def test_date_invalide_rejete(self):
        with pytest.raises(ValidationError):
            Revision(derniere_verification="pas une date", verifie_par="x")


# ────────────────────────── KnowledgeBase ──────────────────────────

class TestKnowledgeBase:
    def test_kb_minimale(self):
        kb = KnowledgeBase(metadata=KBMetadata(version="1.0"), themes=[])
        assert kb.n_articles == 0

    def test_n_articles_calcule(self):
        kb = KnowledgeBase(
            metadata=KBMetadata(version="1.0"),
            themes=[
                Theme(id="t1", label="T1", articles=[
                    Article(id="A1", question_type="Q", mots_cles=[], reponse=Reponse(synthese="s")),
                    Article(id="A2", question_type="Q", mots_cles=[], reponse=Reponse(synthese="s")),
                ]),
                Theme(id="t2", label="T2", articles=[
                    Article(id="A3", question_type="Q", mots_cles=[], reponse=Reponse(synthese="s")),
                ]),
            ],
        )
        assert kb.n_articles == 3

    def test_metadata_obligatoire(self):
        with pytest.raises(ValidationError):
            KnowledgeBase(themes=[])  # metadata manquant

    def test_to_v1_dict_compat_rag(self):
        # Le RAG (Sprint 2.2) attend un dict V1 — on doit pouvoir produire ce format
        kb = KnowledgeBase(
            metadata=KBMetadata(version="1.0"),
            themes=[Theme(id="t", label="L", articles=[
                Article(id="A", question_type="Q", mots_cles=["k"], reponse=Reponse(synthese="s")),
            ])],
        )
        d = kb.to_v1_dict()
        assert "themes" in d
        assert d["themes"][0]["articles"][0]["id"] == "A"


# ────────────────────────── Validators ──────────────────────────

class TestValidators:
    def test_validate_kb_dict_ok(self):
        data = {
            "metadata": {"version": "1.0"},
            "themes": [{"id": "t", "label": "T", "articles": []}],
        }
        kb = validate_kb_dict(data)
        assert isinstance(kb, KnowledgeBase)

    def test_validate_kb_dict_erreur_levee(self):
        data = {"metadata": {"version": "1.0"}, "themes": [{"id": "", "label": "T"}]}
        with pytest.raises(KBValidationError) as exc_info:
            validate_kb_dict(data, source="<test>")
        # Le message doit mentionner le source
        assert "<test>" in str(exc_info.value)

    def test_validate_kb_file_introuvable(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            validate_kb_file(tmp_path / "inexistant.json")

    def test_validate_kb_file_ok(self, tmp_path):
        kb_file = tmp_path / "test.json"
        kb_file.write_text(json.dumps({
            "metadata": {"version": "1.0"},
            "themes": [],
        }))
        kb = validate_kb_file(kb_file)
        assert kb.metadata.version == "1.0"


# ────────────────────────── Validation des 4 KB V1 RÉELLES ──────────────────────────

# Chemin vers les KB V1 (relatif depuis v2/tests/)
_V1_DATA_DIR = Path(__file__).parent.parent.parent / "data"


@pytest.mark.parametrize("kb_name", ["juridique", "formation", "rh", "gouvernance"])
def test_kb_v1_reelle_valide_le_schema(kb_name: str):
    """Les 4 KB V1 actuelles doivent passer le schéma sans modification.

    Si ce test échoue, c'est que le schéma V2 est trop strict — relâcher
    les contraintes (extra="allow" sur les champs free-form) avant de toucher
    les KB.
    """
    path = _V1_DATA_DIR / f"base_{kb_name}.json"
    if not path.exists():
        pytest.skip(f"KB {kb_name} non disponible dans cet environnement")

    kb = validate_kb_file(path)
    # Sanity check : on doit avoir au moins quelques articles
    assert kb.n_articles > 0, f"KB {kb_name} doit avoir des articles"
    assert kb.metadata.version, f"KB {kb_name} doit avoir une version"
