"""Tests unitaires des modèles Pydantic (fix 6).

Couvre ``AskRequest``, ``RdvRequest``, ``AppelRequest``,
``EmailJuristeRequest``, ``FeedbackRequest`` et le helper
``format_validation_error``.

Conventions
-----------
  - Les limites (MAX_CONTEXT_KEY_CHARS, etc.) sont importées du module
    ``validation`` au lieu d'être ré-écrites en dur ici. Si la limite
    bouge côté modèle, le test suit automatiquement.
  - Les assertions vérifient non seulement l'acceptation/le rejet, mais
    aussi que **le champ fautif apparaît dans le message d'erreur** —
    garantie minimale pour les messages remontés au frontend.

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
    MAX_CONTEXT_KEY_CHARS,
    MAX_CONTEXT_VAL_CHARS,
    MAX_HISTORY_MESSAGES,
    MAX_MOTIF_CHARS,
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

    def test_module_insensible_casse_et_espaces(self):
        """Les clients peuvent envoyer 'Juridique ', ' rh', etc."""
        for raw in ("Juridique", " RH ", "Formation  "):
            r = AskRequest.model_validate({"question": "x", "module": raw})
            assert r.module in {"juridique", "rh", "formation"}

    def test_escalation_inconnue_corrige_en_vert(self):
        r = AskRequest.model_validate({
            "question": "x", "escalation_level": "critique",
        })
        assert r.escalation_level == "vert"

    def test_history_plafonnee_a_20_messages(self):
        """Garde les MAX_HISTORY_MESSAGES derniers — protection DoS."""
        history = [{"role": "user", "content": f"m{i}"} for i in range(50)]
        r = AskRequest.model_validate({"question": "x", "history": history})
        assert len(r.history) == MAX_HISTORY_MESSAGES
        # Garde bien les DERNIERS, pas les premiers
        assert r.history[-1]["content"] == "m49"
        assert r.history[0]["content"] == f"m{50 - MAX_HISTORY_MESSAGES}"

    def test_history_non_liste_devient_liste_vide(self):
        """Un history qui n'est PAS une liste (ex: string) → [] silencieusement."""
        for bad in ("pas une liste", 42, None, {"key": "value"}):
            r = AskRequest.model_validate({"question": "x", "history": bad})
            assert r.history == []

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
        assert len(key) == MAX_CONTEXT_KEY_CHARS
        assert len(r.context[key]) == MAX_CONTEXT_VAL_CHARS

    def test_context_non_dict_devient_none(self):
        """Un context de type invalide (list, str, int) → None."""
        for bad in ([1, 2, 3], "une string", 42, True):
            r = AskRequest.model_validate({"question": "x", "context": bad})
            assert r.context is None

    def test_function_profile_tronques_a_80(self):
        r = AskRequest.model_validate({
            "question": "x",
            "function": "a" * 200,
            "profile": "b" * 200,
        })
        # La borne interne est 80 — constante implicite partagée par function/profile.
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

    def test_question_avec_unicode_et_accents(self):
        """Inputs FR : é, è, à, ç, emojis — ne doivent PAS être rejetés ni corrompus."""
        q = "Bonjour, j'ai une question sur les congés payés 🏖️ — urgent !"
        r = AskRequest.model_validate({"question": q})
        assert r.question == q  # pas de perte de caractères


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
        msg = format_validation_error(exc.value).lower()
        assert "email" in msg, f"Message d'erreur doit mentionner 'email' : {msg!r}"

    def test_telephone_trop_court_rejette(self):
        bad = {**self.VALID, "telephone": "123"}
        with pytest.raises(ValidationError) as exc:
            RdvRequest.model_validate(bad)
        msg = format_validation_error(exc.value).lower()
        assert "telephone" in msg or "téléphone" in msg, (
            f"Message d'erreur doit mentionner 'telephone' : {msg!r}"
        )

    @pytest.mark.parametrize("tel", [
        "+33 6 12 34 56 78",   # format international avec espaces
        "06.12.34.56.78",       # points
        "(01) 23-45-67-89",     # parenthèses + tirets
        "0033-6-12-34-56-78",   # préfixe international avec tirets
    ])
    def test_telephone_avec_separateurs_accepte(self, tel):
        """+33, espaces, points, parenthèses, tirets doivent passer ET le
        champ doit rester lisible (pas corrompu par un strip agressif)."""
        payload = {**self.VALID, "telephone": tel}
        r = RdvRequest.model_validate(payload)
        # La validation passe (pas d'exception).
        assert r.telephone  # non-vide
        # Le contenu retourné doit avoir au moins 6 chiffres (seuil _PHONE_DIGITS_RE).
        digits_only = "".join(c for c in r.telephone if c.isdigit())
        assert len(digits_only) >= 6, (
            f"Téléphone normalisé doit garder ≥6 chiffres, "
            f"got {digits_only!r} from {tel!r}"
        )

    @pytest.mark.parametrize("tel", [
        "abcdefghij",           # pas de chiffres
        "12345",                # 5 chiffres : en dessous du min (6)
        "((((()))))----",       # séparateurs sans chiffres
        "+33 abc def",          # mix
    ])
    def test_telephone_invalide_rejette(self, tel):
        """Chaînes sans assez de chiffres → rejet explicite."""
        bad = {**self.VALID, "telephone": tel}
        with pytest.raises(ValidationError):
            RdvRequest.model_validate(bad)

    def test_nom_trop_court_rejette(self):
        bad = {**self.VALID, "nom": "X"}
        with pytest.raises(ValidationError):
            RdvRequest.model_validate(bad)

    def test_nom_avec_accents_ok(self):
        """Noms FR avec accents doivent passer (ne pas être rejetés par
        un strip ASCII trop agressif)."""
        r = RdvRequest.model_validate({**self.VALID, "nom": "Éléonore Gérard"})
        assert r.nom == "Éléonore Gérard"

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
        """Le motif doit respecter MAX_MOTIF_CHARS — borne dérivée du module."""
        bad = {**self.VALID, "motif": "x" * (MAX_MOTIF_CHARS + 100)}
        with pytest.raises(ValidationError):
            AppelRequest.model_validate(bad)

    def test_motif_pile_a_la_limite_ok(self):
        """La borne exacte doit passer (pas d'off-by-one)."""
        r = AppelRequest.model_validate({**self.VALID, "motif": "x" * MAX_MOTIF_CHARS})
        assert len(r.motif) == MAX_MOTIF_CHARS


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
        msg = format_validation_error(exc.value).lower()
        assert "réponses" in msg or "reponses" in msg

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
        for v in (2, 5, 100, -2, -100):
            with pytest.raises(ValidationError):
                FeedbackRequest.model_validate({"rating": v})

    def test_rating_requis(self):
        with pytest.raises(ValidationError):
            FeedbackRequest.model_validate({})

    def test_rating_string_coerce_ou_rejette(self):
        """Pydantic v2 coerce "1" -> 1 par défaut. On vérifie juste le
        comportement attendu : soit coerce (accepté), soit rejet propre."""
        # Cas nominal : "1" devient 1 via coerce
        r = FeedbackRequest.model_validate({"rating": "1"})
        assert r.rating == 1
        # Cas invalide : une string non numérique doit être rejetée
        with pytest.raises(ValidationError):
            FeedbackRequest.model_validate({"rating": "oui"})

    def test_champs_texte_max_length_enforce(self):
        """Pas de troncature automatique : Pydantic REJETTE si max_length
        dépassé. Le handler troncature manuellement avant le write disque.
        Les bornes exactes sont lues depuis les Field du modèle pour éviter
        les magic numbers dans les tests."""
        # Récupère les max_length depuis le schéma Pydantic — single source of truth.
        fields = FeedbackRequest.model_fields
        comment_max = fields["comment"].metadata[0].max_length  # type: ignore[attr-defined]
        question_max = fields["question"].metadata[0].max_length  # type: ignore[attr-defined]
        answer_max = fields["answer"].metadata[0].max_length  # type: ignore[attr-defined]

        # Dépassement → 400
        with pytest.raises(ValidationError):
            FeedbackRequest.model_validate({"rating": 1, "comment": "c" * (comment_max + 1)})
        with pytest.raises(ValidationError):
            FeedbackRequest.model_validate({"rating": 1, "question": "q" * (question_max + 1)})
        with pytest.raises(ValidationError):
            FeedbackRequest.model_validate({"rating": 1, "answer": "a" * (answer_max + 1)})
        # Valeurs à la limite → OK (pas d'off-by-one)
        r = FeedbackRequest.model_validate({
            "rating": 1,
            "comment": "c" * comment_max,
            "question": "q" * question_max,
            "answer": "a" * answer_max,
        })
        assert r.rating == 1


# ──────────────────────── format_validation_error ────────────────────────

class TestFormatValidationError:
    def test_message_mentionne_le_champ_fautif(self):
        """Le message doit contenir le nom du champ en erreur — sinon,
        l'utilisateur final ne sait pas quoi corriger."""
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
            # Pas de "Value error, " dans le message final (nettoyé).
            assert "Value error" not in msg
            # Le nom du champ fautif (nom OU email OU telephone) doit apparaître.
            # Pydantic s'arrête à la première erreur — ici 'nom' (ordre de déclaration).
            low = msg.lower()
            assert any(f in low for f in ("nom", "email", "telephone", "téléphone")), (
                f"Message doit nommer le champ fautif, got {msg!r}"
            )

    def test_message_sur_validation_error_vide(self):
        """Edge case : si errors() est vide, on renvoie un fallback."""
        class _FakeErr:
            def errors(self):
                return []

        msg = format_validation_error(_FakeErr())
        assert msg == "Payload invalide."

    def test_message_robuste_si_errors_raise(self):
        """Si .errors() lève, on renvoie le fallback (pas de crash)."""
        class _BrokenErr:
            def errors(self):
                raise RuntimeError("boom")

        msg = format_validation_error(_BrokenErr())
        assert msg == "Payload invalide."
