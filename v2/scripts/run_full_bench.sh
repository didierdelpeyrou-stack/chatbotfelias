#!/usr/bin/env bash
# run_full_bench.sh — Lance V1 + V2 + benchmark complet
#
# Sprint 5.2-bench — exécute le bench V1 vs V2 sur 70 questions du corpus
# (50 originales + 20 ajoutées Sprint 5.2-data).
#
# Pré-requis :
#   - ANTHROPIC_API_KEY exporté dans l'env
#   - Ports 8080 (V1) et 8000 (V2) libres
#   - Venv Python en .venv/ (à la racine du projet chatbot_elisfa)
#
# Usage :
#   cd chatbot_elisfa/v2/scripts
#   chmod +x run_full_bench.sh
#   ./run_full_bench.sh                   # 70 Q (full)
#   ./run_full_bench.sh --limit 5         # smoke test sur 5 Q
#   ./run_full_bench.sh --skip-v1         # bench V2 seul (V1 a souvent du HTTP 429)
#   ./run_full_bench.sh --keep-running    # ne tue pas les serveurs après le bench

set -uo pipefail

# ────────────────────────── Config ──────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
V2_DIR="$PROJECT_ROOT/v2"
VENV="$PROJECT_ROOT/.venv"
PYTHON="$VENV/bin/python"

V1_PORT=8080
V2_PORT=8000
V1_HEALTH="http://localhost:${V1_PORT}/api/health"
V2_HEALTH="http://localhost:${V2_PORT}/healthz"

LOG_DIR="$V2_DIR/benchmark_results"
RUN_TS="$(date +%Y%m%d_%H%M%S)"
V1_LOG="$LOG_DIR/v1_${RUN_TS}.log"
V2_LOG="$LOG_DIR/v2_${RUN_TS}.log"
BENCH_LOG="$LOG_DIR/bench_${RUN_TS}.log"

V1_PID=""
V2_PID=""
SKIP_V1=false
KEEP_RUNNING=false
EXTRA_ARGS=()

# ────────────────────────── Args ──────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --skip-v1)       SKIP_V1=true; shift ;;
        --keep-running)  KEEP_RUNNING=true; shift ;;
        --limit)         EXTRA_ARGS+=(--limit "$2"); shift 2 ;;
        -h|--help)
            grep "^#" "$0" | sed 's/^# \?//' | head -25
            exit 0
            ;;
        *) EXTRA_ARGS+=("$1"); shift ;;
    esac
done

# ────────────────────────── Couleurs ──────────────────────────
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

# ────────────────────────── Cleanup ──────────────────────────
cleanup() {
    local rc=$?
    if [[ "$KEEP_RUNNING" == "true" ]]; then
        log "Mode --keep-running : V1 (PID=$V1_PID) et V2 (PID=$V2_PID) restent actifs"
        return $rc
    fi
    if [[ -n "$V1_PID" ]] && kill -0 "$V1_PID" 2>/dev/null; then
        log "Arrêt V1 (PID=$V1_PID)"
        kill "$V1_PID" 2>/dev/null || true
        sleep 1
        kill -9 "$V1_PID" 2>/dev/null || true
    fi
    if [[ -n "$V2_PID" ]] && kill -0 "$V2_PID" 2>/dev/null; then
        log "Arrêt V2 (PID=$V2_PID)"
        kill "$V2_PID" 2>/dev/null || true
        sleep 1
        kill -9 "$V2_PID" 2>/dev/null || true
    fi
    return $rc
}
trap cleanup EXIT INT TERM

# ────────────────────────── Vérifications ──────────────────────────
log "${BLD}Sprint 5.2-bench — Bench complet V1 vs V2${NC}"
echo

# Charge .env automatiquement si présent et clé pas déjà exportée
if [[ -z "${ANTHROPIC_API_KEY:-}" ]] && [[ -f "$PROJECT_ROOT/.env" ]]; then
    log "Chargement automatique de $PROJECT_ROOT/.env"
    set -a
    # shellcheck disable=SC1091
    source "$PROJECT_ROOT/.env"
    set +a
fi

if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
    err "ANTHROPIC_API_KEY non défini. Exporter avec : export ANTHROPIC_API_KEY=sk-ant-..."
    err "Ou ajouter dans $PROJECT_ROOT/.env : ANTHROPIC_API_KEY=sk-ant-..."
    exit 1
fi
ok "ANTHROPIC_API_KEY présent (${#ANTHROPIC_API_KEY} chars)"

if [[ ! -x "$PYTHON" ]]; then
    err "Venv Python introuvable : $PYTHON"
    err "Créer le venv : python -m venv $VENV && $VENV/bin/pip install -r requirements.txt"
    exit 1
fi
ok "Venv Python : $PYTHON"

# Check ports
for port in "$V1_PORT" "$V2_PORT"; do
    if [[ "$port" == "$V1_PORT" && "$SKIP_V1" == "true" ]]; then continue; fi
    if lsof -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
        warn "Port $port déjà occupé — un serveur tourne déjà ?"
        warn "Voir : lsof -iTCP:$port -sTCP:LISTEN"
        # On continue : peut-être que l'utilisateur veut bencher contre un serveur déjà lancé
    fi
done

mkdir -p "$LOG_DIR"
log "Logs dans : $LOG_DIR"
echo

# ────────────────────────── Démarrage V1 ──────────────────────────
if [[ "$SKIP_V1" == "false" ]]; then
    log "Démarrage V1 (Flask) sur port $V1_PORT..."
    (cd "$PROJECT_ROOT" && nohup "$PYTHON" app.py > "$V1_LOG" 2>&1) &
    V1_PID=$!
    log "  PID V1 = $V1_PID, log : $V1_LOG"

    # Attente readiness V1
    log "Attente V1 ready (max 30s)..."
    for i in {1..30}; do
        if curl -sf "$V1_HEALTH" > /dev/null 2>&1; then
            ok "V1 ready après ${i}s"
            break
        fi
        if ! kill -0 "$V1_PID" 2>/dev/null; then
            err "V1 a quitté prématurément. Voir : $V1_LOG"
            tail -20 "$V1_LOG" >&2
            exit 1
        fi
        sleep 1
        if [[ $i -eq 30 ]]; then
            err "V1 timeout après 30s. Voir : $V1_LOG"
            tail -20 "$V1_LOG" >&2
            exit 1
        fi
    done
else
    warn "V1 skippé (--skip-v1) — bench V2 seul"
fi

# ────────────────────────── Démarrage V2 ──────────────────────────
log "Démarrage V2 (FastAPI) sur port $V2_PORT..."
(cd "$V2_DIR" && \
    PYTHONPATH=. KB_DATA_DIR=../data \
    nohup "$PYTHON" -m uvicorn app.main:app --host 127.0.0.1 --port "$V2_PORT" \
    > "$V2_LOG" 2>&1) &
V2_PID=$!
log "  PID V2 = $V2_PID, log : $V2_LOG"

# Attente readiness V2
log "Attente V2 ready (max 30s)..."
for i in {1..30}; do
    if curl -sf "$V2_HEALTH" > /dev/null 2>&1; then
        ok "V2 ready après ${i}s"
        break
    fi
    if ! kill -0 "$V2_PID" 2>/dev/null; then
        err "V2 a quitté prématurément. Voir : $V2_LOG"
        tail -20 "$V2_LOG" >&2
        exit 1
    fi
    sleep 1
    if [[ $i -eq 30 ]]; then
        err "V2 timeout après 30s. Voir : $V2_LOG"
        tail -20 "$V2_LOG" >&2
        exit 1
    fi
done

# Smoke test : V2 répond bien à une question simple
log "Smoke test V2 RAG..."
SMOKE_RESPONSE=$(curl -sf -X POST "http://localhost:${V2_PORT}/api/ask" \
    -H "Content-Type: application/json" \
    -d '{"question":"Test smoke","module":"formation"}' 2>&1 || echo "FAILED")
if [[ "$SMOKE_RESPONSE" == "FAILED" ]] || [[ -z "$SMOKE_RESPONSE" ]]; then
    err "Smoke test V2 échoué"
    tail -10 "$V2_LOG" >&2
    exit 1
fi
ok "Smoke test V2 OK"
echo

# ────────────────────────── Lancement bench ──────────────────────────
log "${BLD}Lancement du benchmark sur 70 questions...${NC}"
log "(durée estimée : 5-10 minutes selon rate-limit Anthropic)"
echo

cd "$V2_DIR"
# Bash strict mode + array vide : utiliser l'expansion conditionnelle
PYTHONPATH=. "$PYTHON" scripts/benchmark.py ${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"} 2>&1 | tee "$BENCH_LOG"
BENCH_RC=${PIPESTATUS[0]}

echo
if [[ $BENCH_RC -eq 0 ]]; then
    ok "${BLD}Benchmark terminé avec succès${NC}"
    log "Résultats dans : $LOG_DIR"
    log "Dernier rapport : $(ls -t $LOG_DIR/*.md 2>/dev/null | head -1)"
else
    err "Benchmark a échoué (code $BENCH_RC)"
    err "Voir le log complet : $BENCH_LOG"
fi

exit $BENCH_RC
