"""Tests de kb_cache.py — invalidation par mtime (fix 9).

Couvre :
  - Round-trip : 1er ``get()`` load, les suivants servent le cache.
  - Invalidation par mtime : toucher le fichier déclenche un reload.
  - ``invalidate()`` force un reload au prochain ``get()``.
  - ``invalidate_all()`` invalide tous les caches enregistrés.
  - ``get_cache()`` retourne bien la MÊME instance pour un même path.
  - Thread-safety : deux threads concurrents ne doublent pas le load.
  - Robustesse : loader qui lève lors d'un reload → on garde la valeur
    précédente.

Exécution :
    pytest tests/test_kb_cache.py -v
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import pytest

from kb_cache import FileBackedCache, get_cache, invalidate_all


pytestmark = pytest.mark.unit


# ──────────────────────── helpers ────────────────────────

def _make_loader(counter: list[int]):
    """Retourne un loader qui lit le JSON ET incrémente un compteur.

    Le compteur permet de vérifier combien de fois le loader a été appelé
    (utile pour prouver qu'on ne reload pas inutilement).
    """
    def _loader(path: Path):
        counter.append(1)
        return json.loads(path.read_text(encoding="utf-8"))
    return _loader


# ──────────────────────── FileBackedCache — round trip ────────────────────────

class TestFileBackedCacheRoundTrip:
    def test_premier_get_charge(self, tmp_path):
        p = tmp_path / "kb.json"
        p.write_text(json.dumps({"v": 1}), encoding="utf-8")
        loads: list[int] = []

        cache = FileBackedCache(p, _make_loader(loads), check_interval_s=0.0)
        result = cache.get()
        assert result == {"v": 1}
        assert len(loads) == 1

    def test_second_get_sert_le_cache_si_fichier_inchange(self, tmp_path):
        """Deux get() consécutifs sans modification = 1 seul load."""
        p = tmp_path / "kb.json"
        p.write_text(json.dumps({"v": 1}), encoding="utf-8")
        loads: list[int] = []

        cache = FileBackedCache(p, _make_loader(loads), check_interval_s=0.0)
        cache.get()
        cache.get()
        cache.get()
        # check_interval_s=0 force à stat à chaque fois, mais le mtime
        # est identique → le loader N'EST PAS rappelé.
        assert len(loads) == 1

    def test_fast_path_skip_stat_dans_check_interval(self, tmp_path):
        """Dans la fenêtre check_interval, on ne stat même pas le fichier."""
        p = tmp_path / "kb.json"
        p.write_text(json.dumps({"v": 1}), encoding="utf-8")
        loads: list[int] = []

        cache = FileBackedCache(p, _make_loader(loads), check_interval_s=60.0)
        cache.get()
        # Modification DIRECTE du fichier : le cache ne devrait PAS la voir
        # car on est dans la fenêtre fast-path de 60 s.
        p.write_text(json.dumps({"v": 2}), encoding="utf-8")
        result = cache.get()
        assert result == {"v": 1}  # ← ancienne valeur, normal
        assert len(loads) == 1


# ──────────────────────── Invalidation par mtime ────────────────────────

class TestMTimeInvalidation:
    def test_modification_fichier_declenche_reload(self, tmp_path):
        p = tmp_path / "kb.json"
        p.write_text(json.dumps({"v": 1}), encoding="utf-8")
        loads: list[int] = []

        # check_interval_s=0 = stat à chaque get → invalidation immédiate
        cache = FileBackedCache(p, _make_loader(loads), check_interval_s=0.0)
        assert cache.get() == {"v": 1}
        assert len(loads) == 1

        # On touche le fichier (mtime change) — sleep 1.1s car certains FS
        # (HFS+, ext4) ont une résolution de 1 s sur st_mtime.
        time.sleep(1.1)
        p.write_text(json.dumps({"v": 2}), encoding="utf-8")

        result = cache.get()
        assert result == {"v": 2}
        assert len(loads) == 2  # un 2e load a bien eu lieu

    def test_invalidate_force_reload(self, tmp_path):
        p = tmp_path / "kb.json"
        p.write_text(json.dumps({"v": 1}), encoding="utf-8")
        loads: list[int] = []

        # check_interval_s élevé → normalement pas de reload dans la fenêtre
        cache = FileBackedCache(p, _make_loader(loads), check_interval_s=60.0)
        cache.get()
        assert len(loads) == 1

        # invalidate() DOIT forcer un reload au prochain get, même si le
        # fichier n'a pas bougé.
        cache.invalidate()
        cache.get()
        assert len(loads) == 2

    def test_fichier_absent_renvoie_dernier_cache_si_dispo(self, tmp_path):
        """Si le fichier disparaît puis réapparaît, on ne crash pas."""
        p = tmp_path / "kb.json"
        p.write_text(json.dumps({"v": 1}), encoding="utf-8")
        loads: list[int] = []

        cache = FileBackedCache(p, _make_loader(loads), check_interval_s=0.0)
        cache.get()

        # Fichier supprimé pendant l'exécution : cache renvoie la dernière
        # valeur connue (pas de crash).
        p.unlink()
        result = cache.get()
        # Le comportement exact dépend du loader : ici, le loader tente de
        # lire et lève FileNotFoundError → on garde l'ancienne valeur.
        assert result == {"v": 1}


# ──────────────────────── Registry global ────────────────────────

class TestCacheRegistry:
    def test_get_cache_meme_instance_pour_meme_path(self, tmp_path):
        """get_cache(path) appelé deux fois → même objet."""
        p = tmp_path / "kb.json"
        p.write_text(json.dumps({"v": 1}), encoding="utf-8")
        loads: list[int] = []

        c1 = get_cache(p, _make_loader(loads))
        c2 = get_cache(p, _make_loader(loads))
        assert c1 is c2  # exactement le même objet

    def test_get_cache_instances_differentes_pour_paths_differents(self, tmp_path):
        p1 = tmp_path / "kb1.json"
        p2 = tmp_path / "kb2.json"
        p1.write_text(json.dumps({"a": 1}), encoding="utf-8")
        p2.write_text(json.dumps({"b": 2}), encoding="utf-8")
        loads: list[int] = []

        c1 = get_cache(p1, _make_loader(loads))
        c2 = get_cache(p2, _make_loader(loads))
        assert c1 is not c2
        assert c1.path != c2.path

    def test_invalidate_all_touche_tous_les_caches(self, tmp_path):
        p1 = tmp_path / "kb_all_1.json"
        p2 = tmp_path / "kb_all_2.json"
        p1.write_text(json.dumps({"a": 1}), encoding="utf-8")
        p2.write_text(json.dumps({"b": 2}), encoding="utf-8")

        loads1: list[int] = []
        loads2: list[int] = []
        c1 = get_cache(p1, _make_loader(loads1), check_interval_s=60.0)
        c2 = get_cache(p2, _make_loader(loads2), check_interval_s=60.0)

        # Première charge (1 load chacun)
        c1.get(); c2.get()
        assert len(loads1) == 1 and len(loads2) == 1

        # invalidate_all → les deux caches doivent reloader
        invalidate_all()
        c1.get(); c2.get()
        assert len(loads1) == 2
        assert len(loads2) == 2


# ──────────────────────── Thread-safety ────────────────────────

class TestThreadSafety:
    def test_deux_threads_concurrents_ne_doublent_pas_le_load(self, tmp_path):
        """Sous contention, le double-check locking doit éviter deux loads."""
        p = tmp_path / "kb.json"
        p.write_text(json.dumps({"v": 1}), encoding="utf-8")
        loads: list[int] = []
        loader_started = threading.Event()
        loader_can_continue = threading.Event()

        def _slow_loader(path: Path):
            # Simule un loader lent pour créer une fenêtre de race.
            loader_started.set()
            loader_can_continue.wait(timeout=5.0)
            loads.append(1)
            return json.loads(path.read_text(encoding="utf-8"))

        cache = FileBackedCache(p, _slow_loader, check_interval_s=0.0)
        results: list = []

        def _worker():
            results.append(cache.get())

        t1 = threading.Thread(target=_worker)
        t2 = threading.Thread(target=_worker)
        t1.start()
        # On attend que le premier thread AIT pris le lock avant de lancer
        # le second. Sinon, test flaky : t2 peut arriver avant.
        loader_started.wait(timeout=5.0)
        t2.start()

        # Les deux threads sont maintenant empilés sur le lock : on libère.
        loader_can_continue.set()
        t1.join(timeout=5.0)
        t2.join(timeout=5.0)

        assert len(results) == 2
        assert results[0] == results[1] == {"v": 1}
        # UN SEUL load malgré deux threads (c'est tout l'intérêt du lock)
        assert len(loads) == 1

    def test_get_serialise_les_acces(self, tmp_path):
        """100 threads simultanés → pas de data race, valeur cohérente."""
        p = tmp_path / "kb.json"
        p.write_text(json.dumps({"v": "hello"}), encoding="utf-8")
        loads: list[int] = []

        cache = FileBackedCache(p, _make_loader(loads), check_interval_s=60.0)
        results: list = []
        errors: list[BaseException] = []

        def _worker():
            try:
                results.append(cache.get())
            except BaseException as e:  # pragma: no cover
                errors.append(e)

        threads = [threading.Thread(target=_worker) for _ in range(100)]
        for t in threads: t.start()
        for t in threads: t.join(timeout=5.0)

        assert not errors
        assert len(results) == 100
        assert all(r == {"v": "hello"} for r in results)
        # Avec check_interval=60s : un seul load réel pour 100 threads.
        assert len(loads) == 1


# ──────────────────────── Robustesse du loader ────────────────────────

class TestLoaderRobustness:
    def test_premier_load_rate_leve(self, tmp_path):
        """Si le tout premier load échoue, on ne peut pas servir de valeur
        → la fonction doit laisser passer l'erreur (pas de silent swallow)."""
        p = tmp_path / "absent.json"

        def _bad_loader(path: Path):
            raise FileNotFoundError(path)

        cache = FileBackedCache(p, _bad_loader, check_interval_s=0.0)
        with pytest.raises(FileNotFoundError):
            cache.get()

    def test_reload_rate_garde_ancienne_valeur(self, tmp_path):
        """Si un reload échoue alors qu'on avait déjà une valeur, on ne
        crash pas : l'ancienne valeur reste servie."""
        p = tmp_path / "kb.json"
        p.write_text(json.dumps({"v": 1}), encoding="utf-8")

        call_count = [0]

        def _flaky_loader(path: Path):
            call_count[0] += 1
            if call_count[0] >= 2:
                raise RuntimeError("disk I/O error")
            return json.loads(path.read_text(encoding="utf-8"))

        cache = FileBackedCache(p, _flaky_loader, check_interval_s=0.0)
        assert cache.get() == {"v": 1}

        # Touche le fichier pour forcer un reload → le loader va lever.
        time.sleep(1.1)
        p.write_text(json.dumps({"v": 2}), encoding="utf-8")

        # Ne crash pas → on garde {"v": 1}
        result = cache.get()
        assert result == {"v": 1}
