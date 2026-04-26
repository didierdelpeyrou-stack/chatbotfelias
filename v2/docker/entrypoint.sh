#!/bin/sh
# entrypoint.sh — Sprint 4.4-fix : corrige les permissions du volume logs.
#
# Problème : Docker crée les volumes nommés en root:root par défaut, mais
# notre container tourne en user `elisfa` (UID 999) pour des raisons de
# sécurité. Résultat : `elisfa` ne peut pas écrire dans /app/logs/, ce
# qui fait échouer /api/feedback (Errno 13: Permission denied).
#
# Solution : ce script tourne en root au démarrage, fixe les permissions
# du volume, puis bascule en `elisfa` pour exécuter uvicorn.
#
# Cf. v2/docker/Dockerfile : `ENTRYPOINT ["/entrypoint.sh"]`
# Le `USER elisfa` du Dockerfile est SUPPRIMÉ pour permettre le chown.
set -e

# Si on tourne en root (cas normal au boot du container), corrige les
# perms des volumes RW avant de basculer en elisfa.
if [ "$(id -u)" = "0" ]; then
    # Crée /app/logs si absent (idempotent), fixe owner/group à elisfa:elisfa
    mkdir -p /app/logs
    chown -R elisfa:elisfa /app/logs 2>/dev/null || true

    # Sprint 4.6 : cache embeddings dans volume nommé RW (séparé du mount KB :ro)
    mkdir -p /app/var/embeddings
    chown -R elisfa:elisfa /app/var 2>/dev/null || true

    # `su` est dispo de base sur python:3.12-slim, pas besoin de gosu/tini
    # exec : remplace le PID 1 par le process uvicorn (pour que SIGTERM
    # de Docker arrête proprement le serveur)
    exec su -s /bin/sh -c "exec $*" elisfa
fi

# Si déjà en non-root (override docker run --user X), exec direct
exec "$@"
