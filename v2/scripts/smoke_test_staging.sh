#!/usr/bin/env bash
# Sprint 4.4 — Smoke test V2 staging (refactor Sprint 4.4-fix).
#
# Exécutable depuis n'importe où (pas besoin d'être sur le VPS).
# Vérifie en 30s que le déploiement V2 staging répond correctement sur les
# endpoints critiques.
#
# Usage :
#   bash v2/scripts/smoke_test_staging.sh
#   # ou avec un host custom :
#   STAGING_HOST=v2.example.com bash v2/scripts/smoke_test_staging.sh
#
# Refactor (post-déploiement réel) :
#   - Élimine le bug `eval "$cmd"` qui cassait sur les JSON contenant des
#     apostrophes / retours à la ligne (faisait passer 5/11 alors que les
#     endpoints répondaient bien).
#   - Utilise des fichiers /tmp pour découpler curl du check (pas de pipe
#     fragile avec contenu JSON variable).
#   - Affiche un extrait de la réponse en cas d'échec pour debug rapide.
#
# Code retour : 0 si tout vert, 1 dès qu'un test échoue.

set -u  # pas de set -e : on veut accumuler les erreurs

HOST="${STAGING_HOST:-felias.duckdns.org}"
BASE="https://${HOST}"
TMP_DIR=$(mktemp -d -t elisfa-smoke.XXXXXX)
trap "rm -rf '$TMP_DIR'" EXIT

FAILED=0
PASSED=0

# Couleurs (skip si pas de TTY pour les CI)
if [[ -t 1 ]]; then
    GREEN=$'\e[32m'; RED=$'\e[31m'; YELLOW=$'\e[33m'; DIM=$'\e[2m'; RESET=$'\e[0m'
else
    GREEN=""; RED=""; YELLOW=""; DIM=""; RESET=""
fi

# pass/fail : helper unifié.
#   pass <name>
#   fail <name> [<details>]
pass() {
    echo "${GREEN}✓${RESET} $1"
    PASSED=$((PASSED + 1))
}
fail() {
    echo "${RED}✗${RESET} $1"
    [[ -n "${2:-}" ]] && echo "    ${DIM}$2${RESET}"
    FAILED=$((FAILED + 1))
}

echo "🔍 Smoke test V2 staging — host=${HOST}"
echo

# ─── 1. DNS résolu ───
if host "${HOST}" 2>/dev/null | grep -q 'has address'; then
    pass "DNS résout ${HOST}"
else
    fail "DNS résout ${HOST}" "host ${HOST} n'a pas retourné d'IP"
fi

# ─── 2. HTTPS root répond 200 ───
ROOT_CODE=$(curl -sk -o /dev/null -w '%{http_code}' --max-time 10 "${BASE}/")
if [[ "$ROOT_CODE" == "200" ]]; then
    pass "HTTPS / répond 200"
else
    fail "HTTPS / répond 200" "code reçu : $ROOT_CODE"
fi

# ─── 3. Healthcheck liveness ───
curl -sk --max-time 10 "${BASE}/healthz" -o "$TMP_DIR/healthz.json"
if grep -q '"status":"ok"' "$TMP_DIR/healthz.json" 2>/dev/null; then
    pass "/healthz → status:ok"
else
    fail "/healthz → status:ok" "$(head -c 200 "$TMP_DIR/healthz.json" 2>/dev/null)"
fi

# ─── 4. Readiness (KB chargée + Claude configuré) ───
curl -sk --max-time 10 "${BASE}/readyz" -o "$TMP_DIR/readyz.json"
if grep -q '"status":"ready"' "$TMP_DIR/readyz.json" 2>/dev/null; then
    pass "/readyz → status:ready"
else
    fail "/readyz → status:ready" "$(head -c 200 "$TMP_DIR/readyz.json" 2>/dev/null)"
fi

# ─── 5. Swagger UI ───
DOCS_CODE=$(curl -sk -o /dev/null -w '%{http_code}' --max-time 10 "${BASE}/docs")
if [[ "$DOCS_CODE" == "200" ]]; then
    pass "/docs (Swagger UI) répond 200"
else
    fail "/docs (Swagger UI) répond 200" "code reçu : $DOCS_CODE (vérifier que NGINX route bien vers le container)"
fi

# ─── 6. Metrics Prometheus ───
METRICS_CODE=$(curl -sk -o "$TMP_DIR/metrics.txt" -w '%{http_code}' --max-time 10 "${BASE}/metrics")
if [[ "$METRICS_CODE" == "200" ]] && grep -qE '^# (HELP|TYPE)' "$TMP_DIR/metrics.txt"; then
    pass "/metrics format Prometheus"
else
    fail "/metrics format Prometheus" "code=$METRICS_CODE, head=$(head -c 100 "$TMP_DIR/metrics.txt")"
fi

# ─── 7. /api/ask one-shot — question juridique typique ───
curl -sk --max-time 30 -X POST "${BASE}/api/ask" \
    -H "Content-Type: application/json" \
    -d '{"question":"Quelle est la duree de la periode d essai en CDI ?","module":"juridique"}' \
    -o "$TMP_DIR/ask_juri.json" 2>/dev/null

if grep -q '"answer"' "$TMP_DIR/ask_juri.json" 2>/dev/null; then
    pass "/api/ask juridique : JSON contient 'answer'"

    # Sous-test : answer non vide (>20 chars)
    if python3 -c "
import json, sys
try:
    d = json.load(open('$TMP_DIR/ask_juri.json'))
    sys.exit(0 if len(d.get('answer', '')) > 20 else 1)
except Exception:
    sys.exit(1)
" 2>/dev/null; then
        pass "/api/ask juridique : answer non vide (>20 chars)"
    else
        fail "/api/ask juridique : answer non vide" "answer trop court ou JSON malformé"
    fi
else
    fail "/api/ask juridique : JSON contient 'answer'" "$(head -c 200 "$TMP_DIR/ask_juri.json")"
    fail "/api/ask juridique : answer non vide" "(skipped car JSON invalide)"
fi

# ─── 8. /api/ask hors_corpus → fallback court ───
curl -sk --max-time 30 -X POST "${BASE}/api/ask" \
    -H "Content-Type: application/json" \
    -d '{"question":"recette quiche lorraine","module":"juridique"}' \
    -o "$TMP_DIR/ask_hors.json" 2>/dev/null

if grep -q '"hors_corpus":true' "$TMP_DIR/ask_hors.json" 2>/dev/null; then
    pass "/api/ask hors_corpus → flag hors_corpus:true"
else
    fail "/api/ask hors_corpus → flag hors_corpus:true" "$(head -c 200 "$TMP_DIR/ask_hors.json")"
fi

# ─── 9. POST /api/feedback ───
curl -sk --max-time 10 -X POST "${BASE}/api/feedback" \
    -H 'Content-Type: application/json' \
    -d '{"rating":1,"question":"smoke test","answer":"ok","module":"juridique"}' \
    -o "$TMP_DIR/feedback_post.json" 2>/dev/null

if grep -q '"status":"ok"' "$TMP_DIR/feedback_post.json" 2>/dev/null; then
    pass "POST /api/feedback ok"
else
    fail "POST /api/feedback ok" "$(head -c 200 "$TMP_DIR/feedback_post.json")"
fi

# ─── 10. GET /api/feedback/stats répond ───
curl -sk --max-time 10 "${BASE}/api/feedback/stats" -o "$TMP_DIR/feedback_stats.json" 2>/dev/null
if grep -q '"total"' "$TMP_DIR/feedback_stats.json" 2>/dev/null; then
    pass "GET /api/feedback/stats → champ total"
else
    fail "GET /api/feedback/stats → champ total" "$(head -c 200 "$TMP_DIR/feedback_stats.json")"
fi

echo
TOTAL=$((PASSED + FAILED))
if [[ $FAILED -eq 0 ]]; then
    echo "${GREEN}✅ ${PASSED}/${TOTAL} tests passent — staging V2 opérationnel${RESET}"
    exit 0
else
    echo "${RED}❌ ${FAILED}/${TOTAL} tests ont échoué sur ${TOTAL} — investiguer avant Sprint 4.5${RESET}"
    echo "${YELLOW}Astuce :${RESET}"
    echo "  ${DIM}docker logs chatbot-elisfa-v2-staging --tail 100${RESET}"
    echo "  ${DIM}sudo tail -20 /var/log/nginx/v2-staging.error.log${RESET}"
    exit 1
fi
