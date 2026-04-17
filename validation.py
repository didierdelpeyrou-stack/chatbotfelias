"""Modèles Pydantic pour les payloads JSON entrants.

Pourquoi Pydantic ?
-------------------
La validation manuelle dans app.py (``data.get("x")`` + vérifications ad-hoc)
est fragile : il est facile d'oublier un cas (type, longueur, whitelist), ce
qui laisse passer des payloads malformés jusqu'au cœur de la logique métier
— ou pire, jusqu'à Claude (qui facture chaque token).

Pydantic v2 permet :
  - une validation déclarative unique (un seul endroit, lisible),
  - des messages d'erreur cohérents (sans concaténation ad-hoc),
  - une coercion douce sur les types simples (str/int/float),
  - une vérification stricte de la racine (``extra="ignore"`` pour tolérer
    les clés futures sans casser la compat).

Les constantes de longueur sont ré-importées depuis app.py pour rester la
source de vérité. Cette module n'impose aucune dépendance sur Flask : il
peut être testé en isolation.
"""

from __future__ import annotations

import re
from typing import Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ── Bornes (dupliquées de app.py pour éviter une dépendance circulaire) ──
# Si on les change ici, les changer aussi dans app.py (constantes en haut).
MAX_QUESTION_CHARS = 5000
MAX_DOC_CONTEXT_CHARS = 120_000
MAX_DOC_NAME_CHARS = 200
MAX_HISTORY_MESSAGES = 20
MAX_CONTEXT_ENTRIES = 20
MAX_CONTEXT_KEY_CHARS = 60
MAX_CONTEXT_VAL_CHARS = 200
MAX_NOM_CHARS = 200
MAX_SUJET_CHARS = 500
MAX_STRUCTURE_CHARS = 300
MAX_CONTEXTE_CHARS = 2000
MAX_MOTIF_CHARS = 200
MAX_DESCRIPTION_CHARS = 2000

ALLOWED_MODULES = {"juridique", "formation", "rh", "gouvernance"}
ALLOWED_ESCALATION = {"vert", "orange", "rouge"}
ALLOWED_FEEDBACK_VALUES = {-1, 1}

# Regex cohérentes avec celles de app.py (validate_email/validate_phone)
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE_CLEAN_RE = re.compile(r"[\s\-\.\(\)\+]")
_PHONE_DIGITS_RE = re.compile(r"^\d{6,15}$")


# ── Modèle de base : tolère les clés inconnues (compat future) ──
class _LooseBase(BaseModel):
    """Base commune : ignore les clés non déclarées plutôt que de rejeter.

    Pourquoi ? Si le frontend évolue plus vite que le backend (nouveau champ
    ajouté côté UI mais pas encore côté API), on veut que l'API continue de
    fonctionner avec les champs connus et ignore le reste, au lieu de 400.
    C'est plus robuste sur une architecture client/serveur versionnée
    indépendamment (prod Docker ≠ dev local).
    """

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=False)


# ──────────────────────────── /api/ask ────────────────────────────

class AskRequest(_LooseBase):
    """Payload attendu par ``POST /api/ask``.

    Règles métier (cf. app.py endpoint /api/ask) :
      - ``question`` peut être vide SI ``document`` est fourni (on se replie
        sur "Analyse ce document"). Vérification cross-champs dans
        ``validate_question_or_document``.
      - ``document`` trop long est **tronqué silencieusement** par le handler
        (pour ne pas casser les uploads OCR volumineux). Ici, on plafonne
        juste la taille brute acceptée (via MAX_CONTENT_LENGTH sur Flask).
      - ``module`` doit appartenir à la whitelist, sinon on retombe sur
        ``juridique`` (équivalent logique : le champ est corrigé, pas rejeté).
    """

    question: str = Field(default="", max_length=MAX_QUESTION_CHARS * 2)
    # *2 : on accepte jusqu'à 2× la limite pour tolérer l'ancienne
    # concaténation "question + document" que le handler sépare via regex.
    # La vraie limite après split est appliquée dans /api/ask.

    document: str = Field(default="", max_length=MAX_DOC_CONTEXT_CHARS * 2)
    document_name: str = Field(default="", max_length=MAX_DOC_NAME_CHARS * 2)
    history: list = Field(default_factory=list)
    module: str = "juridique"
    function: Optional[str] = None
    profile: Optional[str] = None
    context: Optional[dict] = None
    rdv_proposed: bool = False
    escalation_level: str = "vert"

    @field_validator("module", mode="before")
    @classmethod
    def _normalize_module(cls, v):
        """Corrige silencieusement un module inconnu vers ``juridique``."""
        if not isinstance(v, str):
            return "juridique"
        v = v.strip().lower()
        return v if v in ALLOWED_MODULES else "juridique"

    @field_validator("escalation_level", mode="before")
    @classmethod
    def _normalize_escalation(cls, v):
        if not isinstance(v, str):
            return "vert"
        v = v.strip().lower()
        return v if v in ALLOWED_ESCALATION else "vert"

    @field_validator("function", "profile", mode="before")
    @classmethod
    def _truncate_short_str(cls, v):
        """Tronque à 80 chars, ou None si pas une str."""
        if not isinstance(v, str):
            return None
        v = v.strip()
        return v[:80] if v else None

    @field_validator("history", mode="before")
    @classmethod
    def _clean_history(cls, v):
        """Garde au plus MAX_HISTORY_MESSAGES entrées. Accepte toute liste."""
        if not isinstance(v, list):
            return []
        return v[-MAX_HISTORY_MESSAGES:]

    @field_validator("context", mode="before")
    @classmethod
    def _clean_context(cls, v):
        """Normalise un dict {str: str} borné. None si rien d'utilisable."""
        if not isinstance(v, dict):
            return None
        cleaned: dict = {}
        for k, val in list(v.items())[:MAX_CONTEXT_ENTRIES]:
            if not isinstance(k, str):
                continue
            if not isinstance(val, (str, int, float)):
                continue
            cleaned[str(k)[:MAX_CONTEXT_KEY_CHARS]] = str(val)[:MAX_CONTEXT_VAL_CHARS]
        return cleaned or None


# ─────────────────── Champs contact communs (RDV, email, appel) ───────────────────

class ContactFields(_LooseBase):
    """Bloc contact partagé (nom + email + téléphone).

    Utilisé comme base pour RdvRequest, AppelRequest, EmailJuristeRequest :
    évite la duplication des règles de validation email/téléphone.
    """

    nom: str = Field(..., min_length=2, max_length=MAX_NOM_CHARS)
    email: str = Field(..., max_length=200)
    telephone: str = Field(..., max_length=30)

    @field_validator("nom")
    @classmethod
    def _strip_nom(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Le nom est requis (2 caractères minimum).")
        return v

    @field_validator("email")
    @classmethod
    def _check_email(cls, v: str) -> str:
        v = v.strip()
        if not _EMAIL_RE.match(v):
            raise ValueError("Adresse email invalide.")
        return v

    @field_validator("telephone")
    @classmethod
    def _check_phone(cls, v: str) -> str:
        cleaned = _PHONE_CLEAN_RE.sub("", v)
        if not _PHONE_DIGITS_RE.match(cleaned):
            raise ValueError("Numéro de téléphone invalide.")
        return v.strip()


# ──────────────────────────── /api/rdv ────────────────────────────

class RdvRequest(ContactFields):
    """Payload de ``POST /api/rdv`` : prise de rendez-vous juriste."""

    sujet: str = Field(..., min_length=1, max_length=MAX_SUJET_CHARS)
    structure: Optional[str] = Field(default=None, max_length=MAX_STRUCTURE_CHARS)
    contexte: Optional[str] = Field(default=None, max_length=MAX_CONTEXTE_CHARS)
    niveau: Optional[str] = Field(default=None, max_length=20)
    theme: Optional[str] = Field(default=None, max_length=200)
    date_souhaitee: Optional[str] = Field(default=None, max_length=50)
    creneau: Optional[str] = Field(default=None, max_length=200)

    @field_validator("sujet")
    @classmethod
    def _strip_sujet(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Le sujet est requis.")
        return v


# ──────────────────────────── /api/appel ────────────────────────────

class AppelRequest(ContactFields):
    """Payload de ``POST /api/appel`` : demande d'appel 15 min."""

    motif: str = Field(..., min_length=1, max_length=MAX_MOTIF_CHARS)
    date: Optional[str] = Field(default=None, max_length=50)
    heure: Optional[str] = Field(default=None, max_length=20)
    description: Optional[str] = Field(default=None, max_length=MAX_DESCRIPTION_CHARS)


# ──────────────────────────── /api/email-juriste ────────────────────────────

class EmailJuristeRequest(ContactFields):
    """Payload de ``POST /api/email-juriste`` : email structuré au juriste."""

    theme_guide: str = Field(..., min_length=1, max_length=200)
    reponses: dict = Field(...)
    sujet: Optional[str] = Field(default=None, max_length=MAX_SUJET_CHARS)

    @field_validator("reponses")
    @classmethod
    def _reponses_nonvide(cls, v: dict) -> dict:
        if not isinstance(v, dict) or not v:
            raise ValueError("Les réponses au guide sont requises.")
        return v


# ──────────────────────────── /api/feedback ────────────────────────────

class FeedbackRequest(_LooseBase):
    """Payload de ``POST /api/feedback`` : rating +1/-1 sur une réponse."""

    rating: int
    question: str = Field(default="", max_length=2000)
    answer: str = Field(default="", max_length=8000)
    comment: str = Field(default="", max_length=2000)
    module: Optional[str] = Field(default=None, max_length=40)
    escalation_level: Optional[str] = Field(default=None, max_length=20)

    @field_validator("rating")
    @classmethod
    def _check_rating(cls, v: int) -> int:
        if v not in ALLOWED_FEEDBACK_VALUES:
            raise ValueError("rating doit être -1 ou +1.")
        return v


# ──────────────────────────── Utilitaire ────────────────────────────

def format_validation_error(err) -> str:
    """Transforme une ``ValidationError`` Pydantic en message FR lisible.

    Prend la première erreur rencontrée — suffisant pour le frontend qui
    affiche un toast. Les détails complets restent disponibles dans
    ``err.errors()`` pour le logging si besoin.
    """
    try:
        errors = err.errors()
        if not errors:
            return "Payload invalide."
        first = errors[0]
        # Pydantic fournit un ctx.reason pour nos ValueError custom
        msg = first.get("msg", "Champ invalide.")
        # Nettoyage : Pydantic préfixe souvent "Value error, <msg>"
        msg = msg.replace("Value error, ", "")
        loc = first.get("loc", ())
        if loc and loc[0] not in ("__root__",):
            return f"{loc[0]} : {msg}"
        return msg
    except Exception:
        return "Payload invalide."


__all__ = [
    "AskRequest",
    "AppelRequest",
    "ContactFields",
    "EmailJuristeRequest",
    "FeedbackRequest",
    "RdvRequest",
    "format_validation_error",
    "ALLOWED_MODULES",
    "ALLOWED_ESCALATION",
    "ALLOWED_FEEDBACK_VALUES",
]
