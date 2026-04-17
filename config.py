"""
ELISFA Chatbot — Configuration centralisée
Toutes les variables d'environnement et paramètres sont définis ici.
"""
import os
from pathlib import Path

# ── Chemins ──
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"
FICHES_DIR = BASE_DIR / "fiches_pratiques"

# ── API Anthropic ──
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
# Modèle par défaut : Haiku (rapide et économique)
# Options : claude-haiku-4-5-20251001, claude-sonnet-4-20250514, claude-opus-4-20250514
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-haiku-4-5-20251001")
CLAUDE_MAX_TOKENS = int(os.environ.get("CLAUDE_MAX_TOKENS", "8000"))

# ── Serveur ──
PORT = int(os.environ.get("PORT", "8080"))
HOST = os.environ.get("HOST", "0.0.0.0")
DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
SECRET_KEY = os.environ.get("SECRET_KEY", os.urandom(32).hex())

# ── Notifications email (SMTP) ──
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
SMTP_FROM = os.environ.get("SMTP_FROM", "chatbot@elisfa.fr")
JURISTE_EMAIL = os.environ.get("JURISTE_EMAIL", "juridique@elisfa.fr")

# ── Webhook MCP / Intégrations ──
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "elisfa-webhook-secret-change-me")
# Calendly : URL d'embed ou API
CALENDLY_URL = os.environ.get("CALENDLY_URL", "")
# Cal.com : URL d'embed
CALCOM_URL = os.environ.get("CALCOM_URL", "")
# Google Calendar API
GOOGLE_CALENDAR_ID = os.environ.get("GOOGLE_CALENDAR_ID", "")
# N8N / Zapier / Make webhook URL pour notifications
NOTIFICATION_WEBHOOK_URL = os.environ.get("NOTIFICATION_WEBHOOK_URL", "")

# ── Niveaux d'escalade ──
ESCALADE_CONFIG = {
    "vert": {
        "label": "Réponse automatique",
        "description": "La réponse est fournie automatiquement par le chatbot.",
        "action": "none",
        "delai": None,
    },
    "orange": {
        "label": "Vérification recommandée",
        "description": "La réponse nécessite une vérification. Un rappel par email est proposé.",
        "action": "email_callback",
        "delai": "48h ouvrées",
    },
    "rouge": {
        "label": "Consultation juriste requise",
        "description": "Le sujet est sensible et nécessite un rendez-vous avec un juriste ELISFA.",
        "action": "rdv_juriste",
        "delai": "Rendez-vous sous 5 jours ouvrés",
    },
}

# ── Rate limiting ──
RATE_LIMIT_PER_MINUTE = int(os.environ.get("RATE_LIMIT_PER_MINUTE", "20"))
RATE_LIMIT_PER_HOUR = int(os.environ.get("RATE_LIMIT_PER_HOUR", "100"))

# ── CORS ──
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*").split(",")
