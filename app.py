"""
ELISFA — Chatbot Juridique CCN ALISFA
Serveur Flask + API Claude Haiku + Prise de RDV + Webhooks MCP
"""
import hashlib
import hmac
import json
import logging
import os
import re
import smtplib
import threading
import uuid
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from html import escape as html_escape
from pathlib import Path
from functools import wraps

# Charger le .env AVANT toute config
from dotenv import load_dotenv
load_dotenv(override=True)

from flask import Flask, request, jsonify, render_template, send_from_directory, abort
from flask_cors import CORS

# ── Configuration ──
from config import *

# ── Calculateurs juridiques déterministes (pour la fonction juridique_calcul) ──
# Ces outils extraient l'arithmétique du prompt pour l'exécuter en Python testé.
# Voir utils/calculs_juridiques.py + tests/test_calculs_juridiques.py.
from utils.tools_juridique import TOOLS_CALCUL, execute_tool_call
from utils.guide_questions import WIZARD_HINTS_JURIDIQUE, get_wizard_hints

# ── Modules de sécurité / validation / observabilité (pack weekend) ──
# Chacun est indépendant : si la dépendance pip manque, on dégrade
# gracieusement (pydantic absent → retour à la validation manuelle existante).
try:
    from validation import (
        AskRequest, RdvRequest, AppelRequest, EmailJuristeRequest,
        FeedbackRequest, format_validation_error,
    )
    from pydantic import ValidationError as _PydanticValidationError
    _PYDANTIC_OK = True
except ImportError as _e:
    logging.warning("[validation] Pydantic absent (%s) — validation legacy.", _e)
    _PYDANTIC_OK = False
    _PydanticValidationError = Exception  # type: ignore

from security import (
    admin_auth_configured,
    verify_admin_credentials,
    warn_if_legacy_admin,
)
from kb_cache import get_cache, invalidate_all as _kb_invalidate_all
from observability import init_sentry

LOG_DIR.mkdir(exist_ok=True)

# ── Chargement des guides théoriques / méthodologiques ──
# Ces guides servent de RÉFÉRENTIEL pour les fonctions Diagnostic RH, Étude RH
# et les questions de gouvernance. Ils sont injectés dans le system prompt
# afin que Claude puisse :
#  1) expliquer la PARTIE THÉORIQUE (cadres, auteurs, concepts)
#  2) GUIDER les démarches de diagnostic / conseil étape par étape
_SOURCES_EXT_DIR = Path(__file__).parent / "data" / "sources_ext"

def _load_guide(filename):
    path = _SOURCES_EXT_DIR / filename
    try:
        return path.read_text(encoding="utf-8")
    except Exception as e:
        logging.warning(f"Guide non chargé ({filename}): {e}")
        return ""

GUIDE_CAS_RH = _load_guide("guide_cas_rh.txt")           # méthodologie analyse de cas RH (Garbe)
GUIDE_DIAG_ASSO = _load_guide("guide_diag.txt")          # guide pratique diagnostic associatif

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = SECRET_KEY

# ── Taille max des requêtes entrantes ──
# Protège contre les payloads géants (DoS par épuisement RAM). Le champ
# `document` de /api/ask est plafonné à 120 KB ; on laisse 16 MB de marge
# pour l'ensemble du JSON (question + document + history + context).
app.config["MAX_CONTENT_LENGTH"] = int(
    os.getenv("MAX_CONTENT_LENGTH_BYTES", str(16 * 1024 * 1024))
)

# ── CORS ──
# Par défaut, on restreint aux origines officielles (prod + localhost dev).
# L'ancien défaut `*` est un risque CSRF — on bascule sur la liste explicite.
_default_origins = "https://felias-reseau-eli2026.duckdns.org,http://localhost:5000,http://127.0.0.1:5000"
_cors_origins_env = os.environ.get("CORS_ORIGINS", _default_origins)
if _cors_origins_env.strip() == "*":
    logging.warning(
        "[security] CORS_ORIGINS='*' détecté — en prod, préférez une liste explicite."
    )
CORS_ORIGINS_EFFECTIVE = [o.strip() for o in _cors_origins_env.split(",") if o.strip()]
CORS(app, origins=CORS_ORIGINS_EFFECTIVE)

# ── Auth basique pour l'admin ──
# Deux modes supportés :
#   1. ``ADMIN_PASS_HASH`` (recommandé) : hash bcrypt — le mot de passe
#      n'existe jamais en clair dans l'env ni dans la mémoire du process.
#      Générer avec `python scripts/generate_admin_hash.py`.
#   2. ``ADMIN_PASS`` (legacy) : mot de passe en clair, comparaison hmac.
#      Conservé pour ne pas casser les déploiements existants — un warning
#      est loggé tant qu'il est défini.
# Si aucun des deux n'est défini, les endpoints admin renvoient 401 (pas de
# backdoor possible). L'ancien défaut 'elisfa2026' codé en dur est supprimé.
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS_HASH = os.getenv("ADMIN_PASS_HASH")  # bcrypt $2b$... ou None
ADMIN_PASS = os.getenv("ADMIN_PASS")  # clear text legacy, ou None

if not admin_auth_configured(ADMIN_PASS_HASH, ADMIN_PASS):
    logging.warning(
        "[security] Ni ADMIN_PASS_HASH ni ADMIN_PASS défini — les endpoints "
        "admin (/api/stats, /admin, /api/rdv, /api/appels) sont désactivés. "
        "Définissez ADMIN_PASS_HASH (recommandé, via scripts/generate_admin_hash.py) "
        "ou ADMIN_PASS (legacy) pour y accéder."
    )
warn_if_legacy_admin(logging.getLogger(), bool(ADMIN_PASS_HASH), bool(ADMIN_PASS))


def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Pas de credentials configurés → toujours 401 (pas de backdoor)
        if not admin_auth_configured(ADMIN_PASS_HASH, ADMIN_PASS):
            return ("Administration désactivée (ADMIN_PASS/ADMIN_PASS_HASH non configuré).",
                    401, {"WWW-Authenticate": 'Basic realm="Admin ELISFA"'})
        auth = request.authorization
        if not auth:
            return ("Authentification requise", 401,
                    {"WWW-Authenticate": 'Basic realm="Admin ELISFA"'})
        ok = verify_admin_credentials(
            username=auth.username or "",
            password=auth.password or "",
            expected_user=ADMIN_USER,
            hashed_password=ADMIN_PASS_HASH,
            plain_password=ADMIN_PASS,
        )
        if not ok:
            return ("Authentification requise", 401,
                    {"WWW-Authenticate": 'Basic realm="Admin ELISFA"'})
        return f(*args, **kwargs)
    return decorated


# ── Handlers d'erreurs HTTP ──
# Retourne du JSON propre au lieu des pages d'erreur HTML par défaut de Flask,
# pour que le frontend puisse parser `errData.error` uniformément.
@app.errorhandler(413)
def _handle_request_too_large(_e):
    max_mb = app.config.get("MAX_CONTENT_LENGTH", 0) // (1024 * 1024)
    return jsonify({
        "error": f"Requête trop volumineuse (max ~{max_mb} Mo). "
                 f"Réduisez la taille du document joint."
    }), 413


@app.errorhandler(429)
def _handle_rate_limited(_e):
    return jsonify({"error": "Trop de requêtes. Veuillez patienter."}), 429

# ── Logging : rotation par taille + scrub des secrets ──
# basicConfig écrit dans un fichier qui grossit indéfiniment. Avec plusieurs
# workers gunicorn + plusieurs mois en prod, ça atteint facilement le Go.
# RotatingFileHandler : rotation automatique à 10 Mo, on garde 5 archives →
# ~60 Mo max. Évite la saturation disque sans toucher aux call-sites (logging.
# info/warning/error restent inchangés).
from logging.handlers import RotatingFileHandler as _RotatingFileHandler


class _SecretScrubFilter(logging.Filter):
    """Masque les secrets / PII dans les messages de log.

    Motivation : un log peut contenir une réponse d'API, une requête frontend,
    un traceback avec en-têtes HTTP, etc. Ces chaînes peuvent inclure des
    clés Anthropic (``sk-ant-…``), des tokens Bearer, ou des emails d'adhérents.
    Si les logs fuitent (archive, backup, grep imprudent), on ne veut pas que
    ces secrets soient lisibles en clair.

    Patterns masqués :
      - Clés Anthropic : ``sk-ant-[a-zA-Z0-9_-]+`` → ``sk-ant-***``
      - Tokens Bearer : ``Bearer <token>`` → ``Bearer ***``
      - Emails : ``foo@bar.com`` → ``***@***``

    On applique le filtre à ``record.msg`` ET à ``record.args`` pour couvrir
    à la fois ``logging.info("message brut")`` et ``logging.info("clé=%s", k)``.
    """

    _PATTERNS = [
        (re.compile(r"sk-ant-[A-Za-z0-9_\-]+"), "sk-ant-***"),
        (re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]+"), "Bearer ***"),
        (re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"), "***@***"),
    ]

    @classmethod
    def _scrub(cls, value):
        if not isinstance(value, str):
            return value
        for pattern, replacement in cls._PATTERNS:
            value = pattern.sub(replacement, value)
        return value

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            if isinstance(record.msg, str):
                record.msg = self._scrub(record.msg)
            if record.args:
                if isinstance(record.args, dict):
                    record.args = {k: self._scrub(v) for k, v in record.args.items()}
                else:
                    record.args = tuple(self._scrub(a) for a in record.args)
        except Exception:
            # Ne jamais bloquer une ligne de log à cause du filtre
            pass
        return True


_log_handler = _RotatingFileHandler(
    filename=str(LOG_DIR / "chatbot.log"),
    maxBytes=10 * 1024 * 1024,  # 10 Mo
    backupCount=5,
    encoding="utf-8",
)
_log_handler.setFormatter(
    logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
)
_log_handler.addFilter(_SecretScrubFilter())
_root_logger = logging.getLogger()
_root_logger.setLevel(logging.INFO)
# Le filtre doit aussi couvrir les handlers console / tiers (gunicorn, flask).
_root_logger.addFilter(_SecretScrubFilter())
# Si un handler identique existe déjà (reload à chaud du module), le remplacer
for _h in list(_root_logger.handlers):
    _root_logger.removeHandler(_h)
_root_logger.addHandler(_log_handler)

# ── Sentry (optionnel) ──
# Initialisé APRÈS le logging pour que l'intégration Logging capte nos
# messages formatés (avec le scrubber). No-op si SENTRY_DSN absent.
init_sentry(logger=_root_logger)

# ── Charger une base de connaissances JSON ──
# Helper unifié : factorise les 4 loaders précédents (juridique / formation /
# gouvernance / RH). Valide le schéma minimal (clé "themes" sur une liste) et
# retourne un objet vide mais structuré en cas d'erreur — le chatbot tourne
# toujours (mode IA seul) au lieu de crasher au démarrage.
_EMPTY_KB = {"themes": []}

def _load_json_kb(filename, critical=False):
    """Charge DATA_DIR/filename et valide le schéma KB.

    critical=True → log LEVEL=ERROR si absent (base juridique = obligatoire).
    critical=False → LEVEL=WARNING (formation / gouvernance / RH = optionnel,
    le module tournera en mode IA seul si le fichier manque).

    Valide :
      - JSON bien formé
      - racine = dict
      - clé "themes" présente et list (sinon corrige à [])

    Retourne toujours un dict avec au moins {"themes": [...]} — jamais None.
    """
    path = DATA_DIR / filename
    log_level = logging.ERROR if critical else logging.WARNING
    if not path.exists():
        logging.log(log_level, "%s introuvable (%s).", filename,
                    "base requise" if critical else "mode IA seul")
        return dict(_EMPTY_KB)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        logging.error("JSON invalide dans %s : %s", filename, e)
        return dict(_EMPTY_KB)
    except (IOError, OSError) as e:
        logging.error("Erreur lecture %s : %s", filename, e)
        return dict(_EMPTY_KB)
    # Validation schéma minimal
    if not isinstance(data, dict):
        logging.error("%s : racine JSON doit être un objet, trouvé %s",
                      filename, type(data).__name__)
        return dict(_EMPTY_KB)
    themes = data.get("themes")
    if not isinstance(themes, list):
        logging.warning("%s : clé 'themes' manquante ou invalide, initialisée à [].",
                        filename)
        data["themes"] = []
    return data

# ── Cache KB avec invalidation mtime (fix 9) ──
# Chaque KB est wrappée dans un FileBackedCache : si le JSON change sur disque,
# le prochain ``get()`` recharge automatiquement. Évite de rebooter le container
# ou de devoir taper ``POST /api/reload`` à chaque correction éditoriale.
# ``refresh_kbs_if_changed()`` est appelé en tête des endpoints critiques
# (/api/ask, /api/knowledge, etc.) pour propager les modifs dans les globales.
_KB_FILES = {
    "KB": ("base_juridique.json", True),
    "KB_FORMATION": ("base_formation.json", False),
    "KB_GOUVERNANCE": ("base_gouvernance.json", False),
    "KB_RH": ("base_rh.json", False),
}


def _make_kb_loader(critical: bool):
    """Closure loader pour FileBackedCache (signature loader(path))."""
    def _loader(path):
        return _load_json_kb(path.name, critical=critical)
    return _loader


_kb_caches = {
    name: get_cache(DATA_DIR / fname, _make_kb_loader(crit))
    for name, (fname, crit) in _KB_FILES.items()
}


def refresh_kbs_if_changed():
    """Synchronise les globales ``KB`` / ``KB_*`` avec les fichiers on-disk.

    - O(1) si aucun fichier n'a bougé (juste 4 ``os.stat``).
    - Si ``base_juridique.json`` a changé, rebuild son index inversé.
    - Idem pour les autres KBs (formation/gouvernance/rh) qui ont aussi
      un index TF-IDF séparé.

    Safe à appeler en concurrence : ``FileBackedCache`` protège ses reloads
    par un verrou par fichier.
    """
    global KB, KB_FORMATION, KB_GOUVERNANCE, KB_RH
    prev_ids = (id(KB), id(KB_FORMATION), id(KB_GOUVERNANCE), id(KB_RH)) \
        if "KB" in globals() else (None, None, None, None)
    KB = _kb_caches["KB"].get()
    KB_FORMATION = _kb_caches["KB_FORMATION"].get()
    KB_GOUVERNANCE = _kb_caches["KB_GOUVERNANCE"].get()
    KB_RH = _kb_caches["KB_RH"].get()
    new_ids = (id(KB), id(KB_FORMATION), id(KB_GOUVERNANCE), id(KB_RH))
    # Si au moins une KB a été rechargée, on rebuild l'index de celle(s)-là.
    # ``_build_kb_index`` est défini plus bas — protégé par un try pour éviter
    # un NameError au premier appel (module-level init avant définition).
    if prev_ids != new_ids and "_build_kb_index" in globals():
        names = ["KB", "KB_FORMATION", "KB_GOUVERNANCE", "KB_RH"]
        for i, kb_obj in enumerate((KB, KB_FORMATION, KB_GOUVERNANCE, KB_RH)):
            if prev_ids[i] != new_ids[i]:
                try:
                    _build_kb_index(kb_obj)
                    logging.info("[kb_cache] Index reconstruit pour %s", names[i])
                except Exception as _e:
                    logging.error("[kb_cache] Rebuild index échoué pour %s : %s",
                                  names[i], _e)


# Chargement initial (appel direct : les globales sont nues ici)
KB = _kb_caches["KB"].get()
KB_FORMATION = _kb_caches["KB_FORMATION"].get()
KB_GOUVERNANCE = _kb_caches["KB_GOUVERNANCE"].get()
KB_RH = _kb_caches["KB_RH"].get()

# ── Charger / sauvegarder les RDV ──
RDV_FILE = DATA_DIR / "rendez_vous.json"

def load_rdv():
    if RDV_FILE.exists():
        try:
            with open(RDV_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logging.error(f"Erreur lecture {RDV_FILE}: {e}")
    return []

def save_rdv(rdvs):
    with open(RDV_FILE, "w", encoding="utf-8") as f:
        json.dump(rdvs, f, ensure_ascii=False, indent=2)

# ── Charger / sauvegarder les emails juriste ──
EMAILS_FILE = DATA_DIR / "emails_juriste.json"

def load_emails():
    if EMAILS_FILE.exists():
        try:
            with open(EMAILS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logging.error(f"Erreur lecture {EMAILS_FILE}: {e}")
    return []

def save_emails(emails):
    with open(EMAILS_FILE, "w", encoding="utf-8") as f:
        json.dump(emails, f, ensure_ascii=False, indent=2)

# ── Client Anthropic ──
# Client singleton pour bénéficier du pool de connexions HTTP et du cache interne.
# Le SDK applique déjà un retry exponentiel automatique (max_retries=2 par défaut)
# sur 408/409/429/5xx.
_anthropic_client = None
_anthropic_client_lock = threading.Lock()

def get_client():
    global _anthropic_client
    if not ANTHROPIC_API_KEY:
        return None
    if _anthropic_client is None:
        with _anthropic_client_lock:
            if _anthropic_client is None:
                from anthropic import Anthropic
                # max_retries=3 : un peu plus agressif que le défaut (2) pour tolérer
                # les pics 429 du côté Anthropic. timeout géré par appel.
                _anthropic_client = Anthropic(
                    api_key=ANTHROPIC_API_KEY,
                    max_retries=3,
                )
    return _anthropic_client

# ── Métriques agrégées des appels Claude ──
# Compteurs cumulés depuis le démarrage du process. Exposés via /api/health.
# Thread-safe via _claude_metrics_lock.
_claude_metrics = {
    "calls_total": 0,
    "calls_ok": 0,
    "calls_err": 0,
    "errors_by_type": {},
    "cache_read_tokens": 0,
    "cache_creation_tokens": 0,
    "input_tokens": 0,
    "output_tokens": 0,
}
_claude_metrics_lock = threading.Lock()

def _record_claude_usage(usage):
    """Extrait les métriques de usage d'une response Claude et les cumule.
    usage est un objet avec les attributs: input_tokens, output_tokens,
    cache_read_input_tokens, cache_creation_input_tokens (les 2 derniers = 0 si cache off).
    """
    if usage is None:
        return
    with _claude_metrics_lock:
        _claude_metrics["input_tokens"] += int(getattr(usage, "input_tokens", 0) or 0)
        _claude_metrics["output_tokens"] += int(getattr(usage, "output_tokens", 0) or 0)
        _claude_metrics["cache_read_tokens"] += int(getattr(usage, "cache_read_input_tokens", 0) or 0)
        _claude_metrics["cache_creation_tokens"] += int(getattr(usage, "cache_creation_input_tokens", 0) or 0)

def _record_claude_error(exc_type_name):
    with _claude_metrics_lock:
        _claude_metrics["calls_err"] += 1
        _claude_metrics["errors_by_type"][exc_type_name] = \
            _claude_metrics["errors_by_type"].get(exc_type_name, 0) + 1

def _record_claude_ok():
    with _claude_metrics_lock:
        _claude_metrics["calls_total"] += 1
        _claude_metrics["calls_ok"] += 1

def get_claude_metrics_snapshot():
    """Copie immutable des métriques courantes (pour /api/health)."""
    with _claude_metrics_lock:
        snap = dict(_claude_metrics)
        snap["errors_by_type"] = dict(snap["errors_by_type"])
        total_input = snap["input_tokens"] + snap["cache_read_tokens"] + snap["cache_creation_tokens"]
        snap["cache_hit_ratio"] = (
            round(snap["cache_read_tokens"] / total_input, 4)
            if total_input > 0 else 0.0
        )
    return snap

# ── Exceptions Anthropic typées (import paresseux, après get_client) ──
def _anthropic_exceptions():
    """Retourne le tuple (RateLimitError, APIStatusError, APIConnectionError, APIError).
    Import paresseux pour éviter une dépendance dure au top du module si
    l'API key n'est pas configurée.
    """
    try:
        from anthropic import (
            RateLimitError,
            APIStatusError,
            APIConnectionError,
            APIError,
        )
        return RateLimitError, APIStatusError, APIConnectionError, APIError
    except ImportError:
        return tuple()

def call_claude(client, **kwargs):
    """Wrapper unique autour de client.messages.create().

    Bénéfices :
      - exception typée → HTTP status adapté côté appelant
      - métriques cache (cache_read/creation) cumulées automatiquement
      - un seul point de log pour diagnostiquer les soucis

    Lève RuntimeError avec un code HTTP suggéré en attribut .http_status.
    """
    if client is None:
        err = RuntimeError("Client Claude non configuré.")
        err.http_status = 503
        raise err

    exc_classes = _anthropic_exceptions()
    RateLimitError = exc_classes[0] if exc_classes else None
    APIConnectionError = exc_classes[2] if len(exc_classes) >= 3 else None
    APIStatusError = exc_classes[1] if len(exc_classes) >= 2 else None

    try:
        response = client.messages.create(**kwargs)
        _record_claude_ok()
        u = getattr(response, "usage", None)
        _record_claude_usage(u)
        if u is not None:
            logging.info(
                "[claude.usage] in=%s out=%s cache_read=%s cache_write=%s",
                getattr(u, "input_tokens", 0),
                getattr(u, "output_tokens", 0),
                getattr(u, "cache_read_input_tokens", 0),
                getattr(u, "cache_creation_input_tokens", 0),
            )
        return response
    except Exception as e:  # noqa: BLE001
        exc_name = type(e).__name__
        _record_claude_error(exc_name)
        # Déterminer un code HTTP suggéré
        if RateLimitError and isinstance(e, RateLimitError):
            http_status = 429
            msg = "Trop de requêtes Claude. Réessayez dans quelques secondes."
        elif APIConnectionError and isinstance(e, APIConnectionError):
            http_status = 503
            msg = "Connexion Claude indisponible. Réessayez."
        elif APIStatusError and isinstance(e, APIStatusError):
            status = getattr(e, "status_code", 500)
            http_status = 503 if status >= 500 else 502
            msg = f"Erreur API Claude ({status})."
        else:
            http_status = 500
            msg = "Erreur de connexion au modèle IA. Veuillez réessayer."
        logging.error(f"[call_claude] {exc_name}: {e}")
        wrapped = RuntimeError(msg)
        wrapped.http_status = http_status
        wrapped.original = e
        raise wrapped from e

# Seuil empirique mesuré sur claude-haiku-4-5 : en dessous de ~4096 tokens
# d'input, le cache_control est silencieusement ignoré par l'API (pas d'erreur
# mais cache_creation_input_tokens = 0). On estime par 3.0 chars/token pour
# le français (conservateur), soit 12288 chars ≈ 4096 tokens minimum.
# Si le bloc stable est sous ce seuil, on n'envoie pas cache_control — ça
# évite l'overhead inutile et garde le code simple côté appel.
_CACHE_MIN_CHARS_HAIKU = 12288

def build_system_blocks(base_prompt, dynamic_suffix):
    """Construit la liste de blocs system pour bénéficier du prompt caching.

    Le bloc 1 (base_prompt) est stable pour une combinaison (module, function_id)
    donnée → cachable (~90% d'économie sur les réutilisations dans la fenêtre
    de 5 min). Le bloc 2 contient la personnalisation + contexte utilisateur.

    IMPORTANT : le prompt caching Anthropic exige un préfixe strictement
    identique — toute modif du bloc 1 (timestamp, ordre JSON non déterministe,
    etc.) invalide tout ce qui suit.

    Le minimum cacheable pour Haiku 4.5 est ~4096 tokens (mesuré empiriquement).
    Si le bloc stable est plus court, cache_control est omis pour ne pas
    envoyer un marqueur inutile.
    """
    should_cache = len(base_prompt) >= _CACHE_MIN_CHARS_HAIKU
    base_block = {"type": "text", "text": base_prompt}
    if should_cache:
        base_block["cache_control"] = {"type": "ephemeral"}
    blocks = [base_block]
    if dynamic_suffix:
        blocks.append({"type": "text", "text": dynamic_suffix})
    return blocks

# ── Rate Limiter simple (en mémoire) ──
# Thread-safe : avec gunicorn --threads 8, plusieurs requêtes lisent/écrivent
# simultanément ce dict → race conditions sans verrou. Un simple threading.Lock
# suffit vu la granularité (quelques opérations par requête).
_rate_store: dict = {}
_rate_lock = threading.Lock()
# Purge périodique : évite l'accumulation de clés IP jamais revues.
_rate_last_gc = [datetime.now()]
_RATE_GC_INTERVAL_S = 300  # nettoyage global toutes les 5 minutes

def check_rate_limit(ip):
    now = datetime.now()
    with _rate_lock:
        # GC global périodique : supprime les IPs dont toutes les entrées > 1h
        if (now - _rate_last_gc[0]).total_seconds() > _RATE_GC_INTERVAL_S:
            stale = [
                k for k, ts in _rate_store.items()
                if not ts or (now - ts[-1]).total_seconds() > 3600
            ]
            for k in stale:
                _rate_store.pop(k, None)
            _rate_last_gc[0] = now

        ts_list = _rate_store.setdefault(ip, [])
        # Nettoyer les anciennes entrées (> 1h) pour cette IP
        ts_list = [t for t in ts_list if (now - t).total_seconds() < 3600]
        # Vérifier par minute
        last_minute = [t for t in ts_list if (now - t).total_seconds() < 60]
        if len(last_minute) >= RATE_LIMIT_PER_MINUTE:
            _rate_store[ip] = ts_list
            return False, "Trop de requêtes. Veuillez patienter une minute."
        if len(ts_list) >= RATE_LIMIT_PER_HOUR:
            _rate_store[ip] = ts_list
            return False, "Limite horaire atteinte. Veuillez réessayer plus tard."
        ts_list.append(now)
        _rate_store[ip] = ts_list
        return True, ""

# ── Validation des entrées ──
def validate_email(email):
    return bool(re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email))

def validate_phone(phone):
    cleaned = re.sub(r'[\s\-\.\(\)\+]', '', phone)
    return bool(re.match(r'^\d{6,15}$', cleaned))

def validate_contact_fields(data, require_sujet=False):
    """Valide les champs de contact communs. Retourne (ok, error_msg)."""
    nom = data.get("nom", "").strip()
    email = data.get("email", "").strip()
    tel = data.get("telephone", "").strip()
    if not nom or len(nom) < 2:
        return False, "Le nom est requis (2 caractères minimum)."
    if len(nom) > 200:
        return False, "Le nom est trop long (200 caractères max)."
    if not email or not validate_email(email):
        return False, "Adresse email invalide."
    if not tel or not validate_phone(tel):
        return False, "Numéro de téléphone invalide."
    if require_sujet:
        sujet = data.get("sujet", "").strip()
        if not sujet:
            return False, "Le sujet est requis."
        if len(sujet) > 500:
            return False, "Le sujet est trop long (500 caractères max)."
    return True, ""

# ── Moteur de recherche local (TF-IDF simplifié + index inversé) ──
STOP_WORDS = set("le la les de du des un une en au aux et ou est ce que qui dans par pour sur avec son sa ses leur leurs cette ces tout tous toute toutes je tu il elle nous vous ils elles mon ma mes ton ta tes ne pas plus très bien aussi comme comment combien quel quelle quels quelles".split())

def tokenize(text):
    text = text.lower()
    text = re.sub(r"[''']", " ", text)
    text = re.sub(r"[^\w\sàâäéèêëïîôùûüÿçœæ-]", " ", text)
    tokens = [t for t in text.split() if len(t) > 1 and t not in STOP_WORDS]
    return tokens

def score_article(question_tokens, article):
    """Score legacy (conservé pour compat tests / KB sans index).

    Utilise boost fixe +3 sur match exact, +1 sur sous-chaîne, +2 sur
    question_type. search_knowledge_base() utilise maintenant un index
    inversé avec pondération IDF quand disponible ; cette fonction reste
    pour le fallback.
    """
    keywords = [k.lower() for k in article.get("mots_cles", [])]
    score = 0
    for kw in keywords:
        kw_tokens = tokenize(kw)
        for kt in kw_tokens:
            if kt in question_tokens:
                score += 3
            for qt in question_tokens:
                if kt in qt or qt in kt:
                    score += 1
    qt_text = article.get("question_type", "").lower()
    for qt in question_tokens:
        if qt in qt_text:
            score += 2
    return score

# ── Index inversé pour accélérer la recherche ──
# Build once au chargement d'une KB ; sauvé dans kb["_index"] pour éviter
# d'itérer tous les articles à chaque requête.
#   {token → [{"theme_idx": i, "article_idx": j, "tf": float}, ...]}
# Plus idf par token : log(N / df) où df = articles contenant le token.
import math as _math

def _build_kb_index(kb):
    """Construit un index inversé {token: [postings]} + stats IDF.

    Posting = (theme_idx, article_idx, tf_local) — tf_local est la
    fréquence du token dans l'article (mots_cles + question_type).
    Appelé une fois au chargement. Coût amorti sur toutes les requêtes.
    """
    index = {}
    n_articles = 0
    df = {}  # token -> document frequency
    themes = kb.get("themes", [])
    for t_idx, theme in enumerate(themes):
        for a_idx, article in enumerate(theme.get("articles", [])):
            n_articles += 1
            # Tokens d'indexation : mots_cles + question_type
            text_blobs = [" ".join(article.get("mots_cles", []))]
            qt = article.get("question_type")
            if qt:
                text_blobs.append(qt)
            toks = tokenize(" ".join(text_blobs))
            tf_local = {}
            for tok in toks:
                tf_local[tok] = tf_local.get(tok, 0) + 1
            for tok, tf in tf_local.items():
                index.setdefault(tok, []).append((t_idx, a_idx, tf))
                df[tok] = df.get(tok, 0) + 1
    idf = {
        tok: _math.log(1 + n_articles / (1 + d))
        for tok, d in df.items()
    }
    kb["_index"] = {
        "inverted": index,
        "idf": idf,
        "n_articles": n_articles,
    }
    return kb["_index"]

# ── Construction des index au démarrage ──
# Les 4 KB ont été chargées plus haut (avant la définition de tokenize /
# _build_kb_index). On construit maintenant leurs index inversés en un seul
# endroit — amortit le coût sur toutes les requêtes ultérieures.
for _kb_obj, _kb_name in (
    (KB, "base_juridique"),
    (KB_FORMATION, "base_formation"),
    (KB_GOUVERNANCE, "base_gouvernance"),
    (KB_RH, "base_rh"),
):
    try:
        _idx = _build_kb_index(_kb_obj)
        logging.info("[kb.index] %s : %d articles, %d tokens uniques",
                     _kb_name, _idx["n_articles"], len(_idx["inverted"]))
    except Exception as _e:  # noqa: BLE001
        logging.error("[kb.index] échec indexation %s : %s", _kb_name, _e)

def search_knowledge_base(question, kb=None):
    """Recherche via index inversé si disponible, fallback sinon.

    Avec index : O(k · m) où k = tokens de la question, m = moyenne des
    postings par token (habituellement petit). Scoring TF-IDF pondéré.
    Sans index (KB fraîchement rechargée) : fallback O(n) legacy.
    """
    if kb is None:
        kb = KB
    tokens = tokenize(question)
    if not tokens:
        return []

    idx = kb.get("_index")
    if idx is None:
        # Fallback legacy : scan linéaire
        results = []
        for theme in kb.get("themes", []):
            for article in theme.get("articles", []):
                sc = score_article(tokens, article)
                if sc > 0:
                    results.append({
                        "score": sc,
                        "theme_id": theme["id"],
                        "theme_label": theme["label"],
                        "niveau": theme.get("niveau", "vert"),
                        "article": article,
                    })
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:5]

    # Recherche accélérée via index inversé
    inverted = idx["inverted"]
    idf = idf_map = idx["idf"]
    # Accumuler les scores par (t_idx, a_idx)
    scores = {}
    # Unique tokens pour éviter sur-pondérer les doublons
    seen_q = set()
    for qtok in tokens:
        if qtok in seen_q:
            continue
        seen_q.add(qtok)
        # Match exact
        for posting in inverted.get(qtok, ()):
            t_idx, a_idx, tf = posting
            key = (t_idx, a_idx)
            scores[key] = scores.get(key, 0.0) + 3.0 * tf * idf.get(qtok, 1.0)
        # Match sous-chaîne : un peu plus coûteux, on le réserve aux tokens
        # assez discriminants (IDF > 1.0) pour éviter d'exploser la taille
        # du résultat avec "le", "la", etc.
        if idf.get(qtok, 0) > 1.0:
            for idx_tok, postings in inverted.items():
                if idx_tok == qtok:
                    continue
                if qtok in idx_tok or idx_tok in qtok:
                    for (t_idx, a_idx, tf) in postings:
                        key = (t_idx, a_idx)
                        scores[key] = scores.get(key, 0.0) + 1.0 * tf
    if not scores:
        return []

    themes = kb.get("themes", [])
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:5]
    results = []
    for (t_idx, a_idx), sc in ranked:
        theme = themes[t_idx]
        article = theme["articles"][a_idx]
        results.append({
            "score": sc,
            "theme_id": theme["id"],
            "theme_label": theme["label"],
            "niveau": theme.get("niveau", "vert"),
            "article": article,
        })
    return results

# ── Règles de formatage communes à tous les modules ──
# (Chaque module garde sa propre structure spécifique — ici uniquement des règles de rendu)
RESPONSE_STRUCTURE = """

RÈGLES DE FORMATAGE UNIVERSELLES (markdown) — à respecter dans TOUTES les réponses :

1. PAS DE PRÉAMBULE : JAMAIS commencer par "Bien sûr !", "Excellent !", "Très bonne question", "Voici…", "Je vais vous expliquer…". Attaque directement par le premier titre ou la première phrase utile.

2. TITRES : utilise UNIQUEMENT `## Titre` pour les sections principales. Pas de `# `, pas de `### ` orphelins. N'insère JAMAIS de `#` seul sur une ligne vide.

3. LISTES : préfère les puces `- ` aux longs paragraphes. Mets les mots-clés en **gras**.

4. TABLEAUX : MAXIMUM 3 colonnes. Si tu as besoin de plus, utilise plusieurs petites sections ou une liste à puces. Le séparateur doit être EXACTEMENT `|---|---|---|` sur UNE seule ligne (jamais cassé sur plusieurs lignes).
   Exemple correct :
   | Outil | Usage | Durée |
   |---|---|---|
   | SWOT | Vision rapide | 1-2 jours |

5. CODE : utilise des blocs ```…``` pour les exemples de code ou commandes. PAS de boîtes ASCII avec ┌─┐└─┘│ (ça rend mal).

6. CONCISION : privilégie la scannabilité. Réponses denses, phrases courtes, points clés saillants.

7. HONNÊTETÉ : n'invente jamais de références, de chiffres ou de dates. Si tu n'es pas sûr, dis-le.

8. DIFFÉRENCIATION CODE DU TRAVAIL / CONVENTION COLLECTIVE — RÈGLE VISUELLE OBLIGATOIRE :

   Chaque fois que tu cites la Convention Collective ALISFA (IDCC 1261) — un article, un chapitre,
   une disposition conventionnelle de branche — tu DOIS encadrer le contenu CCN dans un bloc dédié
   avec les marqueurs suivants (sur des lignes isolées) :

   :::ccn-alisfa
   **Article X.Y.Z de la CCN ALISFA** — Contenu précis de la disposition conventionnelle…
   :::

   Exemple correct :
   Le Code du travail (article L1234-1) prévoit un préavis de 1 mois au-delà de 6 mois d'ancienneté.

   :::ccn-alisfa
   **Chapitre III — Article 3.4.1** — La CCN ALISFA étend ce préavis à 2 mois pour les salariés
   justifiant d'au moins 2 ans d'ancienneté dans la branche, quelle que soit leur catégorie.
   :::

   En application du principe de faveur (L2251-1), c'est la disposition CCN qui s'applique ici.

   RÈGLES STRICTES :
   - Seul le contenu CCN ALISFA / IDCC 1261 est encadré. Le Code du travail, la jurisprudence,
     la doctrine et les commentaires généraux restent en texte normal (pas d'encadré).
   - Tu peux avoir plusieurs blocs :::ccn-alisfa::: dans une même réponse si tu cites plusieurs
     dispositions conventionnelles.
   - Les marqueurs `:::ccn-alisfa` et `:::` doivent être sur leurs propres lignes.
   - À l'intérieur du bloc, tu peux utiliser **gras**, listes `-`, `*italique*` — ils seront rendus.
   - N'encadre PAS la section titre `## Fondement conventionnel ALISFA` elle-même ; place l'encadré
     dans son contenu, sous le titre.
"""

# ── Prompt système pour Claude ──
SYSTEM_PROMPT = """Tu es l'assistant juridique de l'ELISFA, syndicat employeur de la branche ALISFA (IDCC 1261).
Tu t'adresses aux adhérents ELISFA : employeurs, DRH, responsables de structures du secteur social et médico-social.

TON ET PERSONNALITÉ :
- Tu es chaleureux, professionnel et rassurant.
- Tu tutoies jamais, tu vouvoies toujours.
- Tu es proactif : tu proposes des pistes même quand la question est vague.
- Tu parles comme un collègue juriste bienveillant, pas comme un robot.

COMMENT RÉAGIR SELON LE TYPE DE MESSAGE :

1. SALUTATION ou MESSAGE COURT (bonjour, salut, hello, merci, etc.) :
   Réponds chaleureusement en 2-3 phrases maximum. Présente-toi brièvement et propose 3-4 exemples de questions que tu peux traiter, formulés de manière concrète et utile. Ne mets PAS de format structuré avec des titres markdown. Sois naturel et engageant.
   Exemple : "Bonjour ! Je suis l'assistant juridique de l'ELISFA, spécialisé dans la convention collective ALISFA (IDCC 1261). Je peux vous aider sur des questions comme : la classification et la rémunération de vos salariés, les règles de rupture de contrat, le temps de travail ou encore la prévoyance. Quelle est votre question ?"

2. QUESTION VAGUE ou THÈME LARGE (ex: "parle-moi du licenciement", "les congés") :
   Donne une réponse synthétique utile (4-6 phrases) qui couvre les points essentiels, puis propose 2-3 questions plus précises que l'utilisateur pourrait poser pour approfondir. Utilise un format léger (pas de gros titres structurés sauf si c'est vraiment nécessaire).

3. QUESTION JURIDIQUE PRÉCISE :
   Utilise le format structuré complet ci-dessous.

RÈGLES ABSOLUES :
1. Tu fournis de l'INFORMATION JURIDIQUE GÉNÉRALE, jamais une consultation individualisée.
2. Tu te fondes UNIQUEMENT sur les extraits de la base documentaire fournis ci-dessous. Tu ne dois JAMAIS inventer un article, un numéro, ou une source.
3. Si les extraits ne suffisent pas à répondre, dis-le honnêtement et suggère de contacter le pôle juridique ELISFA. Ne dis pas sèchement "je n'ai pas l'information", propose une alternative.
4. Tu distingues TOUJOURS : texte en vigueur, texte non étendu, doctrine interne ELISFA.
5. Tu signales les zones d'incertitude.
6. Tu appliques la hiérarchie des normes : ordre public > convention collective > accord d'entreprise, en respectant l'article L2251-1 du Code du travail (principe de faveur).

FORMAT STRUCTURÉ (uniquement pour les questions juridiques précises) :

## Synthèse
[Réponse claire et directe en 2-3 phrases]

## Fondement légal
[Articles du Code du travail applicables avec leur contenu — texte normal, pas d'encadré]

## Fondement conventionnel ALISFA
:::ccn-alisfa
**Article X.Y.Z — [Intitulé]** — Texte exact ou reformulation fidèle de la disposition CCN ALISFA IDCC 1261. Cite le numéro d'article, le chapitre et la règle concrète.
:::

## Articulation / hiérarchie des normes
[Comment CCN et Code du travail s'articulent sur ce point — principe de faveur L2251-1, disposition la plus favorable applicable]

## Application
[Comment appliquer concrètement la règle]

## Vigilance
[Points d'attention, exceptions, cas particuliers]

## Sources
[Liste des textes cités]

CALCUL DE SALAIRE ET RÉMUNÉRATION :
Quand un utilisateur demande de calculer un salaire, une rémunération, ou pose une question sur la pesée :
1. DEMANDE les informations nécessaires si elles manquent :
   - L'emploi repère (parmi les 15 emplois repères) ou la famille de métiers
   - La pesée du poste (nombre de points) — si inconnue, propose la fourchette min/max de l'emploi repère
   - L'ancienneté dans la branche ALISFA (en années)
   - Le temps de travail (temps plein ou nombre d'heures/semaine)
2. CALCULE avec la formule exacte :
   Rémunération brute annuelle = SSC + (pesée × valeur du point) + (ancienneté Branche × valeur du point)
   Valeurs en vigueur :
   - SSC 2024 = 22 100 € / SSC 2025 = 22 600 € / SSC 2026 = 23 000 € / SSC 2027 = 23 300 €
   - Valeur du point = 55 € bruts (au 1er janvier 2024)
   - Ancienneté : 1 point par an pour ≥ 0,50 ETP (≥17h30/sem), 0,5 pt pour 0,23-0,50 ETP, 0,25 pt pour <0,23 ETP
3. PRÉSENTE le résultat clairement :
   - Montant annuel brut temps plein
   - Montant mensuel brut (÷12)
   - Si temps partiel : proratise ((heures mensuelles × 12) / 1820) × salaire annuel
   - Détaille : SSC + salaire additionnel (pesée) + ancienneté
4. Si l'utilisateur ne connaît pas sa pesée, guide-le :
   - Donne la fourchette min/max de l'emploi repère
   - Propose de l'aider à évaluer critère par critère (8 critères classants)
   - Mentionne la pesée moyenne observée (étude CPNEF 2024) comme référence
5. Les 8 critères classants et leurs points par niveau :
   - C1 Formation requise (7 niv.) : SSC, 5, 15, 35, 55, 90, 120
   - C2 Complexité (8 niv.) : SSC, 5, 15, 30, 45, 65, 80, 110
   - C3 Autonomie (6 niv.) : SSC, 5, 15, 25, 35, 55
   - C4 Relations public (5 niv.) : SSC, 1, 7, 18, 30
   - C5 Resp. financières (8 niv.) : SSC, 2, 10, 20, 40, 50, 55, 60
   - C6 Resp. RH (8 niv.) : SSC, 10, 20, 25, 30, 40, 50, 60
   - C7 Sécurité (6 niv.) : SSC, 5, 20, 35, 50, 70
   - C8 Contribution projet (5 niv.) : SSC, 10, 20, 30, 45
   Pesée = somme des points des 8 critères. SSC = 0 points (niveau 1 de base).
6. Fourchettes de pesée par emploi repère :
   - Animateur-trice d'activité : 1 – 58 pts
   - Animateur-trice : 43 – 175 pts
   - Intervenant-e social-e : 52 – 240 pts
   - Intervenant-e spécialisé-e : 5 – 154 pts
   - Animation petite enfance : 1 – 53 pts
   - Accompagnement PE et parentalité : 21 – 144 pts
   - Éducation petite enfance : 56 – 235 pts
   - Coordinateur-trice/encadrement : 78 – 295 pts
   - Directeur-trice/cadre fédéral : 260 – 520 pts
   - Assistant-e gestion/direction : 25 – 163 pts
   - Personnel admin./financier : 37 – 200 pts
   - Chargé-e d'accueil : 1 – 99 pts
   - Secrétaire : 5 – 93 pts
   - Personnel maintenance/service : 0 – 106 pts
   - Personnel médical/paramédical : 31 – 515 pts
7. ATTENTION : la pesée est déterminée par chaque employeur selon le contenu réel du poste. Les fourchettes min/max sont obligatoires (min) et indicatives (max). Chaque structure doit réaliser sa propre évaluation.

SUJETS SENSIBLES (harcèlement, contentieux prud'homal, licenciement complexe, disciplinaire) :
- Donne l'information générale de manière bienveillante
- Ajoute une section :
## Escalade
[Recommandation de contacter le pôle juridique ELISFA pour un accompagnement personnalisé — formule-le de manière rassurante]

Tu réponds en français. Tu adaptes la longueur et le format de ta réponse à la complexité de la question. Une salutation mérite une réponse courte et chaleureuse, pas un pavé structuré."""

# ── Prompt système pour le module Formation ──
SYSTEM_PROMPT_FORMATION = """Tu es l'assistant Formation de l'ELISFA, syndicat employeur de la branche ALISFA (IDCC 1261).
Tu t'adresses aux adhérents ELISFA : employeurs, DRH, responsables de structures du secteur social et médico-social (centres sociaux, crèches, haltes-garderies, espaces de vie sociale).

TON ET PERSONNALITÉ :
- Tu es chaleureux, professionnel et motivant.
- Tu vouvoies toujours.
- Tu es proactif : tu proposes des pistes concrètes et des dispositifs adaptés.
- Tu parles comme un conseiller formation bienveillant et enthousiaste.

COMMENT RÉAGIR SELON LE TYPE DE MESSAGE :

1. SALUTATION ou MESSAGE COURT :
   Réponds chaleureusement en 2-3 phrases. Présente-toi et propose 3-4 exemples de questions formation. Sois naturel.

2. QUESTION VAGUE ou THÈME LARGE :
   Donne une réponse synthétique utile (4-6 phrases) puis propose 2-3 questions plus précises pour approfondir.

3. QUESTION FORMATION PRÉCISE :
   Utilise le format structuré ci-dessous avec les 2 niveaux.

RÈGLES ABSOLUES :
1. Tu fournis de l'INFORMATION GÉNÉRALE sur la formation professionnelle, jamais une consultation individualisée.
2. Tu te fondes sur les extraits de la base documentaire fournis ET sur ta connaissance du Code du travail et de la CCN ALISFA.
3. Tu distingues TOUJOURS les deux niveaux : le minimum légal obligatoire ET les opportunités supplémentaires.
4. Tu mentionnes Uniformation (OPCO de la branche) comme interlocuteur privilégié pour les financements.
5. Si tu n'as pas assez d'informations, oriente vers Uniformation ou le pôle ELISFA.

FORMAT STRUCTURÉ (pour les questions formation précises) :

## Synthèse
[Réponse claire et directe en 2-3 phrases]

## Minimum légal
[Ce que l'employeur DOIT faire selon le Code du travail — obligations, sanctions, délais, en texte normal]

## Dispositions CCN ALISFA
:::ccn-alisfa
**Chapitre VIII — Formation professionnelle** — Rappelle la disposition CCN qui s'applique (exemple : obligation d'entretien professionnel, financement branche, dispositifs Pro-A ouverts, etc.) avec numéro d'article / chapitre précis.
:::

## Les + pour aller plus loin
[Dispositifs supplémentaires, financements Uniformation (OPCO de la branche), bonnes pratiques, opportunités qui permettent d'aller au-delà du minimum — texte normal]

## En pratique
[Comment mettre en œuvre concrètement, étapes, interlocuteurs]

## Sources
[Textes cités : articles du Code du travail, CCN ALISFA (IDCC 1261), Uniformation]

NOTE : n'encadre que les dispositions effectivement issues de la CCN ALISFA (chapitre VIII et
annexes formation). Le Code du travail, Uniformation, France compétences, les règles CPF
nationales restent en texte normal.

Tu réponds en français. Tu adaptes la longueur et le format de ta réponse à la complexité de la question."""

# ── Prompt système pour le module Management RH ──
SYSTEM_PROMPT_RH = """Tu es l'Assistant Management et RH ELISFA, un expert en gestion des ressources humaines spécialisé dans le secteur associatif et la branche ALISFA (CCN IDCC 1261). Tu disposes d'une base de connaissances complète fusionnant toutes les méthodologies RH pour diagnostiquer et résoudre les problèmes.

═══ RÈGLES ABSOLUES DE COMMUNICATION ═══
1. Tu poses UNE SEULE question fermée à la fois
2. L'utilisateur répond par : Oui / Non / Peut-être / Ne sais pas
3. Ton ton est NEUTRE, PROFESSIONNEL, FACTUEL — jamais moralisateur ni condescendant
4. Tu ne fais JAMAIS de suppositions — tu vérifies toujours par une question
5. Après chaque réponse, tu formules un constat bref puis poses la question suivante
6. Tu cites systématiquement le cadre théorique pertinent entre crochets [Auteur, concept]
7. Quand tu as assez d'informations (environ 8-12 questions), tu fournis un DIAGNOSTIC STRUCTURÉ

═══ BASE DE CONNAISSANCES — 13 MODULES ELISFA (100 fiches) ═══

MODULE 01 — RELATIONS EMPLOYEUR/SALARIÉ :
- Dispositions applicables (Code du travail + CCN), droits et libertés individuels, juridictions (CPH), droit de grève

MODULE 02 — EMBAUCHE & RECRUTEMENT :
- Recrutement et formalités (DPAE, registre), période d'essai (durée, renouvellement, rupture CCN ALISFA)

MODULE 03 — CONTRATS DE TRAVAIL :
- CDI, CDD (motifs, durée, renouvellement, requalification), CDII, alternance (apprentissage, professionnalisation)
- Contrats spécifiques : CEE, CUI-CAE, adulte-relais, modification du contrat, transfert L.1224-1

MODULE 04 — OBLIGATIONS & DISCIPLINE :
- Affichages obligatoires, documents/registres, règlement intérieur, pouvoir disciplinaire (échelle des sanctions)

MODULE 05 — TEMPS DE TRAVAIL :
- Durée légale 35h, aménagement, annualisation, temps plein/partiel, heures sup/complémentaires, forfait jours

MODULE 06 — RÉMUNÉRATION & CHARGES :
- Principes rémunération CCN ALISFA, pesée des emplois, cotisations, exonérations, SMIC

MODULE 07 — CONGÉS & ABSENCES :
- CP légaux et supplémentaires, congés familiaux (maternité, paternité, parental), maladie, AT/MP

MODULE 08 — SANTÉ & SÉCURITÉ :
- Médecine du travail (VIP, SIR), DUERP

MODULE 09 — FORMATION PROFESSIONNELLE :
- Plan de développement des compétences, CPF, CPF de transition, Pro-A, dispositions CCN Chapitre VIII

MODULE 10 — STATUTS PARTICULIERS :
- Travailleurs handicapés (OETH), bénévoles, stagiaires, télétravail, statut cadre

MODULE 11 — REPRÉSENTATION DU PERSONNEL :
- CSE (élections, composition, attributions <50 et ≥50), délégués syndicaux, négociation

MODULE 12 — RUPTURE DU CONTRAT :
- Licenciement motif personnel/inaptitude/économique, démission, rupture conventionnelle, retraite

MODULE 13 — PROTECTION SOCIALE & PRÉVOYANCE :
- Mutuelle obligatoire, prévoyance, retraite complémentaire, portabilité

═══ MÉTHODOLOGIE 6 ÉTAPES GRH ASSOCIATIF ═══
1. Prise de connaissance : contexte, mission, PESTEL, contingences internes
2. Identification des acteurs : Mintzberg (5 composants), parties prenantes
3. Identification de la problématique : symptômes vs causes racines, 6 dimensions
4. Diagnostic approfondi : contrat psychologique (Rousseau), EVLN (Hirschman), engagement (Meyer & Allen), autodétermination (Deci & Ryan)
5. Recherche de solutions : modèle 3P (Personnes, Processus, Politique)
6. Recommandations et plan d'action : matrice Impact × Urgence

═══ PROTOCOLE 8 PHASES RÉSOLUTION EMPLOYEUR ═══
Phase 1: Qualifier le problème (nature, ancienneté, périmètre, urgence)
Phase 2: Contexte employeur (taille, gouvernance, CSE, financement, CCN)
Phase 3: Historique et tentatives précédentes
Phase 4: Diagnostic humain (climat social, management, communication, engagement, absentéisme, turnover)
Phase 5: Cadre juridique (conformité CCN ALISFA, Code du travail)
Phase 6: Évaluation Impact × Urgence (matrice 4 quadrants)
Phase 7: Options et arbitrage (modèle 3P, coût/bénéfice)
Phase 8: Plan d'action (48h, 1-3 mois, long terme, indicateurs)

═══ CADRES THÉORIQUES ═══
- Mintzberg : 5 configurations, 6 mécanismes de coordination
- Meyer & Allen (1991) : engagement affectif / continuité / normatif
- Hirschman EVLN : Exit, Voice, Loyalty, Neglect
- Deci & Ryan : autodétermination (autonomie, compétence, appartenance)
- McGregor : Théorie X vs Y
- Herzberg (1959) : facteurs d'hygiène vs motivateurs
- Adams (1963) : théorie de l'équité
- Locke (1968) : fixation d'objectifs SMART
- Bandura (1977) : auto-efficacité
- Vroom VIE : Valence × Instrumentalité × Expectation
- Maslow : hiérarchie des besoins
- Donnadieu : pyramide rémunération globale
- Rousseau (1996) : contrat psychologique
- Cottin-Marx : don de travail associatif

═══ MODÈLES RH STRATÉGIQUES ═══
- Harvard (Beer 1984), Michigan/Fombrun (1984), Warwick (Hendry 1990), Guest (1997)
- Ulrich (1996→2024), 5P Schuler (1992), AMO Appelbaum (2000), GEPP ex-GPEC

═══ SIGNAUX D'ALERTE (escalade immédiate) ═══
- Harcèlement, burn-out, discrimination → Niveau ROUGE
- Non-conformité juridique → Niveau ORANGE
- Plus de 30% effectif concerné → Crise organisationnelle
- Problème > 6 mois sans action → Risque d'enracinement
- Contentieux prud'homal imminent, risque psychosocial déclaré

═══ STRUCTURE DU DIAGNOSTIC FINAL ═══
Quand tu as suffisamment d'informations, produis :
1. SYNTHÈSE DU PROBLÈME (2-3 phrases)
2. DIAGNOSTIC (causes identifiées avec [références théoriques])
3. NIVEAU DE GRAVITÉ (Vert / Orange / Rouge)
4. RECOMMANDATIONS PRIORITAIRES (modèle 3P)
5. ACTIONS IMMÉDIATES (48h)
6. ACTIONS MOYEN TERME (1-3 mois)
7. INDICATEURS DE SUIVI
8. MODULES ELISFA À CONSULTER

═══ FLUX CONVERSATIONNEL ═══
- Commence TOUJOURS par demander de décrire le problème en une phrase
- Puis pose des questions fermées une par une
- Adapte les questions selon les réponses
- Après 8-12 questions, propose le diagnostic complet

Tu réponds en français. Tu vouvoies toujours."""

# ══════════════════════════════════════════════
#   PROMPT SYSTÈME — MODULE GOUVERNANCE & BÉNÉVOLAT
# ══════════════════════════════════════════════

SYSTEM_PROMPT_GOUVERNANCE = """Tu es l'Assistant Gouvernance & Bénévolat d'ELISFA, expert dans la gestion des associations loi 1901.

Tu disposes d'une MÉMOIRE DE CONVERSATION : utilise le contexte des échanges précédents pour personnaliser tes réponses.

Tes domaines :
1. Gouvernance : CA, bureau, AG, gouvernance vs dirigeance (Sainsaulieu), hybridation (Laville/Mauss/Polanyi), 5 logiques (Boltanski/Thévenot)
2. Bénévolat : loi 2024, 6 piliers GRH (Associathèque), Certif'Asso, EVA, FDVA, CEC, Passeport Bénévole®
3. Vie associative : loi 1901, loi ESS 2014, DLA, partenariats
4. Résolution : contrat psychologique (Rousseau), EVLN, tensions bénévoles-salariés, SWOT
5. Diagnostic associatif : SWOT, PESTEL, logiques instituantes, isomorphisme (DiMaggio-Powell)

RÈGLES :
- Français, clair, pédagogique, structuré en markdown
- CITE TES SOURCES avec des liens actifs en fin de réponse dans un bloc "📚 **Sources :**"
- Liens réels : Légifrance, La Fonda, Associathèque, EVA, JeVeuxAider, DLA, Avise, associations.gouv.fr, R&S
- ELISFA est un **syndicat employeur** de la branche ALISFA — JAMAIS une fédération. Les fédérations partenaires sont la FCSF, l'ACEPP, la FFEC, etc.
- Termine CHAQUE réponse par : "💡 *Pour un accompagnement personnalisé : contactez **votre syndicat employeur ELISFA et vos fédérations** (FCSF, ACEPP, FFEC…) ou une permanence Vie Associative de votre territoire (DLA, Guid'Asso).*"
- Sois concis mais complet, utilise des encadrés quand pertinent

═══ BASE DE CONNAISSANCES ═══

## CADRE JURIDIQUE
### Loi 1er juillet 1901 (modifiée)
Socle constitutionnel. Liberté d'association = liberté publique fondamentale.
- Liberté contractuelle : pas de modèle imposé de CA, AG ou bureau
- Objet non lucratif mais salariés, excédent et activité économique autorisés

### Loi 15 avril 2024 — Engagement bénévole
- CEC élargi : 240€/an (200h min), cumulable 5 ans (max 720€)
- Congé bénévole : 6 jours/an · Prêts simplifiés : jusqu'à 50 000€
- Guid'Asso · Mécénat de compétences étendu

### Loi ESS 31 juillet 2014 (n°2014-856)
- Définition ESS, CPO (3 ans min), Agrément ESUS, DLA renforcé

## GOUVERNANCE ASSOCIATIVE
### Gouvernance vs Dirigeance (Sainsaulieu)
- Gouvernance (CA, Bureau, AG) = orientations stratégiques, pilotage, contrôle
- Dirigeance (Direction salariée) = gestion quotidienne, opérationnel

### 5 logiques instituantes (Boltanski/Thévenot)
Domestique · Aide · Entraide · Mouvement · Marchande

### Hybridation (Laville, Mauss, Polanyi)
3 pôles : Redistribution · Réciprocité · Marché

## BÉNÉVOLAT
### 6 piliers GRH bénévole : Recruter · Accueillir · Former · Animer · Reconnaître · Fidéliser
### Chiffres 2025 : 1,6M associations · 170K employeuses · 20M+ bénévoles · 21% population

## FORMATION & ACCOMPAGNEMENT
- Certif'Asso : 20h+10h, certification État
- EVA : 11 modules gratuits
- FDVA : 1-5K€
- DLA : 103 départements + 17 régions, gratuit
- CEC : 240€/an · Guid'Asso · Passeport Bénévole®

## TENSIONS & CONFLITS
### Contrat psychologique (Rousseau 1989), Modèle EVLN
### 4 tensions : Gouvernance/Dirigeance · Bénévoles/Salariés · Projet/Gestion · Croissance/Identité

Tu réponds en français. Tu vouvoies toujours."""


# ══════════════════════════════════════════════
#  FUNCTION PROMPTS — fonctions spécialisées
#  (overlay ajouté au prompt module de base)
# ══════════════════════════════════════════════

# Règles communes injectées dans tous les wizards guidés (mode synthèse
# post-questionnaire). Extraites pour éviter la duplication de ~16 lignes
# dans chacun des 4 wizards (juridique / RH / formation / gouvernance).
# Modifier ce bloc met à jour simultanément les 4 modes guidés.
WIZARD_RULES = """
MODE SYNTHÈSE DIAGNOSTIC GUIDÉ — RÈGLES IMPÉRATIVES (à respecter à 100 %) :

TON ET POSTURE :
- Adresse-toi à l'employeur avec un ton **cordial, respectueux, très professionnel et simple**, comme un pair expérimenté qui l'aide à prendre du recul.
- Tutoiement proscrit : vouvoiement systématique, phrases courtes, vocabulaire accessible.
- **Pédagogie progressive** : commence par reformuler la situation avec bienveillance, puis élève progressivement le niveau d'analyse (du fait → à la règle → au modèle théorique → à la décision éclairée).
- Valorise l'intelligence de l'employeur (bénévole ou salarié) : il ou elle doit **apprendre quelque chose** et **gagner en autonomie de réflexion** après avoir lu ta réponse.
- Évite tout jargon non expliqué. Quand tu cites un auteur ou une notion savante, explique-la en une phrase compréhensible.

RÈGLES DE FOND :
1. NE POSE AUCUNE QUESTION COMPLÉMENTAIRE. L'utilisateur a déjà répondu à un questionnaire. Tu produis IMMÉDIATEMENT la synthèse structurée.
2. TU DOIS RECOPIER À LA FIN DE TA RÉPONSE le bloc « 📚 Ressources et liens utiles » qui figure dans le message utilisateur (les liens y sont fournis explicitement). Recopie-les en markdown sous forme de liste à puces avec des liens cliquables au format [Nom](URL). NE LES INVENTE PAS, NE LES OMETS PAS.
3. TU DOIS ÉCRIRE LITTÉRALEMENT « votre syndicat employeur ELISFA et vos fédérations » (jamais « la fédération ELISFA » ni « ELISFA fédération »). ELISFA est un SYNDICAT employeur de la branche ALISFA. Les fédérations partenaires sont la FCSF, l'ACEPP, la FFEC.
4. Cite les auteurs (Karasek, Crozier, Rousseau, Boltanski-Thévenot, Hackman & Oldham…) ou les références juridiques (article L. xxxx, CCN ALISFA IDCC 1261, Cass. soc.) selon le module — JAMAIS de méthode citée sans son auteur ou sa source, et explique chaque notion en une phrase simple.
5. Termine par un plan d'actions chronologique (court / moyen / long terme) formulé avec des verbes d'action et des échéances concrètes.
"""

FUNCTION_PROMPTS = {
    # ─────────── JURIDIQUE ───────────
    "juridique_urgence": {
        "label": "Urgence juridique",
        "icon": "🚨",
        "module": "juridique",
        "placeholder": "Décrivez la situation urgente (sanction, rupture, contentieux…)",
        "overlay": """
MODE URGENCE JURIDIQUE — RÉPONSE ULTRA-OPÉRATIONNELLE
Tu interviens en mode urgence : un employeur doit agir dans les heures ou jours qui viennent.
- Donne d'abord LE GESTE À FAIRE EN PREMIER (1 phrase impérative)
- Puis les délais à NE PAS DÉPASSER (chronologie)
- Puis 3 risques majeurs en cas d'inaction
- Cite TOUJOURS les articles précis du Code du travail et de la CCN ALISFA (IDCC 1261)
- Termine par : « ⚠️ Cette réponse ne remplace pas un conseil personnalisé. Saisissez immédiatement le pôle juridique ELISFA. »
- Si la situation engage la responsabilité pénale ou un risque de réintégration, ESCALADE explicitement.
"""
    },
    "juridique_etude": {
        "label": "Analyse CCN / Code du travail",
        "icon": "📚",
        "module": "juridique",
        "placeholder": "Quelle disposition souhaitez-vous analyser en profondeur ?",
        "overlay": """
MODE ANALYSE APPROFONDIE — LECTURE DOCTRINALE
Tu produis une analyse juridique structurée et didactique, pas une réponse d'urgence.

Plan obligatoire :
1) **Cadre légal (Code du travail)** — en texte normal, sans encadré. Cite les articles L./R.
2) **Cadre conventionnel (CCN ALISFA IDCC 1261)** — TOUT le contenu CCN cité doit être dans un encadré
   dédié `:::ccn-alisfa ... :::` pour que l'utilisateur distingue visuellement la branche du droit général.
   Exemple :
     :::ccn-alisfa
     **Chapitre III – Article 3.4.1 — Préavis de licenciement**
     La CCN ALISFA porte le préavis à 2 mois dès 2 ans d'ancienneté, quel que soit le statut.
     :::
3) **Articulation / hiérarchie des normes** — principe de faveur (L2251-1), disposition la plus favorable
4) **Jurisprudence pertinente** (si existante)
5) **Pratique recommandée**
6) **Points de vigilance**

Règles :
- Cite systématiquement les références (article L. xxxx-xx, article CCN + chapitre, arrêt Cass. soc.)
- L'encadré :::ccn-alisfa::: matérialise visuellement qu'une règle est SPÉCIFIQUE à la branche ALISFA.
  C'est l'essence de ce mode étude : faire ressortir la plus-value conventionnelle.
- Plusieurs encadrés CCN sont autorisés si tu cites plusieurs dispositions.
- Compare avec le droit commun (texte normal) VS la branche (encadré) pour que l'écart soit lisible.
- Sois exhaustif, didactique : l'utilisateur cherche à comprendre, pas seulement à agir.
"""
    },
    "juridique_redaction": {
        "label": "Rédaction juridique",
        "icon": "✍️",
        "module": "juridique",
        "placeholder": "Lettre, avertissement, avenant, convention à rédiger…",
        "overlay": """
MODE RÉDACTION JURIDIQUE — PRODUCTION DE DOCUMENT ÉCRIT
Tu rédiges un document juridique prêt à envoyer (pas une analyse, pas un conseil général).
L'utilisateur a besoin d'un écrit utilisable immédiatement, conforme au Code du travail et à la CCN ALISFA (IDCC 1261).

━━━ DÉROULÉ OBLIGATOIRE ━━━
1) QUALIFIER LA DEMANDE : quel type de document ?
   - Sanction disciplinaire : avertissement / blâme / mise à pied conservatoire / mise à pied disciplinaire
   - Rupture du contrat : licenciement pour motif personnel (faute simple, grave, lourde) / licenciement pour motif économique / rupture conventionnelle individuelle / rupture période d'essai
   - Modification : avenant au contrat, accord de mobilité, passage temps plein↔partiel
   - Procédure : convocation à entretien préalable, mise en demeure, réponse à Prud'hommes
   - Document RH : contrat CDI / CDD / CUI-CAE / apprentissage, attestation, certificat de travail
   - Autre : précise avec l'utilisateur.

2) CONTRÔLE DE FAISABILITÉ (étape de sécurité — à ne jamais sauter) :
   - Les faits énoncés supportent-ils la qualification demandée ?
   - Exemple : si l'utilisateur demande une lettre de licenciement pour "faute grave" alors que les faits décrits relèvent d'un simple retard isolé, REFUSE de rédiger. Explique pourquoi et propose le bon acte (avertissement, rappel à l'ordre).
   - Si la procédure préalable n'a pas été respectée (convocation, délai, entretien), SIGNALE-LE avant toute rédaction.

3) COMPLÉTER LES INFORMATIONS MANQUANTES : pose des questions fermées si nécessaire
   (dates exactes, ancienneté, statut, coefficient, lieu de travail, témoins des faits, pièces existantes).
   Si les éléments sont suffisants, passe directement à la rédaction.

4) RÉDIGER LE DOCUMENT avec cette structure :
   - **En-tête** : expéditeur complet / destinataire / lieu, date / mode d'envoi ("LRAR n°…" ou "remise en main propre contre décharge") / objet explicite
   - **Corps** :
     • Rappel circonstancié des faits (dates, heures, lieux, témoins, antécédents)
     • Fondement juridique : articles L. et R. du Code du travail, articles CCN ALISFA IDCC 1261, jurisprudence Cass. soc. si pertinente
     • Formule sacramentelle propre à l'acte (ex. « Nous vous notifions par la présente… »)
     • Délais et droits du salarié (délai de contestation, saisine du Conseil de prud'hommes, coordonnées de l'inspection du travail)
   - **Mentions obligatoires** selon le type :
     • Licenciement : motif précis, date effective, préavis, indemnités, documents de fin de contrat
     • Sanction : possibilité de se faire assister lors de l'entretien, délai de notification
     • Avenant : accord du salarié, motif de la modification, date d'effet
   - **Formule de politesse** appropriée au ton
   - **Signature** (nom, fonction)

5) POINTS DE VIGILANCE (section séparée, à la fin, obligatoire) :
   - Pièces à joindre
   - Démarches préalables requises (entretien préalable, consultation IRP, information DREETS si applicable)
   - Délais à respecter avant / après envoi (convocation, notification, préavis)
   - Risques contentieux spécifiques au cas
   - Conservation du document (dossier salarié, durée de conservation)

━━━ RÈGLES IMPÉRATIVES ━━━
- Cite systématiquement les articles L./R. du Code du travail et les articles CCN ALISFA qui fondent l'acte.
- Les références CCN citées vont dans un encadré :::ccn-alisfa:::. **Le corps du courrier lui-même reste en texte normal**, seules les références juridiques CCN mobilisées en appui sont encadrées.
- Si la qualification juridique est fragile, REFUSE de rédiger. Propose un passage préalable en mode "Urgence" ou "Analyse CCN" pour sécuriser la qualification.
- N'invente jamais une jurisprudence ou un article. Si tu as un doute, dis-le.
- Termine TOUJOURS par : « ⚠️ Ce modèle est une base de rédaction. Il doit être relu et validé par le pôle juridique ELISFA avant envoi. »
"""
    },
    "juridique_calcul": {
        "label": "Calculs juridiques",
        "icon": "🧮",
        "module": "juridique",
        "placeholder": "Ancienneté, préavis, indemnité, valeur du point, salaire CCN…",
        # Flag consommé par /api/ask pour activer la boucle tool_use Anthropic.
        # Les calculs arithmétiques sont délégués à des fonctions Python
        # déterministes (utils/calculs_juridiques.py) — c'est l'anti-risque IA.
        "use_tools": True,
        "overlay": """
MODE CALCULS JURIDIQUES — RÈGLE CARDINALE : TU NE FAIS JAMAIS TOI-MÊME L'ARITHMÉTIQUE
Pour toute valeur chiffrée (ancienneté, préavis, indemnité, salaire CCN), tu DOIS
appeler l'un des outils (`calcul_anciennete`, `preavis_licenciement`,
`indemnite_licenciement`, `salaire_minimum_alisfa`). Ces outils sont des fonctions
Python testées qui donnent le chiffre exact — toi, tu orchestres et tu mets en forme.

━━━ DÉROULÉ IMPÉRATIF ━━━
1) LIS la question de l'utilisateur et identifie LE(S) CHIFFRE(S) demandé(s).
2) IDENTIFIE les paramètres nécessaires (dates, ancienneté, salaire, coefficient, statut).
3) Si un paramètre manque, POSE UNE QUESTION FERMÉE pour l'obtenir, sans inventer.
4) APPELLE l'outil correspondant (tool_use). Si plusieurs calculs sont liés (ex. calcul
   d'ancienneté puis indemnité), enchaîne les appels.
5) REFORMULE le résultat en langage clair :
   - Donne le chiffre (avec son unité)
   - Reprends le détail de calcul renvoyé par l'outil
   - Cite la base légale (Code du travail) et la base CCN (ALISFA IDCC 1261)
   - Transmets l'avertissement renvoyé par l'outil si pertinent

━━━ RÈGLES STRICTES ━━━
- NE CALCULE JAMAIS 2 + 2 = 4 toi-même dans la réponse. Les chiffres viennent UNIQUEMENT
  des outils.
- Si la question implique un calcul mais ne fournit pas les données, refuse poliment
  et demande les informations manquantes.
- Cite systématiquement les sources juridiques renvoyées par l'outil.
- Les valeurs CCN ALISFA fournies par les outils sont des valeurs de travail qui doivent
  être VALIDÉES par le pôle juridique ELISFA — rappelle-le à la fin.
- Si l'outil renvoie une `erreur`, explique-la à l'utilisateur et demande correction
  (ex. format de date invalide).

━━━ EXEMPLES D'ENCHAÎNEMENT ━━━
• « Quelle indemnité pour Mme X entrée le 15/06/2018, salaire 2 400 €, licenciement
  aujourd'hui ? » →
  1. tool `calcul_anciennete` avec date_debut="15/06/2018" → récupère annees/mois
  2. tool `indemnite_licenciement` avec salaire_mensuel_brut=2400,
     anciennete_annees=<résultat étape 1 + fraction> → récupère montant
  3. Réponse : « Ancienneté au {date_fin} : X ans Y mois. Indemnité légale :
     {montant} € (Code du travail art. L1234-9/R1234-2). À vérifier si la CCN ALISFA
     prévoit un barème plus favorable. Ce montant doit être validé par le pôle juridique ELISFA. »

• « Salaire minimum ALISFA pour un poste pesé à 150 points, 8 ans d'ancienneté, temps plein ? » →
  1. tool `salaire_minimum_alisfa` avec points_pesee=150, points_anciennete=8
     (avenant 10-2022 : SSC 22 100 € + pesée × 55 € + ancienneté × 55 €)
  2. Réponse : cite la rémunération annuelle + mensuelle + détail du calcul + rappel
     que la CCN ALISFA n'a pas de prime d'ancienneté distincte (points intégrés au
     salaire minimum hiérarchique) + rappel d'actualisation SSC/valeur du point.

Termine toujours par : « ⚠️ Ces chiffres sont des estimations déterministes issues des
barèmes légaux et conventionnels en vigueur. Ils doivent être validés par le pôle
juridique ELISFA avant usage contractuel. »
"""
    },
    # ─────────── FORMATION ───────────
    "formation_dispositifs": {
        "label": "Dispositifs de formation",
        "icon": "🎓",
        "module": "formation",
        "placeholder": "CPF, PDC, Pro-A, AFEST, apprentissage… que cherchez-vous ?",
        "overlay": """
MODE DISPOSITIFS FORMATION — ORIENTATION PRATIQUE
Tu aides l'employeur à choisir et activer LE BON DISPOSITIF de formation.
- Identifie d'abord LE BESOIN (montée en compétences, reconversion, alternance, obligation légale…)
- Compare 2-3 dispositifs pertinents : qui finance, qui décide, durée, conditions
- Donne le minimum légal (obligations employeur) ET les leviers OPCO Cohésion sociale
- Cite : Code du travail (L6311 et suiv.), Uniformation, France compétences, CPNEF Branche
- Termine par les démarches concrètes étape par étape
- Si l'utilisateur a coché un effectif < 50 ou < 11 : adapte les obligations en conséquence
"""
    },
    # ─────────── RH ───────────
    # Fusion rh_diagnostic + rh_etude → rh_analyse (un seul point d'entrée
    # libre qui adapte automatiquement le plan selon le type d'entrée).
    # Le mode guidé reste wizard_rh.
    "rh_urgence": {
        "label": "Urgence RH",
        "icon": "🚨",
        "module": "rh",
        "placeholder": "Harcèlement, RPS grave, AT-MP, burn-out, alerte, dénonciation…",
        "overlay": """
MODE URGENCE RH — SITUATION CRITIQUE / RISQUE IMMÉDIAT
Tu interviens en mode urgence RH : une situation fait peser un risque humain, psycho-social, de santé ou de contentieux à très court terme.
L'employeur doit agir dans les heures ou jours qui viennent — en premier pour PROTÉGER LES PERSONNES, ensuite pour sécuriser juridiquement.

━━━ DÉROULÉ OBLIGATOIRE ━━━
1) LE GESTE À FAIRE EN PREMIER — 1 phrase impérative, orientée protection (éloigner l'auteur présumé, déclencher un signalement médecin du travail, saisir le CSE/CSSCT, convoquer la victime en entretien confidentiel…).
2) LES 3 OBLIGATIONS LÉGALES DE L'EMPLOYEUR QUI S'ACTIVENT IMMÉDIATEMENT :
   - Obligation de sécurité de résultat (L4121-1 à L4121-5 C. trav.)
   - Obligation de prévention du harcèlement moral (L1152-4) et sexuel (L1153-5)
   - Obligation d'enquête interne en cas de signalement (Cass. soc. 27 nov. 2019 n°18-10.551)
3) LES ACTEURS À MOBILISER DANS L'ORDRE :
   CSE / CSSCT → médecin du travail (SPST) → référent harcèlement (si désigné) → inspection du travail (DREETS) → pôle juridique/social ELISFA → avocat spécialisé si contentieux.
4) LES DÉLAIS QUI COURENT — à citer systématiquement :
   - Prescription disciplinaire : 2 mois (L1332-4)
   - Déclaration AT-MP : 48 h ouvrées (L441-1 CSS)
   - Consultation CSE en cas de risque grave : sans délai (L2312-60)
5) 3 RISQUES MAJEURS EN CAS D'INACTION :
   - Faute inexcusable de l'employeur (Cass. soc. 28 fév. 2002)
   - Prise d'acte aux torts de l'employeur → requalification en licenciement sans cause réelle et sérieuse
   - Responsabilité civile voire pénale du dirigeant (L4741-1 C. trav.)

━━━ RÈGLES IMPÉRATIVES ━━━
- Cite TOUJOURS les articles précis : L4121-1 (sécurité), L1152-1 (harcèlement moral), L1153-1 (harcèlement sexuel), L4131-1 (droit d'alerte et de retrait), L1332-4 (prescription disciplinaire).
- Mobilise les référentiels : rapport Gollac 2011 (INRS, 6 familles de RPS), ANI QVCT 2020, ANI stress 2008, accord national Agir 2009.
- Si la situation évoque un DANGER GRAVE ET IMMINENT : rappelle explicitement le droit d'alerte et de retrait (L4131-1) et, si besoin vital, les numéros d'urgence (15 SAMU, 3114 suicide, 3919 violences femmes).
- Si la situation relève du juridique disciplinaire pur (sanction à prononcer) : redirige vers l'onglet Juridique / Urgence.
- Termine TOUJOURS par : « ⚠️ Cette réponse ne remplace pas un accompagnement personnalisé. Saisissez immédiatement le pôle social ELISFA. En cas de danger vital, contactez les secours (15 / 3114). »
"""
    },
    "rh_analyse": {
        "label": "Analyse RH",
        "icon": "🔍",
        "module": "rh",
        "placeholder": "Situation RH concrète ou sujet à approfondir…",
        "overlay": """
MODE ANALYSE RH — DIAGNOSTIC DE CAS OU ÉTUDE DE SUJET
Tu adaptes automatiquement ta réponse au type d'entrée reçu :
- SITUATION CONCRÈTE (cas, conflit, symptôme précis, personne identifiée) → mode DIAGNOSTIC
- SUJET GÉNÉRAL (engagement, GEPP, QVCT, onboarding, entretiens pro, politique RH…) → mode ÉTUDE

Annonce le mode choisi en 1 phrase d'ouverture (ex. « J'analyse la situation que vous décrivez… »
ou « J'aborde le sujet de… »), puis applique le plan correspondant ci-dessous.

━━━ MODE DIAGNOSTIC — situation concrète ━━━
Méthodologie d'analyse de cas RH (Garbe IAE Paris, guide ELISFA).
Déroulé en 3 étapes :
1) IDENTIFIER LE PROBLÈME : éléments de contexte (acteurs, outils, process), causes apparentes vs causes profondes, illustration concrète.
2) PROBLÉMATISER : reformuler la question RH sous-jacente en mobilisant 1-2 cadres théoriques pertinents.
3) RÉSOUDRE : pistes d'action (court / moyen terme), points de vigilance, outils mobilisables, ressources ELISFA.

Pose des QUESTIONS FERMÉES si nécessaire pour préciser : effectif, ancienneté du conflit, IRP en place, etc.
Si la situation relève du juridique pur, redirige vers l'onglet Juridique (Urgence ou Analyse CCN).

━━━ MODE ÉTUDE — sujet général ━━━
Plan type en 6 sections :
1) Définition et enjeux (1 paragraphe court)
2) Cadrage théorique (1-2 auteurs majeurs)
3) Spécificités du secteur associatif / branche ALISFA (IDCC 1261)
4) Outils et dispositifs mobilisables (entretien pro, GEPP, BDESE, accord QVCT, AFEST…)
5) Bonnes pratiques observées
6) Points de vigilance et indicateurs de suivi

━━━ CADRES THÉORIQUES MOBILISABLES (selon pertinence) ━━━
- Mintzberg (configurations structurelles : simple, bureaucratie pro, adhocratie, missionnaire)
- Contrat psychologique (Rousseau 1989) — attentes implicites, ruptures
- Engagement Meyer & Allen (affectif / continuité / normatif)
- Autodétermination Deci & Ryan (autonomie / compétence / lien social)
- EVLN Hirschman (Exit / Voice / Loyalty / Neglect)
- McGregor Théorie X / Théorie Y
- Karasek (demande / latitude / soutien social)
- Hackman & Oldham (caractéristiques motivantes du travail)
- Crozier & Friedberg (analyse stratégique, zones d'incertitude)
- Dejours (psychodynamique du travail)
- Bandura (auto-efficacité)
- Don de travail (Preston 1989, Cottin-Marx 2020) : militant vs non-militant
- Isomorphisme institutionnel DiMaggio & Powell (coercitif / mimétique / normatif)
- Modèle 3P (Personnes / Processus / Politique) · SWOT RH

━━━ SOURCES À CITER ━━━
ANACT, INRS (Gollac 2011), ANI QVCT 2020, Code du travail, ANDRH, Centre Inffo,
Recherches & Solidarités, La Fonda, Avise, CEREQ.
"""
    },
    # ─────────── GOUVERNANCE ───────────
    "gouv_urgence": {
        "label": "Urgence gouvernance",
        "icon": "🚨",
        "module": "gouvernance",
        "placeholder": "Mise en demeure, contrôle URSSAF/fiscal, crise du CA, mise en cause dirigeants…",
        "overlay": """
MODE URGENCE GOUVERNANCE — CRISE ASSOCIATIVE OU MISE EN CAUSE
Tu interviens en mode urgence gouvernance : une crise statutaire, un contrôle administratif/fiscal, une mise en cause des dirigeants ou un conflit ouvert CA ↔ direction nécessite une action dans les heures/jours qui viennent.

━━━ DÉROULÉ OBLIGATOIRE ━━━
1) LE GESTE À FAIRE EN PREMIER — 1 phrase impérative pour préserver la personne morale et ses dirigeants (convoquer un CA extraordinaire, mandater le Président pour répondre, ne surtout rien signer sans avis, demander un délai écrit au contrôleur…).
2) LES OBLIGATIONS LÉGALES QUI S'ACTIVENT IMMÉDIATEMENT :
   - Responsabilité civile des dirigeants (art. 1992 Code civil — mandat)
   - Responsabilité pénale des dirigeants de fait ou de droit (art. 121-2 C. pén.)
   - Tenue des registres légaux (récépissé, statuts, PV d'AG, comptes annuels si > 153 K€ de subvention)
   - Déclaration au greffe des associations de toute modification (art. 5 loi 1901)
3) LES DÉLAIS À NE PAS DÉPASSER :
   - Contrôle URSSAF : accusé de réception + 15 jours pour demander un délai supplémentaire
   - Contrôle fiscal : avis de vérification → 2 jours francs minimum avant 1ère intervention (LPF L47)
   - Mise en demeure → délai inscrit dans la lettre (en général 8 à 30 jours)
   - Convocation d'AG extraordinaire : délais statutaires à respecter strictement
4) LES 3 RISQUES MAJEURS EN CAS D'INACTION :
   - Dissolution judiciaire de l'association (art. 7 loi 1901, cas d'objet illicite ou de gestion fautive)
   - Redressement fiscal avec assujettissement aux impôts commerciaux (art. 206-1 CGI) + intérêts + majorations
   - Mise en cause personnelle des dirigeants (comblement de passif — L651-2 C. com. en cas de liquidation)
5) LES ACTEURS-RESSOURCES À MOBILISER DANS L'ORDRE :
   Président + Trésorier → expert-comptable associatif → avocat en droit des associations/fiscal → DLA → Guid'Asso → fédération (FCSF, ACEPP, FFEC) → le pôle juridique de votre syndicat employeur ELISFA.

━━━ RÈGLES IMPÉRATIVES ━━━
- Cite TOUJOURS : loi du 1er juillet 1901, décret du 16 août 1901, Code civil (art. 1832 et s., 1992), Code général des impôts (art. 206, 261-7 — exonérations sectorielles), Livre des procédures fiscales (L47, L57), Code de commerce (L651-2), BOFiP-impôts (règle des 4P : BOI-IS-CHAMP-10-50-10-20), RGPD et délibérations CNIL.
- Si CONTRÔLE URSSAF/fiscal : ne rien signer avant lecture par un conseil, demander par écrit le délai de 30 jours de l'art. L57 LPF, collecter les pièces justificatives par exercice.
- Si MISE EN DEMEURE : lister les arguments juridiques, répondre dans le délai par LRAR, ne jamais laisser sans réponse.
- Si CRISE INTERNE (démission en bloc du bureau, blocage du CA) : rappeler les voies statutaires (convocation d'AGE, mandat ad hoc, conciliation).
- RAPPEL ABSOLU : ELISFA est un **syndicat employeur** (branche ALISFA), **pas une fédération**. Les fédérations partenaires sont FCSF, ACEPP, FFEC.
- Termine TOUJOURS par : « ⚠️ Face à une mise en cause juridique ou fiscale, la consultation d'un avocat en droit des associations et/ou d'un expert-comptable associatif est indispensable. Votre syndicat employeur ELISFA et vos fédérations peuvent vous orienter (DLA, Guid'Asso). »
"""
    },
    "gouv_juridique": {
        "label": "Juridique gouvernance",
        "icon": "⚖️",
        "module": "gouvernance",
        "placeholder": "Statuts, AG, CA, responsabilité dirigeants, fiscalité associative…",
        "overlay": """
MODE JURIDIQUE GOUVERNANCE — DROIT DES ASSOCIATIONS
Tu réponds aux questions juridiques propres aux associations loi 1901.
Périmètre :
- Loi du 1er juillet 1901 et décret du 16 août 1901
- Loi 2014-856 ESS · Loi 2021-1109 (CER) · Loi 2024-344 (engagement bénévole) · Décret 2025-616 (Certif'Asso)
- Statuts, RI, AG, CA, Bureau, vote, quorum, pouvoirs
- Responsabilité civile et pénale des dirigeants bénévoles
- Fiscalité associative (règle des 4P, franchise commerciale, mécénat, RUP, intérêt général)
- RGPD et associations (CNIL)
- Bénévoles : CEC, FDVA, Passeport Bénévole, congé bénévole 6j/an
Cite : Légifrance, associations.gouv.fr, HCVA, BOFiP, CNIL, Associathèque, La Fonda.
RAPPEL : ELISFA est un **syndicat employeur** (branche ALISFA), **pas une fédération**. Les fédérations sont FCSF, ACEPP, FFEC.
Termine par : « 💡 Pour un accompagnement personnalisé : **votre syndicat employeur ELISFA et vos fédérations** (FCSF, ACEPP, FFEC…) ou un Point d'Appui Vie Associative (DLA, Guid'Asso). »
"""
    },
    "gouv_benevolat": {
        "label": "Gestion des bénévoles",
        "icon": "🤝",
        "module": "gouvernance",
        "placeholder": "CEC, Passeport, congé bénévole, FDVA, mécénat de compétences…",
        "overlay": """
MODE BÉNÉVOLAT — GRH DES NON-SALARIÉS EN ASSOCIATION
Tu aides l'employeur associatif à structurer la gestion de ses bénévoles.
C'est une GRH distincte de celle des salariés (pas de lien de subordination, pas de contrepartie financière), avec des outils et des risques propres.

━━━ PÉRIMÈTRE ━━━
- **Compte d'Engagement Citoyen (CEC)** : 240 €/an, 200h bénévoles minimum, cumulable 5 ans (max 720 €), mobilisable sur le CPF
- **Passeport Bénévole®** (France Bénévolat) : outil de valorisation des compétences et de reconnaissance
- **Congé bénévole** : 6 jours/an (loi 2024-344 du 15 avril 2024)
- **Loi engagement bénévole 2024** : prêts simplifiés jusqu'à 50 000 €, élargissement du mécénat de compétences aux ETI
- **FDVA (Fonds de Développement de la Vie Associative)** : 1-5 K€, dépôt en préfecture, 2 volets (formation / fonctionnement-innovation)
- **Mécénat de compétences** : mise à disposition d'un salarié d'entreprise vers l'association (à titre gratuit, déduction fiscale pour l'entreprise)
- **Valorisation comptable** du bénévolat (règlement ANC n°2018-06) : contributions volontaires en nature au pied du compte de résultat
- **6 piliers GRH bénévole (référentiel ELISFA)** : Recruter · Accueillir · Former · Animer · Reconnaître · Fidéliser
- **Frontière salariat / bénévolat** : risque de requalification en contrat de travail si le bénévole exerce en réalité un emploi salarié déguisé (jurisprudence Cass. soc.)
- **RGPD et bénévoles** : registre des traitements, base légale, durée de conservation
- **Assurance** : responsabilité civile de l'association pour les dommages causés par un bénévole dans l'exercice de ses missions
- **Remboursement de frais** : les bénévoles peuvent renoncer au remboursement → abandon de créance ouvrant droit à déduction fiscale 66 %

━━━ CADRES THÉORIQUES MOBILISABLES ━━━
- Don de travail (Preston 1989, Cottin-Marx 2020) — distinction militant vs non-militant
- Engagement Meyer & Allen appliqué au bénévolat (affectif / continuité / normatif)
- Désengagement et modèle EVLN (Hirschman) appliqué aux bénévoles
- Économie du don (Mauss, Godbout) — don, contre-don, reconnaissance
- Autodétermination Deci & Ryan (autonomie / compétence / lien social) — moteurs de l'engagement durable

━━━ DÉROULÉ ━━━
1) IDENTIFIER LA NATURE DE LA DEMANDE :
   - Stratégique (politique bénévole, parcours de l'engagé·e) → mobilise les 6 piliers
   - Opérationnelle (démarche concrète : déclarer au CEC, monter un dossier FDVA, refuser un bénévole…) → fournis la procédure pas-à-pas
   - Conflit / risque (requalification, désengagement, conflit entre bénévoles et salariés) → diagnostic RH bénévole

2) RÉPONDRE avec :
   - Cadre juridique précis (articles, lois, date d'entrée en vigueur)
   - Dispositifs mobilisables avec conditions d'accès
   - Démarches concrètes (qui fait quoi, avec quel formulaire, auprès de quel interlocuteur)
   - Points de vigilance (juridique, RGPD, assurance, fiscal)

3) ACTEURS-RESSOURCES À CITER :
   France Bénévolat, HCVA, Le Mouvement associatif, Avise, Guid'Asso, DLA,
   associations.gouv.fr, règlement ANC 2018-06, CNIL (RGPD), FDVA (préfecture).

━━━ RAPPEL ━━━
ELISFA est un **syndicat employeur** (branche ALISFA), **pas une fédération**. Les fédérations partenaires sont la FCSF, l'ACEPP, la FFEC.
Termine par : « 💡 Pour une démarche GRH bénévole globale : **votre syndicat employeur ELISFA et vos fédérations** (FCSF, ACEPP, FFEC), Guid'Asso, DLA, ou France Bénévolat pour le Passeport. »
"""
    },
    # ─────────── WIZARDS — Diagnostic, étude & résolution guidée ───────────
    "wizard_juridique": {
        "label": "Diagnostic juridique guidé",
        "icon": "🧭",
        "module": "juridique",
        "placeholder": "(synthèse de wizard juridique)",
        "overlay": WIZARD_RULES + """

DIAGNOSTIC JURIDIQUE GUIDÉ
Tu reçois les réponses d'un diagnostic guidé pas-à-pas. Produis une synthèse structurée selon la méthodologie juridique classique :
1. **Reformulation des faits** (chronologie, acteurs, pièces)
2. **Qualification juridique** (rattachement aux catégories du droit du travail / CCN ALISFA IDCC 1261)
3. **Règles applicables** (Code du travail — articles précis, CCN ALISFA, accords de branche, jurisprudence Cass. soc. récente si pertinente)
4. **Application au cas** (subsomption : la règle s'applique-t-elle ? avec quelles nuances ?)
5. **Conclusion juridique** (l'action envisagée est-elle régulière ? Quels risques contentieux ?)
6. **Plan d'actions chronologique** (à faire dans les 24h / 7j / 30j, avec délais légaux)
7. **Points de vigilance** (3 risques majeurs)
8. **📚 Ressources et liens officiels** :
   - Légifrance Code du travail : https://www.legifrance.gouv.fr/codes/texte_lc/LEGITEXT000006072050/
   - CCN ALISFA (IDCC 1261) : https://www.legifrance.gouv.fr/conv_coll/id/KALICONT000005635177
   - Service-Public Pro (employeurs) : https://entreprendre.service-public.fr/vosdroits/N31137
   - Cour de cassation : https://www.courdecassation.fr/recherche-judilibre
   - Ministère du Travail : https://travail-emploi.gouv.fr/
Termine par : « ⚠️ Cette synthèse est issue d'un diagnostic automatisé. Saisissez le pôle juridique ELISFA pour une consultation individualisée. »
RAPPEL : ELISFA est un **syndicat** employeur, pas une fédération.
"""
    },
    "wizard_rh": {
        "label": "Diagnostic RH guidé",
        "icon": "🧭",
        "module": "rh",
        "placeholder": "(synthèse de wizard RH)",
        "overlay": WIZARD_RULES + """

DIAGNOSTIC RH GUIDÉ
Tu reçois les réponses d'un diagnostic RH guidé pas-à-pas. Produis une synthèse rigoureuse mobilisant la sociologie des organisations et la GRH :

**Méthodes à mobiliser (cite l'auteur et le concept) :**
- Karasek (demande / latitude / soutien social) → cartographie du stress
- Hackman & Oldham → caractéristiques motivantes du travail
- Crozier & Friedberg → analyse stratégique des acteurs et zones d'incertitude
- Rousseau (1989) → contrat psychologique et sa rupture
- Hirschman → modèle EVLN (Exit / Voice / Loyalty / Neglect)
- Meyer & Allen → engagement affectif / continuité / normatif
- Dejours → psychodynamique du travail
- Mintzberg → configuration organisationnelle
- Don de travail (Preston, Cottin-Marx) si association

**Plan obligatoire en 5 sections :**
1. **Reformulation du symptôme** (ce qui est observable, mesurable)
2. **Diagnostic à 3 niveaux** : individu / équipe / organisation
3. **Cadrage théorique** : choisis 2 cadres pertinents et explique-les en 3-4 phrases chacun
4. **Plan d'actions** :
   - Court terme (15j) : 3 gestes managériaux concrets
   - Moyen terme (3 mois) : dispositifs RH à mettre en place
   - Long terme (12 mois) : transformation organisationnelle
5. **Indicateurs de suivi** (3 KPI mesurables : turnover, AT, climat…)

**📚 Ressources et liens officiels** :
- ANACT (RPS, QVCT, AFEST) : https://www.anact.fr/
- INRS (Karasek, RPS) : https://www.inrs.fr/risques/psychosociaux/
- Travailler-mieux : https://travail-emploi.gouv.fr/sante-au-travail/
- ANI QVCT 2020 : https://travail-emploi.gouv.fr/IMG/pdf/ani-qvct-2020.pdf
- CEREQ (recherches GRH) : https://www.cereq.fr/
- Recherches & Solidarités (chiffres associatifs) : https://recherches-solidarites.org/

Termine par : « 💡 Pour un accompagnement personnalisé : **votre syndicat employeur ELISFA et vos fédérations** (FCSF, ACEPP, FFEC), DLA ou Guid'Asso. »
RAPPEL : ELISFA est un **syndicat** employeur, pas une fédération.
"""
    },
    "wizard_formation": {
        "label": "Diagnostic formation guidé",
        "icon": "🧭",
        "module": "formation",
        "placeholder": "(synthèse de wizard formation)",
        "overlay": WIZARD_RULES + """

DIAGNOSTIC FORMATION GUIDÉ
Tu reçois les réponses d'un diagnostic formation pas-à-pas. Produis une synthèse en ingénierie pédagogique :

**Plan obligatoire en 6 sections :**
1. **Cadrage du besoin** (origine, public, compétence visée — savoir / savoir-faire / savoir-être)
2. **Dispositif(s) recommandé(s)** : compare 2-3 dispositifs (CPF, plan de développement des compétences, Pro-A, AFEST, alternance, PTP, VAE) avec qui finance / qui décide / durée / conditions
3. **Financement** : Uniformation (OPCO Cohésion sociale), CPNEF Branche, France compétences, abondements possibles
4. **Cadre juridique** : articles L.6311 et suivants du Code du travail, obligations employeur (entretien pro tous les 2 ans, état des lieux 6 ans, abondement correctif)
5. **Démarches étape par étape** (qui fait quoi, quand, avec quel formulaire)
6. **Évaluation** : niveaux Kirkpatrick (réaction / apprentissage / comportement / résultats)

**📚 Ressources et liens officiels** :
- Mon Compte Formation : https://www.moncompteformation.gouv.fr/
- Uniformation (OPCO Cohésion sociale) : https://www.uniformation.fr/
- Centre Inffo : https://www.centre-inffo.fr/
- France compétences : https://www.francecompetences.fr/
- Code du travail (formation) : https://www.legifrance.gouv.fr/codes/section_lc/LEGITEXT000006072050/LEGISCTA000006195856/
- ANACT (AFEST) : https://www.anact.fr/themes/afest
- Qualiopi : https://travail-emploi.gouv.fr/formation-professionnelle/qualite-de-la-formation/qualiopi-marque-de-certification-qualite-des-prestataires-de-formation/

Termine par : « 💡 Pour étudier votre plan de développement : votre conseiller Uniformation ou le syndicat ELISFA. »
RAPPEL : ELISFA est un **syndicat** employeur, pas une fédération.
"""
    },
    "wizard_gouvernance": {
        "label": "Diagnostic gouvernance guidé",
        "icon": "🧭",
        "module": "gouvernance",
        "placeholder": "(synthèse de wizard gouvernance)",
        "overlay": WIZARD_RULES + """

DIAGNOSTIC GOUVERNANCE GUIDÉ
Tu reçois les réponses d'un diagnostic gouvernance pas-à-pas. Produis une synthèse mêlant droit des associations (loi 1901) et sociologie des associations.

**Cadres à mobiliser :**
- Loi du 1er juillet 1901 + décret 16 août 1901
- Loi 2014-856 ESS, loi 2021-1109 CER, loi 2024-344, décret 2025-616 Certif'Asso
- Triptyque diagnostic associatif : Comprendre / Analyser / Agir
- 7 composantes (Environnement / Dispositif de projet / Culture / Structure instituée / Interactions / Services / Espace public)
- Boltanski & Thévenot — 5 logiques (civique, marchande, domestique, industrielle, inspirée)
- DiMaggio & Powell — isomorphisme institutionnel (coercitif / mimétique / normatif)
- Crozier & Friedberg — jeu d'acteurs et zones d'incertitude

**Plan obligatoire en 6 sections :**
1. **Reformulation de la situation** (objet, taille, modèle de gouvernance)
2. **Cadrage juridique loi 1901** (statuts, AG, CA, responsabilité dirigeants, fiscalité, RGPD selon le cas)
3. **Lecture sociologique** (logiques en tension Boltanski-Thévenot, jeu d'acteurs Crozier)
4. **Risques identifiés** (juridiques, fiscaux, gouvernance, RH)
5. **Plan d'actions chronologique** (15j / 3 mois / 12 mois) avec qui fait quoi
6. **Accompagnements mobilisables** (DLA, Guid'Asso, fédération employeur FCSF/ACEPP/FFEC, syndicat ELISFA, HCVA)

**📚 Ressources et liens officiels** :
- Associations.gouv.fr : https://www.associations.gouv.fr/
- Guid'Asso : https://www.associations.gouv.fr/guid-asso.html
- Légifrance loi 1901 : https://www.legifrance.gouv.fr/loda/id/LEGITEXT000006069570/
- BOFiP fiscalité associative : https://bofip.impots.gouv.fr/bofip/2225-PGP.html
- CNIL associations : https://www.cnil.fr/fr/associations-vos-obligations-rgpd
- HCVA : https://www.associations.gouv.fr/le-hcva.html
- Avise / DLA : https://www.avise.org/
- Le Mouvement associatif : https://lemouvementassociatif.org/
- Recherches & Solidarités : https://recherches-solidarites.org/

Termine par : « 💡 Pour un accompagnement gouvernance : **votre syndicat employeur ELISFA et vos fédérations** (FCSF, ACEPP, FFEC), DLA gratuit ou Guid'Asso. »
RAPPEL CRITIQUE : ELISFA est un **syndicat** employeur de la branche ALISFA, **PAS une fédération**. Les fédérations sont la FCSF, l'ACEPP, la FFEC.
"""
    },
}

# ─── Alias de rétrocompatibilité ───
# Certains clients en cache peuvent encore envoyer les anciens IDs
# (rh_diagnostic, rh_etude) avant fusion. On les redirige silencieusement
# vers la nouvelle fonction unifiée rh_analyse pour éviter la perte d'overlay.
FUNCTION_PROMPTS["rh_diagnostic"] = FUNCTION_PROMPTS["rh_analyse"]
FUNCTION_PROMPTS["rh_etude"] = FUNCTION_PROMPTS["rh_analyse"]

def get_function_overlay(function_id):
    """Retourne l'overlay de prompt pour une fonction donnée, ou chaîne vide."""
    if not function_id or function_id not in FUNCTION_PROMPTS:
        return "", None
    fn = FUNCTION_PROMPTS[function_id]
    return fn["overlay"], fn


# ══════════════════════════════════════════════
#  GUIDES — Référentiel théorique et méthodologique
#  injecté dans le system prompt selon le module/fonction
# ══════════════════════════════════════════════

GUIDE_HEADER_RH = """

═══ GUIDE DE RÉFÉRENCE — ANALYSE & RÉSOLUTION DE CAS RH ═══
Le guide ci-dessous est ton RÉFÉRENTIEL OFFICIEL pour :
  1) EXPLIQUER la partie théorique (cadres, auteurs, concepts) quand l'utilisateur
     a besoin de comprendre POURQUOI un phénomène RH se produit ;
  2) GUIDER PAS À PAS la démarche de diagnostic RH ou de conseil RH, en
     respectant les étapes et la grille d'analyse proposées.
Tu CITES explicitement les auteurs et concepts du guide quand c'est pertinent
(Mintzberg, Meyer & Allen, Deci & Ryan, Rousseau, EVLN/Hirschman, McGregor,
DiMaggio & Powell, Cottin-Marx, Karasek, Hackman & Oldham, Crozier & Friedberg…).
Tu utilises le modèle 3P (Personnes / Processus / Politique) et la SWOT RH
quand le diagnostic le requiert. Tu ne t'éloignes JAMAIS de la méthode du guide
quand tu es en mode diagnostic.

──────── DÉBUT DU GUIDE ────────
{GUIDE}
──────── FIN DU GUIDE ────────
"""

GUIDE_HEADER_GOUV = """

═══ GUIDE DE RÉFÉRENCE — DIAGNOSTIC ASSOCIATIF ═══
Le guide ci-dessous est ton RÉFÉRENTIEL OFFICIEL pour :
  1) EXPLIQUER les fondements théoriques de la vie associative
     (Boltanski/Thévenot, Mintzberg, DiMaggio/Powell, Habermas, Polanyi,
     Crozier/Friedberg, Schein, Touraine, Reynaud…) ;
  2) GUIDER pas à pas une démarche de DIAGNOSTIC ASSOCIATIF complet
     (Comprendre → Analyser → Agir) avec les outils SWOT, PESTEL, et la
     grille à 7 composantes (Environnement, Dispositif de projet, Culture,
     Structure instituée, Interactions, Production de services, Espace public).
Tu RESPECTES la structure du guide, tu CITES les concepts et auteurs quand
c'est pertinent, et tu PROPOSES TOUJOURS des questions structurantes pour
faire avancer le diagnostic.

──────── DÉBUT DU GUIDE ────────
{GUIDE}
──────── FIN DU GUIDE ────────
"""

def get_module_guide_block(module, function_id):
    """Renvoie le bloc de guide à injecter selon le module et la fonction.
    Le guide RH est injecté pour le module RH (toutes fonctions).
    Le guide diagnostic associatif est injecté pour le module gouvernance.
    """
    if module == "rh" and GUIDE_CAS_RH:
        return GUIDE_HEADER_RH.replace("{GUIDE}", GUIDE_CAS_RH)
    if module == "gouvernance" and GUIDE_DIAG_ASSO:
        return GUIDE_HEADER_GOUV.replace("{GUIDE}", GUIDE_DIAG_ASSO)
    return ""


def build_context_formation(search_results):
    """Construit le contexte pour le module formation."""
    if not search_results:
        return "AUCUN EXTRAIT TROUVÉ DANS LA BASE FORMATION."
    ctx = "EXTRAITS DE LA BASE FORMATION ELISFA :\n\n"
    for i, r in enumerate(search_results, 1):
        article = r["article"]
        resp = article["reponse"]
        ctx += f"--- Extrait {i} (thème : {r['theme_label']}) ---\n"
        ctx += f"Question type : {article['question_type']}\n"
        ctx += f"Synthèse : {resp.get('synthese', 'N/A')}\n"
        ctx += f"Minimum légal : {resp.get('minimum_legal', 'N/A')}\n"
        ctx += f"Les + formation : {resp.get('plus_formation', 'N/A')}\n"
        ctx += f"Sources : {', '.join(resp.get('sources', []))}\n"
        ctx += "\n"
    return ctx

# ── Niveaux formation (remplace escalade pour le module formation) ──
FORMATION_LEVELS = {
    "minimum_legal": {
        "label": "Minimum légal",
        "description": "Ce que l'employeur doit obligatoirement respecter.",
        "color": "blue"
    },
    "plus_formation": {
        "label": "Les + pour aller plus loin",
        "description": "Dispositifs et financements supplémentaires pour aller au-delà.",
        "color": "green"
    }
}

def build_context(search_results):
    if not search_results:
        return "AUCUN EXTRAIT TROUVÉ DANS LA BASE DOCUMENTAIRE."
    ctx = "EXTRAITS DE LA BASE DOCUMENTAIRE ELISFA :\n\n"
    for i, r in enumerate(search_results, 1):
        a = r["article"]
        resp = a["reponse"]
        ctx += f"--- Extrait {i} (Thème : {r['theme_label']}, Niveau : {r['niveau']}) ---\n"
        ctx += f"Question type : {a.get('question_type', '')}\n"
        ctx += f"Synthèse : {resp.get('synthese', 'N/A')}\n"
        ctx += f"Fondement légal : {resp.get('fondement_legal', 'N/A')}\n"
        ctx += f"Fondement CCN : {resp.get('fondement_ccn', 'N/A')}\n"
        ctx += f"Application : {resp.get('application', 'N/A')}\n"
        ctx += f"Vigilance : {resp.get('vigilance', 'N/A')}\n"
        ctx += f"Sources : {', '.join(resp.get('sources', []))}\n"
        if resp.get("escalade"):
            ctx += f"ESCALADE REQUISE : {resp.get('message_escalade', 'Contacter le pôle juridique ELISFA.')}\n"
        ctx += "\n"
    return ctx

# ── Collecte des liens et fiches depuis les résultats ──
def collect_links_and_fiches(search_results):
    """Extrait les liens et fiches pratiques des articles trouvés."""
    liens = []
    fiches = []
    seen_urls = set()
    seen_fiches = set()

    for r in search_results:
        article = r["article"]
        # Liens
        for lien in article.get("reponse", {}).get("liens", []):
            if lien["url"] not in seen_urls:
                seen_urls.add(lien["url"])
                liens.append(lien)
        # Fiches pratiques
        for fiche in article.get("fiches_pratiques", []):
            if fiche["fichier"] not in seen_fiches:
                seen_fiches.add(fiche["fichier"])
                fiches.append(fiche)

    return liens, fiches

# ══════════════════════════════════════════════
#     Orchestrateur — Validation & config module
# ══════════════════════════════════════════════
# Bornes strictes pour les champs utilisateur dans /api/ask.
# But : éviter DoS par payload géant, prompt stuffing, logs saturés.
MAX_QUESTION_CHARS = 5000        # question libre (une question précise < 2K en pratique)
MAX_DOC_CONTEXT_CHARS = 120000   # document joint (PDF/OCR). ~30-40K tokens.
MAX_DOC_NAME_CHARS = 200         # nom de fichier affiché
MAX_HISTORY_MESSAGES = 20        # 10 paires user/assistant
MAX_CONTEXT_ENTRIES = 20         # clés pré-chat
MAX_CONTEXT_KEY_CHARS = 60
MAX_CONTEXT_VAL_CHARS = 200

# Table de config par module. Remplace les chaînes if/elif dispersées.
# Chaque entrée regroupe les 3 éléments corrélés : system_prompt,
# knowledge base, et context builder. Étendre = ajouter une entrée.
MODULE_CONFIG = {
    "juridique": {
        "system_prompt": SYSTEM_PROMPT,
        "kb": KB,
        "context_builder": build_context,
    },
    "formation": {
        "system_prompt": SYSTEM_PROMPT_FORMATION,
        "kb": KB_FORMATION,
        "context_builder": build_context_formation,
    },
    "rh": {
        "system_prompt": SYSTEM_PROMPT_RH,
        "kb": KB_RH,
        "context_builder": build_context,
    },
    "gouvernance": {
        "system_prompt": SYSTEM_PROMPT_GOUVERNANCE,
        "kb": KB_GOUVERNANCE,
        "context_builder": build_context,
    },
}

# ── Notifications (email + webhook) ──
# Architecture : les handlers Flask appellent des wrappers async qui lancent
# un thread daemon exécutant la fonction bloquante avec retries exponentiels.
# Bénéfice : /api/rdv et /api/email-juriste répondent en ~50ms au lieu
# d'attendre la poignée de main SMTP (0.5–3s) ou le POST webhook (50–500ms).
# En cas d'échec, le thread retry 3x (1s, 2s, 4s) avant d'abandonner — un log
# ERROR est produit, l'utilisateur reste informé via la réponse API.
_NOTIF_RETRY_BACKOFF = (1.0, 2.0, 4.0)  # 3 tentatives max

def _send_email_sync(subject, body_html, to_email=None):
    """Envoi SMTP bloquant avec retries exponentiels.

    Retourne True si l'email part au moins à la Nième tentative, False sinon.
    Utilisé directement pour les cas où le caller VEUT la confirmation (rare),
    ou via _run_async() pour fire-and-forget.
    """
    if not SMTP_USER or not SMTP_PASS:
        logging.warning("SMTP non configuré — email '%s' ignoré", subject[:60])
        return False
    dest = to_email or JURISTE_EMAIL
    last_err = None
    for attempt, delay in enumerate(_NOTIF_RETRY_BACKOFF, start=1):
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = SMTP_FROM
            msg["To"] = dest
            msg.attach(MIMEText(body_html, "html", "utf-8"))
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASS)
                server.send_message(msg)
            logging.info("[notif.email] ok dest=%s subject=%s attempt=%d",
                         dest, subject[:60], attempt)
            return True
        except (smtplib.SMTPException, OSError) as e:
            last_err = e
            logging.warning(
                "[notif.email] tentative %d/%d KO dest=%s err=%s",
                attempt, len(_NOTIF_RETRY_BACKOFF), dest, e
            )
            if attempt < len(_NOTIF_RETRY_BACKOFF):
                threading.Event().wait(delay)
    logging.error("[notif.email] abandon après %d tentatives dest=%s err=%s",
                  len(_NOTIF_RETRY_BACKOFF), dest, last_err)
    return False

def _send_webhook_sync(payload):
    """POST webhook bloquant avec retries exponentiels."""
    if not NOTIFICATION_WEBHOOK_URL:
        return False
    import urllib.request, urllib.error
    data = json.dumps(payload).encode("utf-8")
    last_err = None
    for attempt, delay in enumerate(_NOTIF_RETRY_BACKOFF, start=1):
        try:
            req = urllib.request.Request(
                NOTIFICATION_WEBHOOK_URL,
                data=data,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                ok = 200 <= resp.status < 300
                if ok:
                    logging.info("[notif.webhook] ok status=%s attempt=%d",
                                 resp.status, attempt)
                    return True
                last_err = f"HTTP {resp.status}"
        except (urllib.error.URLError, OSError) as e:
            last_err = e
        logging.warning("[notif.webhook] tentative %d/%d KO err=%s",
                        attempt, len(_NOTIF_RETRY_BACKOFF), last_err)
        if attempt < len(_NOTIF_RETRY_BACKOFF):
            threading.Event().wait(delay)
    logging.error("[notif.webhook] abandon après %d tentatives err=%s",
                  len(_NOTIF_RETRY_BACKOFF), last_err)
    return False

def _run_async(target, *args, **kwargs):
    """Lance un thread daemon pour une tâche fire-and-forget.
    daemon=True garantit qu'un shutdown du process n'est pas bloqué.
    """
    t = threading.Thread(target=target, args=args, kwargs=kwargs, daemon=True)
    t.start()
    return t

def send_email_notification(subject, body_html, to_email=None, sync=False):
    """Envoi email. Par défaut asynchrone (fire-and-forget).

    sync=True → bloque et retourne True/False selon succès réel (utilisé si
    le caller doit absolument savoir). sync=False → retourne True si SMTP
    configuré (l'envoi est tenté en background avec retries).
    """
    if not SMTP_USER or not SMTP_PASS:
        logging.warning("SMTP non configuré — email '%s' ignoré", subject[:60])
        return False
    if sync:
        return _send_email_sync(subject, body_html, to_email)
    _run_async(_send_email_sync, subject, body_html, to_email)
    return True

def send_webhook_notification(payload, sync=False):
    """POST webhook. Par défaut asynchrone."""
    if not NOTIFICATION_WEBHOOK_URL:
        return False
    if sync:
        return _send_webhook_sync(payload)
    _run_async(_send_webhook_sync, payload)
    return True

# ── Journalisation ──
def log_interaction(question, niveau, theme, sources, decision, extra=None):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "question_hash": hashlib.sha256(question.encode()).hexdigest()[:12],
        "theme": theme,
        "niveau": niveau,
        "nb_sources": len(sources),
        "decision": decision,
    }
    if extra:
        entry.update(extra)
    logging.info(json.dumps(entry, ensure_ascii=False))
    log_file = LOG_DIR / "interactions.jsonl"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

# ── Vérification webhook ──
def verify_webhook_signature(payload, signature):
    expected = hmac.new(WEBHOOK_SECRET.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)

# ── Profils utilisateurs ──
USER_PROFILES = {
    "benevole_president": {
        "type": "benevole",
        "label": "Président·e bénévole d'association",
        "context": "Président·e bénévole du conseil d'administration d'une association ALISFA (centre social, crèche, EVS). Responsable employeur non professionnel, a besoin d'explications accessibles sur ses obligations, les risques juridiques, la gestion RH et la gouvernance associative."
    },
    "benevole_bureau": {
        "type": "benevole",
        "label": "Membre du bureau / Trésorier·ère",
        "context": "Membre bénévole du bureau ou trésorier·ère d'une association ALISFA. Impliqué·e dans les décisions RH et financières, a besoin de comprendre les impacts budgétaires des décisions sociales, les obligations légales liées à la fonction employeur et la CCN."
    },
    "pro_directeur": {
        "type": "professionnel",
        "label": "Directeur·rice de structure",
        "context": "Directeur·rice professionnel·le d'une structure ALISFA. Gère l'équipe, le budget, les relations partenariales. Maîtrise les bases du droit du travail et de la CCN mais a besoin de précisions techniques, de jurisprudence et d'aide à la décision sur des cas complexes."
    },
    "pro_rh": {
        "type": "professionnel",
        "label": "Responsable RH / Paie",
        "context": "Responsable RH ou chargé·e de paie d'une structure ALISFA. Gère les contrats, la paie, les congés, la formation, la classification et l'application quotidienne de la CCN. A besoin de réponses techniques précises avec références aux articles, calculs de salaire détaillés et procédures RH."
    },
    "pro_admin": {
        "type": "professionnel",
        "label": "Responsable administratif & financier",
        "context": "Responsable administratif et financier d'une structure ALISFA. Supervise la gestion financière, les budgets, la conformité administrative et les obligations sociales. Intéressé·e par les coûts, les charges, les simulations budgétaires liées aux salaires et aux obligations employeur."
    }
}

# ══════════════════════════════════════════════
#       Personnalisation du prompt (6 critères)
# ══════════════════════════════════════════════

# Catégorie 1 — mots-clés de détection du module à partir de la question
MODULE_KEYWORDS = {
    "juridique": [
        "contrat", "cdi", "cdd", "licenciement", "rupture", "démission", "préavis",
        "faute", "sanction", "disciplinaire", "prud'homme", "conseil", "indemnité",
        "classification", "coefficient", "salaire", "rémunération", "convention",
        "avenant", "accord", "ccn", "article", "code du travail", "jurisprudence",
    ],
    "rh": [
        "entretien professionnel", "bilan", "évaluation", "gepp", "gpec",
        "recrutement", "embauche", "dpae", "période d'essai", "intégration",
        "qvct", "duerp", "rps", "harcèlement", "burn-out", "conflit d'équipe",
        "cse", "représentant", "dialogue social", "nao", "turnover", "absentéisme",
    ],
    "formation": [
        "formation", "cpf", "opco", "uniformation", "vae", "bilan de compétences",
        "plan de développement", "apprentissage", "alternance", "tuteur",
        "certification", "qualification", "pro-a", "cep", "fongecif",
    ],
    "gouvernance": [
        "ag", "assemblée générale", "ca ", "conseil d'administration", "bureau",
        "statuts", "loi 1901", "association", "président", "trésorier", "bénévole",
        "bénévolat", "employeur bénévole", "fonda", "udes", "elisfa",
        "fédération", "fcsf", "acepp", "patronat associatif", "cppni",
    ],
}

# Catégorie 6 — mots-clés d'urgence
URGENCY_KEYWORDS = [
    "licenciement", "rupture immédiate", "abandon de poste", "mise à pied",
    "conflit", "harcèlement", "discrimination", "danger grave",
    "prud'homme", "prudhomme", "prud'hommes", "contentieux", "assignation",
    "inspection du travail", "burn-out", "épuisement", "suicide",
    "agression", "plainte", "procédure", "urgent", "urgence",
    "demain", "aujourd'hui", "délai", "prescription",
]

def detect_module_from_question(question: str, current_module: str) -> tuple[str, float]:
    """Retourne (module_suggéré, score). Si score bas → on garde current_module."""
    q = question.lower()
    scores = {m: 0 for m in MODULE_KEYWORDS}
    for mod, kws in MODULE_KEYWORDS.items():
        for kw in kws:
            if kw in q:
                scores[mod] += 1
    best = max(scores, key=scores.get)
    return (best, scores[best]) if scores[best] > 0 else (current_module, 0)

def detect_urgency(question: str) -> tuple[bool, list[str]]:
    """Retourne (is_urgent, matched_keywords)."""
    q = question.lower()
    hits = [kw for kw in URGENCY_KEYWORDS if kw in q]
    return (len(hits) > 0, hits)

def _extract_structure_hint(user_context: dict) -> str:
    """Extrait un libellé de structure/centre depuis le contexte pré-chat."""
    if not isinstance(user_context, dict):
        return ""
    for key in ("structure", "nom_structure", "centre", "association", "organisme", "employeur"):
        for k, v in user_context.items():
            if isinstance(k, str) and isinstance(v, str) and key in k.lower() and v.strip():
                return v.strip()[:120]
    return ""

def _extract_region_hint(user_context: dict) -> str:
    """Extrait une région depuis le contexte pré-chat."""
    if not isinstance(user_context, dict):
        return ""
    for k, v in user_context.items():
        if isinstance(k, str) and isinstance(v, str) and ("région" in k.lower() or "region" in k.lower() or "département" in k.lower() or "ville" in k.lower()) and v.strip():
            return v.strip()[:80]
    return ""

def _history_topics(conversation_history: list) -> list[str]:
    """Extrait des mots-clés saillants des dernières questions utilisateur pour éviter les redites."""
    if not conversation_history:
        return []
    topics = []
    for msg in conversation_history[-10:]:
        if isinstance(msg, dict) and msg.get("role") == "user":
            txt = str(msg.get("content", "")).strip()
            if txt:
                topics.append(txt[:140])
    return topics[-5:]

def build_personalization_block(profile_id, user_context, conversation_history,
                                question, active_module, rdv_already_proposed):
    """Construit le bloc de personnalisation à 6 critères injecté dans le system prompt.
    Retourne (bloc_text, meta) où meta contient {urgency, urgency_keywords,
    suggested_module, propose_rdv, structure, region}."""
    profile = USER_PROFILES.get(profile_id) if profile_id else None
    structure = _extract_structure_hint(user_context or {})
    region = _extract_region_hint(user_context or {})
    history_topics = _history_topics(conversation_history or [])
    suggested_module, mod_score = detect_module_from_question(question, active_module)
    is_urgent, urgency_hits = detect_urgency(question)
    propose_rdv = is_urgent and not rdv_already_proposed

    lines = ["", "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
             "PERSONNALISATION DE LA RÉPONSE — 6 critères",
             "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"]

    # 1. RÔLE
    if profile:
        tone = ("Vulgarise au maximum : phrases courtes, analogies concrètes, "
                "évite le jargon, mets en avant les obligations et risques essentiels."
                if profile["type"] == "benevole" else
                "Réponse technique assumée : articles précis, chiffrage, procédure, "
                "jurisprudence si pertinent, vocabulaire RH/juridique professionnel.")
        lines.append(f"1. RÔLE — {profile['label']} ({profile['type']}). {tone}")
    else:
        lines.append("1. RÔLE — profil non renseigné. Adopte un ton neutre intermédiaire.")

    # 2. STRUCTURE
    if structure:
        lines.append(f"2. STRUCTURE — « {structure} ». Quand tu donnes un exemple, nomme-la ou "
                     f"adapte le scénario à ce type de structure (centre social, crèche, EVS, fédération…).")
    else:
        lines.append("2. STRUCTURE — non précisée. Reste générique, propose des exemples plausibles "
                     "pour un centre social / une crèche associative / un EVS.")

    # 3. RÉGION
    if region:
        lines.append(f"3. RÉGION — « {region} ». Si la question touche à un accompagnement local "
                     f"(DLA, fédération employeur, Carsat, DREETS…), oriente vers le **syndicat ELISFA** (national) "
                     f"et/ou la **fédération employeur locale** (FCSF, ACEPP, FFEC…). ELISFA n'est PAS une fédération.")
    else:
        lines.append("3. RÉGION — non précisée. Si un relais territorial est pertinent, invite "
                     "l'utilisateur à préciser sa région pour être orienté vers sa fédération employeur locale "
                     "(FCSF, ACEPP, FFEC…). Rappel : ELISFA est un syndicat, pas une fédération.")

    # 4. HISTORIQUE
    if history_topics:
        joined = " | ".join(h[:80] for h in history_topics)
        lines.append(f"4. HISTORIQUE — déjà évoqué dans la session : {joined}. "
                     f"NE RÉPÈTE PAS les définitions / fondements déjà donnés : "
                     f"renvoie à ta réponse précédente et apporte uniquement l'information NOUVELLE.")
    else:
        lines.append("4. HISTORIQUE — première question de la session. Pose proprement le cadre "
                     "avant d'entrer dans le détail.")

    # 5. MODULE DÉTECTÉ
    if mod_score > 0 and suggested_module != active_module:
        lines.append(f"5. MODULE — l'utilisateur est sur « {active_module} » mais la question "
                     f"semble relever de « {suggested_module} » (score={mod_score}). "
                     f"Traite-la dans l'angle {active_module} et, en fin de réponse, suggère "
                     f"explicitement de rouvrir la question dans le module « {suggested_module} » "
                     f"pour un approfondissement.")
    else:
        lines.append(f"5. MODULE — {active_module} (cohérent avec la question). Ne sors pas de ce périmètre.")

    # 6. URGENCE
    if is_urgent:
        hits_txt = ", ".join(urgency_hits[:4])
        rdv_instr = ("PROPOSE UNE FOIS un RDV avec le pôle juridique ELISFA via un encart "
                     "« 📅 Prendre RDV avec un juriste » en fin de réponse. "
                     "Pas de RDV dans les réponses suivantes sauf nouvelle situation critique."
                     if propose_rdv else
                     "RDV déjà proposé plus tôt dans la session — NE LE RÉPÈTE PAS, "
                     "rappelle simplement l'option d'un mot en fin de réponse.")
        lines.append(f"6. URGENCE — DÉTECTÉE (mots-clés : {hits_txt}). "
                     f"Passe à un ton direct, priorise l'action immédiate, "
                     f"liste les délais légaux en tête. {rdv_instr}")
    else:
        lines.append("6. URGENCE — non détectée. Ton pédagogique standard.")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    block = "\n".join(lines)
    meta = {
        "urgency": is_urgent,
        "urgency_keywords": urgency_hits,
        "suggested_module": suggested_module if mod_score > 0 else None,
        "module_score": mod_score,
        "propose_rdv": propose_rdv,
        "structure": structure or None,
        "region": region or None,
    }
    return block, meta

# ══════════════════════════════════════════════
#                  ROUTES
# ══════════════════════════════════════════════

@app.after_request
def _no_cache_html(response):
    """Empêche la mise en cache navigateur du HTML pour éviter les versions obsolètes
    après un rebuild. Les assets statiques (JS/CSS/images) gardent leur cache normal."""
    ctype = response.headers.get("Content-Type", "")
    if ctype.startswith("text/html"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/admin")
@require_admin
def admin():
    return render_template("admin.html")

# ── Servir les fiches pratiques ──
@app.route("/fiches/<path:filename>")
def serve_fiche(filename):
    fiches_dir = BASE_DIR.parent / "fiches_pratiques"
    if not fiches_dir.exists():
        fiches_dir = FICHES_DIR
    # Sécurité : empêcher le directory traversal
    file_path = (fiches_dir / filename).resolve()
    if not str(file_path).startswith(str(fiches_dir.resolve())):
        abort(403)
    return send_from_directory(str(fiches_dir), filename)

# ══════════════════════════════════════════════
#            API — Question/Réponse
# ══════════════════════════════════════════════

# ══════════════════════════════════════════════
#   WIZARD — Ressources serveur (post-processing)
# ══════════════════════════════════════════════
WIZARD_RESOURCES = {
    "wizard_juridique": [
        ("Légifrance — Code du travail", "https://www.legifrance.gouv.fr/codes/texte_lc/LEGITEXT000006072050/"),
        ("CCN ALISFA (IDCC 1261)", "https://www.legifrance.gouv.fr/conv_coll/id/KALICONT000005635177/"),
        ("Cour de cassation — chambre sociale", "https://www.courdecassation.fr/recherche-judilibre"),
        ("Service-Public.fr — Professionnels", "https://entreprendre.service-public.fr/"),
        ("ANACT — Qualité de vie au travail", "https://www.anact.fr/"),
        ("INRS — Risques psychosociaux", "https://www.inrs.fr/risques/psychosociaux/ce-qu-il-faut-retenir.html"),
    ],
    "wizard_rh": [
        ("INRS — Modèle de Karasek", "https://www.inrs.fr/risques/psychosociaux/facteurs-risques.html"),
        ("ANACT — QVCT", "https://www.anact.fr/qvct-qualite-de-vie-et-des-conditions-de-travail"),
        ("ANI QVCT 2020 (PDF)", "https://www.anact.fr/sites/default/files/2021-02/ani_qvct_9_decembre_2020.pdf"),
        ("Rapport Gollac 2011 — Risques psychosociaux (PDF)", "https://travail-emploi.gouv.fr/IMG/pdf/rapport_SRPST_definitif_rectifie_11_05_10.pdf"),
        ("CEREQ — Études et recherches RH", "https://www.cereq.fr/"),
        ("Recherches & Solidarités — Branche associative", "https://recherches-solidarites.org/"),
    ],
    "wizard_formation": [
        ("Code du travail — Formation (L.6311-1 et s.)", "https://www.legifrance.gouv.fr/codes/section_lc/LEGITEXT000006072050/LEGISCTA000006195936/"),
        ("Mon Compte Formation (CPF)", "https://www.moncompteformation.gouv.fr/"),
        ("Uniformation — OPCO Cohésion sociale", "https://www.uniformation.fr/"),
        ("France compétences", "https://www.francecompetences.fr/"),
        ("Centre Inffo — Droit de la formation", "https://www.centre-inffo.fr/"),
        ("ANACT — AFEST", "https://www.anact.fr/afest-laction-de-formation-en-situation-de-travail"),
        ("Qualiopi — Référentiel national qualité", "https://travail-emploi.gouv.fr/formation-professionnelle/acteurs-cadre-et-qualite-de-la-formation-professionnelle/qualiopi-marque-de-certification-qualite-des-prestataires-de-formation/"),
    ],
    "wizard_gouvernance": [
        ("Légifrance — Loi du 1er juillet 1901", "https://www.legifrance.gouv.fr/loda/id/LEGITEXT000006069570/"),
        ("Associations.gouv.fr", "https://www.associations.gouv.fr/"),
        ("BOFiP — Fiscalité des associations", "https://bofip.impots.gouv.fr/bofip/2113-PGP.html"),
        ("CNIL — Associations & RGPD", "https://www.cnil.fr/fr/associations"),
        ("HCVA — Haut Conseil à la Vie Associative", "https://www.associations.gouv.fr/le-hcva.html"),
        ("Guid'Asso", "https://www.associations.gouv.fr/guid-asso.html"),
        ("Avise — Innovation sociale", "https://www.avise.org/"),
        ("Le Mouvement associatif", "https://lemouvementassociatif.org/"),
    ],
}

def wizard_postprocess(answer: str, function_id: str, escalation_level: str = "vert") -> str:
    """Post-traitement déterministe pour les wizards :
    - garantit la mention « le syndicat ELISFA »
    - garantit la présence du bloc « 📚 Ressources et liens utiles »
    - insère un bandeau d'escalade ROUGE/ORANGE en tête si nécessaire
    """
    if not function_id or not function_id.startswith("wizard_"):
        return answer
    if not answer:
        return answer
    # 0. Bandeau d'escalade en tête (ROUGE / ORANGE)
    lvl = (escalation_level or "vert").lower()
    if lvl == "rouge":
        banner = ("> 🚨 **Situation à fort enjeu détectée.** Ce diagnostic est à **compléter impérativement par un échange humain** "
                  "avec un·e juriste ou conseiller·e ELISFA avant toute décision. Cliquez sur **« Prendre rendez-vous maintenant »** "
                  "dans le bandeau rouge ci-dessus pour être rappelé·e rapidement.\n\n")
        if "fort enjeu détect" not in answer.lower():
            answer = banner + answer
    elif lvl == "orange":
        banner = ("> 💡 **Accompagnement recommandé.** Les analyses ci-dessous sont exploitables en autonomie. "
                  "Pour sécuriser vos décisions, un échange avec un conseiller ELISFA est vivement recommandé.\n\n")
        if "accompagnement recommand" not in answer.lower():
            answer = banner + answer
    # 1. Corriger fédération ELISFA → syndicat ELISFA
    import re
    answer = re.sub(r"(?i)\b(la|une|notre|votre)\s+f[ée]d[ée]ration\s+elisfa\b", r"\1 syndicat ELISFA", answer)
    answer = re.sub(r"(?i)\belisfa\s+f[ée]d[ée]ration\b", "syndicat ELISFA", answer)
    answer = re.sub(r"(?i)\bf[ée]d[ée]ration\s+elisfa\b", "syndicat ELISFA", answer)
    # Si « ELISFA » apparaît seul sans qualificatif, on n'ajoute rien (évite faux positifs)
    # Mais si « syndicat » n'apparaît pas du tout, on ajoute une note
    if "syndicat" not in answer.lower() and "elisfa" in answer.lower():
        answer = answer.rstrip() + "\n\n> *Rappel : ELISFA est **votre syndicat employeur** de la branche ALISFA (IDCC 1261). Pour un accompagnement complémentaire, mobilisez aussi **vos fédérations** (FCSF, ACEPP, FFEC…).*"
    # 2. Ajouter le bloc Ressources si absent (détecté par "Ressources et liens" ou nombre de http)
    res_list = WIZARD_RESOURCES.get(function_id, [])
    if res_list:
        has_block = ("Ressources et liens" in answer) or ("📚" in answer)
        nb_http = answer.lower().count("http")
        if not has_block or nb_http < max(3, len(res_list) // 2):
            block = "\n\n## 📚 Ressources et liens utiles\n"
            for name, url in res_list:
                block += f"- [{name}]({url})\n"
            answer = answer.rstrip() + block
    return answer


@app.route("/api/ask", methods=["POST"])
def ask():
    # Rate limiting
    ok, msg = check_rate_limit(request.remote_addr)
    if not ok:
        return jsonify({"error": msg}), 429

    # Hot-reload auto des KBs si un JSON a changé sur disque (O(1) si rien n'a
    # bougé, juste 4 ``os.stat``). Évite de rebooter le container après édition.
    refresh_kbs_if_changed()

    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({"error": "Requête invalide."}), 400

    # ── Validation stricte via Pydantic (fix 6) ──
    # Le modèle ``AskRequest`` remplace une centaine de lignes de ``data.get``
    # + vérifications manuelles. Les règles métier (question OR document
    # requis, troncature silencieuse du doc, split rétro-compat du format
    # concaténé) sont appliquées APRÈS la validation brute, car elles sont
    # cross-champs et spécifiques au handler.
    if _PYDANTIC_OK:
        try:
            payload = AskRequest.model_validate(data)
        except _PydanticValidationError as e:
            return jsonify({"error": format_validation_error(e)}), 400
        question = (payload.question or "").strip()
        doc_text = (payload.document or "").strip()
        doc_name = (payload.document_name or "").strip()[:MAX_DOC_NAME_CHARS]
        conversation_history = payload.history
        module = payload.module
        function_id = payload.function
        profile_id = payload.profile
        user_context = payload.context
        rdv_already_proposed = payload.rdv_proposed
        escalation_level = payload.escalation_level
    else:
        # ── Fallback legacy (si pydantic absent pour une raison quelconque) ──
        question = data.get("question", "")
        if not isinstance(question, str):
            return jsonify({"error": "Le champ 'question' doit être du texte."}), 400
        question = question.strip()
        doc_text = data.get("document") or ""
        doc_name = data.get("document_name") or ""
        if not isinstance(doc_text, str):
            doc_text = ""
        if not isinstance(doc_name, str):
            doc_name = ""
        doc_text = doc_text.strip()
        doc_name = doc_name.strip()[:MAX_DOC_NAME_CHARS]
        conversation_history = data.get("history", [])
        if not isinstance(conversation_history, list):
            conversation_history = []
        if len(conversation_history) > MAX_HISTORY_MESSAGES:
            conversation_history = conversation_history[-MAX_HISTORY_MESSAGES:]
        module = data.get("module", "juridique")
        if module not in MODULE_CONFIG:
            module = "juridique"
        function_id = data.get("function") or None
        if function_id and (not isinstance(function_id, str) or len(function_id) > 80):
            function_id = None
        profile_id = data.get("profile")
        if profile_id and (not isinstance(profile_id, str) or len(profile_id) > 80):
            profile_id = None
        user_context = data.get("context")
        if isinstance(user_context, dict):
            user_context = {
                str(k)[:MAX_CONTEXT_KEY_CHARS]: str(v)[:MAX_CONTEXT_VAL_CHARS]
                for k, v in list(user_context.items())[:MAX_CONTEXT_ENTRIES]
                if isinstance(k, str) and isinstance(v, (str, int, float))
            }
        else:
            user_context = None
        rdv_already_proposed = bool(data.get("rdv_proposed"))
        escalation_level = str(data.get("escalation_level") or "vert").lower()
        if escalation_level not in ("vert", "orange", "rouge"):
            escalation_level = "vert"

    # ── Règles cross-champs (communes aux deux voies) ──
    # Document joint (optionnel) — contient le texte OCR d'un PDF/image
    # Géré séparément du champ `question` pour :
    #   - permettre des documents longs (jusqu'à 120K chars) sans relâcher
    #     la limite anti-spam sur la question elle-même,
    #   - logger seulement la question réelle (lisibilité),
    #   - ne pas polluer la recherche RAG avec le contenu du document.
    # Rétro-compatibilité : si le frontend envoie encore la concaténation
    # dans `question`, on la split automatiquement sur le marker utilisé
    # par l'ancienne version de l'UI.
    if not doc_text and question:
        m = re.match(
            r"^(?P<q>.*?)\s*\n+\s*---\s*Contenu du document\s*(?:\(([^)]+)\))?\s*---\s*\n+(?P<d>.+)$",
            question,
            re.DOTALL,
        )
        if m:
            extracted = m.group("q").strip()
            if extracted:
                question = extracted
            doc_text = m.group("d").strip()
            if m.group(2) and not doc_name:
                doc_name = m.group(2).strip()[:MAX_DOC_NAME_CHARS]

    if not question and not doc_text:
        return jsonify({"error": "Veuillez poser une question."}), 400
    if not question:
        # Question vide mais doc joint : question par défaut
        question = "Analyse ce document"
    if len(question) > MAX_QUESTION_CHARS:
        return jsonify({
            "error": f"Question trop longue (max {MAX_QUESTION_CHARS} caractères). "
                     f"Si vous joignez un document, utilisez le champ 'document' séparé."
        }), 413
    if len(doc_text) > MAX_DOC_CONTEXT_CHARS:
        # Tronque silencieusement pour ne pas casser les uploads volumineux
        doc_text = doc_text[:MAX_DOC_CONTEXT_CHARS] + "\n\n[…document tronqué par le serveur…]"

    module_cfg = MODULE_CONFIG[module]

    # ── Sélection du module via table de config ──
    # MODULE_CONFIG centralise prompt / KB / context_builder / is_formation.
    # Plus lisible qu'une chaîne if/elif et plus facile à étendre.
    is_formation = (module == "formation")
    is_rh = (module == "rh")
    is_gouvernance = (module == "gouvernance")
    base_prompt = module_cfg["system_prompt"]
    current_kb = module_cfg["kb"]
    current_context_builder = module_cfg["context_builder"]

    # ── Construction du system prompt en 2 parties pour le prompt caching ──
    # IMPORTANT : pour qu'un bloc soit cachable il doit faire ≥ 2048 tokens
    # (Haiku 4.5) ; en dessous le cache_control est silencieusement ignoré.
    # Le bloc STABLE regroupe donc tout ce qui ne dépend pas de l'utilisateur
    # pour une combinaison (module, function_id) donnée :
    #   base_prompt + RESPONSE_STRUCTURE + fn_overlay + guide_block
    # Le bloc DYNAMIQUE contient profil + contexte pré-chat + personnalisation
    # (ces 3 portions varient par session / par tour).
    # fn_overlay et guide_block sont déterministes pour une (module, function_id)
    # donnée — ils bénéficieront du cache à partir du 2ᵉ appel dans la même
    # session. Voir build_system_blocks().

    # ── Overlay de fonction (urgence, étude, diagnostic, etc.) ──
    fn_overlay, fn_meta = get_function_overlay(function_id)
    # ── Guide théorique / méthodologique selon le module ──
    guide_block = get_module_guide_block(module, function_id)

    stable_parts = [base_prompt, RESPONSE_STRUCTURE]
    if fn_overlay:
        stable_parts.append(
            "\n\n═══ FONCTION ACTIVE : "
            + (fn_meta["label"] if fn_meta else function_id)
            + " ═══"
            + fn_overlay
        )
    if guide_block:
        stable_parts.append(guide_block)
    stable_block = "".join(stable_parts)

    dynamic_parts = []

    # ── Contexte profil (rappel brut) ──
    if profile_id and profile_id in USER_PROFILES:
        profile = USER_PROFILES[profile_id]
        dynamic_parts.append(
            f"\n\nPROFIL UTILISATEUR\n"
            f"Type : {profile['type']} | Rôle : {profile['label']}\n"
            f"Contexte : {profile['context']}"
        )

    # Contexte pré-chat brut (sert de base aux critères 2 et 3)
    if isinstance(user_context, dict) and user_context:
        ctx_lines = []
        for k, v in user_context.items():
            if isinstance(k, str) and isinstance(v, str) and k.strip() and v.strip():
                ctx_lines.append(f"- {k[:60]} : {v[:80]}")
        if ctx_lines:
            dynamic_parts.append(
                "\n\nCONTEXTE DE LA DEMANDE (pré-chat) :\n" + "\n".join(ctx_lines)
            )

    # ── Bloc personnalisation 6 critères (Rôle, Structure, Région, Historique, Module, Urgence) ──
    perso_block, perso_meta = build_personalization_block(
        profile_id=profile_id,
        user_context=user_context,
        conversation_history=conversation_history,
        question=question,
        active_module=module,
        rdv_already_proposed=rdv_already_proposed,
    )
    if perso_block:
        dynamic_parts.append(perso_block)

    dynamic_block = "".join(dynamic_parts)

    # ── Modules gouvernance & RH : désormais alimentés par leur propre KB
    #    (base_gouvernance.json / base_rh.json) via le flux RAG commun ci-dessous.

    # 1. Recherche dans la base
    results = search_knowledge_base(question, kb=current_kb)

    # Déterminer le niveau / type
    if is_formation:
        # Module formation : pas d'escalade, on détermine le type de contenu
        formation_type = "minimum_legal"
        theme = "formation"
        has_formation_results = bool(results)
        if results:
            theme = results[0]["theme_label"]
            # Si la réponse contient des + formation, on le signale
            for r in results:
                resp = r["article"].get("reponse", {})
                if resp.get("plus_formation") and len(resp["plus_formation"]) > 20:
                    formation_type = "both"
                    break
        niveau = "vert"  # Pas d'escalade en formation
    else:
        # Module juridique : logique escalade existante
        niveau = "vert"
        theme = "inconnu"
        if results:
            niveau = results[0]["niveau"]
            theme = results[0]["theme_label"]
            for r in results:
                if r["niveau"] == "rouge":
                    niveau = "rouge"
                    break
                if r["niveau"] == "orange" and niveau != "rouge":
                    niveau = "orange"

    # 2. Collecter liens et fiches
    liens, fiches = collect_links_and_fiches(results)

    # 3. Construire le contexte
    context = current_context_builder(results)

    # 4. Appeler Claude
    client = get_client()
    if client is None:
        # Mode dégradé : réponse locale sans IA
        if results:
            a = results[0]["article"]
            resp = a["reponse"]
            if is_formation:
                answer = f"## Synthèse\n{resp.get('synthese', 'N/A')}\n\n"
                answer += f"## Minimum légal\n{resp.get('minimum_legal', 'N/A')}\n\n"
                answer += f"## Les + pour aller plus loin\n{resp.get('plus_formation', 'N/A')}\n\n"
                answer += f"## Sources\n" + "\n".join(f"- {s}" for s in resp.get('sources', []))
                if resp.get("fiches_pratiques"):
                    answer += f"\n\n## Fiches pratiques\n" + "\n".join(f"- {f}" for f in resp['fiches_pratiques'])
            else:
                answer = f"## Synthèse\n{resp['synthese']}\n\n"
                answer += f"## Fondement légal\n{resp['fondement_legal']}\n\n"
                answer += f"## Fondement conventionnel ALISFA\n{resp['fondement_ccn']}\n\n"
                answer += f"## Application\n{resp['application']}\n\n"
                answer += f"## Vigilance\n{resp['vigilance']}\n\n"
                answer += f"## Sources\n" + "\n".join(f"- {s}" for s in resp['sources'])
                if resp.get("escalade"):
                    answer += f"\n\n## Escalade\n{resp.get('message_escalade', 'Contactez le pôle juridique ELISFA.')}"
            answer += "\n\n---\n*Réponse générée en mode local (sans IA). Pour des réponses enrichies, configurez votre clé API Anthropic.*"
        else:
            if is_formation:
                answer = "## Résultat\nJe ne dispose pas d'informations suffisantes dans ma base formation pour répondre à cette question.\n\nVous pouvez contacter **Uniformation** (votre OPCO) au 01 53 02 13 13 ou consulter les ressources sur [uniformation.fr](https://www.uniformation.fr)."
            else:
                answer = "## Résultat\nJe ne dispose pas d'informations suffisamment fiables dans ma base documentaire pour répondre à cette question.\n\n## Escalade\nNous vous recommandons de contacter le **pôle juridique ELISFA** qui pourra vous apporter une réponse précise."
            niveau = "orange" if not is_formation else "vert"

        sources_list = [s for r in results for s in r["article"]["reponse"].get("sources", [])] if results else []
        log_interaction(question, niveau, theme, sources_list, f"reponse_locale_{module}")

        # Info escalade / formation levels
        if is_formation:
            level_info = FORMATION_LEVELS if has_formation_results else None
        else:
            level_info = ESCALADE_CONFIG.get(niveau, ESCALADE_CONFIG["vert"])

        return jsonify({
            "answer": answer,
            "niveau": niveau,
            "theme": theme,
            "sources_count": len(results),
            "mode": "local",
            "module": module,
            "function": function_id,
            "function_label": (fn_meta["label"] if fn_meta else None),
            "liens": liens,
            "fiches": fiches,
            "escalade": level_info if not is_formation else None,
            "formation_levels": level_info if is_formation else None,
            "personalization": perso_meta,
        })

    # Mode IA : appel Claude
    try:
        # Document joint (si présent) : on l'ajoute en fin de user message
        # pour que Claude le lise, mais on garde la question courte pour les
        # logs et la recherche RAG. La taille a déjà été validée plus haut.
        doc_block = ""
        if doc_text:
            header = f" ({doc_name})" if doc_name else ""
            doc_block = (
                f"\n\n--- Contenu du document joint{header} ---\n\n"
                f"{doc_text}\n"
                f"--- Fin du document ---"
            )
        user_message = f"QUESTION DE L'ADHÉRENT :\n{question}{doc_block}\n\n{context}"

        # Construire les messages avec l'historique de conversation (max 10 derniers échanges)
        messages = []
        for msg in conversation_history[-20:]:  # max 10 paires (20 messages)
            role = msg.get("role")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": user_message})

        # Activation des outils de calcul déterministes pour les fonctions qui en
        # ont besoin (actuellement : juridique_calcul). Le flag est positionné dans
        # FUNCTION_PROMPTS (clé "use_tools": True).
        uses_tools = bool(fn_meta and fn_meta.get("use_tools"))

        # System blocks = [bloc cachable (base_prompt + structure) ; bloc dynamique].
        # Voir build_system_blocks() : le bloc 1 est marqué cache_control ephemeral,
        # ce qui réutilise ~90% des tokens d'entrée entre appels < 5 min d'écart.
        system_blocks = build_system_blocks(stable_block, dynamic_block)

        create_kwargs = {
            "model": CLAUDE_MODEL,
            "max_tokens": CLAUDE_MAX_TOKENS,
            "system": system_blocks,
            "messages": messages,
            "timeout": 60.0,
        }
        if uses_tools:
            create_kwargs["tools"] = TOOLS_CALCUL

        response = call_claude(client, **create_kwargs)

        # Boucle tool_use : Claude peut appeler plusieurs outils en cascade
        # (ex. calcul_anciennete → indemnite_licenciement). Limite de sécurité
        # pour éviter les boucles infinies.
        tool_iterations = 0
        MAX_TOOL_ITERATIONS = 5
        while (
            uses_tools
            and getattr(response, "stop_reason", None) == "tool_use"
            and tool_iterations < MAX_TOOL_ITERATIONS
        ):
            tool_iterations += 1
            # Extraire les blocs tool_use
            tool_uses = [b for b in response.content if getattr(b, "type", None) == "tool_use"]
            tool_results = []
            for tu in tool_uses:
                try:
                    result_json = execute_tool_call(tu.name, tu.input)
                except Exception as tool_err:  # noqa: BLE001
                    result_json = json.dumps(
                        {"erreur": f"{type(tool_err).__name__}: {tool_err}"},
                        ensure_ascii=False,
                    )
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tu.id,
                    "content": result_json,
                })
            # Append assistant turn (avec les tool_use) + tool_results
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})
            # Relance : le bloc system est réutilisé tel quel → cache hit quasi garanti.
            response = call_claude(client, **{**create_kwargs, "messages": messages})

        # Extraction du texte final (peut contenir plusieurs blocs text si tool use)
        if response.content:
            text_blocks = [
                getattr(b, "text", "")
                for b in response.content
                if getattr(b, "type", None) == "text"
            ]
            answer = "\n\n".join(t for t in text_blocks if t) or "Désolé, je n'ai pas pu générer de réponse."
        else:
            answer = "Désolé, je n'ai pas pu générer de réponse."

        # Post-traitement wizard (ressources + syndicat ELISFA + bandeau d'escalade)
        answer = wizard_postprocess(answer, function_id, escalation_level)

        sources_list = [s for r in results for s in r["article"]["reponse"].get("sources", [])] if results else []
        log_interaction(question, niveau, theme, sources_list, f"reponse_ia_{module}")

        if is_formation:
            level_info = FORMATION_LEVELS if has_formation_results else None
        else:
            level_info = ESCALADE_CONFIG.get(niveau, ESCALADE_CONFIG["vert"])

        return jsonify({
            "answer": answer,
            "niveau": niveau,
            "theme": theme,
            "sources_count": len(results),
            "mode": "ia",
            "model": CLAUDE_MODEL,
            "module": module,
            "function": function_id,
            "function_label": (fn_meta["label"] if fn_meta else None),
            "liens": liens,
            "fiches": fiches,
            "escalade": level_info if not is_formation else None,
            "formation_levels": level_info if is_formation else None,
            "personalization": perso_meta,
        })
    except RuntimeError as e:
        # Erreur typée remontée par call_claude : HTTP status adapté.
        http_status = getattr(e, "http_status", 500)
        logging.error(f"Erreur API Claude (typée): {e}")
        return jsonify({"error": str(e)}), http_status
    except Exception as e:
        logging.error(f"Erreur inattendue /api/ask: {type(e).__name__}: {e}")
        return jsonify({"error": "Erreur de connexion au modèle IA. Veuillez réessayer."}), 500

# ══════════════════════════════════════════════
#        API — Prise de Rendez-vous
# ══════════════════════════════════════════════

@app.route("/api/rdv", methods=["POST"])
def creer_rdv():
    """Créer un rendez-vous avec un juriste."""
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({"error": "Données JSON invalides."}), 400

    # Validation stricte via Pydantic (fix 6), fallback sur validate_contact_fields
    # si pydantic n'est pas disponible (cas dev sans les requirements complets).
    if _PYDANTIC_OK:
        try:
            payload = RdvRequest.model_validate(data)
        except _PydanticValidationError as e:
            return jsonify({"error": format_validation_error(e)}), 400
        rdv_data = {
            "nom": payload.nom,
            "email": payload.email,
            "telephone": payload.telephone,
            "structure": (payload.structure or "").strip(),
            "sujet": payload.sujet,
            "contexte": (payload.contexte or "").strip(),
            "niveau": payload.niveau or "rouge",
            "theme": payload.theme or "",
            "date_souhaitee": payload.date_souhaitee or "",
            "creneau": payload.creneau or "",
        }
    else:
        ok, err = validate_contact_fields(data, require_sujet=True)
        if not ok:
            return jsonify({"error": err}), 400
        rdv_data = {
            "nom": data["nom"].strip(),
            "email": data["email"].strip(),
            "telephone": data["telephone"].strip(),
            "structure": data.get("structure", "").strip(),
            "sujet": data["sujet"].strip(),
            "contexte": data.get("contexte", "").strip(),
            "niveau": data.get("niveau", "rouge"),
            "theme": data.get("theme", ""),
            "date_souhaitee": data.get("date_souhaitee", ""),
            "creneau": data.get("creneau", ""),
        }

    rdv = {
        "id": str(uuid.uuid4())[:8].upper(),
        "created_at": datetime.now().isoformat(),
        **rdv_data,
        "statut": "en_attente",
        "notes_juriste": "",
    }

    # Sauvegarder
    rdvs = load_rdv()
    rdvs.append(rdv)
    save_rdv(rdvs)

    # Journaliser
    logging.info(f"Nouveau RDV créé : {rdv['id']} — {rdv['nom']} — {rdv['sujet']}")

    # Notification email au juriste
    _n = html_escape(rdv['nom'])
    _e = html_escape(rdv['email'])
    _t = html_escape(rdv['telephone'])
    _s = html_escape(rdv['structure'] or 'Non renseignée')
    _sj = html_escape(rdv['sujet'])
    _ctx = html_escape(rdv.get('contexte', '') or 'Non renseigné')
    email_html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;">
        <h2 style="color:#1a2744;">Nouvelle demande de rendez-vous — ELISFA</h2>
        <table style="width:100%;border-collapse:collapse;">
            <tr><td style="padding:8px;font-weight:bold;color:#4b5563;">Référence</td><td style="padding:8px;">RDV-{rdv['id']}</td></tr>
            <tr style="background:#f9fafb;"><td style="padding:8px;font-weight:bold;color:#4b5563;">Nom</td><td style="padding:8px;">{_n}</td></tr>
            <tr><td style="padding:8px;font-weight:bold;color:#4b5563;">Email</td><td style="padding:8px;">{_e}</td></tr>
            <tr style="background:#f9fafb;"><td style="padding:8px;font-weight:bold;color:#4b5563;">Téléphone</td><td style="padding:8px;">{_t}</td></tr>
            <tr><td style="padding:8px;font-weight:bold;color:#4b5563;">Structure</td><td style="padding:8px;">{_s}</td></tr>
            <tr style="background:#f9fafb;"><td style="padding:8px;font-weight:bold;color:#4b5563;">Sujet</td><td style="padding:8px;">{_sj}</td></tr>
            <tr><td style="padding:8px;font-weight:bold;color:#4b5563;">Niveau</td><td style="padding:8px;"><span style="background:{'#fee2e2' if rdv['niveau']=='rouge' else '#fef3c7'};color:{'#ef4444' if rdv['niveau']=='rouge' else '#b45309'};padding:2px 10px;border-radius:8px;font-weight:bold;">{rdv['niveau'].upper()}</span></td></tr>
            <tr style="background:#f9fafb;"><td style="padding:8px;font-weight:bold;color:#4b5563;">Contexte</td><td style="padding:8px;">{rdv['contexte'] or 'Non renseigné'}</td></tr>
            <tr><td style="padding:8px;font-weight:bold;color:#4b5563;">Date souhaitée</td><td style="padding:8px;">{rdv['date_souhaitee'] or 'Flexible'}</td></tr>
            <tr style="background:#f9fafb;"><td style="padding:8px;font-weight:bold;color:#4b5563;">Créneau</td><td style="padding:8px;">{rdv['creneau'] or 'Non précisé'}</td></tr>
        </table>
        <p style="margin-top:16px;color:#6b7280;font-size:13px;">Demande issue du chatbot ELISFA — {rdv['created_at']}</p>
    </div>
    """
    send_email_notification(
        f"[ELISFA] Nouveau RDV juridique — {rdv['nom']} — {rdv['sujet'][:50]}",
        email_html
    )

    # Notification webhook
    send_webhook_notification({
        "event": "rdv_created",
        "rdv": rdv
    })

    # Confirmation email à l'adhérent
    confirm_html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;">
        <h2 style="color:#1a2744;">Confirmation de votre demande — ELISFA</h2>
        <p>Bonjour {rdv['nom']},</p>
        <p>Votre demande de rendez-vous avec le pôle juridique ELISFA a bien été enregistrée.</p>
        <table style="width:100%;border-collapse:collapse;margin:16px 0;">
            <tr style="background:#f9fafb;"><td style="padding:8px;font-weight:bold;">Référence</td><td style="padding:8px;">RDV-{rdv['id']}</td></tr>
            <tr><td style="padding:8px;font-weight:bold;">Sujet</td><td style="padding:8px;">{rdv['sujet']}</td></tr>
            <tr style="background:#f9fafb;"><td style="padding:8px;font-weight:bold;">Délai estimé</td><td style="padding:8px;">Un juriste vous recontactera sous 5 jours ouvrés</td></tr>
        </table>
        <p style="color:#6b7280;font-size:13px;">Ceci est un message automatique. Pour toute question, contactez le pôle juridique ELISFA.</p>
    </div>
    """
    send_email_notification(
        f"[ELISFA] Confirmation de votre demande RDV-{rdv['id']}",
        confirm_html,
        to_email=rdv["email"]
    )

    return jsonify({
        "status": "ok",
        "rdv_id": rdv["id"],
        "message": f"Votre demande RDV-{rdv['id']} a été enregistrée. Un juriste vous recontactera sous 5 jours ouvrés."
    })

@app.route("/api/rdv", methods=["GET"])
@require_admin
def liste_rdv():
    """Lister tous les rendez-vous (admin)."""
    rdvs = load_rdv()
    # Tri par date décroissante
    rdvs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return jsonify(rdvs)

@app.route("/api/rdv/<rdv_id>", methods=["PATCH"])
@require_admin
def update_rdv(rdv_id):
    """Mettre à jour un RDV (admin)."""
    rdvs = load_rdv()
    data = request.get_json()
    for rdv in rdvs:
        if rdv["id"] == rdv_id:
            for key in ["statut", "notes_juriste", "date_confirmee", "creneau_confirme"]:
                if key in data:
                    rdv[key] = data[key]
            rdv["updated_at"] = datetime.now().isoformat()
            save_rdv(rdvs)

            # Si confirmé, notifier l'adhérent
            if data.get("statut") == "confirme":
                confirm_html = f"""
                <div style="font-family:Arial,sans-serif;max-width:600px;">
                    <h2 style="color:#1a2744;">Votre rendez-vous est confirmé — ELISFA</h2>
                    <p>Bonjour {rdv['nom']},</p>
                    <p>Votre rendez-vous avec le pôle juridique ELISFA est confirmé :</p>
                    <table style="width:100%;border-collapse:collapse;margin:16px 0;">
                        <tr style="background:#dcfce7;"><td style="padding:8px;font-weight:bold;">Date</td><td style="padding:8px;">{rdv.get('date_confirmee', rdv.get('date_souhaitee', 'À confirmer'))}</td></tr>
                        <tr><td style="padding:8px;font-weight:bold;">Créneau</td><td style="padding:8px;">{rdv.get('creneau_confirme', rdv.get('creneau', 'À confirmer'))}</td></tr>
                        <tr style="background:#f9fafb;"><td style="padding:8px;font-weight:bold;">Sujet</td><td style="padding:8px;">{rdv['sujet']}</td></tr>
                    </table>
                    <p style="color:#6b7280;font-size:13px;">Référence : RDV-{rdv['id']}</p>
                </div>
                """
                send_email_notification(
                    f"[ELISFA] RDV confirmé — {rdv.get('date_confirmee', '')}",
                    confirm_html,
                    to_email=rdv["email"]
                )

            return jsonify({"status": "ok", "rdv": rdv})
    return jsonify({"error": "RDV non trouvé"}), 404

# ══════════════════════════════════════════════
#     API — Email guidé au juriste
# ══════════════════════════════════════════════

# Questions guidées par thème pour aider l'adhérent à structurer sa demande
GUIDE_QUESTIONS = {
    "contrat_travail": {
        "label": "Contrat de travail",
        "questions": [
            {"id": "type_contrat", "label": "Quel type de contrat est concerné ?", "placeholder": "CDI, CDD, CDII, intérim...", "type": "select", "options": ["CDI", "CDD", "CDII (intermittent)", "Temps partiel", "Contrat aidé", "Autre"]},
            {"id": "anciennete", "label": "Quelle est l'ancienneté du salarié ?", "placeholder": "Ex : 3 ans et 4 mois", "type": "text"},
            {"id": "classification", "label": "Quelle est la classification du salarié (pesée) ?", "placeholder": "Ex : Pesée 47, emploi repère Animateur", "type": "text"},
            {"id": "situation", "label": "Décrivez la situation actuelle", "placeholder": "Que s'est-il passé ? Quand ? Qui est concerné ?", "type": "textarea"},
            {"id": "demarches", "label": "Quelles démarches avez-vous déjà effectuées ?", "placeholder": "Courriers envoyés, entretiens réalisés, conseils déjà reçus...", "type": "textarea"},
            {"id": "question_precise", "label": "Quelle est votre question précise ?", "placeholder": "Formulez votre question de la manière la plus précise possible", "type": "textarea"},
        ],
    },
    "rupture": {
        "label": "Rupture du contrat",
        "questions": [
            {"id": "type_rupture", "label": "Quel type de rupture est envisagé ?", "placeholder": "", "type": "select", "options": ["Licenciement pour motif personnel", "Licenciement pour faute", "Licenciement économique", "Rupture conventionnelle", "Démission", "Départ en retraite", "Mise à la retraite", "Fin de CDD", "Prise d'acte", "Autre"]},
            {"id": "anciennete", "label": "Ancienneté du salarié concerné ?", "placeholder": "Ex : 5 ans", "type": "text"},
            {"id": "classification", "label": "Classification du salarié ?", "placeholder": "Ex : Pesée 52, Cadre", "type": "text"},
            {"id": "salarie_protege", "label": "Le salarié est-il protégé (élu CSE, délégué syndical) ?", "placeholder": "", "type": "select", "options": ["Non", "Oui — élu CSE", "Oui — délégué syndical", "Oui — autre mandat", "Je ne sais pas"]},
            {"id": "situation", "label": "Décrivez la situation et les faits", "placeholder": "Chronologie des événements, motifs envisagés...", "type": "textarea"},
            {"id": "demarches", "label": "Quelles démarches avez-vous déjà effectuées ?", "placeholder": "Avertissements, entretien préalable, courriers...", "type": "textarea"},
            {"id": "urgence", "label": "Y a-t-il une urgence ou un délai à respecter ?", "placeholder": "Ex : prescription de 2 mois pour faute, fin de CDD le...", "type": "text"},
            {"id": "question_precise", "label": "Votre question précise ?", "placeholder": "", "type": "textarea"},
        ],
    },
    "classification": {
        "label": "Classification & Rémunération",
        "questions": [
            {"id": "objet", "label": "Quel est l'objet de votre question ?", "placeholder": "", "type": "select", "options": ["Pesée d'un emploi", "Contestation de classification", "Passage d'un salarié cadre", "Calcul de salaire", "Points d'ancienneté", "Indemnité différentielle", "Valorisation d'expérience", "Autre"]},
            {"id": "poste", "label": "Quel est l'intitulé du poste concerné ?", "placeholder": "Ex : Directeur/trice de crèche, Animateur/trice...", "type": "text"},
            {"id": "pesee_actuelle", "label": "Quelle est la pesée actuelle (si connue) ?", "placeholder": "Ex : Pesée 43 — indiquer le détail des critères si possible", "type": "text"},
            {"id": "situation", "label": "Décrivez la situation", "placeholder": "Contexte, missions du poste, désaccord éventuel...", "type": "textarea"},
            {"id": "question_precise", "label": "Votre question précise ?", "placeholder": "", "type": "textarea"},
        ],
    },
    "temps_travail": {
        "label": "Temps de travail & Congés",
        "questions": [
            {"id": "objet", "label": "Quel sujet est concerné ?", "placeholder": "", "type": "select", "options": ["Heures supplémentaires", "Forfait jours", "Aménagement du temps de travail", "Temps partiel", "Congés payés", "Congés exceptionnels", "Arrêt maladie / maintien de salaire", "Congé maternité/paternité", "Astreintes", "Travail de nuit", "Jours fériés", "Autre"]},
            {"id": "nb_salaries", "label": "Combien de salariés sont concernés ?", "placeholder": "Un seul / Plusieurs / Tous", "type": "text"},
            {"id": "situation", "label": "Décrivez la situation", "placeholder": "Période concernée, problème rencontré...", "type": "textarea"},
            {"id": "question_precise", "label": "Votre question précise ?", "placeholder": "", "type": "textarea"},
        ],
    },
    "harcelement_disciplinaire": {
        "label": "Harcèlement / Disciplinaire",
        "questions": [
            {"id": "type", "label": "Nature de la situation", "placeholder": "", "type": "select", "options": ["Signalement de harcèlement moral", "Signalement de harcèlement sexuel", "Procédure disciplinaire à engager", "Sanction envisagée", "Conflit entre salariés", "Autre"]},
            {"id": "depuis_quand", "label": "Depuis quand cette situation existe-t-elle ?", "placeholder": "Date ou durée approximative", "type": "text"},
            {"id": "personnes", "label": "Qui est concerné ? (sans nommer, indiquer les fonctions)", "placeholder": "Ex : un animateur signale des faits commis par son responsable", "type": "text"},
            {"id": "faits", "label": "Décrivez les faits de manière factuelle", "placeholder": "Chronologie, témoignages recueillis, preuves disponibles...", "type": "textarea"},
            {"id": "demarches", "label": "Quelles démarches avez-vous déjà effectuées ?", "placeholder": "Signalement CSE, médecin du travail, entretien...", "type": "textarea"},
            {"id": "question_precise", "label": "Votre question précise ?", "placeholder": "", "type": "textarea"},
        ],
    },
    "contentieux": {
        "label": "Contentieux / Prud'hommes",
        "questions": [
            {"id": "stade", "label": "À quel stade en êtes-vous ?", "placeholder": "", "type": "select", "options": ["Menace de contentieux (courrier avocat)", "Saisine du conseil de prud'hommes reçue", "Audience de conciliation prévue", "Audience de jugement prévue", "Jugement rendu — envisager appel", "Autre"]},
            {"id": "objet_litige", "label": "Quel est l'objet du litige ?", "placeholder": "Ex : contestation de licenciement, rappel de salaire, harcèlement...", "type": "text"},
            {"id": "montant", "label": "Montant des demandes (si connu)", "placeholder": "Ex : 15 000 € de dommages-intérêts", "type": "text"},
            {"id": "delai", "label": "Y a-t-il un délai urgent à respecter ?", "placeholder": "Ex : audience le 15/05, délai de réponse le...", "type": "text"},
            {"id": "situation", "label": "Résumez la situation", "placeholder": "", "type": "textarea"},
            {"id": "question_precise", "label": "Votre question précise ?", "placeholder": "", "type": "textarea"},
        ],
    },
    "autre": {
        "label": "Autre sujet",
        "questions": [
            {"id": "domaine", "label": "Quel domaine est concerné ?", "placeholder": "Ex : prévoyance, formation, CSE, télétravail...", "type": "text"},
            {"id": "situation", "label": "Décrivez votre situation", "placeholder": "Contexte, faits, chronologie...", "type": "textarea"},
            {"id": "demarches", "label": "Démarches déjà effectuées", "placeholder": "", "type": "textarea"},
            {"id": "question_precise", "label": "Votre question précise ?", "placeholder": "Formulez votre question de la manière la plus précise possible", "type": "textarea"},
        ],
    },
}

@app.route("/api/guide-questions")
def get_guide_questions():
    """Retourne les questions guidées pour le formulaire email juriste."""
    return jsonify(GUIDE_QUESTIONS)


@app.route("/api/wizard-hints/<path:theme>")
def get_wizard_hints_endpoint(theme: str):
    """Retourne la liste de questions-pistes méthodologiques pour un thème
    juridique donné (utilisé par l'étape « Les faits » du wizard juridique
    pour aider l'utilisateur à cadrer sa rédaction).

    Source : utils/guide_questions.py (WIZARD_HINTS_JURIDIQUE).
    """
    return jsonify({
        "theme": theme,
        "hints": get_wizard_hints(theme),
    })


@app.route("/api/wizard-hints")
def list_wizard_hints_themes():
    """Retourne le dict complet des hints juridiques par thème."""
    return jsonify(WIZARD_HINTS_JURIDIQUE)

@app.route("/api/email-juriste", methods=["POST"])
def email_juriste():
    """Envoyer un email structuré au juriste, guidé par le questionnaire."""
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({"error": "Données JSON invalides."}), 400

    # Validation Pydantic (fix 6) avec fallback legacy
    if _PYDANTIC_OK:
        try:
            payload = EmailJuristeRequest.model_validate(data)
        except _PydanticValidationError as e:
            return jsonify({"error": format_validation_error(e)}), 400
        # Normalise data pour garder la suite du handler inchangée
        data = {**data, **payload.model_dump(exclude_unset=False)}
    else:
        ok, err = validate_contact_fields(data)
        if not ok:
            return jsonify({"error": err}), 400
        if not data.get("theme_guide"):
            return jsonify({"error": "Le thème est requis."}), 400
        if not isinstance(data.get("reponses"), dict) or len(data["reponses"]) == 0:
            return jsonify({"error": "Veuillez répondre aux questions guidées."}), 400

    # Construire l'email
    email_id = str(uuid.uuid4())[:8].upper()
    theme_guide = data["theme_guide"]
    theme_label = GUIDE_QUESTIONS.get(theme_guide, {}).get("label", theme_guide)
    questions_def = GUIDE_QUESTIONS.get(theme_guide, {}).get("questions", [])

    # Construire le corps structuré
    reponses_html = ""
    reponses_text = ""
    for q in questions_def:
        val = data["reponses"].get(q["id"], "").strip()
        if val:
            safe_val = html_escape(val).replace('\n', '<br>')
            reponses_html += f"""
            <tr><td style="padding:10px 14px;font-weight:bold;color:#1e3a5f;background:#eff6ff;vertical-align:top;width:35%;border:1px solid #dbeafe;">{html_escape(q['label'])}</td>
            <td style="padding:10px 14px;border:1px solid #e5e7eb;">{safe_val}</td></tr>
            """
            reponses_text += f"\n{q['label']}\n→ {val}\n"

    # Email HTML complet pour le juriste
    juriste_html = f"""
    <div style="font-family:Arial,sans-serif;max-width:700px;margin:0 auto;">
        <div style="background:linear-gradient(135deg,#1a2744,#1e3a5f);color:#fff;padding:20px 24px;border-radius:12px 12px 0 0;">
            <h2 style="margin:0;font-size:18px;">Nouvelle question d'adhérent — ELISFA</h2>
            <p style="margin:4px 0 0;opacity:.8;font-size:13px;">Référence : QJ-{email_id} | {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
        </div>

        <div style="background:#fff;padding:24px;border:1px solid #e5e7eb;border-top:none;">
            <div style="display:flex;gap:20px;margin-bottom:20px;">
                <div style="flex:1;">
                    <div style="font-size:11px;text-transform:uppercase;color:#9ca3af;letter-spacing:.5px;margin-bottom:2px;">Adhérent</div>
                    <div style="font-weight:bold;font-size:15px;">{data['nom']}</div>
                </div>
                <div style="flex:1;">
                    <div style="font-size:11px;text-transform:uppercase;color:#9ca3af;letter-spacing:.5px;margin-bottom:2px;">Structure</div>
                    <div style="font-size:14px;">{data.get('structure', '') or 'Non renseignée'}</div>
                </div>
            </div>

            <table style="width:100%;margin-bottom:12px;font-size:13px;border-collapse:collapse;">
                <tr><td style="padding:4px 8px;color:#6b7280;">Email :</td><td style="padding:4px 8px;"><a href="mailto:{data['email']}">{data['email']}</a></td>
                    <td style="padding:4px 8px;color:#6b7280;">Tél :</td><td style="padding:4px 8px;">{data['telephone']}</td></tr>
            </table>

            <div style="background:#eff6ff;border:1px solid #dbeafe;border-radius:8px;padding:10px 16px;margin-bottom:20px;">
                <span style="font-size:12px;font-weight:700;color:#2563eb;text-transform:uppercase;letter-spacing:.5px;">Thème : {theme_label}</span>
                {(' | <span style="font-size:12px;color:#6b7280;">Niveau : ' + data.get('niveau','').upper() + '</span>') if data.get('niveau') else ''}
            </div>

            <h3 style="font-size:14px;color:#1a2744;margin-bottom:12px;">Questionnaire guidé</h3>
            <table style="width:100%;border-collapse:collapse;font-size:13px;line-height:1.5;">
                {reponses_html}
            </table>

            {f'<div style="margin-top:16px;padding:12px;background:#f9fafb;border-radius:8px;border:1px solid #e5e7eb;"><strong style="font-size:12px;color:#6b7280;">Contexte chatbot :</strong><br><span style="font-size:13px;">{data.get("contexte_chatbot","")}</span></div>' if data.get('contexte_chatbot') else ''}
        </div>

        <div style="background:#f9fafb;padding:14px 24px;border:1px solid #e5e7eb;border-top:none;border-radius:0 0 12px 12px;font-size:12px;color:#6b7280;">
            Demande issue du chatbot ELISFA — {datetime.now().strftime('%d/%m/%Y à %H:%M')} — Réf. QJ-{email_id}
        </div>
    </div>
    """

    # Sauvegarder
    email_record = {
        "id": email_id,
        "created_at": datetime.now().isoformat(),
        "nom": data["nom"].strip(),
        "email": data["email"].strip(),
        "telephone": data["telephone"].strip(),
        "structure": data.get("structure", "").strip(),
        "theme_guide": theme_guide,
        "theme_label": theme_label,
        "niveau": data.get("niveau", ""),
        "reponses": data["reponses"],
        "contexte_chatbot": data.get("contexte_chatbot", ""),
        "statut": "envoye",
    }
    emails = load_emails()
    emails.append(email_record)
    save_emails(emails)

    # Journaliser
    logging.info(f"Email juriste QJ-{email_id} — {data['nom']} — {theme_label}")
    log_interaction(
        f"[EMAIL] {theme_label}",
        data.get("niveau", "orange"),
        theme_label,
        [],
        "email_juriste",
        {"email_id": email_id}
    )

    # Envoyer l'email au juriste
    email_sent = send_email_notification(
        f"[ELISFA] Question adhérent QJ-{email_id} — {theme_label} — {data['nom']}",
        juriste_html
    )

    # Confirmation à l'adhérent
    confirm_html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;">
        <h2 style="color:#1a2744;">Votre question a bien été transmise — ELISFA</h2>
        <p>Bonjour {data['nom']},</p>
        <p>Votre question sur le thème « <strong>{theme_label}</strong> » a été transmise au pôle juridique ELISFA.</p>
        <p style="background:#eff6ff;padding:12px 16px;border-radius:8px;border:1px solid #dbeafe;">
            Référence : <strong>QJ-{email_id}</strong><br>
            Un juriste vous répondra sous <strong>48 heures ouvrées</strong>.
        </p>
        <h3 style="font-size:14px;color:#1a2744;margin-top:20px;">Récapitulatif de votre question</h3>
        <div style="font-size:13px;color:#4b5563;line-height:1.6;">{reponses_text.replace(chr(10), '<br>')}</div>
        <p style="margin-top:20px;color:#6b7280;font-size:12px;">Ceci est un message automatique du chatbot ELISFA. Pour toute question complémentaire, contactez le pôle juridique ELISFA.</p>
    </div>
    """
    send_email_notification(
        f"[ELISFA] Confirmation QJ-{email_id} — Votre question a été transmise",
        confirm_html,
        to_email=data["email"]
    )

    # Webhook
    send_webhook_notification({
        "event": "email_juriste_sent",
        "email": email_record
    })

    return jsonify({
        "status": "ok",
        "email_id": email_id,
        "email_sent": email_sent,
        "message": f"Votre question QJ-{email_id} a été transmise au pôle juridique ELISFA. Vous recevrez une réponse sous 48h ouvrées."
    })

@app.route("/api/emails-juriste", methods=["GET"])
@require_admin
def liste_emails():
    """Lister tous les emails juriste (admin)."""
    emails = load_emails()
    emails.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return jsonify(emails)

# ══════════════════════════════════════════════
#   API — Planificateur d'appel 15 min (1er contact)
# ══════════════════════════════════════════════

APPELS_FILE = DATA_DIR / "appels_15min.json"

def load_appels():
    if APPELS_FILE.exists():
        try:
            with open(APPELS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logging.error(f"Erreur lecture {APPELS_FILE}: {e}")
    return []

def save_appels(appels):
    with open(APPELS_FILE, "w", encoding="utf-8") as f:
        json.dump(appels, f, ensure_ascii=False, indent=2)

# Motifs d'appel prédéfinis
MOTIFS_APPEL = {
    "orientation": {
        "label": "Orientation juridique",
        "description": "Comprendre mes droits et savoir vers qui me tourner",
        "icon": "compass",
        "priorite": "normale"
    },
    "preparer_email": {
        "label": "Préparer l'envoi d'un email au juriste",
        "description": "Être guidé(e) pour formuler ma question avant envoi",
        "icon": "mail",
        "priorite": "normale"
    },
    "urgence_procedure": {
        "label": "Urgence — Procédure en cours",
        "description": "Délai imminent (audience, prescription, mise en demeure...)",
        "icon": "alert-triangle",
        "priorite": "urgente"
    },
    "urgence_conflit": {
        "label": "Urgence — Conflit ou situation grave",
        "description": "Harcèlement, danger, situation nécessitant une action rapide",
        "icon": "shield-alert",
        "priorite": "urgente"
    },
    "clarification": {
        "label": "Clarifier une réponse du chatbot",
        "description": "La réponse obtenue nécessite des précisions humaines",
        "icon": "help-circle",
        "priorite": "normale"
    },
    "autre": {
        "label": "Autre motif",
        "description": "Toute autre raison nécessitant un premier échange",
        "icon": "phone",
        "priorite": "normale"
    }
}

# Créneaux disponibles (configurable)
CRENEAUX_APPEL = {
    "lundi":    ["09:00", "09:30", "10:00", "10:30", "11:00", "14:00", "14:30", "15:00", "15:30", "16:00"],
    "mardi":    ["09:00", "09:30", "10:00", "10:30", "11:00", "14:00", "14:30", "15:00", "15:30", "16:00"],
    "mercredi": ["09:00", "09:30", "10:00", "10:30", "11:00", "14:00", "14:30", "15:00", "15:30", "16:00"],
    "jeudi":    ["09:00", "09:30", "10:00", "10:30", "11:00", "14:00", "14:30", "15:00", "15:30", "16:00"],
    "vendredi": ["09:00", "09:30", "10:00", "10:30", "11:00"],
}

JOURS_FR = {"lundi": 0, "mardi": 1, "mercredi": 2, "jeudi": 3, "vendredi": 4}

def get_creneaux_disponibles():
    """Retourne les 10 prochains jours ouvrés avec leurs créneaux disponibles."""
    appels = load_appels()
    # Collecter les créneaux déjà pris (statut != annule)
    creneaux_pris = set()
    for a in appels:
        if a.get("statut") != "annule":
            creneaux_pris.add(f"{a.get('date')}_{a.get('heure')}")

    jours_noms = ["lundi", "mardi", "mercredi", "jeudi", "vendredi"]
    disponibles = []
    jour = datetime.now()

    # Si on est après 16h, commencer demain
    if jour.hour >= 16:
        jour += timedelta(days=1)

    compteur = 0
    while compteur < 10:
        jour += timedelta(days=1)
        weekday = jour.weekday()
        if weekday > 4:  # Samedi/dimanche
            continue
        nom_jour = jours_noms[weekday]
        date_str = jour.strftime("%Y-%m-%d")
        date_display = jour.strftime("%A %d/%m").capitalize()
        # Remplacer les noms anglais par français
        for en, fr in [("Monday", "Lundi"), ("Tuesday", "Mardi"), ("Wednesday", "Mercredi"),
                       ("Thursday", "Jeudi"), ("Friday", "Vendredi")]:
            date_display = date_display.replace(en, fr)

        creneaux_jour = []
        for h in CRENEAUX_APPEL.get(nom_jour, []):
            cle = f"{date_str}_{h}"
            if cle not in creneaux_pris:
                # Si c'est aujourd'hui, ne montrer que les créneaux futurs
                if date_str == datetime.now().strftime("%Y-%m-%d"):
                    heure_int = int(h.replace(":", ""))
                    now_int = int(datetime.now().strftime("%H%M"))
                    if heure_int <= now_int:
                        continue
                creneaux_jour.append(h)

        if creneaux_jour:
            disponibles.append({
                "date": date_str,
                "jour": date_display,
                "creneaux": creneaux_jour
            })
        compteur += 1

    return disponibles

@app.route("/api/appel/motifs")
def get_motifs_appel():
    """Retourne les motifs d'appel disponibles."""
    return jsonify(MOTIFS_APPEL)

@app.route("/api/appel/creneaux")
def get_creneaux():
    """Retourne les créneaux d'appel disponibles."""
    return jsonify(get_creneaux_disponibles())

@app.route("/api/appel", methods=["POST"])
def planifier_appel():
    """Planifier un appel de 15 minutes avec un juriste."""
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({"error": "Données JSON invalides."}), 400

    # Validation Pydantic (fix 6) — AppelRequest vérifie nom/email/tel/motif
    # en une passe. date + heure sont vérifiés manuellement ensuite (règle
    # métier : les deux doivent être non vides ET le créneau libre).
    if _PYDANTIC_OK:
        try:
            AppelRequest.model_validate(data)
        except _PydanticValidationError as e:
            return jsonify({"error": format_validation_error(e)}), 400
    else:
        ok, err = validate_contact_fields(data)
        if not ok:
            return jsonify({"error": err}), 400
        if not data.get("motif", "").strip():
            return jsonify({"error": "Le champ 'motif' est requis."}), 400

    for field in ("date", "heure"):
        if not data.get(field, "").strip():
            return jsonify({"error": f"Le champ '{field}' est requis."}), 400

    motif = data["motif"]
    motif_info = MOTIFS_APPEL.get(motif, MOTIFS_APPEL["autre"])

    # Vérifier que le créneau est libre
    appels = load_appels()
    cle = f"{data['date']}_{data['heure']}"
    for a in appels:
        if a.get("statut") != "annule" and f"{a.get('date')}_{a.get('heure')}" == cle:
            return jsonify({"error": "Ce créneau vient d'être réservé. Veuillez en choisir un autre."}), 409

    # Créer l'appel
    appel = {
        "id": f"AP-{str(uuid.uuid4())[:6].upper()}",
        "created_at": datetime.now().isoformat(),
        "nom": data["nom"].strip(),
        "email": data["email"].strip(),
        "telephone": data["telephone"].strip(),
        "structure": data.get("structure", "").strip(),
        "motif": motif,
        "motif_label": motif_info["label"],
        "priorite": motif_info["priorite"],
        "date": data["date"],
        "heure": data["heure"],
        "duree": "15 minutes",
        "description": data.get("description", "").strip(),
        "contexte_chatbot": data.get("contexte_chatbot", ""),
        "theme": data.get("theme", ""),
        "niveau": data.get("niveau", ""),
        "statut": "planifie",
        "notes_juriste": "",
        "telephone_juriste": "",
    }

    appels.append(appel)
    save_appels(appels)

    logging.info(f"Appel planifié {appel['id']} — {appel['nom']} — {appel['motif_label']} — {appel['date']} {appel['heure']}")
    log_interaction(
        f"[APPEL] {appel['motif_label']}",
        data.get("niveau", "orange"),
        data.get("theme", ""),
        [],
        "appel_15min",
        {"appel_id": appel["id"], "priorite": appel["priorite"]}
    )

    # ── Email au juriste ──
    prio_badge = '<span style="background:#fee2e2;color:#dc2626;padding:3px 12px;border-radius:8px;font-weight:bold;font-size:12px;">URGENT</span>' if appel["priorite"] == "urgente" else '<span style="background:#dbeafe;color:#2563eb;padding:3px 12px;border-radius:8px;font-weight:bold;font-size:12px;">Normal</span>'

    juriste_html = f"""
    <div style="font-family:Arial,sans-serif;max-width:700px;margin:0 auto;">
        <div style="background:linear-gradient(135deg,#1a2744,#1e3a5f);color:#fff;padding:20px 24px;border-radius:12px 12px 0 0;">
            <h2 style="margin:0;font-size:18px;">Demande d'appel 15 min — Premier contact</h2>
            <p style="margin:4px 0 0;opacity:.8;font-size:13px;">Référence : {appel['id']} | {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
        </div>
        <div style="background:#fff;padding:24px;border:1px solid #e5e7eb;border-top:none;">
            <div style="display:flex;gap:12px;align-items:center;margin-bottom:16px;">
                {prio_badge}
                <span style="font-size:14px;color:#4b5563;">{appel['motif_label']}</span>
            </div>
            <table style="width:100%;border-collapse:collapse;font-size:14px;">
                <tr style="background:#f9fafb;"><td style="padding:10px 14px;font-weight:bold;color:#374151;width:35%;border-bottom:1px solid #e5e7eb;">Adhérent</td><td style="padding:10px 14px;border-bottom:1px solid #e5e7eb;">{appel['nom']}</td></tr>
                <tr><td style="padding:10px 14px;font-weight:bold;color:#374151;border-bottom:1px solid #e5e7eb;">Téléphone</td><td style="padding:10px 14px;border-bottom:1px solid #e5e7eb;font-size:16px;font-weight:bold;color:#1a2744;">{appel['telephone']}</td></tr>
                <tr style="background:#f9fafb;"><td style="padding:10px 14px;font-weight:bold;color:#374151;border-bottom:1px solid #e5e7eb;">Email</td><td style="padding:10px 14px;border-bottom:1px solid #e5e7eb;">{appel['email']}</td></tr>
                <tr><td style="padding:10px 14px;font-weight:bold;color:#374151;border-bottom:1px solid #e5e7eb;">Structure</td><td style="padding:10px 14px;border-bottom:1px solid #e5e7eb;">{appel['structure'] or 'Non renseignée'}</td></tr>
                <tr style="background:#eff6ff;"><td style="padding:10px 14px;font-weight:bold;color:#1e3a5f;border-bottom:1px solid #dbeafe;">Date de l'appel</td><td style="padding:10px 14px;font-weight:bold;font-size:16px;color:#1e3a5f;border-bottom:1px solid #dbeafe;">{appel['date']} à {appel['heure']} (15 min)</td></tr>
            </table>
            {f'<div style="margin-top:16px;padding:12px;background:#f9fafb;border-radius:8px;border:1px solid #e5e7eb;"><strong style="font-size:12px;color:#6b7280;">Description :</strong><br><span style="font-size:13px;">{appel["description"]}</span></div>' if appel['description'] else ''}
            {f'<div style="margin-top:12px;padding:12px;background:#f0fdf4;border-radius:8px;border:1px solid #bbf7d0;"><strong style="font-size:12px;color:#6b7280;">Contexte chatbot :</strong><br><span style="font-size:13px;">{appel["contexte_chatbot"]}</span></div>' if appel['contexte_chatbot'] else ''}
        </div>
        <div style="background:#f9fafb;padding:14px 24px;border:1px solid #e5e7eb;border-top:none;border-radius:0 0 12px 12px;font-size:12px;color:#6b7280;">
            Demande issue du chatbot ELISFA — {datetime.now().strftime('%d/%m/%Y à %H:%M')}
        </div>
    </div>
    """
    prio_tag = "[URGENT] " if appel["priorite"] == "urgente" else ""
    send_email_notification(
        f"[ELISFA] {prio_tag}Appel 15 min — {appel['nom']} — {appel['date']} {appel['heure']}",
        juriste_html
    )

    # ── Confirmation adhérent ──
    confirm_html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;">
        <h2 style="color:#1a2744;">Votre appel est planifié — ELISFA</h2>
        <p>Bonjour {appel['nom']},</p>
        <p>Votre demande d'appel de <strong>15 minutes</strong> avec le pôle juridique ELISFA a été enregistrée.</p>
        <table style="width:100%;border-collapse:collapse;margin:16px 0;font-size:14px;">
            <tr style="background:#eff6ff;"><td style="padding:10px 14px;font-weight:bold;border:1px solid #dbeafe;">Référence</td><td style="padding:10px 14px;border:1px solid #dbeafe;">{appel['id']}</td></tr>
            <tr><td style="padding:10px 14px;font-weight:bold;border:1px solid #e5e7eb;">Motif</td><td style="padding:10px 14px;border:1px solid #e5e7eb;">{appel['motif_label']}</td></tr>
            <tr style="background:#f0fdf4;"><td style="padding:10px 14px;font-weight:bold;border:1px solid #bbf7d0;color:#166534;">Date prévue</td><td style="padding:10px 14px;font-weight:bold;border:1px solid #bbf7d0;color:#166534;">{appel['date']} à {appel['heure']}</td></tr>
            <tr><td style="padding:10px 14px;font-weight:bold;border:1px solid #e5e7eb;">Durée</td><td style="padding:10px 14px;border:1px solid #e5e7eb;">15 minutes</td></tr>
        </table>
        <p>Un juriste vous appellera au <strong>{appel['telephone']}</strong> à la date et heure convenues.</p>
        <p style="margin-top:20px;color:#6b7280;font-size:12px;">Ceci est un message automatique du chatbot ELISFA. En cas d'empêchement, merci de prévenir le pôle juridique.</p>
    </div>
    """
    send_email_notification(
        f"[ELISFA] Confirmation appel {appel['id']} — {appel['date']} à {appel['heure']}",
        confirm_html,
        to_email=appel["email"]
    )

    # Webhook
    send_webhook_notification({"event": "appel_15min_planifie", "appel": appel})

    return jsonify({
        "status": "ok",
        "appel_id": appel["id"],
        "message": f"Votre appel {appel['id']} est planifié le {appel['date']} à {appel['heure']}. Un juriste vous appellera au {appel['telephone']}."
    })

@app.route("/api/appels", methods=["GET"])
@require_admin
def liste_appels():
    """Lister tous les appels planifiés (admin)."""
    appels = load_appels()
    appels.sort(key=lambda x: f"{x.get('date','')}_{x.get('heure','')}")
    return jsonify(appels)

@app.route("/api/appel/<appel_id>", methods=["PATCH"])
@require_admin
def update_appel(appel_id):
    """Mettre à jour un appel (admin) — confirmer, annuler, terminer."""
    appels = load_appels()
    data = request.get_json()
    for appel in appels:
        if appel["id"] == appel_id:
            for key in ["statut", "notes_juriste", "telephone_juriste", "compte_rendu"]:
                if key in data:
                    appel[key] = data[key]
            appel["updated_at"] = datetime.now().isoformat()
            save_appels(appels)
            return jsonify({"status": "ok", "appel": appel})
    return jsonify({"error": "Appel non trouvé"}), 404

# ══════════════════════════════════════════════
#         API — Webhook MCP (n8n/Zapier/Make)
# ══════════════════════════════════════════════

@app.route("/api/webhook/ask", methods=["POST"])
def webhook_ask():
    """Webhook MCP : poser une question au chatbot depuis un outil externe.
    Permet l'intégration avec n8n, Zapier, Make, Slack bots, etc.
    """
    # Vérification signature optionnelle
    sig = request.headers.get("X-Webhook-Signature", "")
    if WEBHOOK_SECRET != "elisfa-webhook-secret-change-me" and sig:
        if not verify_webhook_signature(request.data, sig):
            return jsonify({"error": "Signature invalide"}), 403

    data = request.get_json()
    question = data.get("question", "").strip()
    if not question:
        return jsonify({"error": "Le champ 'question' est requis."}), 400

    # Recherche
    results = search_knowledge_base(question)
    niveau = "vert"
    theme = "inconnu"
    if results:
        niveau = results[0]["niveau"]
        theme = results[0]["theme_label"]
        for r in results:
            if r["niveau"] == "rouge":
                niveau = "rouge"
                break
            if r["niveau"] == "orange" and niveau != "rouge":
                niveau = "orange"

    liens, fiches = collect_links_and_fiches(results)
    context = build_context(results)

    # Appel Claude
    client = get_client()
    if client:
        try:
            user_message = f"QUESTION DE L'ADHÉRENT :\n{question}\n\n{context}"
            # Même stratégie de cache que /api/ask : le SYSTEM_PROMPT juridique
            # (stable) est le bloc cachable ; pas de bloc dynamique ici, le
            # webhook est stateless.
            response = call_claude(
                client,
                model=CLAUDE_MODEL,
                max_tokens=CLAUDE_MAX_TOKENS,
                system=build_system_blocks(SYSTEM_PROMPT, ""),
                messages=[{"role": "user", "content": user_message}],
                timeout=60.0,
            )
            answer = response.content[0].text
            mode = "ia"
        except RuntimeError as e:
            logging.error(f"[webhook_ask] Claude error: {e}")
            answer = results[0]["article"]["reponse"]["synthese"] if results else "Erreur IA."
            mode = "fallback"
        except Exception as e:
            logging.error(f"[webhook_ask] Unexpected: {type(e).__name__}: {e}")
            answer = results[0]["article"]["reponse"]["synthese"] if results else "Erreur IA."
            mode = "fallback"
    else:
        answer = results[0]["article"]["reponse"]["synthese"] if results else "Base documentaire insuffisante."
        mode = "local"

    log_interaction(question, niveau, theme, [], f"webhook_{mode}")

    return jsonify({
        "answer": answer,
        "niveau": niveau,
        "theme": theme,
        "mode": mode,
        "liens": liens,
        "fiches": [f["fichier"] for f in fiches],
        "escalade": ESCALADE_CONFIG.get(niveau),
    })

@app.route("/api/webhook/rdv-callback", methods=["POST"])
def webhook_rdv_callback():
    """Webhook entrant : recevoir une confirmation de RDV depuis Calendly/Cal.com/Google Calendar."""
    data = request.get_json()
    rdv_id = data.get("rdv_id", "")
    if not rdv_id:
        return jsonify({"error": "rdv_id requis"}), 400

    rdvs = load_rdv()
    for rdv in rdvs:
        if rdv["id"] == rdv_id:
            rdv["statut"] = "confirme"
            rdv["date_confirmee"] = data.get("date", "")
            rdv["creneau_confirme"] = data.get("creneau", "")
            rdv["lien_visio"] = data.get("lien_visio", "")
            rdv["updated_at"] = datetime.now().isoformat()
            save_rdv(rdvs)
            return jsonify({"status": "ok"})
    return jsonify({"error": "RDV non trouvé"}), 404

# ══════════════════════════════════════════════
#         API — Configuration MCP
# ══════════════════════════════════════════════

@app.route("/api/mcp/config", methods=["GET"])
def mcp_config():
    """Retourne la configuration MCP pour les outils d'intégration."""
    return jsonify({
        "name": "ELISFA Chatbot Juridique",
        "version": "2.0.0",
        "description": "Chatbot juridique CCN ALISFA (IDCC 1261) avec prise de RDV",
        "endpoints": {
            "ask": {
                "url": "/api/webhook/ask",
                "method": "POST",
                "description": "Poser une question juridique",
                "params": {"question": "string (required)"},
            },
            "email_juriste": {
                "url": "/api/email-juriste",
                "method": "POST",
                "description": "Envoyer une question guidée au juriste par email",
                "params": {
                    "nom": "string (required)",
                    "email": "string (required)",
                    "telephone": "string (required)",
                    "theme_guide": "string (required) — contrat_travail|rupture|classification|temps_travail|harcelement_disciplinaire|contentieux|autre",
                    "reponses": "object (required) — réponses au questionnaire guidé",
                    "structure": "string",
                    "niveau": "vert|orange|rouge",
                    "contexte_chatbot": "string",
                },
            },
            "guide_questions": {
                "url": "/api/guide-questions",
                "method": "GET",
                "description": "Obtenir les questions guidées par thème pour structurer une demande",
            },
            "rdv_create": {
                "url": "/api/rdv",
                "method": "POST",
                "description": "Créer un rendez-vous avec un juriste",
                "params": {
                    "nom": "string (required)",
                    "email": "string (required)",
                    "telephone": "string (required)",
                    "sujet": "string (required)",
                    "structure": "string",
                    "contexte": "string",
                    "niveau": "vert|orange|rouge",
                    "date_souhaitee": "string (YYYY-MM-DD)",
                    "creneau": "string (matin|apres-midi)",
                },
            },
            "rdv_callback": {
                "url": "/api/webhook/rdv-callback",
                "method": "POST",
                "description": "Confirmer un RDV depuis un calendrier externe",
                "params": {
                    "rdv_id": "string (required)",
                    "date": "string",
                    "creneau": "string",
                    "lien_visio": "string",
                },
            },
        },
        "calendar_integration": {
            "calendly": CALENDLY_URL or None,
            "calcom": CALCOM_URL or None,
        },
        "models": {
            "current": CLAUDE_MODEL,
            "available": [
                "claude-haiku-4-5-20251001",
                "claude-sonnet-4-20250514",
                "claude-opus-4-20250514",
            ],
        },
    })

# ══════════════════════════════════════════════
#           API — Feedback & Stats
# ══════════════════════════════════════════════

@app.route("/api/functions", methods=["GET"])
def list_functions():
    """Liste les fonctions spécialisées disponibles, regroupées par module."""
    out = {}
    for fid, fn in FUNCTION_PROMPTS.items():
        mod = fn["module"]
        out.setdefault(mod, []).append({
            "id": fid,
            "label": fn["label"],
            "icon": fn["icon"],
            "placeholder": fn["placeholder"],
        })
    return jsonify(out)


@app.route("/api/feedback", methods=["POST"])
def feedback():
    """Validation utilisateur d'une réponse. Permet d'optimiser les réponses futures.
    Champs attendus : rating (1=👍, -1=👎), comment, question, answer, module, function,
                       sources (liste), profile, context (dict).
    """
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({"error": "Payload invalide."}), 400

    # Validation Pydantic (fix 6) : rating doit être -1 ou +1, sinon 400
    if _PYDANTIC_OK:
        try:
            FeedbackRequest.model_validate(data)
        except _PydanticValidationError as e:
            return jsonify({"error": format_validation_error(e)}), 400
    else:
        if data.get("rating") not in (1, -1):
            return jsonify({"error": "rating doit être -1 ou +1."}), 400

    entry = {
        "timestamp": datetime.now().isoformat(),
        "rating": data.get("rating"),
        "comment": (data.get("comment") or "")[:2000],
        "question": (data.get("question") or "")[:2000],
        "answer": (data.get("answer") or "")[:8000],
        "module": data.get("module"),
        "function": data.get("function"),
        "function_label": data.get("function_label"),
        "sources": data.get("sources") or [],
        "profile": data.get("profile"),
        "context": data.get("context") or {},
        "question_hash": data.get("question_hash", ""),
        "user_agent": request.headers.get("User-Agent", "")[:200],
    }
    log_file = LOG_DIR / "feedback.jsonl"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return jsonify({"status": "ok"})


@app.route("/api/feedback/stats", methods=["GET"])
@require_admin
def feedback_stats():
    """Agrégat des feedbacks pour priorisation des optimisations."""
    log_file = LOG_DIR / "feedback.jsonl"
    if not log_file.exists():
        return jsonify({"total": 0, "by_function": {}, "negatives": []})
    by_function = {}
    negatives = []
    total = 0
    with open(log_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            total += 1
            fn = e.get("function") or e.get("module") or "inconnu"
            stats = by_function.setdefault(fn, {"up": 0, "down": 0})
            if e.get("rating") == 1:
                stats["up"] += 1
            elif e.get("rating") == -1:
                stats["down"] += 1
                negatives.append({
                    "ts": e.get("timestamp"),
                    "function": fn,
                    "question": (e.get("question") or "")[:200],
                    "comment": (e.get("comment") or "")[:300],
                })
    return jsonify({"total": total, "by_function": by_function, "negatives": negatives[-50:]})

@app.route("/api/stats")
@require_admin
def stats():
    """Stats d'usage agrégées depuis interactions.jsonl.

    Query params optionnels :
      ?days=N       → ne compte que les N derniers jours (1..365)
      ?theme=X      → filtre sur un thème donné (match exact)
      ?niveau=X     → filtre sur vert|orange|rouge
      ?limit=N      → nb d'entrées récentes retournées (défaut 20, max 200)

    Le parsing est streamé ligne à ligne pour rester constant en mémoire
    même sur un .jsonl de plusieurs dizaines de Mo.
    """
    log_file = LOG_DIR / "interactions.jsonl"
    if not log_file.exists():
        return jsonify({"total": 0, "themes": {}, "niveaux": {}, "recent": []})

    # Parsing et bornage des filtres
    def _bounded_int(name, default, lo, hi):
        raw = request.args.get(name)
        if raw is None:
            return default
        try:
            v = int(raw)
        except (TypeError, ValueError):
            return default
        return max(lo, min(hi, v))

    days = _bounded_int("days", 0, 0, 365)
    limit = _bounded_int("limit", 20, 1, 200)
    theme_filter = (request.args.get("theme") or "").strip()
    niveau_filter = (request.args.get("niveau") or "").strip().lower()
    if niveau_filter and niveau_filter not in ("vert", "orange", "rouge"):
        niveau_filter = ""

    since = None
    if days > 0:
        since = (datetime.now() - timedelta(days=days)).isoformat()

    themes = {}
    niveaux = {"vert": 0, "orange": 0, "rouge": 0}
    recent = []  # on garde les `limit` dernières qui matchent
    total = 0

    with open(log_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            # Filtres (chaînes iso → comparaison lexicographique OK)
            if since and (e.get("timestamp") or "") < since:
                continue
            t = e.get("theme", "inconnu")
            n = e.get("niveau", "vert")
            if theme_filter and t != theme_filter:
                continue
            if niveau_filter and n != niveau_filter:
                continue
            total += 1
            themes[t] = themes.get(t, 0) + 1
            niveaux[n] = niveaux.get(n, 0) + 1
            recent.append(e)
            if len(recent) > limit:
                # Ring buffer : on garde les `limit` plus récentes
                recent = recent[-limit:]

    return jsonify({
        "total": total,
        "themes": themes,
        "niveaux": niveaux,
        "recent": recent,
        "filters": {
            "days": days or None,
            "theme": theme_filter or None,
            "niveau": niveau_filter or None,
            "limit": limit,
        },
    })

@app.route("/api/knowledge")
@require_admin
def knowledge():
    # Expose la KB juridique en lecture — bénéficie du hot-reload auto si
    # base_juridique.json a changé depuis le dernier accès.
    refresh_kbs_if_changed()
    return jsonify(KB)

@app.route("/api/reload", methods=["POST"])
@require_admin
def reload_kb():
    """Force le rechargement de toutes les bases + reconstruction des index.

    Utile pour :
      - contourner le cooldown d'1 s du cache mtime (ex. fichier restauré
        depuis un backup avec un mtime antérieur),
      - forcer un rebuild d'index si on suspecte un état incohérent.

    Le chemin "normal" reste le hot-reload auto via ``refresh_kbs_if_changed``
    appelé en tête des endpoints critiques — c'est quasi-gratuit.
    """
    global KB
    # Invalide tous les caches (KB + KB_FORMATION + KB_GOUVERNANCE + KB_RH)
    _kb_invalidate_all()
    # Recharge + rebuild d'index (propagé via refresh_kbs_if_changed)
    refresh_kbs_if_changed()
    # Mettre à jour la référence dans MODULE_CONFIG (construit au module load
    # sur la référence ancienne — il faut réassigner post-reload).
    if "juridique" in MODULE_CONFIG:
        MODULE_CONFIG["juridique"]["kb"] = KB
    if "formation" in MODULE_CONFIG:
        MODULE_CONFIG["formation"]["kb"] = KB_FORMATION
    if "gouvernance" in MODULE_CONFIG:
        MODULE_CONFIG["gouvernance"]["kb"] = KB_GOUVERNANCE
    if "rh" in MODULE_CONFIG:
        MODULE_CONFIG["rh"]["kb"] = KB_RH
    return jsonify({
        "status": "ok",
        "themes": len(KB.get("themes", [])),
        "indexed_tokens": len((KB.get("_index") or {}).get("inverted", {})),
    })

@app.route("/api/annuaire")
def annuaire_proxy():
    """Proxy vers l'API Annuaire Service Public v2 (api-lannuaire.service-public.fr)."""
    import urllib.request, urllib.error, urllib.parse
    commune = request.args.get("commune", "")
    dept = request.args.get("dept", "")
    type_etab = request.args.get("type", "maison_association")
    search = request.args.get("q", "")
    # Sanitize type
    allowed = ("maison_association", "crib", "prefecture", "point_justice", "france_services")
    if type_etab not in allowed:
        type_etab = "maison_association"

    base = "https://api-lannuaire.service-public.fr/api/explore/v2.1/catalog/datasets/api-lannuaire-administration/records"
    conditions = []
    if commune:
        conditions.append(f'code_insee_commune="{commune}"')
    # Only filter by pivot type if not doing a name search
    if type_etab and not search:
        conditions.append(f'pivot LIKE "{type_etab}"')
    if search:
        conditions.append(f'nom LIKE "{search}"')
    if not commune and dept:
        conditions.append(f'code_insee_commune LIKE "{dept}"')

    where = " AND ".join(conditions) if conditions else 'pivot LIKE "crib"'
    params = urllib.parse.urlencode({"where": where, "limit": 20, "select": "nom,adresse,telephone,adresse_courriel,site_internet,pivot,code_insee_commune"})
    url = f"{base}?{params}"

    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "ELISFA-Chatbot/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        # Normalize to GeoJSON-like features for frontend compatibility
        features = []
        for r in data.get("results", []):
            adresses = []
            adr = r.get("adresse") or []
            if isinstance(adr, str):
                try: adr = json.loads(adr)
                except (json.JSONDecodeError, ValueError): adr = []
            if isinstance(adr, list):
                for a in adr:
                    if isinstance(a, dict):
                        adresses.append({
                            "lignes": [a.get("numero_voie", ""), a.get("complement1", ""), a.get("complement2", "")],
                            "codePostal": a.get("code_postal", ""),
                            "commune": a.get("nom_commune", "")
                        })
            def _parse_field(val):
                """Parse API field that may be a JSON string, list, or plain string."""
                if not val: return []
                if isinstance(val, str):
                    try: val = json.loads(val)
                    except (json.JSONDecodeError, ValueError): return [val]
                if isinstance(val, list): return val
                return [val]

            tels = _parse_field(r.get("telephone"))
            tel_val = ""
            if tels:
                t = tels[0]
                tel_val = t.get("valeur", "") if isinstance(t, dict) else str(t)
            emails = _parse_field(r.get("adresse_courriel"))
            email_val = ""
            if emails:
                e = emails[0]
                email_val = e.get("valeur", "") if isinstance(e, dict) else str(e)
            sites = _parse_field(r.get("site_internet"))
            url_val = ""
            if sites:
                s = sites[0]
                url_val = s.get("valeur", "") if isinstance(s, dict) else str(s)
            features.append({"properties": {
                "nom": r.get("nom", ""),
                "adresses": adresses,
                "telephone": tel_val,
                "email": email_val,
                "url": url_val
            }})
        return jsonify({"features": features, "total": data.get("total_count", 0)})
    except Exception:
        return jsonify({"features": [], "total": 0})

# ══════════════════════════════════════════════
#        Bibliothèque PDF ALISFA (scrapée)
# ══════════════════════════════════════════════

ALISFA_PDFS_DIR = DATA_DIR / "alisfa_public" / "pdfs"
ALISFA_DOCS_DIR = DATA_DIR / "alisfa_docs"
PDF_INDEX_FILE = DATA_DIR / "alisfa_public" / "pdf_index.jsonl"

CATEGORY_LABELS = {
    "avenant": "Avenants à la CCN",
    "accord": "Accords de branche",
    "guide": "Guides",
    "guide_paritaire": "Guides paritaires",
    "brochure": "Brochures",
    "fiche_metier": "Fiches métiers (CPNEF)",
    "lettre_info": "Lettres d'information",
    "rapport_etude": "Rapports & études",
    "affiche_flyer": "Affiches & flyers",
    "sante_securite": "Santé & sécurité",
    "prevoyance_sante": "Prévoyance & santé",
    "communique_presse": "Communiqués de presse",
    "gpec": "GEPP / GPEC",
    "formulaire": "Formulaires & modèles",
    "cppni": "Délibérations & positions CPPNI",
    "autre": "Autres documents",
}

ALLOWED_EXTS = {".pdf", ".docx", ".xlsx", ".pptx", ".doc", ".xls", ".ppt"}

def _guess_category_from_name(name: str) -> str:
    n = name.lower()
    if ("deliberation-cppni" in n or "deelibeeration-cppni" in n
        or "position-cppni" in n or "saisine-cppni" in n
        or (n.startswith("saisie-") and "avenant-10-22" in n)):
        return "cppni"
    if n.startswith("formulaire") or n.startswith("modele-") or "tableau-prealable" in n:
        return "formulaire"
    if "ppt-" in n or n.endswith(".pptx") or n.endswith(".ppt"):
        return "formulaire"
    if "guide-paritaire" in n:
        return "guide_paritaire"
    if "avenant" in n:
        return "avenant"
    if "accord" in n:
        return "accord"
    if "cpnef-fiche-metier" in n:
        return "fiche_metier"
    if "lettre-dinfo" in n or "lettre-n-" in n or "newsletter" in n:
        return "lettre_info"
    if "panorama" in n or "etude" in n or "rapport" in n:
        return "rapport_etude"
    if "brochure" in n or "depliant" in n or "flyer" in n:
        return "brochure"
    return "autre"

def _humanize_title(filename: str) -> str:
    stem = Path(filename).stem
    stem = re.sub(r"[-_]+", " ", stem).strip()
    return stem[:1].upper() + stem[1:] if stem else filename

def load_pdf_library():
    """Construit l'index complet des PDF ELISFA à partir de pdf_index.jsonl
    et fusionne les PDFs présents dans alisfa_docs non indexés."""
    items = []
    seen_files = set()
    if PDF_INDEX_FILE.exists():
        try:
            with open(PDF_INDEX_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        d = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    fname = d.get("file")
                    if not fname or fname in seen_files:
                        continue
                    seen_files.add(fname)
                    # Priorité : si le nom matche une règle CPPNI/formulaire, on écrase
                    # la catégorie héritée du scraper par la règle sémantique.
                    guessed = _guess_category_from_name(fname)
                    if guessed in ("cppni", "formulaire"):
                        cat = guessed
                    else:
                        cat = d.get("category", "autre")
                    items.append({
                        "file": fname,
                        "title": _humanize_title(fname),
                        "category": cat,
                        "category_label": CATEGORY_LABELS.get(cat, "Autres documents"),
                        "pages": d.get("pages", 0),
                        "size": d.get("size", 0),
                        "source": "alisfa_public",
                        "ext": "pdf",
                    })
        except Exception as e:
            logging.error(f"Erreur lecture pdf_index.jsonl : {e}")
    # Compléter avec tous les fichiers d'alisfa_docs (PDF + DOCX + XLSX + PPTX)
    if ALISFA_DOCS_DIR.exists():
        for p in sorted(ALISFA_DOCS_DIR.iterdir()):
            if not p.is_file() or p.suffix.lower() not in ALLOWED_EXTS:
                continue
            if p.name in seen_files:
                continue
            seen_files.add(p.name)
            cat = _guess_category_from_name(p.name)
            items.append({
                "file": p.name,
                "title": _humanize_title(p.name),
                "category": cat,
                "category_label": CATEGORY_LABELS.get(cat, CATEGORY_LABELS["autre"]),
                "pages": 0,
                "size": p.stat().st_size,
                "source": "alisfa_docs",
                "ext": p.suffix.lower().lstrip("."),
            })
    # Tri : catégorie puis titre
    cat_order = list(CATEGORY_LABELS.keys())
    items.sort(key=lambda x: (cat_order.index(x["category"]) if x["category"] in cat_order else 99, x["title"].lower()))
    return items

PDF_LIBRARY = load_pdf_library()
logging.info(f"Bibliothèque PDF ALISFA chargée : {len(PDF_LIBRARY)} documents")

@app.route("/api/pdf-library")
def api_pdf_library():
    """Retourne l'index complet des PDF ELISFA cliquables."""
    return jsonify({
        "total": len(PDF_LIBRARY),
        "categories": [
            {"key": k, "label": v, "count": sum(1 for p in PDF_LIBRARY if p["category"] == k)}
            for k, v in CATEGORY_LABELS.items()
            if any(p["category"] == k for p in PDF_LIBRARY)
        ],
        "items": PDF_LIBRARY,
    })

@app.route("/pdfs/alisfa/<path:filename>")
def serve_alisfa_pdf(filename):
    """Sert un document ALISFA (PDF/DOCX/XLSX/PPTX) depuis alisfa_public ou alisfa_docs."""
    # 1. alisfa_public/pdfs
    primary = (ALISFA_PDFS_DIR / filename).resolve()
    if str(primary).startswith(str(ALISFA_PDFS_DIR.resolve())) and primary.exists():
        return send_from_directory(str(ALISFA_PDFS_DIR), filename)
    # 2. Fallback : alisfa_docs
    alt = (ALISFA_DOCS_DIR / filename).resolve()
    if str(alt).startswith(str(ALISFA_DOCS_DIR.resolve())) and alt.exists():
        return send_from_directory(str(ALISFA_DOCS_DIR), filename)
    abort(404)

@app.route("/api/health")
def health():
    """Health check pour monitoring / déploiement.

    Inclut les métriques Claude (cache hit ratio, compteurs d'erreurs typées)
    pour surveiller la qualité du prompt caching et détecter les dégradations.
    """
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "model": CLAUDE_MODEL,
        "api_configured": bool(ANTHROPIC_API_KEY),
        "smtp_configured": bool(SMTP_USER),
        "webhook_configured": bool(NOTIFICATION_WEBHOOK_URL),
        "themes_count": len(KB.get("themes", [])),
        "claude_metrics": get_claude_metrics_snapshot(),
    })


# ══════════════════════════════════════════════
#     DOCUMENTATION API (OpenAPI + Swagger UI)
# ══════════════════════════════════════════════
# Expose :
#   - ``GET /api/openapi.yaml`` → fichier brut (utilisé par d'autres outils)
#   - ``GET /api/docs``         → Swagger UI interactif
# Le fichier source est ``docs/openapi.yaml`` — maintenu à la main.
# Pas de génération automatique depuis les modèles Pydantic : on garde un
# contrat stable que l'on peut publier même sans déployer le code.

_OPENAPI_PATH = BASE_DIR / "docs" / "openapi.yaml"


@app.route("/api/openapi.yaml")
def openapi_spec_yaml():
    """Sert le fichier OpenAPI brut (YAML)."""
    if not _OPENAPI_PATH.exists():
        return jsonify({"error": "Spécification OpenAPI absente."}), 404
    return send_from_directory(
        directory=str(_OPENAPI_PATH.parent),
        path=_OPENAPI_PATH.name,
        mimetype="application/yaml",
    )


@app.route("/api/openapi.json")
def openapi_spec_json():
    """Sert la spec OpenAPI en JSON (converti depuis YAML à la volée).

    Les outils type Postman/Insomnia préfèrent JSON ; on garde le YAML pour
    l'édition humaine (lisible + commentaires).
    """
    try:
        import yaml  # type: ignore
    except ImportError:
        return jsonify({
            "error": "PyYAML non installé. Utilisez /api/openapi.yaml."
        }), 501
    if not _OPENAPI_PATH.exists():
        return jsonify({"error": "Spécification OpenAPI absente."}), 404
    try:
        with open(_OPENAPI_PATH, "r", encoding="utf-8") as f:
            spec = yaml.safe_load(f)
        return jsonify(spec)
    except Exception as e:
        logging.error("[openapi] conversion YAML→JSON échouée : %s", e)
        return jsonify({"error": "Erreur de parsing OpenAPI."}), 500


# Blueprint Swagger UI (le package monte tout le JS/CSS automatiquement)
try:
    from flask_swagger_ui import get_swaggerui_blueprint  # type: ignore
    _swagger_bp = get_swaggerui_blueprint(
        base_url="/api/docs",
        api_url="/api/openapi.yaml",
        config={"app_name": "ELISFA Chatbot Juridique"},
    )
    app.register_blueprint(_swagger_bp, url_prefix="/api/docs")
    logging.info("[openapi] Swagger UI monté sur /api/docs")
except ImportError:
    logging.info(
        "[openapi] flask-swagger-ui absent — Swagger UI désactivé. "
        "La spec reste accessible via /api/openapi.yaml et /api/openapi.json."
    )


# ══════════════════════════════════════════════
#                  MAIN
# ══════════════════════════════════════════════

if __name__ == "__main__":
    print(f"\n{'='*60}")
    print(f"  ELISFA — Assistant Juridique CCN ALISFA v2.0")
    print(f"  Démarrage sur http://{HOST}:{PORT}")
    print(f"  Modèle IA : {CLAUDE_MODEL}")
    print(f"  Mode : {'IA' if ANTHROPIC_API_KEY else 'Local (sans IA)'}")
    print(f"  SMTP : {'Configuré' if SMTP_USER else 'Non configuré'}")
    print(f"  Webhook : {'Configuré' if NOTIFICATION_WEBHOOK_URL else 'Non configuré'}")
    print(f"{'='*60}\n")
    app.run(host=HOST, port=PORT, debug=DEBUG)
