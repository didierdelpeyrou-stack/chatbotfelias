#!/usr/bin/env bash
# Sprint 4.4 — Smoke test V2 staging.
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
# Code retour : 0 si tout vert, 1 dès qu'un test échoue.

set -u  # pas de set -e : on veut accumuler les erreurs

HOST="${STAGING_HOST:-felias-reseau-eli2026-v2.duckdns.org}"
BASE="https://${HOST}"
FAILED=0
PASSED=0

# Couleurs (skip si pas de TTY pour les CI)
if [[ -t 1 ]]; then
    GREEN=$'\e[32m'; RED=$'\e[31m'; YELLOW=$'\e[33m'; RESET=$'\e[0m'
else
    GREEN=""; RED=""; YELLOW=""; RESET=""
fi

check() {
    local name="$1"
    local cmd="$2"
    if eval "$cmd" >/dev/null 2>&1; then
        echo "${GREEN}✓${RESET} $name"
        PASSED=$((PASSED + 1))
    else
        echo "${RED}✗${RESET} $name"
        echo "    cmd: $cmd"
        FAILED=$((FAILED + 1))
    fi
}

echo "🔍 Smoke test V2 staging — host=${HOST}"
echo

# ─── 1. DNS résolu ───
check "DNS résout ${HOST}" \
      "host ${HOST} | grep -q 'has address'"

# ─── 2. HTTPS répond ───
check "HTTPS root répond 200" \
      "curl -sf -o /dev/null -w '%{http_code}' ${BASE}/ | grep -q 200"

# ─── 3. Healthcheck liveness ───
check "/healthz → status:ok" \
      "curl -sf ${BASE}/healthz | grep -q '\"status\":\"ok\"'"

# ─── 4. Readiness (vérifie que la KB est chargée + Anthropic configuré) ───
check "/readyz → status:ready" \
      "curl -sf ${BASE}/readyz | grep -q '\"status\":\"ready\"'"

# ─── 5. Swagger doc ───
check "/docs (Swagger UI) répond 200" \
      "curl -sf -o /dev/null -w '%{http_code}' ${BASE}/docs | grep -q 200"

# ─── 6. Metrics Prometheus ───
check "/metrics format Prometheus" \
      "curl -sf ${BASE}/metrics | grep -qE '^# HELP elisfa_v2'"

# ─── 7. /api/ask one-shot — question juridique typique ───
ASK_RESPONSE=$(curl -sf -X POST "${BASE}/api/ask" \
    -H "Content-Type: application/json" \
    -d '{"question":"Quelle est la durée de la période d'\''essai ?","module":"juridique"}' \
    || echo "ERROR")
check "/api/ask juridique renvoie un JSON avec answer" \
      "echo '$ASK_RESPONSE' | grep -q '\"answer\"'"

check "/api/ask juridique : answer non vide" \
      "echo '$ASK_RESPONSE' | python3 -c 'import json,sys; d=json.loads(sys.stdin.read()); sys.exit(0 if len(d.get(\"answer\",\"\"))>20 else 1)'"

# ─── 8. /api/ask hors_corpus → fallback court ───
HORS_CORPUS=$(curl -sf -X POST "${BASE}/api/ask" \
    -H "Content-Type: application/json" \
    -d '{"question":"recette quiche lorraine","module":"juridique"}' \
    || echo "ERROR")
check "/api/ask hors_corpus → flag hors_corpus:true" \
      "echo '$HORS_CORPUS' | grep -q '\"hors_corpus\":true'"

# ─── 9. /api/feedback POST 👍 ───
check "POST /api/feedback ok" \
      "curl -sf -X POST ${BASE}/api/feedback \
        -H 'Content-Type: application/json' \
        -d '{\"rating\":1,\"question\":\"smoke test\",\"answer\":\"ok\",\"module\":\"juridique\"}' \
        | grep -q '\"status\":\"ok\"'"

# ─── 10. /api/feedback/stats répond ───
check "GET /api/feedback/stats → champ total" \
      "curl -sf ${BASE}/api/feedback/stats | grep -q '\"total\"'"

echo
TOTAL=$((PASSED + FAILED))
if [[ $FAILED -eq 0 ]]; then
    echo "${GREEN}✅ ${PASSED}/${TOTAL} tests passent — staging V2 opérationnel${RESET}"
    exit 0
else
    echo "${RED}❌ ${FAILED}/${TOTAL} tests ont échoué — investiguer avant Sprint 4.5${RESET}"
    echo "${YELLOW}Astuce : ssh user@vps && docker logs chatbot-elisfa-v2-staging --tail 100${RESET}"
    exit 1
fi
