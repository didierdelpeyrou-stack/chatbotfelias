# Chatbot ELISFA V2 — FastAPI

Refonte du chatbot ELISFA basée sur les audits 2026-04-21. Cohabite avec V1 (Flask, racine du repo) jusqu'au cutover.

## État courant : Sprint 2.1 ✅

- Scaffold FastAPI minimal opérationnel
- Endpoints `/`, `/healthz`, `/readyz`, `/docs` (Swagger auto)
- Settings via `pydantic-settings`
- CORS configurable selon environnement

À venir :

| Sprint | Sujet |
|--------|-------|
| 2.2 | RAG TF-IDF + seuil hors_corpus (R1) |
| 2.3 | KB Pydantic schema validation |
| 2.4 | LLM wrapper Anthropic |
| 3.1 | KB loader + hot-reload |
| 3.2 | `/api/ask` streaming |
| 3.3 | Prometheus (5 metrics) |
| 3.4 | Docker multi-stage |

## Démarrage local

```bash
cd v2/
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env  # éditer ANTHROPIC_API_KEY
uvicorn app.main:app --reload --port 8000
```

Tester :
- http://localhost:8000/         → JSON root
- http://localhost:8000/healthz   → liveness
- http://localhost:8000/readyz    → readiness (vérifie config Anthropic)
- http://localhost:8000/docs      → Swagger UI auto-généré

## Cohabitation V1 / V2

| Composant | V1 (port 8080) | V2 (port 8000) |
|-----------|---------------|----------------|
| Framework | Flask + Gunicorn | **FastAPI + Uvicorn** |
| Validation | Pydantic v2 (limitée) | **Pydantic v2 systématique** |
| Streaming | manuel | **Native async** |
| Métriques | Logs JSONL (Sprint 0.4) | **Prometheus** (Sprint 3.3) |
| Healthchecks | `/api/health` | **`/healthz` + `/readyz`** |

## Tests

```bash
cd v2/
pytest --cov=app --cov-report=term
```

## Pourquoi un sous-dossier `v2/` plutôt qu'un repo séparé ?

Une seule branche `v2-dev`, un seul CI (GitHub Actions), un seul historique git. Le cutover (Sprint 7) se fera en désactivant V1 + bascule DNS — le code V1 reste accessible via le tag `v1-stable`.
