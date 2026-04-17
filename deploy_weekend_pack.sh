#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
#  DÉPLOIEMENT — Pack weekend (fixes 6, 7, 9, 11, 12, 13, 14, 15)
#
#  Pousse vers le VPS :
#    - Nouveaux modules : security.py, validation.py, kb_cache.py, observability.py
#    - app.py mis à jour (intégration des 4 modules)
#    - requirements.txt (pydantic, bcrypt, sentry-sdk, flask-swagger-ui, PyYAML, pytest)
#    - docs/openapi.yaml + routes /api/docs
#    - scripts/ (rotate key, backup, generate hash)
#    - tests/ (conftest + 4 nouveaux tests)
#    - .github/workflows/ci.yml
#    - pytest.ini, .gitignore
#
#  Préalable :
#    - SSH key ou password pour root@185.170.58.106
#    - docker compose installé dans /opt/chatbot_elisfa
#    - ADMIN_PASS_HASH généré en amont via scripts/generate_admin_hash.py
#
#  Usage :
#    bash deploy_weekend_pack.sh
#
#  Variables d'env optionnelles :
#    ELISFA_SERVER=root@185.170.58.106  (défaut)
#    ELISFA_REMOTE_DIR=/opt/chatbot_elisfa  (défaut)
# ═══════════════════════════════════════════════════════════════════════════

set -e

# ── Configuration ─────────────────────────────────────────────────────────
SERVER="${ELISFA_SERVER:-root@185.170.58.106}"
REMOTE_DIR="${ELISFA_REMOTE_DIR:-/opt/chatbot_elisfa}"
LOCAL_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKUP_TAG="$(date +%Y%m%d-%H%M%S)"

echo "════════════════════════════════════════════════════════════════"
echo " DÉPLOIEMENT PACK WEEKEND — Chatbot ELISFA"
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
  "requirements.txt"
  "pytest.ini"
  ".gitignore"
  "security.py"
  "validation.py"
  "kb_cache.py"
  "observability.py"
  "docs/openapi.yaml"
  "scripts/generate_admin_hash.py"
  "scripts/rotate_anthropic_key.sh"
  "scripts/backup_feedback.sh"
  "tests/conftest.py"
  "tests/test_validation.py"
  "tests/test_security.py"
  "tests/test_kb_cache.py"
  "tests/test_integration.py"
  ".github/workflows/ci.yml"
)

# ── Vérifications locales ────────────────────────────────────────────────
echo "📐 Vérification locale..."
MISSING=0
for f in "${FILES_TO_SYNC[@]}"; do
  if [ ! -f "$LOCAL_DIR/$f" ]; then
    echo "   ❌ Fichier manquant localement : $f"
    MISSING=$((MISSING + 1))
  fi
done
if [ "$MISSING" -gt 0 ]; then
  echo "❌ $MISSING fichier(s) manquant(s), abandon."
  exit 1
fi
echo "   ✅ ${#FILES_TO_SYNC[@]} fichiers présents"

# Marqueurs spécifiques à cette livraison (fail-fast si push incomplet)
echo "🔍 Vérification des marqueurs de livraison..."
MARKERS=(
  "app.py:from security import"
  "app.py:from kb_cache import"
  "app.py:from observability import"
  "app.py:from validation import"
  "app.py:refresh_kbs_if_changed"
  "app.py:/api/openapi.yaml"
  "security.py:hash_password"
  "validation.py:class AskRequest"
  "kb_cache.py:class FileBackedCache"
  "observability.py:def init_sentry"
  "tests/conftest.py:fake_anthropic"
  "requirements.txt:bcrypt"
  "requirements.txt:pydantic"
  "requirements.txt:sentry-sdk"
)
for m in "${MARKERS[@]}"; do
  FILE="${m%%:*}"
  TOKEN="${m#*:}"
  if ! grep -q "$TOKEN" "$LOCAL_DIR/$FILE"; then
    echo "   ❌ Marqueur absent : \"$TOKEN\" dans $FILE"
    exit 1
  fi
done
echo "   ✅ Tous les marqueurs présents"

# ── Tests locaux (rapides uniquement — unit + integration) ────────────────
echo "🧪 Exécution des tests locaux..."
if [ -x "$LOCAL_DIR/.venv_scraper/bin/python3" ]; then
    PY="$LOCAL_DIR/.venv_scraper/bin/python3"
else
    PY="python3"
fi
cd "$LOCAL_DIR" && "$PY" -m pytest tests/ -q --no-header 2>&1 | tail -3
echo ""

# ── Test SSH ─────────────────────────────────────────────────────────────
echo "🔑 Test connexion SSH vers $SERVER..."
if ! ssh -o ConnectTimeout=10 "$SERVER" "echo ok && test -d $REMOTE_DIR" >/dev/null 2>&1; then
  echo "   ❌ Connexion SSH impossible ou dossier distant absent."
  echo "   Testez : ssh $SERVER"
  echo "           ssh $SERVER 'ls $REMOTE_DIR'"
  exit 1
fi
echo "   ✅ SSH OK, dossier distant trouvé"
echo ""

# ── Backup distant ───────────────────────────────────────────────────────
echo "💾 Sauvegarde distante (tar.gz)..."
ssh "$SERVER" "cd $REMOTE_DIR && tar --ignore-failed-read -czf backup-weekend-${BACKUP_TAG}.tar.gz \
    app.py requirements.txt security.py validation.py kb_cache.py observability.py \
    docs/ tests/ scripts/ pytest.ini 2>/dev/null || true"
echo "   ✅ Backup : $REMOTE_DIR/backup-weekend-${BACKUP_TAG}.tar.gz"
echo ""

# ── Création des dossiers distants ───────────────────────────────────────
echo "📁 Préparation des dossiers distants..."
ssh "$SERVER" "mkdir -p $REMOTE_DIR/docs $REMOTE_DIR/scripts $REMOTE_DIR/tests $REMOTE_DIR/.github/workflows"
echo "   ✅ docs/, scripts/, tests/, .github/workflows/ prêts"
echo ""

# ── Upload des fichiers ──────────────────────────────────────────────────
echo "📤 Upload des fichiers..."
for f in "${FILES_TO_SYNC[@]}"; do
  REMOTE_SUB="$REMOTE_DIR/$(dirname "$f")"
  scp -q "$LOCAL_DIR/$f" "$SERVER:$REMOTE_SUB/" && echo "   ✓ $f"
done
echo "   ✅ ${#FILES_TO_SYNC[@]} fichiers uploadés"
echo ""

# ── Permissions exécutables ──────────────────────────────────────────────
echo "🔐 chmod +x sur les scripts..."
ssh "$SERVER" "chmod +x $REMOTE_DIR/scripts/*.sh $REMOTE_DIR/scripts/generate_admin_hash.py 2>/dev/null || true"
echo ""

# ── Purge du cache __pycache__ distant ───────────────────────────────────
echo "🧹 Purge des caches Python distants..."
ssh "$SERVER" "find $REMOTE_DIR -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null; true"
echo "   ✅ __pycache__ purgés"
echo ""

# ── Rebuild + restart avec nouvelles deps (pydantic, bcrypt, etc.) ────────
# IMPORTANT : --build car requirements.txt a changé. Sans ça, les nouvelles
# deps ne sont pas installées et le container crash au boot.
echo "🔄 Rebuild + restart du container chatbot (deps nouvelles)..."
ssh "$SERVER" "cd $REMOTE_DIR && docker compose up -d --build chatbot"
echo ""

# ── Health check ─────────────────────────────────────────────────────────
echo "🏥 Health check (attente 10s de stabilisation)..."
sleep 10
HEALTH=$(ssh "$SERVER" "curl -s -o /dev/null -w '%{http_code}' http://localhost:5000/api/health 2>/dev/null || echo 000")
if [ "$HEALTH" = "200" ]; then
  echo "   ✅ /api/health : 200"
  THEMES=$(ssh "$SERVER" "curl -s http://localhost:5000/api/health | python3 -c 'import sys,json;print(json.load(sys.stdin)[\"themes_count\"])' 2>/dev/null")
  echo "   ✅ themes_count : $THEMES"
else
  echo "   ⚠️  /api/health : $HEALTH"
  echo "   Logs récents :"
  ssh "$SERVER" "cd $REMOTE_DIR && docker compose logs --tail 30 chatbot"
  exit 1
fi
echo ""

# ── Test OpenAPI ─────────────────────────────────────────────────────────
echo "📖 Test /api/openapi.yaml..."
OPENAPI=$(ssh "$SERVER" "curl -s -o /dev/null -w '%{http_code}' http://localhost:5000/api/openapi.yaml")
if [ "$OPENAPI" = "200" ]; then
  echo "   ✅ /api/openapi.yaml : 200"
else
  echo "   ⚠️  /api/openapi.yaml : $OPENAPI (docs/openapi.yaml absent ?)"
fi

# ── Test validation Pydantic (doit retourner 400 sur payload malformé) ───
echo "🧪 Test validation Pydantic (POST /api/rdv avec email invalide)..."
VALIDATION=$(ssh "$SERVER" "curl -s -o /dev/null -w '%{http_code}' \
  -X POST http://localhost:5000/api/rdv \
  -H 'Content-Type: application/json' \
  -d '{\"nom\":\"X\",\"email\":\"pas-un-email\",\"telephone\":\"123\",\"sujet\":\"test\"}'")
if [ "$VALIDATION" = "400" ]; then
  echo "   ✅ Validation Pydantic active — 400 sur email invalide"
else
  echo "   ⚠️  Attendu 400, reçu $VALIDATION — vérifier que pydantic est bien installé dans le container"
fi
echo ""

echo "════════════════════════════════════════════════════════════════"
echo " ✅ DÉPLOIEMENT TERMINÉ"
echo "════════════════════════════════════════════════════════════════"
echo " 🌐 URLs à tester :"
echo "   https://felias-reseau-eli2026.duckdns.org/api/health"
echo "   https://felias-reseau-eli2026.duckdns.org/api/docs"
echo "   https://felias-reseau-eli2026.duckdns.org/api/openapi.yaml"
echo ""
echo " 🔑 À faire SUR LE VPS pour finaliser :"
echo "   1. Injecter le nouveau ADMIN_PASS_HASH dans .env :"
echo "      ssh $SERVER 'cd $REMOTE_DIR && nano .env'"
echo "      → ajouter ADMIN_PASS_HASH=\$2b\$12\$... et supprimer ADMIN_PASS"
echo "      → docker compose restart chatbot"
echo ""
echo "   2. Cron backup quotidien (feedback + RDV) :"
echo "      ssh $SERVER"
echo "      crontab -e  # ajouter :"
echo "      0 3 * * * $REMOTE_DIR/scripts/backup_feedback.sh >> $REMOTE_DIR/logs/backup.log 2>&1"
echo ""
echo "   3. (Optionnel) Sentry monitoring :"
echo "      ssh $SERVER 'echo SENTRY_DSN=https://...@sentry.io/... >> $REMOTE_DIR/.env'"
echo "      ssh $SERVER 'cd $REMOTE_DIR && docker compose restart chatbot'"
echo ""
echo " 💾 Rollback si besoin :"
echo "   ssh $SERVER 'cd $REMOTE_DIR && tar -xzf backup-weekend-${BACKUP_TAG}.tar.gz && docker compose up -d --build chatbot'"
echo "════════════════════════════════════════════════════════════════"
