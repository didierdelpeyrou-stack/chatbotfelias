#!/usr/bin/env bash
# Backup automatique des fichiers critiques (fix 14).
#
# Fichiers sauvegardés :
#   - logs/feedback.jsonl     (feedback utilisateur — source des optimisations)
#   - logs/interactions.jsonl (historique anonymisé des questions)
#   - data/rendez_vous.json   (demandes RDV non encore traitées)
#   - data/appels_15min.json  (appels planifiés)
#   - data/emails_juriste.json (questions envoyées au juriste)
#
# Stratégie :
#   1. Copie atomique (cp + mv) vers ./backups/YYYY-MM-DD/HH-MM.<name>.gz
#   2. Rotation : supprime les backups > 30 jours
#   3. Log dans logs/backup.log (append)
#
# Cron recommandé (crontab -e sur le VPS) :
#   0 3 * * * /root/chatbot_elisfa/scripts/backup_feedback.sh >> /root/chatbot_elisfa/logs/backup.log 2>&1
#
# Restauration :
#   gunzip -c backups/2026-04-17/03-00.feedback.jsonl.gz > logs/feedback.jsonl

set -euo pipefail

# ── Config ──
PROJECT_DIR="${PROJECT_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
BACKUP_ROOT="${BACKUP_ROOT:-${PROJECT_DIR}/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"

cd "${PROJECT_DIR}"

# ── Fichiers à backuper (chemin_source:nom_backup) ──
FILES=(
    "logs/feedback.jsonl:feedback.jsonl"
    "logs/interactions.jsonl:interactions.jsonl"
    "data/rendez_vous.json:rendez_vous.json"
    "data/appels_15min.json:appels_15min.json"
    "data/emails_juriste.json:emails_juriste.json"
)

# ── Timestamp et répertoire de destination ──
DATE_DIR=$(date +%Y-%m-%d)
TIME_PREFIX=$(date +%H-%M)
DEST_DIR="${BACKUP_ROOT}/${DATE_DIR}"

mkdir -p "${DEST_DIR}"

# ── Boucle de backup ──
count=0
for entry in "${FILES[@]}"; do
    src="${entry%%:*}"
    name="${entry##*:}"
    if [[ ! -f "${src}" ]]; then
        # Pas d'erreur si le fichier n'existe pas encore (ex. pas de feedback reçu)
        continue
    fi
    dest="${DEST_DIR}/${TIME_PREFIX}.${name}.gz"
    # gzip atomic : on pipe dans un tmp puis mv
    tmp="${dest}.tmp"
    gzip -c "${src}" > "${tmp}"
    mv "${tmp}" "${dest}"
    count=$((count + 1))
done

echo "[$(date -Iseconds)] Backup OK : ${count} fichier(s) → ${DEST_DIR}"

# ── Rotation : supprime les backups > RETENTION_DAYS jours ──
# find -mtime +N : fichiers modifiés il y a plus de N jours.
if [[ -d "${BACKUP_ROOT}" ]]; then
    deleted=$(find "${BACKUP_ROOT}" -type f -name "*.gz" -mtime "+${RETENTION_DAYS}" -print -delete | wc -l | tr -d ' ')
    # Supprime aussi les répertoires de date devenus vides
    find "${BACKUP_ROOT}" -type d -empty -mindepth 1 -delete 2>/dev/null || true
    if [[ "${deleted}" -gt 0 ]]; then
        echo "[$(date -Iseconds)] Rotation : ${deleted} ancien(s) backup(s) supprimé(s) (>${RETENTION_DAYS}j)"
    fi
fi
