"""Tests unitaires des modèles Pydantic (fix 6).

Couvre ``AskRequest``, ``RdvRequest``, ``AppelRequest``,
``EmailJuristeRequest``, ``FeedbackRequest`` et le helper
``format_validation_error``.

Exécution :
    pytest tests/test_validation.py -v
    ou
    python3 -m unittest tests.test_validation
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from validation import (
    AskRequest,
    RdvRequest,
    AppelRequest,
    EmailJuristeRequest,
    FeedbackRequest,
    format_validation_error,
)


pytestmark = pytest.mark.unit


# ──────────────────────── AskRequest ────────────────────────

class TestAskRequest:
    def test_payload_minimal_valide(self):
        r = AskRequest.model_validate({"question": "Bonjour"})
        assert r.question == "Bonjour"
        assert r.module == "juridique"  # default
        assert r.escalation_level == "vert"  # default
        assert r.history == []
        assert r.function is None

    def test_module_inconnu_corrige_en_juridique(self):
        """Règle métier : un module inconnu ne doit PAS rejeter, mais
        retomber silencieusement sur 'juridique' pour ne pas casser les
        clients qui ont une typo."""
        r = AskRequest.model_validate({"question": "x", "module": "inexistant"})
        assert r.module == "juridique"

    def test_module_valide(self):
        for mod in ("juridique", "formation", "rh", "gouvernance"):
            r = AskRequest.model_validate({"question": "x", "module": mod})
            assert r.module == mod

    def test_escalation_inconnue_corrige_en_vert(self):
        r = AskRequest.model_validate({
            "question": "x", "escalation_level": "critique",
        })
        assert r.escalation_level == "vert"

    def test_history_plafonnee_a_20_messages(self):
        """Garde les 20 derniers — protection DoS par historique énorme."""
        history = [{"role": "user", "content": f"m{i}"} for i in range(50)]
        r = AskRequest.model_validate({"question": "x", "history": history})
        assert len(r.history) == 20
        # Garde bien les DERNIERS, pas les premiers
        assert r.history[-1]["content"] == "m49"
        assert r.history[0]["content"] == "m30"

    def test_context_valeurs_non_str_ignorees(self):
        """Le context n'accepte que {str: str|int|float} — les autres types
        sont skip silencieusement au lieu de 400."""
        r = AskRequest.model_validate({
            "question": "x",
            "context": {
                "nom": "Dupont",
                "age": 42,
                "tel": 33612345678,
                "meta": {"nested": "dict"},  # ignoré
                "tags": ["a", "b"],           # ignoré
            },
        })
        assert r.context is not None
        assert "nom" in r.context
        assert "age" in r.context
        assert "meta" not in r.context
        assert "tags" not in r.context

    def test_context_tronque_cles_et_valeurs(self):
        r = AskRequest.model_validate({
            "question": "x",
            "context": {"k" * 100: "v" * 500},
        })
        key = next(iter(r.context))
        assert len(key) == 60  # MAX_CONTEXT_KEY_CHARS
        assert len(r.context[key]) == 200  # MAX_CONTEXT_VAL_CHARS

    def test_function_profile_tronques_a_80(self):
        r = AskRequest.model_validate({
            "question": "x",
            "function": "a" * 200,
            "profile": "b" * 200,
        })
        assert len(r.function) == 80
        assert len(r.profile) == 80

    def test_question_vide_acceptee_si_document_present(self):
        # La validation cross-champs (question OR document requis) est faite
        # dans le handler /api/ask, pas dans le modèle : ici on vérifie
        # juste que le modèle accepte un payload avec document et question vide.
        r = AskRequest.model_validate({"question": "", "document": "abc"})
        assert r.question == ""
        assert r.document == "abc"

    def test_extras_ignores(self):
        """Les clés futures ajoutées côté frontend ne doivent pas casser
        l'API (extra='ignore')."""
        r = AskRequest.model_validate({
            "question": "x",
            "feature_flag_v2": True,
            "future_field": [1, 2, 3],
        })
        assert r.question == "x"


# ──────────────────────── RdvRequest ────────────────────────

class TestRdvRequest:
    VALID = {
        "nom": "Jean Dupont",
        "email": "jean@exemple.fr",
        "telephone": "0612345678",
        "sujet": "Question sur un CDD",
    }

    def test_payload_valide(self):
        r = RdvRequest.model_validate(self.VALID)
        assert r.nom == "Jean Dupont"
        assert r.sujet == "Question sur un CDD"

    def test_email_invalide_rejette(self):
        bad = {**self.VALID, "email": "pas-un-email"}
        with pytest.raises(ValidationError) as exc:
            RdvRequest.model_validate(bad)
        assert "email" in format_validation_error(exc.value).lower()

    def test_telephone_trop_court_rejette(self):
        bad = {**self.VALID, "telephone": "123"}
        with pytest.raises(ValidationError):
            RdvRequest.model_validate(bad)

    def test_telephone_avec_separateurs_accepte(self):
        """+33, espaces, points, parenthèses, tirets doivent passer."""
        for tel in ("+33 6 12 34 56 78", "06.12.34.56.78", "(01) 23-45-67-89"):
            payload = {**self.VALID, "telephone": tel}
            r = RdvRequest.model_validate(payload)
            assert r.telephone  # juste besoin que la validation passe

    def test_nom_trop_court_rejette(self):
        bad = {**self.VALID, "nom": "X"}
        with pytest.raises(ValidationError):
            RdvRequest.model_validate(bad)

    def test_sujet_obligatoire(self):
        bad = {k: v for k, v in self.VALID.items() if k != "sujet"}
        with pytest.raises(ValidationError):
            RdvRequest.model_validate(bad)

    def test_champs_optionnels(self):
        r = RdvRequest.model_validate({
            **self.VALID,
            "structure": "Crèche La Licorne",
            "contexte": "Situation compliquée",
            "niveau": "rouge",
            "theme": "contrat_travail",
        })
        assert r.structure == "Crèche La Licorne"
        assert r.niveau == "rouge"


# ──────────────────────── AppelRequest ────────────────────────

class TestAppelRequest:
    VALID = {
        "nom": "Marie Durand",
        "email": "marie@crea.fr",
        "telephone": "0698765432",
        "motif": "Question urgente sur rupture",
    }

    def test_payload_valide(self):
        r = AppelRequest.model_validate(self.VALID)
        assert r.motif == "Question urgente sur rupture"
        assert r.date is None
        assert r.heure is None

    def test_motif_vide_rejette(self):
        bad = {**self.VALID, "motif": ""}
        with pytest.raises(ValidationError):
            AppelRequest.model_validate(bad)

    def test_motif_trop_long_rejette(self):
        bad = {**self.VALID, "motif": "x" * 1000}
        with pytest.raises(ValidationError):
            AppelRequest.model_validate(bad)


# ──────────────────────── EmailJuristeRequest ────────────────────────

class TestEmailJuristeRequest:
    VALID = {
        "nom": "Pierre Martin",
        "email": "pierre@elisfa.fr",
        "telephone": "0612345678",
        "theme_guide": "contrat_travail",
        "reponses": {"type_contrat": "CDI", "anciennete": "3 ans"},
    }

    def test_payload_valide(self):
        r = EmailJuristeRequest.model_validate(self.VALID)
        assert r.theme_guide == "contrat_travail"
        assert r.reponses["type_contrat"] == "CDI"

    def test_reponses_vide_rejette(self):
        bad = {**self.VALID, "reponses": {}}
        with pytest.raises(ValidationError) as exc:
            EmailJuristeRequest.model_validate(bad)
        assert "réponses" in format_validation_error(exc.value).lower() or \
               "reponses" in format_validation_error(exc.value).lower()

    def test_reponses_pas_dict_rejette(self):
        bad = {**self.VALID, "reponses": "pas un dict"}
        with pytest.raises(ValidationError):
            EmailJuristeRequest.model_validate(bad)


# ──────────────────────── FeedbackRequest ────────────────────────

class TestFeedbackRequest:
    def test_rating_plus_un_valide(self):
        r = FeedbackRequest.model_validate({"rating": 1})
        assert r.rating == 1

    def test_rating_moins_un_valide(self):
        r = FeedbackRequest.model_validate({"rating": -1})
        assert r.rating == -1

    def test_rating_zero_rejette(self):
        with pytest.raises(ValidationError):
            FeedbackRequest.model_validate({"rating": 0})

    def test_rating_hors_plage_rejette(self):
        with pytest.raises(ValidationError):
            FeedbackRequest.model_validate({"rating": 5})

    def test_rating_requis(self):
        with pytest.raises(ValidationError):
            FeedbackRequest.model_validate({})

    def test_champs_texte_max_length_enforce(self):
        """Pas de troncature automatique : Pydantic REJETTE si max_length
        dépassé. Le handler troncature manuellement avant le write disque.
        Le test vérifie juste que les max_length du modèle sont stricts."""
        # comment > 2000 → 400
        with pytest.raises(ValidationError):
            FeedbackRequest.model_validate({"rating": 1, "comment": "c" * 2001})
        # question > 2000 → 400
        with pytest.raises(ValidationError):
            FeedbackRequest.model_validate({"rating": 1, "question": "q" * 2001})
        # answer > 8000 → 400
        with pytest.raises(ValidationError):
            FeedbackRequest.model_validate({"rating": 1, "answer": "a" * 8001})
        # Dans les limites → OK (les valeurs à la limite doivent passer)
        r = FeedbackRequest.model_validate({
            "rating": 1,
            "comment": "c" * 2000,
            "question": "q" * 2000,
            "answer": "a" * 8000,
        })
        assert r.rating == 1


# ──────────────────────── format_validation_error ────────────────────────

class TestFormatValidationError:
    def test_message_lisible(self):
        try:
            RdvRequest.model_validate({
                "nom": "X",  # trop court
                "email": "bad",
                "telephone": "123",
                "sujet": "ok",
            })
        except ValidationError as e:
            msg = format_validation_error(e)
            assert isinstance(msg, str)
            assert len(msg) > 10
            # Pas de "Value error, " dans le message final (nettoyé)
            assert "Value error" not in msg
