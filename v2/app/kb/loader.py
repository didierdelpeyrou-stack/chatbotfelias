"""KBStore — chargement + hot-reload des 4 KB V1 (Sprint 3.1).

Cycle de vie :
  1. Boot     : `await store.load_all()` lit les 4 fichiers JSON,
                valide via Pydantic (Sprint 2.3),
                construit l'index TF-IDF (Sprint 2.2),
                stocke (kb, index) en mémoire.
  2. Runtime  : `store.get(module)` retourne (kb_dict, index).
                Hot-reload basé sur mtime — si le fichier a changé,
                on relit + reindexe la base concernée seulement.
  3. Shutdown : pas de cleanup nécessaire (pure mémoire Python).

Thread-safety :
  - On utilise un asyncio.Lock par module pour éviter qu'une requête
    voie un index half-built pendant un reload concurrent.
  - mtime-check est atomique (os.stat), pas de lock nécessaire.
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.kb.schema import KnowledgeBase
from app.kb.validators import KBValidationError, validate_kb_file
from app.rag.embeddings import Embedder
from app.rag.index import build_index

logger = logging.getLogger(__name__)

# Modules supportés — ordre de chargement
DEFAULT_MODULES: tuple[str, ...] = ("juridique", "formation", "gouvernance", "rh")


@dataclass
class LoadedKB:
    """Une KB chargée + son index + métadonnées de fraîcheur."""
    kb: KnowledgeBase
    kb_dict: dict[str, Any]      # format consommé par app.rag.retrieval.search()
    index: dict[str, Any]         # produit par app.rag.index.build_index()
    file_path: Path
    mtime: float
    n_articles: int


class KBStore:
    """Cache en mémoire des KB + hot-reload mtime.

    Usage typique (depuis `lifespan` dans `app/main.py`) :
        store = KBStore(data_dir=Path("../data"))
        await store.load_all()
        app.state.kb_store = store
        ...
        kb_dict, index = await store.get("juridique")
    """

    def __init__(
        self,
        data_dir: Path | str,
        *,
        modules: Iterable[str] = DEFAULT_MODULES,
        embedder: Embedder | None = None,
    ):
        self.data_dir = Path(data_dir)
        self.modules = tuple(modules)
        self.embedder = embedder  # Si None ou is_active=False : pas d'embeddings
        self._loaded: dict[str, LoadedKB] = {}
        self._locks: dict[str, asyncio.Lock] = {m: asyncio.Lock() for m in self.modules}

    # ── Chemin de fichier par module ──
    def _path_for(self, module: str) -> Path:
        return self.data_dir / f"base_{module}.json"

    # ── Chargement initial ──
    async def load_all(self) -> dict[str, int]:
        """Charge toutes les KB déclarées. Renvoie un récap {module: n_articles}.

        Une base manquante ou invalide :
          - log un warning structuré
          - n'apparaît pas dans le résultat
          - ne fait pas planter les autres
        """
        summary: dict[str, int] = {}
        for module in self.modules:
            try:
                loaded = await self._load_one(module)
                summary[module] = loaded.n_articles
                logger.info(
                    "[kb] %s loaded: %d articles, %d unique tokens",
                    module, loaded.n_articles, len(loaded.index["inverted"]),
                )
            except FileNotFoundError as exc:
                logger.warning("[kb] %s skipped (file not found): %s", module, exc)
            except KBValidationError as exc:
                logger.error("[kb] %s skipped (validation failed):\n%s", module, exc)
        return summary

    async def _load_one(self, module: str) -> LoadedKB:
        """Charge une seule KB : valide + indexe. Atomique sous lock.

        Si self.embedder est actif (Sprint 5.2-stack), calcule aussi les
        embeddings sémantiques de tous les articles + les stocke dans index.
        """
        path = self._path_for(module)
        async with self._locks[module]:
            kb = validate_kb_file(path)
            kb_dict = kb.to_v1_dict()
            index = build_index(kb_dict)

            # Sprint 5.2-stack : indexation embeddings si embedder actif
            if self.embedder is not None and self.embedder.is_active:
                await self._index_embeddings(module, kb_dict, index)

            loaded = LoadedKB(
                kb=kb,
                kb_dict=kb_dict,
                index=index,
                file_path=path,
                mtime=path.stat().st_mtime,
                n_articles=kb.n_articles,
            )
            self._loaded[module] = loaded
            return loaded

    # ── Accès avec hot-reload mtime ──
    async def get(self, module: str) -> tuple[dict[str, Any], dict[str, Any]]:
        """Retourne (kb_dict, index) pour le module.

        Vérifie le mtime du fichier — si changé, recharge la base avant
        de retourner. C'est le hot-reload qui permet d'éditer une KB
        sans redémarrer le serveur.

        Raises:
          KeyError : si le module n'a jamais été chargé (et le fichier
                     n'existe pas). Le caller (endpoint) doit retourner
                     un 404 ou 503.
        """
        if module not in self.modules:
            raise KeyError(f"Module inconnu: {module}. Attendu: {list(self.modules)}")

        loaded = self._loaded.get(module)

        # Cas 1 : pas chargé (ou erreur au boot) → tentative de chargement à la demande
        if loaded is None:
            loaded = await self._load_one(module)
            return loaded.kb_dict, loaded.index

        # Cas 2 : check du mtime — hot-reload si le fichier a changé
        try:
            current_mtime = loaded.file_path.stat().st_mtime
        except OSError:
            # Fichier disparu → on garde la version en mémoire mais on log
            logger.warning("[kb] %s : file disappeared, serving cached version", module)
            return loaded.kb_dict, loaded.index

        if current_mtime > loaded.mtime:
            logger.info("[kb] %s : mtime changed, reloading", module)
            loaded = await self._load_one(module)

        return loaded.kb_dict, loaded.index

    # ── Sprint 5.2-stack : indexation embeddings sémantiques ──
    async def _index_embeddings(
        self, module: str, kb_dict: dict[str, Any], index: dict[str, Any],
    ) -> None:
        """Calcule + stocke les embeddings de tous les articles dans index.

        Format ajouté à index :
          - 'embeddings': np.ndarray (N, dim) — embeddings normalisés
          - 'flat_ids': list[(theme_idx, article_idx)] — mapping plat→arborescent

        En cas d'erreur API, on log un warning et on continue sans embeddings
        (fallback gracieux : retrieval.py utilise alors TF-IDF seul).
        """
        if self.embedder is None:
            return

        themes = kb_dict.get("themes", [])
        flat_ids: list[tuple[int, int]] = []
        texts: list[str] = []

        for ti, theme in enumerate(themes):
            for ai, article in enumerate(theme.get("articles", [])):
                # Texte à embedder : titre + champs clés de la réponse.
                # On évite la verbosité totale pour limiter les tokens (et le coût).
                parts = [
                    str(article.get("question_type", "")),
                    " | ".join(article.get("mots_cles", [])[:15]),
                ]
                reponse = article.get("reponse", {})
                for field in ("synthese", "fondement_legal", "fondement_ccn"):
                    val = reponse.get(field)
                    if val:
                        parts.append(str(val)[:800])  # Tronquer à 800 chars/champ
                texts.append("\n".join(p for p in parts if p))
                flat_ids.append((ti, ai))

        if not texts:
            logger.info("[kb.embed] %s : aucun article à indexer", module)
            return

        try:
            t0 = asyncio.get_event_loop().time()
            embeddings = await self.embedder.embed_documents(texts)
            duration = asyncio.get_event_loop().time() - t0
            index["embeddings"] = embeddings
            index["flat_ids"] = flat_ids
            logger.info(
                "[kb.embed] %s : %d articles indexés (dim=%d) en %.2fs",
                module, len(texts), self.embedder.dim, duration,
            )
        except Exception as exc:
            logger.warning(
                "[kb.embed] %s : indexation embeddings échouée (%s) — fallback TF-IDF",
                module, exc,
            )

    # ── Inspection (utile pour /readyz et le mode debug) ──
    def is_loaded(self, module: str) -> bool:
        return module in self._loaded

    def all_loaded(self) -> bool:
        return all(m in self._loaded for m in self.modules)

    def stats(self) -> dict[str, dict[str, Any]]:
        """Snapshot pour /readyz et /metrics — pas d'IO, lecture pure."""
        return {
            module: {
                "n_articles": loaded.n_articles,
                "n_tokens": len(loaded.index["inverted"]),
                "mtime": loaded.mtime,
            }
            for module, loaded in self._loaded.items()
        }
