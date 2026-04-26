"""Embeddings sémantiques pour RAG hybride (Sprint 5.2-stack).

Architecture :
- `Embedder` : interface abstraite (embed_documents, embed_query)
- `VoyageEmbedder` : Voyage AI (recommandé Anthropic, qualité top, latence ~30ms)
- `FakeEmbedder` : déterministe basé sur hash, pour tests sans réseau
- `NoOpEmbedder` : retourne None partout — fallback si pas de clé API
- Cache LRU sur `embed_query` : 60-70% hit rate attendu en prod après rodage

Pipeline RAG hybride :
    1. TF-IDF lexical → top-K candidats (rapide, 3 ms)
    2. Si tfidf_norm top-1 > seuil : skip embeddings (économie latence)
    3. Sinon : embedding question (~30 ms) + cosine sim → re-rank top-3
    4. Score final : α · tfidf_norm + (1-α) · cosine_sim

Fallback gracieux :
- Si VOYAGE_API_KEY absent : NoOpEmbedder, RAG TF-IDF seul (comportement Sprint 4.2)
- Si erreur API Voyage : log + fallback sur TF-IDF (latence stable, jamais down)
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
from abc import ABC, abstractmethod
from collections import OrderedDict
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


# ───────────────────────────── Interface ─────────────────────────────


class Embedder(ABC):
    """Interface abstraite pour les fournisseurs d'embeddings."""

    dim: int  # Dimension du vecteur (ex: 1024 pour voyage-3-large)

    @abstractmethod
    async def embed_documents(self, texts: list[str]) -> np.ndarray:
        """Embeddings batch pour les articles. Retourne (N, dim) float32."""

    @abstractmethod
    async def embed_query(self, text: str) -> np.ndarray:
        """Embedding d'une question utilisateur. Retourne (dim,) float32."""

    @property
    def is_active(self) -> bool:
        """True si l'embedder est opérationnel (clé API valide, etc.)."""
        return True


# ───────────────────────────── Implémentations ─────────────────────────────


class NoOpEmbedder(Embedder):
    """Embedder factice — retourne des zéros. Utilisé quand pas de clé API.

    Permet à `retrieval.py` de coder une seule fois le pipeline hybride :
    si is_active=False, le caller skip les embeddings et reste en TF-IDF seul.
    """

    dim = 1

    async def embed_documents(self, texts: list[str]) -> np.ndarray:
        return np.zeros((len(texts), self.dim), dtype=np.float32)

    async def embed_query(self, text: str) -> np.ndarray:
        return np.zeros(self.dim, dtype=np.float32)

    @property
    def is_active(self) -> bool:
        return False


class FakeEmbedder(Embedder):
    """Embedder déterministe basé sur hash — pour les tests unitaires.

    Pas de réseau, pas de clé API. Utile pour valider le pipeline hybride
    sans dépendre de Voyage/OpenAI.
    """

    def __init__(self, dim: int = 64):
        self.dim = dim

    def _hash_to_vec(self, text: str) -> np.ndarray:
        # Hash texte → seed → vecteur normalisé déterministe
        h = hashlib.sha256(text.encode("utf-8")).digest()
        seed = int.from_bytes(h[:4], "big")
        rng = np.random.default_rng(seed)
        v = rng.standard_normal(self.dim).astype(np.float32)
        return v / (np.linalg.norm(v) + 1e-8)

    async def embed_documents(self, texts: list[str]) -> np.ndarray:
        return np.stack([self._hash_to_vec(t) for t in texts])

    async def embed_query(self, text: str) -> np.ndarray:
        return self._hash_to_vec(text)


class VoyageEmbedder(Embedder):
    """Voyage AI (https://docs.voyageai.com/) — recommandé Anthropic.

    Modèles supportés :
    - voyage-3-large (1024 dim, qualité top, ~30ms) ← défaut
    - voyage-3 (1024 dim, 3× moins cher, qualité très bonne)
    - voyage-3-lite (512 dim, plus rapide ~20ms)

    Caractéristiques :
    - Async via httpx (compatibilité avec FastAPI)
    - Retry exponentiel (3 essais)
    - Cache LRU sur embed_query (cache_size=512 par défaut)
    - Batch embed_documents (max 128 textes par appel)
    """

    # Dimensions par modèle (voir docs Voyage)
    _MODEL_DIMS = {
        "voyage-3-large": 1024,
        "voyage-3": 1024,
        "voyage-3-lite": 512,
        "voyage-multilingual-2": 1024,
    }
    _BATCH_SIZE = 16  # Free tier conservateur : batchs petits
    _API_URL = "https://api.voyageai.com/v1/embeddings"
    _MAX_RETRIES = 5
    _INITIAL_BACKOFF = 10.0  # Premier retry après 10s
    _INTER_BATCH_SLEEP = 30.0  # Conservateur : 1 batch / 30s = 2 RPM

    def __init__(self, api_key: str, model: str = "voyage-3-large", *, cache_size: int = 512):
        self.api_key = api_key
        self.model = model
        self.dim = self._MODEL_DIMS.get(model, 1024)
        # OrderedDict comme cache LRU manuel (asyncio-safe)
        self._query_cache: OrderedDict[str, np.ndarray] = OrderedDict()
        self._cache_size = cache_size
        self._cache_hits = 0
        self._cache_misses = 0

    @property
    def is_active(self) -> bool:
        return bool(self.api_key)

    async def _call_api(self, texts: list[str], input_type: str) -> np.ndarray:
        """Appel API Voyage avec retry. input_type ∈ {document, query}."""
        import httpx

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "input": texts,
            "model": self.model,
            "input_type": input_type,
        }

        last_exc: Exception | None = None
        for attempt in range(self._MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(self._API_URL, json=payload, headers=headers)
                    if resp.status_code == 429:
                        # Rate limit : backoff exponentiel large pour free tier
                        wait = self._INITIAL_BACKOFF * (2 ** attempt)
                        logger.warning("[voyage] rate limit, retry in %.0fs (attempt %d/%d)",
                                       wait, attempt + 1, self._MAX_RETRIES)
                        await asyncio.sleep(wait)
                        continue
                    resp.raise_for_status()
                    data = resp.json()
                    vecs = [d["embedding"] for d in data["data"]]
                    return np.array(vecs, dtype=np.float32)
            except (httpx.HTTPError, KeyError, ValueError) as exc:
                last_exc = exc
                if attempt < self._MAX_RETRIES - 1:
                    await asyncio.sleep(self._INITIAL_BACKOFF * (2 ** attempt))
                    continue

        raise RuntimeError(f"Voyage API failed after {self._MAX_RETRIES} retries: {last_exc}")

    async def embed_documents(self, texts: list[str]) -> np.ndarray:
        """Batch indexing au boot. Cf. _BATCH_SIZE pour la taille max.

        Free tier : ~3 RPM, on espace les chunks de _INTER_BATCH_SLEEP secondes.
        Pour 156 articles avec batch=32 = 5 chunks = ~110s de boot (acceptable).
        """
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        chunks = [texts[i:i + self._BATCH_SIZE] for i in range(0, len(texts), self._BATCH_SIZE)]
        results = []
        for i, chunk in enumerate(chunks):
            if i > 0:
                logger.info("[voyage] batch %d/%d : sleeping %ds (free tier RPM)",
                            i + 1, len(chunks), int(self._INTER_BATCH_SLEEP))
                await asyncio.sleep(self._INTER_BATCH_SLEEP)
            vecs = await self._call_api(chunk, input_type="document")
            results.append(vecs)
        return np.vstack(results)

    async def embed_query(self, text: str) -> np.ndarray:
        """Embedding d'une question, avec cache LRU."""
        cache_key = text.strip().lower()
        if cache_key in self._query_cache:
            # Move to end (LRU)
            self._query_cache.move_to_end(cache_key)
            self._cache_hits += 1
            return self._query_cache[cache_key]

        self._cache_misses += 1
        vecs = await self._call_api([text], input_type="query")
        vec = vecs[0]

        self._query_cache[cache_key] = vec
        if len(self._query_cache) > self._cache_size:
            self._query_cache.popitem(last=False)
        return vec

    def cache_stats(self) -> dict[str, Any]:
        """Snapshot pour observabilité (Prometheus, /readyz)."""
        total = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / total if total else 0.0
        return {
            "cache_size": len(self._query_cache),
            "cache_capacity": self._cache_size,
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "hit_rate": round(hit_rate, 3),
        }


# ───────────────────────────── Factory ─────────────────────────────


def make_embedder(api_key: str, model: str = "voyage-3-large") -> Embedder:
    """Factory : retourne un VoyageEmbedder si clé valide, sinon NoOpEmbedder.

    Gère le fallback gracieux : pas de clé = pas d'embeddings, mais l'app
    démarre quand même en mode TF-IDF seul (compat Sprint 4.2).
    """
    if api_key:
        logger.info("[embeddings] Voyage AI activé (modèle: %s)", model)
        return VoyageEmbedder(api_key=api_key, model=model)
    logger.info("[embeddings] VOYAGE_API_KEY absent — fallback TF-IDF seul")
    return NoOpEmbedder()


# ───────────────────────────── Utils similarité ─────────────────────────────


def cosine_similarity_batch(query_vec: np.ndarray, doc_vecs: np.ndarray) -> np.ndarray:
    """Cosine sim entre 1 query et N documents.

    Args:
      query_vec: (dim,) — déjà normalisé OU pas (on normalise ici)
      doc_vecs: (N, dim) — déjà normalisé OU pas

    Returns:
      (N,) array de similarités cosinus dans [-1, 1].
    """
    if query_vec.ndim == 1:
        q = query_vec / (np.linalg.norm(query_vec) + 1e-8)
    else:
        q = query_vec[0] / (np.linalg.norm(query_vec[0]) + 1e-8)
    norms = np.linalg.norm(doc_vecs, axis=1, keepdims=True) + 1e-8
    docs_normed = doc_vecs / norms
    return docs_normed @ q
