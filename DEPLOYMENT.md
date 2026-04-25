# Déploiement — Chatbot ELISFA V1

**Audience :** dev qui reprend le projet (toi dans 2 semaines, ou un futur contributeur).
**Maintenu :** version Sprint 0.5, 2026-04-25.

---

## 🚀 1. Démarrage local (5 min)

### Prérequis

- macOS / Linux
- Python **3.11, 3.12 ou 3.14** (testé en CI sur 3.11/3.12, dev local sur 3.14)
- Une clé API Anthropic ([console.anthropic.com](https://console.anthropic.com/settings/keys))
- Git

### Setup

```bash
# 1. Cloner le repo
git clone https://github.com/0xZ1337/chatbot_elisfa.git
cd chatbot_elisfa

# 2. Créer un venv propre
python3 -m venv .venv
source .venv/bin/activate

# 3. Installer les dépendances (~30s)
pip install -r requirements.txt

# 4. Configurer .env (copier le template)
cp .env.example .env
#   éditer .env et renseigner ANTHROPIC_API_KEY=sk-ant-xxxx

# 5. Lancer le serveur
python app.py
```

✅ Serveur sur **http://localhost:8080**
✅ Healthcheck : `curl http://localhost:8080/api/health` → `{"status":"ok",...}`

### Test rapide UI

Ouvre [http://localhost:8080](http://localhost:8080) → sélectionne un profil → pose une question. Tu devrais voir :
- Réponse markdown structurée
- Badge **CONFIANCE FORTE · 87.4** (Sprint 0.1)
- Footer : `1 question • 8.5s en moyenne` (Sprint 0.1)
- `logs/events.jsonl` qui se remplit (Sprint 0.4)

### Mode debug

Ouvre [http://localhost:8080?debug=1](http://localhost:8080?debug=1) → panneau latéral droit avec score RAG, theme, latence, top suggestions.

---

## 🧪 2. Lancer les tests

```bash
# Lint + tests rapides
ruff check .
ANTHROPIC_API_KEY=test-key-not-real CLAUDE_MODEL=claude-haiku-4-5-20251001 \
  pytest --tb=short

# Avec couverture (Sprint 0.3)
pytest --cov=. --cov-report=term --cov-report=html
open htmlcov/index.html  # rapport navigable
```

### Pre-commit hooks (Sprint 0.2)

Installation **une seule fois** :
```bash
pip install pre-commit
pre-commit install
```

À chaque `git commit`, tournent automatiquement :
- ruff (auto-fix)
- trim trailing whitespace
- end-of-file-fixer
- check-yaml / check-json
- check large files (>2 MB)
- detect-private-key

---

## 🌳 3. Branches & flux

| Branche | Rôle |
|---------|------|
| `main` | Production stable. **Protégée** : push direct interdit. |
| `v1-stable` | Snapshot prod actuelle. Filet de sécurité pour rollback. |
| `v2-dev` | Dev V2 — toutes les améliorations Sprint 0.x sont là. |

Flow recommandé :

```
v2-dev → travail quotidien → push (CI auto) → PR vers main quand validé
```

**Le CI (GitHub Actions) tourne sur push/PR vers `main` ou `v2-dev`** (Sprint 0.2). 4 jobs :
- `pytest (Python 3.11)` + `pytest (Python 3.12)`
- `ruff lint`
- `Docker build`

Lien : https://github.com/0xZ1337/chatbot_elisfa/actions

---

## 🐳 4. Déploiement production (Hostinger VPS)

### Image Docker

Le `Dockerfile` produit une image légère basée sur `python:3.11-slim`. Build local :

```bash
docker build -t chatbot-elisfa:latest .
docker run -p 8080:8080 --env-file .env chatbot-elisfa:latest
```

### Sur le VPS Hostinger

```bash
# Pull de la dernière image
ssh user@vps
cd /opt/chatbot_elisfa
git pull origin main

# Rebuild + restart via docker-compose
docker-compose down
docker-compose up -d --build
docker-compose logs -f  # vérifier le boot
```

### Variables d'env requises en prod

Voir `.env.example`. Critiques :
- `ANTHROPIC_API_KEY` (clé Claude — obligatoire)
- `CLAUDE_MODEL=claude-haiku-4-5-20251001` (modèle production)
- `ADMIN_PASS_HASH` (bcrypt — pour `/admin`)
- `SENTRY_DSN` (optionnel — monitoring distant)

### Sanity check post-déploiement

```bash
curl https://felias-reseau-eli2026.duckdns.org/api/health
# Doit renvoyer {"status":"ok","api_configured":true,...}

curl -X POST https://felias-reseau-eli2026.duckdns.org/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"Quelle durée de préavis ?","module":"juridique"}'
# Doit renvoyer une réponse JSON avec "answer", "confidence", "fiches" (≤5)
```

---

## 🔄 5. Rollback en cas de pépin

V1 actuelle reste sur `main` + tag `v1-stable`. Pour rollback :

```bash
# Sur le VPS, revenir à la dernière version stable connue
ssh user@vps
cd /opt/chatbot_elisfa
git fetch origin
git checkout v1-stable
docker-compose down
docker-compose up -d --build
```

⏱ Rollback complet : ~3 minutes.

---

## 📊 6. Logs et monitoring

| Source | Fichier | Quoi |
|--------|---------|------|
| Logs structurés (Sprint 0.4) | `logs/events.jsonl` | kb_loaded, ask_request, rag_retrieval, claude_call, error_caught |
| Logs Flask | `logs/chatbot.log` | Logs applicatifs Python |
| Interactions | `logs/interactions.jsonl` | Questions/réponses agrégées (théme, niveau) |
| Feedback | `logs/feedback.jsonl` | 👍/👎 utilisateurs |

### Analyses utiles

```bash
# Distribution des scores RAG
jq 'select(.event=="rag_retrieval") | .top_score' logs/events.jsonl | \
  python3 -c "import sys; xs=[float(x) for x in sys.stdin]; \
              print(f'min={min(xs):.1f} avg={sum(xs)/len(xs):.1f} max={max(xs):.1f}')"

# Latence Claude moyenne
jq 'select(.event=="claude_call") | .latency_ms' logs/events.jsonl | \
  python3 -c "import sys; xs=[float(x) for x in sys.stdin]; \
              print(f'Claude: {sum(xs)/len(xs)/1000:.2f}s en moyenne')"

# Erreurs des dernières 24h
jq 'select(.event=="error_caught")' logs/events.jsonl | tail -20
```

### Sentry — monitoring d'erreurs distantes (Sprint 1.2)

Sentry est intégré via [observability.py](./observability.py). Activation conditionnelle : si `SENTRY_DSN` est vide, c'est un no-op silencieux (pas d'erreur au boot).

**Setup initial** (une fois, ~10 min) :

1. Créer un compte gratuit sur [sentry.io](https://sentry.io) → New Project → Python/Flask
2. Copier le **DSN** (format `https://xxx@oNNN.ingest.sentry.io/MMM`)
3. L'ajouter dans `.env` du VPS :
   ```bash
   SENTRY_DSN=https://xxx@oNNN.ingest.sentry.io/MMM
   SENTRY_ENVIRONMENT=production
   SENTRY_RELEASE=$(git rev-parse --short HEAD)
   ```
4. `docker-compose restart` → au boot, le log doit afficher `[sentry] Initialisé (env=production, ...)`

**Tester que ça marche end-to-end** (Sprint 1.2) :

```bash
# Depuis ton poste, après avoir mis SENTRY_DSN en prod :
curl -X POST -u admin:<password> https://felias-reseau-eli2026.duckdns.org/api/sentry/test

# Réponse attendue :
# {"status":"ok","message":"2 events envoyés (1 INFO + 1 RuntimeError)..."}
```

Va ensuite sur Sentry → Issues. Tu dois voir 2 nouveaux événements en quelques secondes :
- `ELISFA Sentry self-test triggered (admin)` (INFO)
- `RuntimeError: ELISFA Sentry self-test exception (safe to ignore)` (ERROR)

Si rien n'arrive → vérifier que le DSN est correct (pas de `xxx` placeholder), que le boot a bien initialisé Sentry (cf. logs Flask), et que le pare-feu sortant du VPS autorise `*.ingest.sentry.io:443`.

**Configurer les alertes** (Sentry UI, ~5 min) :

Sentry → Alerts → Create Alert. Règles recommandées :

| Condition | Action | Fréquence |
|---|---|---|
| Nouvelle issue créée | Email à toi | Immédiat |
| Issue avec >10 events/h | Email + Slack si configuré | Toutes les heures |
| Régression (issue résolue qui revient) | Email | Immédiat |

Évite les règles trop sensibles au début — un setup `>5 events/min` te spamme à la moindre microcoupure réseau Anthropic. Calibrer selon le volume réel après 1-2 semaines.

**Privacy / RGPD** :

Le scrubber [observability.py:_scrub_sentry_event](./observability.py) filtre automatiquement avant envoi :
- Clés `sk-ant-*` (Anthropic)
- Tokens `Bearer ...`
- Adresses email (remplacées par `***@***`)

`send_default_pii=False` désactive aussi la capture d'IP utilisateur côté Sentry. Aucun mot de passe ni hash bcrypt n'est jamais transmis.

---

## 🆘 Aide rapide

- 🐛 Une panne ? → voir [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
- 📐 Architecture détaillée ? → voir le plan stratégique dans `_PLAN_enrichissement_modules_2026-04-21.md`
- 🔧 Tests ne passent pas ? → relancer en local avec les vars d'env, vérifier le CI
- 🔑 Clé API perdue ? → console.anthropic.com → Settings → API keys
