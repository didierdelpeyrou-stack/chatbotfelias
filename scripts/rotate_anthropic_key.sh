#!/usr/bin/env bash
# Rotation de la clé API Anthropic (fix 8).
#
# Contexte : la clé peut fuiter via l'historique Git, les logs de build, les
# captures d'écran d'admin, etc. La pratique standard est de la tourner tous
# les 90 jours OU immédiatement après toute fuite suspectée.
#
# Cette procédure est IDEMPOTENTE : elle peut être relancée sans danger,
# elle se contente de pousser la nouvelle clé et redémarrer les services.
#
# Usage :
#   1. Ouvrir https://console.anthropic.com/settings/keys → "Create key"
#   2. Copier la nouvelle clé (format sk-ant-…)
#   3. Exécuter :
#        bash scripts/rotate_anthropic_key.sh sk-ant-api03-NEW_KEY
#   4. Vérifier :
#        curl https://felias-reseau-eli2026.duckdns.org/api/health
#        → "api_configured": true, pas d'erreur dans les logs
#   5. RÉVOQUER l'ancienne clé depuis la console Anthropic (bouton Delete)
#
# ⚠️  Étape 5 = CRITIQUE. Sans révocation, l'ancienne clé reste utilisable
# même si elle a fuité.

set -euo pipefail

NEW_KEY="${1:-}"
VPS_HOST="${VPS_HOST:-185.170.58.106}"
VPS_USER="${VPS_USER:-root}"
REMOTE_DIR="${REMOTE_DIR:-/opt/chatbot_elisfa}"
ENV_FILE="${ENV_FILE:-${REMOTE_DIR}/.env}"

# ── Validations ──

if [[ -z "${NEW_KEY}" ]]; then
    echo "❌ Usage : $0 <sk-ant-api03-NEW_KEY>" >&2
    echo "   Pour obtenir une nouvelle clé : https://console.anthropic.com/settings/keys" >&2
    exit 1
fi

if [[ ! "${NEW_KEY}" =~ ^sk-ant- ]]; then
    echo "❌ La clé ne commence pas par 'sk-ant-' — format incorrect." >&2
    exit 2
fi

if [[ "${#NEW_KEY}" -lt 50 ]]; then
    echo "❌ Clé trop courte (${#NEW_KEY} chars, attendu ≥ 50)." >&2
    exit 3
fi

echo "ℹ️  Nouvelle clé : ${NEW_KEY:0:15}…${NEW_KEY: -6}"
echo "ℹ️  Cible : ${VPS_USER}@${VPS_HOST}:${ENV_FILE}"

read -p "Confirmer la rotation sur le VPS ? [y/N] " -r confirm
if [[ ! "${confirm}" =~ ^[Yy]$ ]]; then
    echo "Abandon."
    exit 0
fi

# ── 1. Backup du .env courant ──
echo "→ Backup du .env existant…"
ssh "${VPS_USER}@${VPS_HOST}" "cp ${ENV_FILE} ${ENV_FILE}.bak-\$(date +%Y%m%d-%H%M%S)"

# ── 2. Mise à jour de la ligne ANTHROPIC_API_KEY ──
# On utilise sed en mode safe : si la ligne existe on la remplace, sinon on l'ajoute.
echo "→ Écriture de la nouvelle clé…"
ssh "${VPS_USER}@${VPS_HOST}" bash -se <<EOF
set -euo pipefail
cd ${REMOTE_DIR}
if grep -q '^ANTHROPIC_API_KEY=' ${ENV_FILE}; then
    sed -i 's|^ANTHROPIC_API_KEY=.*|ANTHROPIC_API_KEY=${NEW_KEY}|' ${ENV_FILE}
else
    echo 'ANTHROPIC_API_KEY=${NEW_KEY}' >> ${ENV_FILE}
fi
# Protéger le .env (lecture owner seulement)
chmod 600 ${ENV_FILE}
EOF

# ── 3. Redémarrage du container ──
echo "→ Redémarrage du container Docker…"
ssh "${VPS_USER}@${VPS_HOST}" "cd ${REMOTE_DIR} && docker compose down && docker compose up -d"

# ── 4. Attente du démarrage ──
echo "→ Attente du démarrage (jusqu'à 30 s)…"
for i in $(seq 1 30); do
    if ssh "${VPS_USER}@${VPS_HOST}" "curl -fsS http://localhost:5000/api/health" > /dev/null 2>&1; then
        echo "✅ Service de nouveau disponible après ${i}s."
        break
    fi
    sleep 1
done

# ── 5. Smoke test ──
echo "→ Smoke test /api/health…"
ssh "${VPS_USER}@${VPS_HOST}" "curl -sS http://localhost:5000/api/health | head -c 500"
echo
echo

# ── 6. Smoke test d'un appel Claude réel (optionnel mais recommandé) ──
echo "→ Smoke test /api/ask (appel Claude réel)…"
if ssh "${VPS_USER}@${VPS_HOST}" \
    "curl -sSf -X POST http://localhost:5000/api/ask -H 'Content-Type: application/json' -d '{\"question\":\"bonjour\",\"module\":\"juridique\"}' | head -c 200"; then
    echo
    echo "✅ Rotation terminée avec succès."
else
    echo
    echo "⚠️  Le smoke test /api/ask a échoué. Vérifiez les logs :" >&2
    echo "    ssh ${VPS_USER}@${VPS_HOST} 'docker compose logs --tail=50 chatbot'" >&2
    exit 4
fi

cat <<'NEXT'

ÉTAPE SUIVANTE CRITIQUE :
─────────────────────────
🔴 Connectez-vous sur https://console.anthropic.com/settings/keys
🔴 SUPPRIMEZ l'ancienne clé (sinon elle reste utilisable si elle a fuité).

Sans cette étape, la rotation n'a servi à rien pour la sécurité.
NEXT
