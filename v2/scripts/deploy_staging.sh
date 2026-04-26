#!/usr/bin/env bash
# deploy_staging.sh — Déploiement V2 staging sur VPS (Sprint 4.4 + Sprint 5.2-stack)
#
# Automatise les étapes 5-8 du runbook v2/STAGING.md :
#   - vérification pré-requis (.env, caches embeddings, DNS)
#   - configuration NGINX (avec confirmation sudo)
#   - certificat Let's Encrypt si absent
#   - build + up Docker compose staging
#   - readiness check + smoke test 10/10
#   - validation Voyage AI actif (logs container)
#
# À exécuter SUR LE VPS (pas en local) :
#   ssh user@<vps-ip>
#   cd /opt/chatbot_elisfa
#   bash v2/scripts/deploy_staging.sh
#
# Pré-requis manuels (une seule fois, cf. v2/STAGING.md §1 et §2) :
#   - DNS DuckDNS felias.duckdns.org configuré et résolu
#   - git pull origin v2-dev déjà fait
#   - .env.staging créé et rempli (ANTHROPIC_API_KEY + VOYAGE_API_KEY)
#   - caches embeddings dans data/v2/_embeddings_*.npz (scp depuis local)
#
# Options :
#   --skip-nginx   : ne touche pas à NGINX (utile si déjà configuré)
#   --skip-cert    : ne touche pas à certbot (utile si certif déjà actif)
#   --rebuild      : force docker compose build sans cache
#   --dry-run      : affiche les commandes sans les exécuter

set -uo pipefail

# ────────────────────────── Config ──────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
V2_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_ROOT="$(cd "$V2_DIR/.." && pwd)"

DOMAIN="felias.duckdns.org"
NGINX_CONF_SRC="$V2_DIR/docker/nginx/v2-staging.conf"
NGINX_CONF_DST="/etc/nginx/sites-available/v2-staging.conf"
NGINX_LINK="/etc/nginx/sites-enabled/v2-staging.conf"

ENV_FILE="$V2_DIR/.env.staging"
COMPOSE_FILE="$V2_DIR/docker/docker-compose.staging.yml"
SMOKE_TEST="$V2_DIR/scripts/smoke_test_staging.sh"
CONTAINER_NAME="chatbot-elisfa-v2-staging"
EMBEDDING_CACHE_DIR="$PROJECT_ROOT/data/v2"

SKIP_NGINX=false
SKIP_CERT=false
REBUILD=false
DRY_RUN=false

# ────────────────────────── Args ──────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --skip-nginx) SKIP_NGINX=true; shift ;;
        --skip-cert)  SKIP_CERT=true; shift ;;
        --rebuild)    REBUILD=true; shift ;;
        --dry-run)    DRY_RUN=true; shift ;;
        -h|--help)
            grep "^#" "$0" | sed 's/^# \?//' | head -30
            exit 0
            ;;
        *) echo "Option inconnue : $1" >&2; exit 1 ;;
    esac
done

# ────────────────────────── Couleurs + helpers ──────────────────────────
if [[ -t 1 ]]; then
    RED=$'\033[0;31m'; GRN=$'\033[0;32m'; YLW=$'\033[0;33m'
    BLU=$'\033[0;34m'; BLD=$'\033[1m'; NC=$'\033[0m'
else
    RED=""; GRN=""; YLW=""; BLU=""; BLD=""; NC=""
fi

log()  { echo "${BLU}[$(date +%H:%M:%S)]${NC} $*"; }
ok()   { echo "${GRN}✅${NC} $*"; }
warn() { echo "${YLW}⚠️${NC}  $*"; }
err()  { echo "${RED}❌${NC} $*" >&2; }
step() { echo; echo "${BLD}═══ $* ═══${NC}"; }

run() {
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "  [dry-run] $*"
    else
        eval "$@"
    fi
}

# ────────────────────────── Validation pré-requis ──────────────────────────
step "1/8 — Validation des pré-requis"

# Doit tourner sur le VPS (pas en local)
if [[ "$(uname)" == "Darwin" ]]; then
    warn "macOS détecté — ce script est conçu pour le VPS Linux."
    warn "Si vous testez en local, attendez-vous à des erreurs sur sudo/nginx/certbot."
fi

# DNS résolu ?
if ! host "$DOMAIN" > /dev/null 2>&1; then
    err "DNS $DOMAIN non résolu. Configurer DuckDNS d'abord (cf. STAGING.md §1)."
    exit 1
fi
ok "DNS $DOMAIN résolu : $(host "$DOMAIN" | awk '{print $NF}' | head -1)"

# .env.staging présent
if [[ ! -f "$ENV_FILE" ]]; then
    err "Fichier $ENV_FILE absent. Faire : cp .env.staging.example .env.staging"
    exit 1
fi
ok "$ENV_FILE présent"

# Variables critiques renseignées
ANTHROPIC=$(grep "^ANTHROPIC_API_KEY=" "$ENV_FILE" | cut -d= -f2-)
VOYAGE=$(grep "^VOYAGE_API_KEY=" "$ENV_FILE" | cut -d= -f2-)
if [[ -z "$ANTHROPIC" ]] || [[ "$ANTHROPIC" == "sk-ant-xxxxxxxxxxxxxxxxxxxxxxxx" ]]; then
    err "ANTHROPIC_API_KEY non renseignée dans $ENV_FILE"
    exit 1
fi
ok "ANTHROPIC_API_KEY renseignée (${#ANTHROPIC} chars)"
if [[ -z "$VOYAGE" ]] || [[ "$VOYAGE" == "pa-xxxxxxxxxxxxxxxxxxxxxxxx" ]]; then
    warn "VOYAGE_API_KEY non renseignée — V2 fonctionnera en TF-IDF seul (~70% au lieu de 75%)"
else
    ok "VOYAGE_API_KEY renseignée (${#VOYAGE} chars)"
fi

# Cache embeddings présent ?
NB_CACHES=$(find "$EMBEDDING_CACHE_DIR" -name "_embeddings_*.npz" 2>/dev/null | wc -l | tr -d ' ')
if [[ "$NB_CACHES" -lt 4 ]]; then
    warn "Caches embeddings : $NB_CACHES/4 trouvés dans $EMBEDDING_CACHE_DIR"
    warn "V2 va tenter de générer les manquants au boot (long avec free tier Voyage)."
    warn "Pour transférer depuis local : scp data/v2/_embeddings_*.npz user@vps:$EMBEDDING_CACHE_DIR/"
else
    SIZE_MB=$(du -sh "$EMBEDDING_CACHE_DIR"/_embeddings_*.npz 2>/dev/null | awk '{s+=$1} END {print s}')
    ok "Caches embeddings : 4/4 présents"
fi

# Docker dispo ?
if ! command -v docker > /dev/null 2>&1; then
    err "Docker non installé sur ce système."
    exit 1
fi
ok "Docker $(docker --version | awk '{print $3}' | tr -d ',')"

# ────────────────────────── NGINX ──────────────────────────
step "2/8 — NGINX (server block + reload)"

if [[ "$SKIP_NGINX" == "true" ]]; then
    warn "NGINX skippé (--skip-nginx)"
elif [[ ! -f "$NGINX_CONF_SRC" ]]; then
    err "Conf NGINX source absente : $NGINX_CONF_SRC"
    exit 1
else
    if [[ -f "$NGINX_CONF_DST" ]]; then
        warn "$NGINX_CONF_DST déjà présent — overwrite"
    fi
    log "Copie de la conf vers $NGINX_CONF_DST (sudo)..."
    run "sudo cp '$NGINX_CONF_SRC' '$NGINX_CONF_DST'"
    log "Activation (lien symbolique)..."
    run "sudo ln -sf '$NGINX_CONF_DST' '$NGINX_LINK'"
    log "Test de la conf..."
    if run "sudo nginx -t"; then
        run "sudo systemctl reload nginx"
        ok "NGINX rechargé"
    else
        err "nginx -t échoué — voir 'sudo nginx -T' pour debug"
        exit 1
    fi
fi

# ────────────────────────── Certbot ──────────────────────────
step "3/8 — Certificat Let's Encrypt"

if [[ "$SKIP_CERT" == "true" ]]; then
    warn "Certbot skippé (--skip-cert)"
else
    if sudo test -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem"; then
        ok "Certificat $DOMAIN déjà actif"
    else
        log "Demande de certificat (interactif si besoin email/conditions)..."
        run "sudo certbot --nginx -d '$DOMAIN' --redirect --non-interactive --agree-tos --register-unsafely-without-email"
        if sudo test -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem"; then
            ok "Certificat installé"
        else
            err "certbot a échoué — relancer manuellement : sudo certbot --nginx -d $DOMAIN"
            exit 1
        fi
    fi
fi

# ────────────────────────── Docker compose ──────────────────────────
step "4/8 — Docker compose staging"

cd "$V2_DIR"
BUILD_OPTS="--build"
[[ "$REBUILD" == "true" ]] && BUILD_OPTS="--build --no-cache"

log "Arrêt de l'ancien container (si présent)..."
run "docker compose -f '$COMPOSE_FILE' --env-file '$ENV_FILE' down 2>/dev/null || true"

log "Build + up détaché..."
run "docker compose -f '$COMPOSE_FILE' --env-file '$ENV_FILE' up -d $BUILD_OPTS"

# ────────────────────────── Readiness check ──────────────────────────
step "5/8 — Attente readiness V2 (/healthz)"

log "Polling /healthz (max 60s)..."
ready=false
for i in {1..60}; do
    if curl -sf http://127.0.0.1:8000/healthz > /dev/null 2>&1; then
        ok "V2 healthy après ${i}s"
        ready=true
        break
    fi
    sleep 1
done

if [[ "$ready" != "true" ]]; then
    err "V2 n'a pas démarré en 60s. Voir logs :"
    run "docker logs --tail 50 $CONTAINER_NAME"
    exit 1
fi

# ────────────────────────── Validation Voyage AI ──────────────────────────
step "6/8 — Validation Voyage AI + KB enrichie"

log "Inspection logs container pour confirmer KB + Voyage..."
LOGS=$(docker logs "$CONTAINER_NAME" 2>&1 | head -100)

if echo "$LOGS" | grep -q "Voyage AI activé"; then
    ok "Voyage AI activé"
elif echo "$LOGS" | grep -q "VOYAGE_API_KEY absent"; then
    warn "VOYAGE_API_KEY absent — fallback TF-IDF (V2 ~70%)"
else
    warn "Statut Voyage indéterminé — voir logs complets"
fi

KB_COUNT=$(echo "$LOGS" | grep "KB store:" | grep -oP "(?<=formation': )\d+" | head -1)
if [[ "$KB_COUNT" -ge 156 ]]; then
    ok "KB V2 enrichie chargée ($KB_COUNT articles formation)"
elif [[ "$KB_COUNT" -ge 40 ]]; then
    warn "KB V1 chargée ($KB_COUNT articles formation) — vérifier KB_DATA_DIR"
else
    err "KB non chargée correctement (formation=$KB_COUNT)"
fi

if echo "$LOGS" | grep -q "cache hit"; then
    ok "Cache embeddings utilisé (boot rapide)"
elif echo "$LOGS" | grep -q "indexés via API"; then
    warn "Embeddings indexés en live (cache absent ou KB modifiée)"
fi

# ────────────────────────── Smoke test public ──────────────────────────
step "7/8 — Smoke test public (10 checks)"

if [[ -x "$SMOKE_TEST" ]]; then
    if run "bash '$SMOKE_TEST'"; then
        ok "Smoke test passé"
    else
        err "Smoke test échoué — voir output ci-dessus"
        exit 1
    fi
else
    warn "Script smoke_test_staging.sh introuvable ou non exécutable"
fi

# ────────────────────────── Bilan ──────────────────────────
step "8/8 — Bilan déploiement"

echo
echo "${GRN}${BLD}🚀 V2 staging déployée avec succès${NC}"
echo
echo "URL publique : https://$DOMAIN/"
echo "Swagger UI   : https://$DOMAIN/docs"
echo "Health       : https://$DOMAIN/healthz"
echo "Ready        : https://$DOMAIN/readyz"
echo "Metrics      : https://$DOMAIN/metrics (interne)"
echo
echo "Container    : $CONTAINER_NAME"
echo "Logs         : docker logs -f $CONTAINER_NAME"
echo "Stop         : docker compose -f $COMPOSE_FILE down"
echo
echo "${BLU}Prochaine étape :${NC}"
echo "  - Tests internes ELISFA (5-10 j) avec 5-10 utilisateurs ciblés"
echo "  - Bug fixes selon retours"
echo "  - Décision go bêta-test 100 users (Sprint 4.5)"
echo

# Trace dans le log de déploiement
GIT_SHA=$(cd "$PROJECT_ROOT" && git rev-parse --short HEAD 2>/dev/null || echo "unknown")
DEPLOY_LOG="/var/log/elisfa-deploys.log"
if sudo test -w "$(dirname "$DEPLOY_LOG")" 2>/dev/null; then
    echo "$(date -Iseconds) — staging V2 déployée commit=$GIT_SHA via deploy_staging.sh" \
        | sudo tee -a "$DEPLOY_LOG" > /dev/null
    ok "Trace ajoutée à $DEPLOY_LOG"
fi

exit 0
