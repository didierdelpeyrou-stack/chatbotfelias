#!/usr/bin/env python3
"""Génère un hash bcrypt pour ADMIN_PASS_HASH (fix 7/8).

Usage
-----
Mode interactif (mot de passe saisi à l'aveugle, non loggé) :
    python3 scripts/generate_admin_hash.py

Mode automatisé (mot de passe passé en argument — à éviter en prod car
visible dans l'historique shell) :
    python3 scripts/generate_admin_hash.py 'mon-mdp-secret'

Mode rotation (génère un mdp aléatoire fort + son hash) :
    python3 scripts/generate_admin_hash.py --random

Sortie
------
Imprime deux lignes :
    ADMIN_PASS_HASH=<bcrypt-hash>
    (et en mode --random) ADMIN_PASS_PLAIN=<mdp-aléatoire-à-transmettre>

À coller dans ``.env`` ou dans les variables Docker, puis supprimer
``ADMIN_PASS`` (mdp en clair — à proscrire en prod).

Sécurité
--------
  - Le mot de passe n'est JAMAIS écrit sur disque par ce script.
  - ``rounds=12`` par défaut (robuste 2026) — surcharge via $BCRYPT_ROUNDS.
  - Le hash est déterministe par input+salt — on peut le regénérer plus
    tard pour vérifier sans exposer le mdp.
"""

from __future__ import annotations

import argparse
import os
import sys
from getpass import getpass
from pathlib import Path

# Permet ``python3 scripts/generate_admin_hash.py`` depuis la racine du projet
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from security import generate_random_password, hash_password  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Génère un ADMIN_PASS_HASH bcrypt pour le chatbot ELISFA.",
    )
    parser.add_argument(
        "password",
        nargs="?",
        help="Mot de passe en clair (optionnel — si omis, saisie interactive).",
    )
    parser.add_argument(
        "--random",
        action="store_true",
        help="Génère un mot de passe aléatoire fort (recommandé pour la rotation).",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=int(os.getenv("BCRYPT_ROUNDS", "12")),
        help="Coût bcrypt (défaut 12 ≈ 300 ms sur CPU moderne).",
    )
    args = parser.parse_args()

    if args.random:
        pwd = generate_random_password(length=24)
        print(f"# ⚠️  Conservez ce mot de passe en lieu sûr — il ne sera PAS ré-affiché.")
        print(f"ADMIN_PASS_PLAIN={pwd}")
    elif args.password:
        pwd = args.password
    else:
        pwd = getpass("Nouveau mot de passe admin : ")
        pwd2 = getpass("Confirmer : ")
        if pwd != pwd2:
            print("❌ Les deux saisies diffèrent.", file=sys.stderr)
            return 1
        if len(pwd) < 10:
            print(
                "⚠️  Mot de passe < 10 caractères — fortement déconseillé en prod.",
                file=sys.stderr,
            )

    if not pwd:
        print("❌ Mot de passe vide.", file=sys.stderr)
        return 1

    try:
        h = hash_password(pwd, rounds=args.rounds)
    except Exception as e:
        print(f"❌ Échec du hachage : {e}", file=sys.stderr)
        return 2

    print(f"ADMIN_PASS_HASH={h}")
    print(
        f"# Coût bcrypt : {args.rounds} rounds — "
        f"pour changer, relancez avec --rounds N (12=robuste, 14=paranoïaque)."
    )
    print(
        "# Collez la ligne ADMIN_PASS_HASH=... dans .env ou dans les vars Docker,\n"
        "# puis SUPPRIMEZ ADMIN_PASS (mdp en clair) du .env."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
