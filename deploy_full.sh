#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
#  DÉPLOIEMENT COMPLET — Chatbot ELISFA
#  Livraison : juridique_calcul (P3) + rh_urgence + gouv_urgence
#             + wizard hints (GUIDE_QUESTIONS reconnecté)
#             + renommage bouton wizard
#
#  Différence avec deploy_eisenhower.sh : ce script pousse TOUS les fichiers
#  modifiés (app.py + utils/ + templates/index.html + tests/), pas seulement
#  le template.
#
#  Préalable :
#    - Clé SSH configurée ou disposer du mot de passe root pour le VPS
#    - docker compose installé côté serveur dans /opt/chatbot_elisfa
# ═══════════════════════════════════════════════════════════════════════════

set -e

# ── Configuration ─────────────────────────────────────────────────────────
SERVER="${ELISFA_SERVER:-root@185.170.58.106}"
REMOTE_DIR="${ELISFA_REMOTE_DIR:-/opt/chatbot_elisfa}"
LOCAL_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKUP_TAG="$(date +%Y%m%d-%H%M%S)"

echo "════════════════════════════════════════════════════════════════"
echo " DÉPLOIEMENT COMPLET — Chatbot ELISFA"
echo "════════════════════════════════════════════════════════════════"
echo " Serveur       : $SERVER"
echo " Dossier       : $REMOTE_DIR"
echo " Local         : $LOCAL_DIR"
echo " Tag backup    : $BACKUP_TAG"
echo "════════════════════════════════════════════════════════════════"
echo ""

# ── Fichiers à pousser ───────────────────────────────────────────────────
FILES_TO_SYNC=(
  "app.py"
  "templates/index.html"
  "utils/__init__.py"
  "utils/calculs_juridiques.py"
  "utils/tools_juridique.py"
  "utils/guide_questions.py"
  "tests/test_calculs_juridiques.py"
  "tests/test_guide_questions.py"
)

# ── Vérifications locales ────────────────────────────────────────────────
echo "📐 Vérification locale..."
for f in "${FILES_TO_SYNC[@]}"; do
  if [ ! -f "$LOCAL_DIR/$f" ]; then
    echo "❌ Fichier manquant localement : $f"
    exit 1
  fi
done
echo "   ✅ ${#FILES_TO_SYNC[@]} fichiers présents"

# Marqueurs spécifiques à cette livraison
echo "🔍 Vérification des marqueurs de livraison..."
MARKERS=(
  "app.py:rh_urgence"
  "app.py:gouv_urgence"
  "app.py:juridique_calcul"
  "app.py:WIZARD_HINTS_JURIDIQUE"
  "app.py:/api/wizard-hints"
  "templates/index.html:hintsFromTheme"
  "templates/index.html:Diagnostic, analyse"
  "utils/guide_questions.py:WIZARD_HINTS_JURIDIQUE"
  "utils/tools_juridique.py:TOOLS_CALCUL"
)
for m in "${MARKERS[@]}"; do
  FILE="${m%%:*}"
  TOKEN="${m#*:}"
  if ! grep -q "$TOKEN" "$LOCAL_DIR/$FILE"; then
    echo "❌ Marqueur absent : $TOKEN dans $FILE"
    exit 1
  fi
done
echo "   ✅ Tous les marqueurs présents"

# Tests locaux
echo "🧪 Exécution des tests unitaires..."
cd "$LOCAL_DIR" && python3 -m unittest discover tests -v 2>&1 | tail -3
echo ""

# ── Test SSH ─────────────────────────────────────────────────────────────
echo "🔑 Test connexion SSH vers $SERVER (mot de passe si demandé)..."
if ! ssh -o ConnectTimeout=10 "$SERVER" "echo ok && test -d $REMOTE_DIR" >/dev/null 2>&1; then
  echo "❌ Connexion SSH impossible ou dossier distant absent."
  echo "   Testez : ssh $SERVER"
  echo "           ssh $SERVER 'ls $REMOTE_DIR'"
  exit 1
fi
echo "   ✅ SSH OK, dossier distant trouvé"
echo ""

# ── Backup distant ───────────────────────────────────────────────────────
echo "💾 Sauvegarde distante (tar.gz)..."
ssh "$SERVER" "cd $REMOTE_DIR && tar -czf backup-${BACKUP_TAG}.tar.gz \
    app.py templates/index.html utils/ tests/ 2>/dev/null || \
    tar -czf backup-${BACKUP_TAG}.tar.gz app.py templates/index.html"
echo "   ✅ Backup : $REMOTE_DIR/backup-${BACKUP_TAG}.tar.gz"
echo ""

# ── Création des dossiers distants ───────────────────────────────────────
echo "📁 Préparation des dossiers distants..."
ssh "$SERVER" "mkdir -p $REMOTE_DIR/utils $REMOTE_DIR/tests $REMOTE_DIR/templates"
echo "   ✅ utils/, tests/, templates/ prêts"
echo ""

# ── Upload des fichiers ──────────────────────────────────────────────────
echo "📤 Upload des fichiers..."
for f in "${FILES_TO_SYNC[@]}"; do
  REMOTE_SUB="$REMOTE_DIR/$(dirname $f)"
  scp -q "$LOCAL_DIR/$f" "$SERVER:$REMOTE_SUB/" && echo "   ✓ $f"
done
echo "   ✅ ${#FILES_TO_SYNC[@]} fichiers uploadés"
echo ""

# ── Purge du cache __pycache__ distant ───────────────────────────────────
echo "🧹 Purge des caches Python distants..."
ssh "$SERVER" "find $REMOTE_DIR -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null; true"
echo "   ✅ __pycache__ purgés"
echo ""

# ── Redémarrage du service ───────────────────────────────────────────────
echo "🔄 Redémarrage du container chatbot..."
ssh "$SERVER" "cd $REMOTE_DIR && (
  if [ -f docker-compose.yml ] && command -v docker >/dev/null; then
    echo '   → docker compose restart chatbot'
    docker compose restart chatbot 2>/dev/null || docker-compose restart chatbot
  elif systemctl list-units --type=service 2>/dev/null | grep -q elisfa; then
    echo '   → systemctl restart elisfa-chatbot'
    systemctl restart elisfa-chatbot
  else
    echo '   ⚠️  Aucun orchestrateur détecté — relance manuelle requise'
  fi
)"
echo ""

# ── Health check ─────────────────────────────────────────────────────────
echo "🏥 Health check (attente 8s de stabilisation)..."
sleep 8
HEALTH=$(ssh "$SERVER" "curl -s -o /dev/null -w '%{http_code}' http://localhost:5000/api/health 2>/dev/null || echo 000")
if [ "$HEALTH" = "200" ]; then
  echo "   ✅ /api/health : 200"
else
  echo "   ⚠️  /api/health : $HEALTH — vérifiez les logs :"
  echo "      ssh $SERVER 'cd $REMOTE_DIR && docker compose logs --tail 50 chatbot'"
fi

# Tester le nouvel endpoint wizard-hints
echo "🧪 Test du nouvel endpoint /api/wizard-hints..."
HINTS=$(ssh "$SERVER" "curl -s http://localhost:5000/api/wizard-hints 2>/dev/null | head -c 100")
if echo "$HINTS" | grep -q "Discipline"; then
  echo "   ✅ /api/wizard-hints renvoie des données"
else
  echo "   ⚠️  /api/wizard-hints ne répond pas comme attendu :"
  echo "      $HINTS"
fi
echo ""

echo "════════════════════════════════════════════════════════════════"
echo " ✅ DÉPLOIEMENT TERMINÉ"
echo "════════════════════════════════════════════════════════════════"
echo " 🌐 Tester : http://185.170.58.106/"
echo "            ⟶ Module RH → pastille 🚨 Urgence"
echo "            ⟶ Module Gouvernance → pastille 🚨 Urgence"
echo "            ⟶ Juridique → 🧮 Calculs (question ancienneté/indemnité)"
echo "            ⟶ Bouton wizard renommé : « Diagnostic, analyse & résolution »"
echo ""
echo " 💾 Rollback si besoin :"
echo "    ssh $SERVER 'cd $REMOTE_DIR && \\"
echo "                 tar -xzf backup-${BACKUP_TAG}.tar.gz && \\"
echo "                 docker compose restart chatbot'"
echo "════════════════════════════════════════════════════════════════"
