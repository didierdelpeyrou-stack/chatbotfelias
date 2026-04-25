# syntax=docker/dockerfile:1.7
#
# Dockerfile V2 — multi-stage pour image production légère.
#
# Build context attendu : la racine du repo (chatbot_elisfa/), pas v2/.
# Cela permet d'inclure les KB depuis data/ et de suivre la même convention
# que le Dockerfile V1 à la racine.
#
# Build :
#   cd chatbot_elisfa/
#   docker build -f v2/docker/Dockerfile -t chatbot-elisfa-v2:latest .
#
# Run :
#   docker run --rm -p 8000:8000 \
#     -e ANTHROPIC_API_KEY=sk-ant-... \
#     -v $(pwd)/data:/app/data:ro \
#     chatbot-elisfa-v2:latest


# ════════════════════════════════════════════════════════════
# Stage 1 — Builder : install deps Python + compile native
# ════════════════════════════════════════════════════════════
FROM python:3.12-slim AS builder

# Pas de .pyc, pas de buffering — bonnes pratiques container Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Outils nécessaires pour compiler bcrypt + uvloop
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# On installe tout dans /opt/venv pour copier proprement vers le runtime
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copie minimale pour profiter du cache Docker layer :
# 1. requirements.txt change rarement → couche cachée
# 2. code change souvent → couche après
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt


# ════════════════════════════════════════════════════════════
# Stage 2 — Runtime : image slim avec venv + code
# ════════════════════════════════════════════════════════════
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    # Sprint 3.1 : KB par défaut montée dans /app/data (volume)
    KB_DATA_DIR=/app/data

# Utilitaire HTTP pour HEALTHCHECK (curl est ~30 KB après cleanup)
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Sécurité : utilisateur non-root pour exécuter l'app
RUN groupadd --system elisfa && useradd --system --gid elisfa --no-create-home elisfa

# Copie du venv depuis le builder (pas de gcc/build-essential dans le runtime)
COPY --from=builder /opt/venv /opt/venv

WORKDIR /app

# Code V2 uniquement (V1 reste hors image — déployée séparément)
# Fait depuis la racine du repo (build context) :
COPY --chown=elisfa:elisfa v2/ /app/

USER elisfa
EXPOSE 8000

# Health-check : utilisé par docker-compose et les orchestrateurs (k8s, swarm)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl --fail --silent http://localhost:8000/healthz || exit 1

# Uvicorn directement (pas Gunicorn) — FastAPI async natif, 1 worker suffit
# pour un VPS Hostinger 2 CPUs. Pour scaler plus tard, ajouter --workers 2.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
