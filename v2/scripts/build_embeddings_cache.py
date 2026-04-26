"""Indexe les embeddings de chaque KB et écrit le cache disque.

À exécuter UNE FOIS (ou quand la KB change). Tolère le rate-limit du free
tier Voyage en faisant des batchs lents (16 articles, 30s entre chaque).

Pour 156 articles : ~10 chunks × 30s = ~5 minutes.

Une fois le cache écrit dans data/v2/_embeddings_<module>_<model>.npz,
le boot V2 charge en ~50ms (pas d'appel API).

Usage :
  cd v2/
  PYTHONPATH=. ../.venv/bin/python scripts/build_embeddings_cache.py
  # ou avec un module spécifique :
  PYTHONPATH=. ../.venv/bin/python scripts/build_embeddings_cache.py --module formation
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.kb.loader import KBStore  # noqa: E402
from app.rag.embeddings import make_embedder  # noqa: E402
from app.settings import get_settings  # noqa: E402


async def main(modules: list[str]) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s :: %(message)s",
    )
    log = logging.getLogger("build_embeddings_cache")

    settings = get_settings()
    if not settings.voyage_api_key:
        log.error("VOYAGE_API_KEY absent. Ajouter la clé dans .env d'abord.")
        return 1

    embedder = make_embedder(api_key=settings.voyage_api_key, model=settings.voyage_model)
    log.info("Modèle : %s (dim=%d)", settings.voyage_model, embedder.dim)

    data_dir = Path(__file__).resolve().parent.parent / "data" / "v2"
    if not data_dir.exists():
        # Fallback : on est dans v2/, donc data est ../data/v2
        data_dir = Path(__file__).resolve().parent.parent.parent / "data" / "v2"
    log.info("data_dir : %s", data_dir)

    store = KBStore(data_dir=data_dir, modules=tuple(modules), embedder=embedder)

    for module in modules:
        log.info("=== Module %s ===", module)
        t0 = time.time()
        try:
            await store._load_one(module)
            duration = time.time() - t0
            loaded = store._loaded.get(module)
            if loaded and "embeddings" in loaded.index:
                emb = loaded.index["embeddings"]
                cache_path = store._embedding_cache_path(module)
                size_kb = cache_path.stat().st_size / 1024 if cache_path.exists() else 0
                log.info(
                    "✅ %s : %d articles indexés en %.1fs, cache=%s (%.1f KB)",
                    module, emb.shape[0], duration, cache_path.name, size_kb,
                )
            else:
                log.warning("⚠️ %s : pas d'embeddings indexés (rate-limit ?)", module)
        except Exception as exc:  # noqa: BLE001
            log.error("❌ %s : indexation échouée — %s", module, exc)

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--module", action="append",
        help="Module(s) à indexer (défaut : tous les 4)",
    )
    args = parser.parse_args()
    modules = args.module or ["juridique", "formation", "gouvernance", "rh"]
    sys.exit(asyncio.run(main(modules)))
