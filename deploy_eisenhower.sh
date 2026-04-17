#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
#  DÉPLOIEMENT — Intégration matrice d'Eisenhower + mentions légales + PDF
#  À exécuter depuis votre machine (SSH configuré vers le VPS)
# ═══════════════════════════════════════════════════════════════════════════

set -e  # arrêt sur la première erreur

# ── Configuration ─────────────────────────────────────────────────────────
SERVER="${ELISFA_SERVER:-root@185.170.58.106}"
REMOTE_DIR="${ELISFA_REMOTE_DIR:-/opt/chatbot_elisfa}"  # à ajuster selon votre VPS
LOCAL_TEMPLATE="$(dirname "$0")/templates/index.html"
BACKUP_TAG="$(date +%Y%m%d-%H%M%S)"

echo "════════════════════════════════════════════════════════════════"
echo " DÉPLOIEMENT — Chatbot ELISFA (matrice Eisenhower + mentions)"
echo "════════════════════════════════════════════════════════════════"
echo " Serveur       : $SERVER"
echo " Dossier       : $REMOTE_DIR"
echo " Fichier local : $LOCAL_TEMPLATE"
echo " Tag backup    : $BACKUP_TAG"
echo "════════════════════════════════════════════════════════════════"
echo ""

# ── Vérifications préalables ─────────────────────────────────────────────
if [ ! -f "$LOCAL_TEMPLATE" ]; then
  echo "❌ Fichier local introuvable : $LOCAL_TEMPLATE"
  exit 1
fi

echo "📐 Vérification locale..."
LOCAL_SIZE=$(stat -c%s "$LOCAL_TEMPLATE" 2>/dev/null || stat -f%z "$LOCAL_TEMPLATE")
LOCAL_LINES=$(wc -l < "$LOCAL_TEMPLATE")
echo "   Taille : ${LOCAL_SIZE} octets"
echo "   Lignes : ${LOCAL_LINES}"

# Sanity check : le fichier doit contenir nos nouvelles features
for marker in "renderEmCompact" "EM_LEGAL_HTML" "em-welcome-modal" "em-footer-link"; do
  if ! grep -q "$marker" "$LOCAL_TEMPLATE"; then
    echo "❌ Marqueur manquant : $marker — le fichier n'est pas à jour"
    exit 1
  fi
done
echo "   ✅ Tous les marqueurs Eisenhower/mentions légales présents"
echo ""

# ── Test connexion SSH ────────────────────────────────────────────────────
echo "🔑 Test connexion SSH vers $SERVER..."
if ! ssh -o ConnectTimeout=5 -o BatchMode=yes "$SERVER" "echo ok" >/dev/null 2>&1; then
  echo "❌ Connexion SSH impossible."
  echo "   Vérifiez : ssh $SERVER"
  exit 1
fi
echo "   ✅ SSH OK"
echo ""

# ── Backup sur le serveur ─────────────────────────────────────────────────
echo "💾 Sauvegarde distante..."
ssh "$SERVER" "cd $REMOTE_DIR/templates && cp index.html index.html.bak-$BACKUP_TAG"
echo "   ✅ Backup : $REMOTE_DIR/templates/index.html.bak-$BACKUP_TAG"
echo ""

# ── Upload ────────────────────────────────────────────────────────────────
echo "📤 Upload du nouveau template..."
scp "$LOCAL_TEMPLATE" "$SERVER:$REMOTE_DIR/templates/index.html"
echo "   ✅ Uploadé"
echo ""

# ── Vérification taille distante ─────────────────────────────────────────
REMOTE_SIZE=$(ssh "$SERVER" "stat -c%s $REMOTE_DIR/templates/index.html")
if [ "$LOCAL_SIZE" != "$REMOTE_SIZE" ]; then
  echo "⚠️  Tailles différentes (local: $LOCAL_SIZE, distant: $REMOTE_SIZE)"
  echo "    Rollback recommandé."
  exit 1
fi
echo "   ✅ Intégrité OK (${REMOTE_SIZE} octets)"
echo ""

# ── Redémarrage du service ───────────────────────────────────────────────
echo "🔄 Redémarrage du service..."
# Tenter docker-compose puis systemd puis gunicorn manuel
ssh "$SERVER" "cd $REMOTE_DIR && (
  if [ -f docker-compose.yml ] && command -v docker >/dev/null; then
    echo '   → docker-compose'
    docker compose restart chatbot || docker-compose restart chatbot
  elif systemctl list-units --type=service 2>/dev/null | grep -q elisfa; then
    echo '   → systemd'
    systemctl restart elisfa-chatbot
  else
    echo '   → redémarrage manuel requis côté serveur'
  fi
)"
echo ""

# ── Health check ─────────────────────────────────────────────────────────
echo "🏥 Health check (attente 5s de stabilisation)..."
sleep 5
HEALTH=$(ssh "$SERVER" "curl -s -o /dev/null -w '%{http_code}' http://localhost:5000/api/health 2>/dev/null || echo 000")
if [ "$HEALTH" = "200" ]; then
  echo "   ✅ /api/health retourne 200"
else
  echo "   ⚠️  /api/health retourne $HEALTH — vérifiez les logs"
  echo "      ssh $SERVER 'docker compose logs --tail 50 chatbot'"
fi
echo ""

echo "════════════════════════════════════════════════════════════════"
echo " ✅ DÉPLOIEMENT TERMINÉ"
echo "════════════════════════════════════════════════════════════════"
echo " 🌐 Tester : http://185.170.58.106/"
echo " 💾 Rollback si besoin :"
echo "    ssh $SERVER 'cd $REMOTE_DIR/templates && \\"
echo "                 cp index.html.bak-$BACKUP_TAG index.html && \\"
echo "                 cd .. && docker compose restart chatbot'"
echo "════════════════════════════════════════════════════════════════"
