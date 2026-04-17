"""Cache KB avec invalidation par mtime.

Problème résolu
---------------
Les bases de connaissances (``data/base_*.json``) sont chargées une seule
fois au démarrage du serveur. Si on modifie un JSON à chaud (ex. correction
d'un article, ajout d'un thème), il faut relancer le container pour voir
l'effet — ou appeler ``POST /api/reload`` manuellement (endpoint admin).

Ce module ajoute une **invalidation automatique par mtime** : avant chaque
lecture, on vérifie si le fichier a été modifié depuis le dernier load. Si
oui, on recharge. Sinon, on sert la version en cache (quasi-gratuit : une
seule syscall ``os.stat`` par check).

Architecture
------------
  - ``FileBackedCache`` : cache générique par fichier, thread-safe.
  - ``load_kb_with_cache(path, loader_fn)`` : wrapper pratique pour
    ``_load_json_kb`` de app.py qui garde une compat parfaite.

Thread-safety
-------------
Gunicorn tourne en mode threads (1 worker × 8 threads, cf. Dockerfile).
Plusieurs threads peuvent accéder au cache en concurrence → on utilise un
``threading.Lock`` par fichier pour éviter :
  - les doubles loads inutiles sous charge (two threads voient
    ``_mtime`` obsolète en même temps),
  - les lectures partielles (si un thread reload, l'autre doit attendre
    de voir l'état post-reload).

Performance
-----------
Sur un VPS avec SSD, ``os.stat`` sur un fichier de 300 KB = ~0.05 ms.
Pour une API qui gère ~10 req/s, c'est 0.5 ms/s de CPU consommé par les
stat checks — négligeable par rapport aux ~300 ms de latence d'un appel
Claude.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Callable, Optional


class FileBackedCache:
    """Cache générique indexé sur le mtime d'un fichier.

    Usage
    -----
        cache = FileBackedCache(path="data/foo.json", loader=_load_foo)
        data = cache.get()  # recharge si foo.json modifié depuis le dernier get
        cache.invalidate()  # force un reload au prochain get (utilisé par /api/reload)
    """

    def __init__(
        self,
        path: Path,
        loader: Callable[[Path], Any],
        *,
        check_interval_s: float = 1.0,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        """Initialise le cache.

        Parameters
        ----------
        path : Path
            Chemin du fichier à watcher.
        loader : Callable[[Path], Any]
            Fonction qui retourne l'objet chargé (ex. ``_load_json_kb``).
            Ne doit PAS lever en cas de fichier absent : l'appelant est
            responsable de renvoyer une structure vide si nécessaire.
        check_interval_s : float, default 1.0
            Intervalle mini entre deux ``os.stat`` successifs. À 0, on
            stat à chaque ``get`` (précis mais plus coûteux). À 5, on
            accepte jusqu'à 5 s de décalage — plus économe.
        logger : logging.Logger, optional
            Logger à utiliser pour les messages de reload. Default = root.
        """
        self._path = Path(path)
        self._loader = loader
        self._check_interval_s = max(0.0, check_interval_s)
        self._log = logger or logging.getLogger(__name__)
        self._lock = threading.Lock()
        self._value: Any = None
        self._loaded = False
        self._mtime: float = 0.0
        self._last_check: float = 0.0

    # ── API publique ──

    def get(self) -> Any:
        """Retourne la valeur en cache, rechargeant si le fichier a changé."""
        now = time.monotonic()
        # Fast-path : si on a déjà vérifié récemment et que le cache est
        # chargé, on skip le stat. Évite de thrash les I/O sous charge.
        if self._loaded and (now - self._last_check) < self._check_interval_s:
            return self._value

        with self._lock:
            # Double-check locking : un autre thread a peut-être rechargé
            # pendant qu'on attendait le verrou.
            now = time.monotonic()
            if self._loaded and (now - self._last_check) < self._check_interval_s:
                return self._value

            try:
                current_mtime = self._path.stat().st_mtime if self._path.exists() else 0.0
            except OSError:
                current_mtime = 0.0

            self._last_check = now

            if not self._loaded or current_mtime != self._mtime:
                try:
                    self._value = self._loader(self._path)
                    self._mtime = current_mtime
                    self._loaded = True
                    if current_mtime:
                        self._log.info(
                            "[kb_cache] %s rechargé (mtime=%s)",
                            self._path.name,
                            int(current_mtime),
                        )
                except Exception as e:
                    # Le loader doit être robuste : si on arrive ici, c'est
                    # un vrai bug (disk I/O, race condition pendant un
                    # déploiement). On garde la valeur précédente si possible.
                    self._log.error(
                        "[kb_cache] Erreur de reload pour %s : %s",
                        self._path.name, e,
                    )
                    if not self._loaded:
                        # Première charge ratée → on doit quand même renvoyer
                        # quelque chose. Laisser le loader décider (il peut
                        # renvoyer un dict vide).
                        self._value = self._loader(self._path)
                        self._loaded = True
            return self._value

    def invalidate(self) -> None:
        """Force un reload au prochain ``get``."""
        with self._lock:
            self._loaded = False
            self._mtime = 0.0
            self._last_check = 0.0

    @property
    def path(self) -> Path:
        return self._path


# ── Registre global : un cache par fichier KB ──
# Évite qu'un même JSON soit wrappé par plusieurs FileBackedCache concurrents
# (ce qui casserait la cohérence mtime).
_registry: dict[str, FileBackedCache] = {}
_registry_lock = threading.Lock()


def get_cache(
    path: Path,
    loader: Callable[[Path], Any],
    **kwargs,
) -> FileBackedCache:
    """Récupère (ou crée) le cache associé à un fichier."""
    key = str(Path(path).resolve())
    with _registry_lock:
        if key not in _registry:
            _registry[key] = FileBackedCache(path, loader, **kwargs)
        return _registry[key]


def invalidate_all() -> None:
    """Invalide tous les caches enregistrés. Utilisé par ``/api/reload``."""
    with _registry_lock:
        for c in _registry.values():
            c.invalidate()


__all__ = ["FileBackedCache", "get_cache", "invalidate_all"]
