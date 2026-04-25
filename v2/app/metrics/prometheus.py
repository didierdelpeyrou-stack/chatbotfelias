"""5 métriques Prometheus essentielles pour V2.

Convention de nommage : `elisfa_v2_<sujet>_<unit>`. Le préfixe `elisfa_v2`
évite tout conflit avec Félias (`felias_*`) si on les scrape ensemble.

Endpoint d'exposition : GET /metrics — format text/plain Prometheus standard.
Scrape attendu : `prometheus.yml` côté infra.

Buckets choisis :
  - score   : [0, 0.5, 1, 2, 5, 10, 30, 100, +inf]   (cohérent avec SCORE_HIGH=5.0)
  - latence : [0.1, 0.5, 1, 2, 5, 10, 20, 30, +inf]  (timeout 60s côté Claude)
"""
from __future__ import annotations

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Histogram,
    generate_latest,
)

# ── Registre dédié V2 — facilite les tests (on peut créer un registre frais) ──
# `default registry` global de prometheus_client est partagé entre les imports,
# ce qui pose problème en pytest (DuplicatedTimeSeriesError). On expose un
# registre privé qu'on peut instancier par test.
REGISTRY = CollectorRegistry()


# ────────────────────────── 5 métriques essentielles ──────────────────────────

REQUESTS_TOTAL = Counter(
    "elisfa_v2_requests_total",
    "Nombre total de requêtes /api/ask par module et par statut",
    labelnames=("module", "status"),  # status: ok | hors_corpus | error
    registry=REGISTRY,
)

RAG_SCORE = Histogram(
    "elisfa_v2_rag_score",
    "Distribution des best_score TF-IDF par requête",
    labelnames=("module",),
    buckets=(0.0, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 100.0, float("inf")),
    registry=REGISTRY,
)

RAG_HORS_CORPUS_TOTAL = Counter(
    "elisfa_v2_rag_hors_corpus_total",
    "Nombre de requêtes ayant déclenché le seuil hors_corpus (R1)",
    labelnames=("module",),
    registry=REGISTRY,
)

REQUEST_LATENCY = Histogram(
    "elisfa_v2_request_latency_seconds",
    "Latence end-to-end des requêtes /api/ask",
    labelnames=("module", "path"),
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, float("inf")),
    registry=REGISTRY,
)

CLAUDE_TOKENS_TOTAL = Counter(
    "elisfa_v2_claude_tokens_total",
    "Tokens Claude consommés par type (input, output, cache_read, cache_creation)",
    labelnames=("type",),
    registry=REGISTRY,
)


# ────────────────────────── Helpers d'enregistrement ──────────────────────────

def record_request(*, module: str, status: str) -> None:
    """Counter de requêtes /api/ask — appelé après chaque pipeline."""
    REQUESTS_TOTAL.labels(module=module, status=status).inc()


def record_rag(*, module: str, best_score: float, hors_corpus: bool) -> None:
    """Observation du score TF-IDF + flag hors_corpus."""
    RAG_SCORE.labels(module=module).observe(best_score)
    if hors_corpus:
        RAG_HORS_CORPUS_TOTAL.labels(module=module).inc()


def record_latency(*, module: str, path: str, seconds: float) -> None:
    """Latence end-to-end — appeler avec time.perf_counter() en début/fin."""
    REQUEST_LATENCY.labels(module=module, path=path).observe(seconds)


def record_claude_tokens(
    *,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cache_creation_tokens: int = 0,
    cache_read_tokens: int = 0,
) -> None:
    """Mise à jour des compteurs de tokens Claude après chaque .complete() / .stream()."""
    if input_tokens:
        CLAUDE_TOKENS_TOTAL.labels(type="input").inc(input_tokens)
    if output_tokens:
        CLAUDE_TOKENS_TOTAL.labels(type="output").inc(output_tokens)
    if cache_creation_tokens:
        CLAUDE_TOKENS_TOTAL.labels(type="cache_creation").inc(cache_creation_tokens)
    if cache_read_tokens:
        CLAUDE_TOKENS_TOTAL.labels(type="cache_read").inc(cache_read_tokens)


# ────────────────────────── Exposition ──────────────────────────

def render_metrics() -> tuple[bytes, str]:
    """Sérialise le registre en format Prometheus text. Retourne (body, content-type)."""
    return generate_latest(REGISTRY), CONTENT_TYPE_LATEST
