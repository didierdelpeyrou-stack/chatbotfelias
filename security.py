"""Sécurité — hash des secrets admin & helpers d'authentification.

Objectif
--------
Jusqu'ici, ``ADMIN_PASS`` était chargé en clair depuis l'environnement puis
comparé via ``hmac.compare_digest``. Ça résiste aux timing attacks, mais :

  1. Le mot de passe reste en clair dans la mémoire du process tant qu'il
     tourne — n'importe quel ``/proc/<pid>/environ`` ou core dump le révèle.
  2. Le fichier ``.env`` sur le VPS contient le secret en clair : si la
     machine est compromise ou si un backup fuite, le mot de passe l'est.
  3. Impossible de prouver au code qu'on connaît le hash sans connaître le
     secret — toute rotation demande de modifier ``.env`` puis de redémarrer.

Cette couche introduit **bcrypt** (12 rounds par défaut, équivalent
~250 ms/check sur un VPS moderne) et une **compat descendante** avec
l'ancienne variable ``ADMIN_PASS``. Tant que la prod a ``ADMIN_PASS``
défini, elle continue à fonctionner. Quand on aura généré un hash via
``scripts/generate_admin_hash.py`` et défini ``ADMIN_PASS_HASH``, le code
préfère systématiquement le hash et un warning est loggé si ``ADMIN_PASS``
traîne encore.

Choix de bcrypt (et pas argon2/scrypt)
--------------------------------------
  - bcrypt est dans la stdlib C (via ``libffi``), 1 dépendance, largement
    audité, pas de paramètres ésotériques à comprendre.
  - argon2-cffi tire 2 dépendances natives + 3 paramètres (time_cost,
    memory_cost, parallelism) qu'on aurait tuné sans vrai besoin.
  - Pour un endpoint admin à faible fréquence (< 10 req/jour), bcrypt est
    largement suffisant (le but est ≥100 ms/tentative, pas 1 ms).
"""

from __future__ import annotations

import hmac
import logging
import os
import secrets
from typing import Optional

try:
    import bcrypt  # type: ignore
except ImportError:  # pragma: no cover
    bcrypt = None  # module optionnel — si absent, on loggue au 1er check


# ── Cost factor ──
# 12 rounds = ~250 ms/check sur un CPU moderne (2024). Au-delà, on ralentit
# inutilement les tentatives légitimes sans gain significatif (l'attaquant
# utilisera de toute façon un ASIC ou une GPU farm). 12 est le défaut
# actuel recommandé par OWASP.
BCRYPT_ROUNDS = int(os.getenv("BCRYPT_ROUNDS", "12"))


class AdminAuthError(Exception):
    """Erreur d'auth admin (mauvais login OU configuration absente)."""


def hash_password(plain: str, rounds: Optional[int] = None) -> str:
    """Hash un mot de passe en clair avec bcrypt.

    Renvoie le hash au format ``$2b$12$...`` (ASCII, 60 chars). À stocker
    dans ``ADMIN_PASS_HASH`` du ``.env``, JAMAIS dans le dépôt Git.

    Usage
    -----
        >>> hash_password("elisfa2026")
        '$2b$12$xYz...'
    """
    if bcrypt is None:
        raise RuntimeError(
            "bcrypt non installé — `pip install bcrypt>=4.1` "
            "(voir requirements.txt)."
        )
    if not plain:
        raise ValueError("Mot de passe vide.")
    salt = bcrypt.gensalt(rounds=rounds or BCRYPT_ROUNDS)
    return bcrypt.hashpw(plain.encode("utf-8"), salt).decode("ascii")


def verify_password(plain: str, hashed: str) -> bool:
    """Compare un mot de passe clair à son hash bcrypt.

    Robuste : renvoie False proprement si le hash est malformé ou vide,
    plutôt que de lever. Les exceptions au niveau bcrypt sont silencées
    pour éviter qu'un admin malheureux expose si le hash est présent ou pas.
    """
    if bcrypt is None:
        return False
    if not plain or not hashed:
        return False
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        # Hash malformé, signature non bcrypt, etc. → refus propre
        return False


def verify_admin_credentials(
    username: str,
    password: str,
    *,
    expected_user: str,
    hashed_password: Optional[str] = None,
    plain_password: Optional[str] = None,
) -> bool:
    """Vérifie les credentials admin avec compat descendante.

    Ordre de priorité :
      1. Si ``hashed_password`` (``ADMIN_PASS_HASH``) est fourni → bcrypt.
      2. Sinon, si ``plain_password`` (``ADMIN_PASS``) est fourni → hmac
         compare_digest (comportement legacy).
      3. Sinon → refus (pas de credential configuré).

    La vérification du username passe toujours par ``hmac.compare_digest``
    pour éviter les timing attacks (longueur variable).

    Le choix de privilégier le hash SI il est fourni assure une migration
    en douceur : en prod, on peut déployer le code puis définir
    ``ADMIN_PASS_HASH`` plus tard — rien ne casse entre-temps.
    """
    # username toujours en timing-safe compare
    user_ok = hmac.compare_digest(
        (username or "").encode("utf-8"),
        (expected_user or "").encode("utf-8"),
    )
    if not user_ok:
        return False

    if hashed_password:
        return verify_password(password, hashed_password)
    if plain_password:
        return hmac.compare_digest(
            (password or "").encode("utf-8"),
            plain_password.encode("utf-8"),
        )
    return False


def admin_auth_configured(
    hashed_password: Optional[str] = None,
    plain_password: Optional[str] = None,
) -> bool:
    """Indique si au moins un credential admin est configuré.

    Utilisé au démarrage pour logger un warning lisible si l'admin est
    désactivé (pas de password, pas de hash) — et par ``require_admin``
    pour court-circuiter proprement.
    """
    return bool(hashed_password) or bool(plain_password)


def generate_random_password(length: int = 24) -> str:
    """Génère un mot de passe alphanumérique aléatoire (URL-safe).

    Utilisé par ``scripts/generate_admin_hash.py`` en mode "je veux juste
    un nouveau mdp aléatoire fort". ``secrets`` > ``random`` : entropie
    cryptographique, pas déterministe.
    """
    # 24 chars de base64 URL-safe = 18 octets = 144 bits d'entropie.
    # Largement au-dessus du seuil de brute-force offline.
    return secrets.token_urlsafe(max(12, length * 3 // 4))[:length]


def warn_if_legacy_admin(logger: logging.Logger, has_hash: bool, has_plain: bool) -> None:
    """Log un warning si ``ADMIN_PASS`` est encore défini alors que
    ``ADMIN_PASS_HASH`` existe aussi (migration incomplète)."""
    if has_hash and has_plain:
        logger.warning(
            "[security] ADMIN_PASS_HASH et ADMIN_PASS sont tous deux définis. "
            "Le hash prime ; supprimez ADMIN_PASS du .env pour clore la "
            "migration et éviter la présence du secret en clair."
        )
    elif not has_hash and has_plain:
        logger.warning(
            "[security] ADMIN_PASS est encore en clair dans l'environnement. "
            "Générez un hash bcrypt via `python scripts/generate_admin_hash.py` "
            "et remplacez ADMIN_PASS par ADMIN_PASS_HASH dans votre .env."
        )


__all__ = [
    "AdminAuthError",
    "admin_auth_configured",
    "generate_random_password",
    "hash_password",
    "verify_admin_credentials",
    "verify_password",
    "warn_if_legacy_admin",
    "BCRYPT_ROUNDS",
]
