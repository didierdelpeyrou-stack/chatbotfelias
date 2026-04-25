"""Writer asynchrone JSONL pour les feedbacks (Sprint 4.3).

Cohabite avec V1 (`structured_logger.py` à la racine) :
  - V1 écrit dans `logs/feedback.jsonl` (Flask, threading.Lock)
  - V2 écrit dans le même fichier mais via asyncio.Lock (FastAPI async)

Hot-reload-safe : le path est calculé à chaque écriture (override via env
`ELISFA_FEEDBACK_LOG`), pas mis en cache au boot.

Concurrence
-----------
On utilise `asyncio.Lock` pour sérialiser les writes côté event loop
ET on délègue le fopen+write à `asyncio.to_thread()` pour ne pas bloquer
la loop sur un disque lent. Le lock garantit qu'une ligne JSONL n'est
jamais entrelacée avec une autre.

Sécurité
--------
- Question hashée si non fournie (sha256 tronqué, identique à V1)
- Tronquage des champs longs déjà fait dans `FeedbackEntry.from_request`
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
from pathlib import Path

from app.feedback.schema import FeedbackEntry, FeedbackRequest

logger = logging.getLogger(__name__)

# Sérialise les writes async (1 process FastAPI, plusieurs requêtes concurrentes)
_FEEDBACK_LOCK = asyncio.Lock()

# Path par défaut : `logs/feedback.jsonl` à la racine du repo (cohabitation V1/V2).
# v2/app/feedback/logger.py → parent.parent.parent.parent = chatbot_elisfa/
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_DEFAULT_LOG_FILE = _REPO_ROOT / "logs" / "feedback.jsonl"


def _feedback_log_path() -> Path:
    """Path du fichier feedback (override env `ELISFA_FEEDBACK_LOG` pour tests)."""
    override = os.getenv("ELISFA_FEEDBACK_LOG")
    if override:
        return Path(override)
    return _DEFAULT_LOG_FILE


def hash_question(question: str) -> str:
    """SHA-256 tronqué — identique à V1 pour pouvoir corréler les datasets."""
    if not question:
        return ""
    return hashlib.sha256(question.encode("utf-8")).hexdigest()[:12]


def _write_line_sync(path: Path, line: str) -> None:
    """Append blocking (appelé via asyncio.to_thread)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")


async def append_feedback(req: FeedbackRequest) -> FeedbackEntry:
    """Persiste un feedback validé. Retourne l'entrée écrite (utile pour tests).

    Ne lève jamais d'exception métier — un échec d'IO log un warning et
    propage l'exception (l'endpoint la convertit en 500).
    """
    qhash = req.question_hash or hash_question(req.question)
    entry = FeedbackEntry.from_request(req, question_hash=qhash)
    line = json.dumps(entry.model_dump(), ensure_ascii=False, default=str)

    path = _feedback_log_path()
    async with _FEEDBACK_LOCK:
        try:
            await asyncio.to_thread(_write_line_sync, path, line)
        except OSError as exc:
            logger.error("[feedback] write failed (path=%s): %s", path, exc)
            raise
    return entry


def read_all_feedbacks() -> list[dict]:
    """Lit toutes les entrées du JSONL. Retourne [] si fichier absent.

    Usage : endpoint /api/feedback/stats. Pas async — on lit en bloc,
    rapide tant que le volume est raisonnable (< 100k lignes).
    """
    path = _feedback_log_path()
    if not path.exists():
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                logger.warning("[feedback] skipping malformed line in %s", path)
                continue
    return out
