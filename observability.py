"""Intégration Sentry (optionnelle) pour monitoring d'erreurs distant.

Comportement
------------
Sentry n'est initialisé QUE si la variable d'environnement ``SENTRY_DSN``
est présente. Sinon, ``init_sentry`` est un no-op silencieux — on ne veut
pas que l'absence de cette dépendance affecte le boot en local/CI.

Pourquoi Sentry ?
-----------------
Aujourd'hui, les erreurs 500 sont loggées dans ``logs/chatbot.log`` (après
scrubbing). Pour les détecter, il faut SSH + grep. Sentry :
  - remonte les exceptions en temps réel (notifs email/Slack),
  - dédoublonne les erreurs (pas de spam si 1000 req cassent de la même
    manière),
  - agrège par release (``SENTRY_RELEASE``) pour voir si un déploiement a
    introduit une régression,
  - capture le contexte utilisateur (IP anonymisée) sans fuiter les
    payloads complets (on filtre via ``before_send``).

Config par env
--------------
  - ``SENTRY_DSN`` (requis) : URL projet, format ``https://xxx@sentry.io/NNN``.
  - ``SENTRY_ENVIRONMENT`` (optionnel) : "production" / "staging" / "dev".
  - ``SENTRY_RELEASE`` (optionnel) : tag de release (ex. commit SHA).
  - ``SENTRY_TRACES_SAMPLE_RATE`` (optionnel, default 0.0) : % de transactions
    à échantillonner pour les perfs. 0.0 = pas de tracing (juste les erreurs).
"""

from __future__ import annotations

import logging
import os
import re
from typing import Optional


# Patterns à scrubber dans les events Sentry (doublons avec SecretScrubFilter
# côté logs, mais Sentry fait ses propres captures). Mieux vaut redondant
# qu'une fuite.
_SENTRY_SCRUB_PATTERNS = [
    (re.compile(r"sk-ant-[A-Za-z0-9_\-]+"), "sk-ant-***"),
    (re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]+"), "Bearer ***"),
    (re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"), "***@***"),
]


def _scrub_sentry_event(event, _hint):
    """Hook ``before_send`` : nettoie les secrets avant envoi à Sentry.

    On parcourt les chaînes des ``request.data``, ``extra``, ``breadcrumbs``,
    et ``exception.values[].value``. Les autres champs (stacktrace, stack
    locals) sont laissés tels quels — on assume que le code source ne
    contient pas de secrets en dur (et si c'est le cas, le problème est en
    amont).
    """
    def _scrub(s):
        if not isinstance(s, str):
            return s
        for pat, repl in _SENTRY_SCRUB_PATTERNS:
            s = pat.sub(repl, s)
        return s

    def _walk(obj):
        if isinstance(obj, str):
            return _scrub(obj)
        if isinstance(obj, list):
            return [_walk(x) for x in obj]
        if isinstance(obj, dict):
            return {k: _walk(v) for k, v in obj.items()}
        return obj

    try:
        # Request body : souvent la source n°1 de fuite
        if "request" in event and isinstance(event["request"], dict):
            if "data" in event["request"]:
                event["request"]["data"] = _walk(event["request"]["data"])
            if "query_string" in event["request"]:
                event["request"]["query_string"] = _walk(
                    event["request"]["query_string"]
                )
        # Extras et breadcrumbs
        if "extra" in event:
            event["extra"] = _walk(event["extra"])
        if "breadcrumbs" in event and isinstance(event["breadcrumbs"], dict):
            if "values" in event["breadcrumbs"]:
                event["breadcrumbs"]["values"] = _walk(event["breadcrumbs"]["values"])
        # Exception message
        if "exception" in event and isinstance(event["exception"], dict):
            if "values" in event["exception"]:
                for v in event["exception"]["values"]:
                    if isinstance(v, dict) and "value" in v:
                        v["value"] = _scrub(v["value"])
    except Exception:
        # Ne JAMAIS faire planter Sentry à cause du scrubber
        pass
    return event


def init_sentry(
    *,
    dsn: Optional[str] = None,
    environment: Optional[str] = None,
    release: Optional[str] = None,
    traces_sample_rate: Optional[float] = None,
    logger: Optional[logging.Logger] = None,
) -> bool:
    """Initialise Sentry si un DSN est configuré. Retourne True si actif.

    Tous les paramètres sont lus depuis l'env si non fournis :
      - dsn → ``SENTRY_DSN``
      - environment → ``SENTRY_ENVIRONMENT``
      - release → ``SENTRY_RELEASE``
      - traces_sample_rate → ``SENTRY_TRACES_SAMPLE_RATE``

    Si ``sentry_sdk`` n'est pas installé ou si le DSN est vide, retourne
    False silencieusement (avec un INFO). Pas d'exception — on veut que
    l'app boot même sans Sentry.
    """
    log = logger or logging.getLogger(__name__)

    dsn = dsn or os.getenv("SENTRY_DSN", "").strip()
    if not dsn:
        log.info("[sentry] SENTRY_DSN non défini → monitoring désactivé.")
        return False

    try:
        import sentry_sdk  # type: ignore
        from sentry_sdk.integrations.flask import FlaskIntegration  # type: ignore
        from sentry_sdk.integrations.logging import LoggingIntegration  # type: ignore
    except ImportError:
        log.warning(
            "[sentry] SENTRY_DSN est défini mais `sentry-sdk[flask]` n'est "
            "pas installé. `pip install sentry-sdk[flask]>=1.40`."
        )
        return False

    sample_rate = traces_sample_rate
    if sample_rate is None:
        try:
            sample_rate = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.0"))
        except ValueError:
            sample_rate = 0.0

    sentry_sdk.init(
        dsn=dsn,
        environment=environment or os.getenv("SENTRY_ENVIRONMENT", "production"),
        release=release or os.getenv("SENTRY_RELEASE"),
        traces_sample_rate=sample_rate,
        integrations=[
            FlaskIntegration(),
            # Capture les logs WARNING+ comme breadcrumbs, ERROR+ comme events
            LoggingIntegration(
                level=logging.INFO,
                event_level=logging.ERROR,
            ),
        ],
        # Scrub avant envoi — cf. _scrub_sentry_event
        before_send=_scrub_sentry_event,
        # Désactive l'envoi d'IP utilisateur (RGPD)
        send_default_pii=False,
    )
    log.info(
        "[sentry] Initialisé (env=%s, traces_rate=%.2f).",
        environment or os.getenv("SENTRY_ENVIRONMENT", "production"),
        sample_rate,
    )
    return True


__all__ = ["init_sentry"]
