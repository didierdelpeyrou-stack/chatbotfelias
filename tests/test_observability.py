"""Tests du module observability (init Sentry + scrubber).

Sentry SDK n'est pas appelé en CI (pas de DSN) → on teste surtout :
- Le no-op silencieux quand SENTRY_DSN est vide
- Le scrubber sur des payloads sensibles (clés API, tokens, emails)
"""
from __future__ import annotations

import os
import unittest
from unittest.mock import patch

import observability


class TestInitSentryNoOp(unittest.TestCase):
    """init_sentry doit être silencieux si pas de DSN configuré."""

    def test_pas_de_dsn_renvoie_false(self):
        # On force l'absence de DSN
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SENTRY_DSN", None)
            result = observability.init_sentry()
            self.assertFalse(result)

    def test_dsn_vide_renvoie_false(self):
        with patch.dict(os.environ, {"SENTRY_DSN": ""}):
            self.assertFalse(observability.init_sentry())

    def test_dsn_espaces_uniquement_renvoie_false(self):
        # Un DSN avec uniquement des espaces doit être considéré comme vide après strip
        with patch.dict(os.environ, {"SENTRY_DSN": "   "}):
            self.assertFalse(observability.init_sentry())

    def test_dsn_argument_pris_en_compte(self):
        # Quand on passe dsn=None et qu'aucun SENTRY_DSN n'est dans l'env → no-op
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SENTRY_DSN", None)
            result = observability.init_sentry(dsn=None)
            self.assertFalse(result)


class TestScrubSentryEvent(unittest.TestCase):
    """Le scrubber doit masquer les secrets avant envoi à Sentry."""

    def test_scrub_cle_anthropic(self):
        event = {
            "request": {"data": "Bonjour, ma clé est sk-ant-abc123def456ghi789jkl"}
        }
        scrubbed = observability._scrub_sentry_event(event, None)
        self.assertNotIn("sk-ant-abc123def456ghi789jkl", scrubbed["request"]["data"])
        self.assertIn("sk-ant-***", scrubbed["request"]["data"])

    def test_scrub_bearer_token(self):
        event = {"request": {"data": "Authorization: Bearer eyJabc.def.ghi"}}
        scrubbed = observability._scrub_sentry_event(event, None)
        self.assertNotIn("eyJabc.def.ghi", scrubbed["request"]["data"])
        self.assertIn("Bearer ***", scrubbed["request"]["data"])

    def test_scrub_email(self):
        event = {"extra": {"contact": "user@example.com"}}
        scrubbed = observability._scrub_sentry_event(event, None)
        self.assertEqual(scrubbed["extra"]["contact"], "***@***")

    def test_scrub_dans_query_string(self):
        event = {"request": {"query_string": "token=Bearer secret123"}}
        scrubbed = observability._scrub_sentry_event(event, None)
        self.assertIn("Bearer ***", scrubbed["request"]["query_string"])

    def test_scrub_dans_listes_imbriquees(self):
        event = {
            "extra": {
                "items": ["sk-ant-abcdefghijklmnop", "ok", {"nested": "user@host.fr"}]
            }
        }
        scrubbed = observability._scrub_sentry_event(event, None)
        items = scrubbed["extra"]["items"]
        self.assertIn("sk-ant-***", items[0])
        self.assertEqual(items[1], "ok")
        self.assertEqual(items[2]["nested"], "***@***")

    def test_scrub_exception_message(self):
        event = {
            "exception": {
                "values": [{"value": "API failed for sk-ant-secrettoken123"}]
            }
        }
        scrubbed = observability._scrub_sentry_event(event, None)
        self.assertIn("sk-ant-***", scrubbed["exception"]["values"][0]["value"])

    def test_scrub_breadcrumbs(self):
        event = {
            "breadcrumbs": {
                "values": [
                    {"message": "Hit user@test.com on sk-ant-abc123def456"}
                ]
            }
        }
        scrubbed = observability._scrub_sentry_event(event, None)
        msg = scrubbed["breadcrumbs"]["values"][0]["message"]
        self.assertIn("***@***", msg)
        self.assertIn("sk-ant-***", msg)

    def test_scrub_event_vide_ne_crashe_pas(self):
        # Un event minimal/cassé ne doit pas faire planter le scrubber
        result = observability._scrub_sentry_event({}, None)
        self.assertEqual(result, {})

    def test_scrub_event_malforme_ne_crashe_pas(self):
        # Si le scrubber rencontre un objet inattendu, il doit retourner l'event tel quel
        event = {"request": "pas un dict"}  # request devrait être dict
        # Ne doit PAS lever
        result = observability._scrub_sentry_event(event, None)
        # Le request est laissé tel quel (pas de modification)
        self.assertEqual(result["request"], "pas un dict")


if __name__ == "__main__":
    unittest.main()
