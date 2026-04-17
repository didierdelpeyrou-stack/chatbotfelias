FROM python:3.11-slim

WORKDIR /app

# Dépendances système
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier l'application
COPY . .

# Créer les dossiers nécessaires
RUN mkdir -p logs data

# Port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/api/health || exit 1

# Lancement avec Gunicorn pour la production.
# 1 worker + 8 threads : le rate-limiter et les caches (prompt, index KB) sont
# in-memory ; avec plusieurs workers chaque process a son propre état, ce qui
# dégrade l'efficacité et permet de contourner le rate-limit par round-robin.
# Concurrence : les endpoints sont I/O-bound (appels Claude + SMTP), donc les
# threads suffisent largement pour plusieurs centaines de req/min.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "8", "--timeout", "120", "app:app"]
