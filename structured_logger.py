"""Logger JSONL structuré pour télémétrie locale (Sprint 0.4).

Pourquoi
--------
``observability.py`` gère le monitoring **distant** (Sentry). Ici on pose les
**logs locaux structurés** qui serviront de matière première pour calibrer
les seuils RAG (Sprint 2.2) et benchmarker V1 vs V2 (Sprint 4).

Format
------
Une ligne JSON par événement, écrite dans ``logs/events.jsonl`` (rotation
gérée par ``logrotate`` côté VPS, ou par les outils de log shipping).

Chaque entrée a a minima :
  - ``ts`` : timestamp ISO 8601 UTC
  - ``event`` : nom court de l'événement (ex. ``ask_request``, ``rag_retrieval``)
  - les champs additionnels passés en kwargs

Exploitation typique (post-prod)
-------------------------------
    jq '.score' logs/events.jsonl | datamash min mean median max
    jq 'select(.event == "rag_retrieval") | .latency_ms' logs/events.jsonl
    jq 'select(.event == "ask_request" and .module == "juridique")' logs/events.jsonl

Sécurité
--------
Aucun ``answer`` complet, aucun PII : on log uniquement ``question_hash``
(SHA-256 tronqué) pour pouvoir corréler sans stocker le texte brut.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Lock pour les écritures concurrentes (Gunicorn 8 threads)
_LOG_LOCK = threading.Lock()

# Chemin du fichier de logs — par défaut ``logs/events.jsonl`` à la racine de l'app.
# Override possible via ELISFA_EVENTS_LOG (utile en tests).
_DEFAULT_LOG_FILE = Path(__file__).parent / "logs" / "events.jsonl"


def _events_log_path() -> Path:
    override = os.getenv("ELISFA_EVENTS_LOG")
    if override:
        return Path(override)
    return _DEFAULT_LOG_FILE


def hash_question(question: str) -> str:
    """SHA-256 tronqué (12 chars) — corrélation sans stocker le texte clair."""
    if not question:
        return ""
    return hashlib.sha256(question.encode("utf-8")).hexdigest()[:12]


def log_event(event: str, **fields: Any) -> None:
    """Écrit un événement structuré dans ``logs/events.jsonl``.

    Ne lève jamais d'exception — un échec d'IO ne doit pas casser une requête.
    """
    entry: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "event": event,
    }
    # Filtre les valeurs None pour des logs plus lisibles
    for k, v in fields.items():
        if v is not None:
            entry[k] = v

    line = json.dumps(entry, ensure_ascii=False, default=str)

    try:
        log_file = _events_log_path()
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with _LOG_LOCK:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(line + "\n")
    except Exception as exc:
        # Fallback : on log via logging si l'écriture JSONL échoue (disque plein, perms...)
        logging.getLogger(__name__).warning("[structured_logger] write failed: %s", exc)


__all__ = ["log_event", "hash_question"]
