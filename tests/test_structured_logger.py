"""Tests du logger JSONL structuré (Sprint 0.4).

Couvre :
- hash_question : déterminisme, longueur, cas vide
- log_event : écriture JSONL valide, append, filtrage None, UTF-8
- Robustesse : ne crashe pas si IO impossible (fallback silencieux)
"""
from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

import structured_logger as sl


class TestHashQuestion(unittest.TestCase):
    def test_hash_deterministe(self):
        h1 = sl.hash_question("Quelle durée de préavis ?")
        h2 = sl.hash_question("Quelle durée de préavis ?")
        self.assertEqual(h1, h2)

    def test_longueur_12_chars(self):
        self.assertEqual(len(sl.hash_question("test")), 12)

    def test_chaine_vide(self):
        self.assertEqual(sl.hash_question(""), "")

    def test_questions_differentes_hashs_differents(self):
        h1 = sl.hash_question("Q1")
        h2 = sl.hash_question("Q2")
        self.assertNotEqual(h1, h2)

    def test_unicode(self):
        # Caractères accentués doivent être encodés en UTF-8 sans crash
        h = sl.hash_question("Préavis légal éà")
        self.assertEqual(len(h), 12)


class TestLogEvent(unittest.TestCase):
    def setUp(self):
        # Redirige le log vers un fichier temporaire pour éviter de polluer logs/
        import tempfile
        self.tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False, encoding="utf-8"
        )
        self.tmp.close()
        os.environ["ELISFA_EVENTS_LOG"] = self.tmp.name

    def tearDown(self):
        os.environ.pop("ELISFA_EVENTS_LOG", None)
        Path(self.tmp.name).unlink(missing_ok=True)

    def _read_lines(self):
        return Path(self.tmp.name).read_text(encoding="utf-8").strip().splitlines()

    def test_event_basique_ecrit(self):
        sl.log_event("test_event", foo="bar", n=42)
        lines = self._read_lines()
        self.assertEqual(len(lines), 1)
        entry = json.loads(lines[0])
        self.assertEqual(entry["event"], "test_event")
        self.assertEqual(entry["foo"], "bar")
        self.assertEqual(entry["n"], 42)
        self.assertIn("ts", entry)

    def test_timestamp_iso(self):
        sl.log_event("e1")
        entry = json.loads(self._read_lines()[0])
        # Format ISO : "YYYY-MM-DDTHH:MM:SS.fff+00:00"
        self.assertRegex(entry["ts"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")

    def test_append_pas_overwrite(self):
        sl.log_event("e1", n=1)
        sl.log_event("e2", n=2)
        sl.log_event("e3", n=3)
        lines = self._read_lines()
        self.assertEqual(len(lines), 3)
        self.assertEqual(json.loads(lines[0])["n"], 1)
        self.assertEqual(json.loads(lines[2])["n"], 3)

    def test_valeurs_none_filtrees(self):
        # Filtre lisibilité : on n'écrit pas les champs None
        sl.log_event("e", real="ok", absent=None)
        entry = json.loads(self._read_lines()[0])
        self.assertEqual(entry["real"], "ok")
        self.assertNotIn("absent", entry)

    def test_utf8_caracteres_accentues(self):
        sl.log_event("e", message="préavis éàç")
        entry = json.loads(self._read_lines()[0])
        self.assertEqual(entry["message"], "préavis éàç")

    def test_objets_complexes_serialises_via_default(self):
        # L'écriture JSONL utilise default=str pour les objets non sérialisables
        from datetime import datetime
        d = datetime(2026, 4, 25, 10, 30)
        sl.log_event("e", when=d)
        # Pas de crash, le datetime est stringifié
        entry = json.loads(self._read_lines()[0])
        self.assertIn("2026-04-25", entry["when"])

    def test_event_ne_crashe_pas_si_io_impossible(self):
        # Force un chemin invalide → la fonction ne doit PAS lever
        os.environ["ELISFA_EVENTS_LOG"] = "/nonexistent_dir_xyz_999/sub/sub/file.jsonl"
        try:
            # Cas où même mkdir échoue : on patch pour simuler permission denied
            with patch.object(Path, "mkdir", side_effect=PermissionError):
                # Doit retourner None silencieusement, sans propager
                result = sl.log_event("e", k=1)
                self.assertIsNone(result)
        finally:
            # Restore env pour ne pas polluer les autres tests
            os.environ["ELISFA_EVENTS_LOG"] = self.tmp.name


class TestEventsLogPath(unittest.TestCase):
    def test_default_path(self):
        os.environ.pop("ELISFA_EVENTS_LOG", None)
        path = sl._events_log_path()
        self.assertEqual(path.name, "events.jsonl")
        self.assertEqual(path.parent.name, "logs")

    def test_override_via_env(self):
        os.environ["ELISFA_EVENTS_LOG"] = "/tmp/custom-elisfa.jsonl"
        try:
            self.assertEqual(str(sl._events_log_path()), "/tmp/custom-elisfa.jsonl")
        finally:
            os.environ.pop("ELISFA_EVENTS_LOG", None)


if __name__ == "__main__":
    unittest.main()
