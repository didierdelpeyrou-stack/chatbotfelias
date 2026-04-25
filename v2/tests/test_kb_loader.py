"""Tests du KBStore — chargement, hot-reload mtime, robustesse aux pannes.

Stratégie : on utilise tmp_path pour créer des fichiers JSON synthétiques,
et on manipule leur mtime via os.utime() pour simuler des modifications.
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path

import pytest

from app.kb.loader import KBStore

# ────────────────────────── Helpers ──────────────────────────

def _kb_payload(version: str = "1.0", *, n_articles: int = 1) -> dict:
    """KB minimale conforme au schéma Pydantic."""
    return {
        "metadata": {"version": version},
        "themes": [
            {
                "id": "t1",
                "label": "Theme 1",
                "articles": [
                    {
                        "id": f"ART_{i}",
                        "question_type": f"Question {i} ?",
                        "mots_cles": ["test", f"keyword{i}"],
                        "reponse": {"synthese": f"synthèse {i}"},
                    }
                    for i in range(n_articles)
                ],
            }
        ],
    }


def _write_kb(dir_path: Path, module: str, payload: dict) -> Path:
    """Écrit base_<module>.json dans dir_path."""
    file_path = dir_path / f"base_{module}.json"
    file_path.write_text(json.dumps(payload), encoding="utf-8")
    return file_path


# ────────────────────────── Chargement initial ──────────────────────────

class TestLoadAll:
    @pytest.mark.asyncio
    async def test_charge_les_modules_disponibles(self, tmp_path):
        _write_kb(tmp_path, "juridique", _kb_payload(n_articles=3))
        _write_kb(tmp_path, "formation", _kb_payload(n_articles=2))
        # rh + gouvernance absents

        store = KBStore(data_dir=tmp_path)
        summary = await store.load_all()

        assert summary == {"juridique": 3, "formation": 2}
        assert store.is_loaded("juridique")
        assert not store.is_loaded("rh")

    @pytest.mark.asyncio
    async def test_kb_invalide_skippee_pas_de_crash(self, tmp_path):
        # KB juridique valide, formation invalide (mots_cles = string)
        _write_kb(tmp_path, "juridique", _kb_payload())
        bad_kb = _kb_payload()
        bad_kb["themes"][0]["articles"][0]["mots_cles"] = "string au lieu de list"
        _write_kb(tmp_path, "formation", bad_kb)

        store = KBStore(data_dir=tmp_path)
        summary = await store.load_all()

        # Juridique chargé, formation skippé silencieusement
        assert "juridique" in summary
        assert "formation" not in summary

    @pytest.mark.asyncio
    async def test_aucune_base_load_all_renvoie_dict_vide(self, tmp_path):
        store = KBStore(data_dir=tmp_path)
        summary = await store.load_all()
        assert summary == {}
        assert not store.all_loaded()


# ────────────────────────── get() ──────────────────────────

class TestGet:
    @pytest.mark.asyncio
    async def test_get_renvoie_kb_dict_et_index(self, tmp_path):
        _write_kb(tmp_path, "juridique", _kb_payload(n_articles=2))
        store = KBStore(data_dir=tmp_path)
        await store.load_all()

        kb_dict, index = await store.get("juridique")
        assert "themes" in kb_dict
        assert "inverted" in index
        assert index["n_articles"] == 2

    @pytest.mark.asyncio
    async def test_get_module_inconnu_raise_keyerror(self, tmp_path):
        store = KBStore(data_dir=tmp_path)
        with pytest.raises(KeyError):
            await store.get("module_inexistant")

    @pytest.mark.asyncio
    async def test_get_avec_lazy_load_si_pas_charge(self, tmp_path):
        # Fichier présent mais load_all() pas appelé → lazy load à la demande
        _write_kb(tmp_path, "juridique", _kb_payload(n_articles=1))
        store = KBStore(data_dir=tmp_path)
        # Pas de load_all()

        kb_dict, index = await store.get("juridique")
        assert index["n_articles"] == 1


# ────────────────────────── Hot-reload mtime ──────────────────────────

class TestHotReload:
    @pytest.mark.asyncio
    async def test_modification_fichier_recharge_kb(self, tmp_path):
        # 1. Boot avec 1 article
        path = _write_kb(tmp_path, "juridique", _kb_payload(n_articles=1))
        store = KBStore(data_dir=tmp_path)
        await store.load_all()

        kb_dict, _ = await store.get("juridique")
        assert len(kb_dict["themes"][0]["articles"]) == 1

        # 2. On modifie le fichier (3 articles maintenant)
        _write_kb(tmp_path, "juridique", _kb_payload(n_articles=3))
        # Force le mtime à être strictement > précédent
        future = time.time() + 5
        os.utime(path, (future, future))

        # 3. get() doit voir la nouvelle version sans redémarrage
        kb_dict, index = await store.get("juridique")
        assert len(kb_dict["themes"][0]["articles"]) == 3
        assert index["n_articles"] == 3

    @pytest.mark.asyncio
    async def test_pas_de_reload_si_mtime_identique(self, tmp_path):
        _write_kb(tmp_path, "juridique", _kb_payload(n_articles=1))
        store = KBStore(data_dir=tmp_path)
        await store.load_all()

        # On capture l'index "original" (objet en mémoire)
        _, index_first = await store.get("juridique")

        # Sans toucher au fichier, on rappelle get()
        _, index_second = await store.get("juridique")

        # Même objet en mémoire → pas de reload (sinon on créerait un nouveau dict)
        assert index_first is index_second

    @pytest.mark.asyncio
    async def test_fichier_disparu_garde_version_cachee(self, tmp_path):
        path = _write_kb(tmp_path, "juridique", _kb_payload(n_articles=1))
        store = KBStore(data_dir=tmp_path)
        await store.load_all()

        # Suppression du fichier après le boot
        path.unlink()

        # get() ne crashe pas — sert la version en mémoire avec un warning
        kb_dict, index = await store.get("juridique")
        assert index["n_articles"] == 1


# ────────────────────────── Inspection ──────────────────────────

class TestInspection:
    @pytest.mark.asyncio
    async def test_stats_retourne_metadata_des_kb_chargees(self, tmp_path):
        _write_kb(tmp_path, "juridique", _kb_payload(n_articles=5))
        store = KBStore(data_dir=tmp_path)
        await store.load_all()

        stats = store.stats()
        assert "juridique" in stats
        assert stats["juridique"]["n_articles"] == 5
        assert stats["juridique"]["n_tokens"] > 0
        assert stats["juridique"]["mtime"] > 0

    @pytest.mark.asyncio
    async def test_all_loaded_false_si_partiel(self, tmp_path):
        _write_kb(tmp_path, "juridique", _kb_payload())
        store = KBStore(data_dir=tmp_path, modules=("juridique", "formation"))
        await store.load_all()
        assert not store.all_loaded()  # formation manque


# ────────────────────────── Concurrence (lock) ──────────────────────────

class TestConcurrency:
    @pytest.mark.asyncio
    async def test_get_concurrent_pas_de_race(self, tmp_path):
        _write_kb(tmp_path, "juridique", _kb_payload(n_articles=2))
        store = KBStore(data_dir=tmp_path)
        await store.load_all()

        # 50 appels get() en parallèle — aucun ne doit lever
        results = await asyncio.gather(*[store.get("juridique") for _ in range(50)])
        assert len(results) == 50
        # Tous renvoient la même structure
        assert all(idx["n_articles"] == 2 for _, idx in results)
