# Déploiement V2 staging — Runbook (Sprint 4.4)

**Audience :** toi, sur le VPS Hostinger, avec accès SSH root.
**Prérequis :** V1 tourne déjà sur `felias-reseau-eli2026.duckdns.org` (port 80/443, nginx + Docker).
**Cible :** V2 cohabite sur `felias.duckdns.org` (sous-domaine séparé).
**Durée totale estimée :** 3-4h, dont ~30 min de propagation DNS.

---

## Architecture cible

```
                    Internet
                        │
                        ├── felias-reseau-eli2026.duckdns.org      → nginx :443 → V1 (Flask :8080)
                        └── felias.duckdns.org   → nginx :443 → V2 (FastAPI :8000)
                                                                              ↓
                                                                        Docker container
                                                                        chatbot-elisfa-v2-staging
                                                                        (image multi-stage Sprint 3.4)
```

**Principes :**
- V1 et V2 cohabitent **sur le même VPS, même nginx**, deux sous-domaines.
- V2 staging écoute uniquement sur `127.0.0.1:8000` (pas exposé publiquement, nginx fait la proxification HTTPS).
- Logs persistés dans un volume Docker nommé `elisfa-v2-logs` → survivent aux redéploiements.
- Robots bloqués (`X-Robots-Tag: noindex`) — staging non indexable.

---

## §1 — DNS (DuckDNS) — 5 min + 5-30 min de propagation

DuckDNS gratuit autorise jusqu'à 5 sous-domaines par compte.

1. Va sur [duckdns.org](https://www.duckdns.org/) (login Google/GitHub).
2. Section **add domain** : tape `felias` → bouton **add**.
3. Dans le tableau, à la ligne du nouveau sous-domaine :
   - **current ip** : colle l'IP publique du VPS (la même que pour `felias-reseau-eli2026`).
   - Clic **update ip**.
4. Note le **token** affiché en haut de la page (utile pour automatiser le refresh d'IP).

**Vérifier la propagation** depuis ta machine locale :

```bash
host felias.duckdns.org
# Attendu : felias.duckdns.org has address <IP du VPS>
```

Si pas résolu après 5 min, attendre encore 25 min — DuckDNS peut être lent les premières fois.

---

## §2 — Pull du code sur le VPS — 2 min

```bash
ssh user@<vps-ip>
cd /opt/chatbot_elisfa
git fetch origin
git checkout v2-dev
git pull origin v2-dev

# Vérifier qu'on est bien sur le commit Sprint 4.4
git log --oneline -3
```

**Résultat attendu :** le dernier commit doit mentionner `Sprint 4.4` ou être au-dessus de `0ffd1c2` (Sprint 4.3).

---

## §3 — nginx server block — 10 min

Copier la conf, l'activer, recharger nginx :

```bash
# Copier le template depuis le repo
sudo cp /opt/chatbot_elisfa/v2/docker/nginx/v2-staging.conf \
        /etc/nginx/sites-available/v2-staging.conf

# Activer (lien symbolique)
sudo ln -sf /etc/nginx/sites-available/v2-staging.conf \
            /etc/nginx/sites-enabled/v2-staging.conf

# Tester la conf (DOIT renvoyer "syntax is ok" + "test is successful")
sudo nginx -t

# Recharger sans downtime
sudo systemctl reload nginx
```

À ce stade, `http://felias.duckdns.org` répond en HTTP (mais redirige déjà vers HTTPS — qui n'a pas encore de certif → erreur cert attendue).

---

## §4 — Certificat Let's Encrypt — 5 min

```bash
sudo certbot --nginx -d felias.duckdns.org

# Réponses :
#   Email     : <ton email pour les alertes d'expiration>
#   Terms     : (A)gree
#   EFF email : (N)o sauf si tu veux leur newsletter
#   Redirect  : 2 (Redirect HTTP → HTTPS — recommandé)
```

certbot patche automatiquement `v2-staging.conf` pour ajouter les directives `ssl_certificate` et `ssl_certificate_key` qui sont commentées dans le template.

**Vérifier le renouvellement auto :**

```bash
sudo systemctl list-timers | grep certbot
# Attendu : une ligne `certbot.timer` avec NEXT (renouvellement tous les 60-89j)
```

---

## §5 — Variables d'env staging — 3 min

```bash
cd /opt/chatbot_elisfa/v2
cp .env.staging.example .env.staging
nano .env.staging
```

Champs à remplir :

| Variable | Valeur staging |
|---|---|
| `ANTHROPIC_API_KEY` | **Réutilise la même qu'en prod V1** (rate limits = par compte Anthropic, pas par app) |
| `CLAUDE_MODEL` | `claude-haiku-4-5-20251001` |
| `ENVIRONMENT` | `staging` |
| `LOG_LEVEL` | `INFO` |
| **`VOYAGE_API_KEY`** | **Sprint 5.2-stack** : compte gratuit https://dash.voyageai.com — clé `pa-...` |
| `VOYAGE_MODEL` | `voyage-3-large` (1024 dim, recommandé Anthropic) |
| `RAG_HYBRID_ALPHA` | `0.5` (équilibré TF-IDF + embeddings, calibré bench) |
| `KB_DATA_DIR` | `/app/data/v2` (KB enrichie 271 articles, IMPORTANT) |

`.env.staging` est dans `.gitignore` → ne fuit pas. Vérifie :

```bash
git check-ignore -v .env.staging   # doit imprimer "Got check"
```

---

## §5b — Cache embeddings Voyage (Sprint 5.2-stack) — 5 min

Le cache embeddings est généré localement (5-10 min sur free tier) puis
persisté dans `data/v2/_embeddings_*.npz` (~1 MB total). Il **doit être
dans le volume** monté du container, sinon V2 met 20+ min à booter (rate-limit).

**Option A — Cache déjà généré localement** (si tu as fait la Phase A1) :

```bash
# Depuis ta machine locale, push les caches sur le VPS
scp data/v2/_embeddings_*.npz user@<vps-ip>:/opt/chatbot_elisfa/data/v2/
```

**Option B — Générer sur le VPS** (5-10 min, conservateur free tier) :

```bash
# Sur le VPS, dans le container une fois lancé
ssh user@<vps-ip>
cd /opt/chatbot_elisfa/v2
docker compose -f docker/docker-compose.staging.yml exec chatbot-v2-staging \
    python scripts/build_embeddings_cache.py
```

**Vérifier** :

```bash
ls -la /opt/chatbot_elisfa/data/v2/_embeddings_*.npz
# Attendu : 4 fichiers .npz, total ~1 MB
```

Si pas de cache : V2 fonctionne en **TF-IDF seul** (fallback gracieux),
score V2 = ~70 % au lieu de 75 %. Mieux vaut générer le cache avant le bêta.

---

## §6 — Lancer le container Docker V2 — 5 min

```bash
cd /opt/chatbot_elisfa/v2

# Build + up en mode détaché (-d)
docker compose -f docker/docker-compose.staging.yml \
               --env-file .env.staging \
               up -d --build

# Suivre les logs jusqu'à voir "ELISFA V2 boot" + "KB store: {...}"
docker compose -f docker/docker-compose.staging.yml logs -f
# Ctrl+C une fois que le boot est OK
```

**Validation locale (depuis le VPS, avant test public) :**

```bash
curl -s http://127.0.0.1:8000/healthz
# Attendu : {"status":"ok","version":"2.0.0-alpha.1",...}

curl -s http://127.0.0.1:8000/readyz
# Attendu : {"status":"ready","kb_loaded":true,"claude_configured":true}
```

Si `/readyz` renvoie `kb_loaded:false` ou `claude_configured:false`, vérifier :
- volume `data/` correctement monté (`docker inspect chatbot-elisfa-v2-staging | jq .[0].Mounts`)
- `ANTHROPIC_API_KEY` bien lue (`docker exec chatbot-elisfa-v2-staging env | grep ANTHROPIC`)

---

## §7 — Smoke test public — 5 min

Depuis ta machine locale (ou le VPS, peu importe) :

```bash
bash /opt/chatbot_elisfa/v2/scripts/smoke_test_staging.sh
```

10 checks couvrent : DNS, HTTPS, healthz/readyz, /docs, /metrics, /api/ask (juridique + hors_corpus), /api/feedback POST + GET stats.

**Résultat attendu :** `✅ 10/10 tests passent — staging V2 opérationnel`.

---

## §8 — Test utilisateur dans un navigateur — 2 min

Ouvre [https://felias.duckdns.org/docs](https://felias.duckdns.org/docs) — Swagger UI doit s'afficher.

Test interactif :
1. Section **chat** → POST `/api/ask`
2. Try it out → body :
   ```json
   {"question": "Quel est le préavis CCN ALISFA après 2 ans d'ancienneté ?", "module": "juridique"}
   ```
3. Execute → réponse 200 avec `answer` non vide, `confidence.label="high"` ou `"medium"`.

---

## §9 — Documenter la version déployée — 1 min

Sur le VPS :

```bash
echo "$(date -Iseconds) — staging V2 = $(git rev-parse --short HEAD)" \
  | sudo tee -a /var/log/elisfa-deploys.log
```

Sur ton repo local, mettre à jour [v2/README.md](v2/README.md) Section "État courant" si tu veux (optionnel).

---

## §10 — Rollback (si problème majeur) — 3 min

```bash
cd /opt/chatbot_elisfa/v2
docker compose -f docker/docker-compose.staging.yml down
sudo rm /etc/nginx/sites-enabled/v2-staging.conf
sudo systemctl reload nginx
```

V2 staging est éteinte. V1 prod n'a **pas été touchée** → continue à servir normalement.

---

## Concept ML inline — Data drift

Pourquoi du staging avec utilisateurs réels alors qu'on a déjà un benchmark à 74% (Sprint 4.2) ?

Parce que le benchmark est un **dataset figé**, écrit par toi+moi. Les vraies questions des animateurs ELISFA peuvent **diverger** :
- Vocabulaire métier différent ("CSE" plutôt que "comité économique")
- Questions plus contextuelles ("dans notre cas où on a un CDD…")
- Distribution thématique inattendue (peut-être 70% RH au lieu de 40% juridique)

C'est ce qu'on appelle **data drift** : la distribution des données en production diverge de celle d'entraînement/test. Un modèle qui score 95% en bench peut tomber à 60% en prod si le drift est fort.

**Mitigation côté Sprint 4.5 :**
- Logs RAG (Sprint 0.4) → on capture les `top_score` réels et compare à la distribution du benchmark.
- Feedback 👍/👎 (Sprint 4.3) → signal direct de drift perçu.
- Si on voit une catégorie de questions où `top_score < 1.5` (hors_corpus) explose, c'est qu'on a une zone de KB à enrichir (Sprint 6.x).

C'est le pont **offline-eval → online-eval** : les deux se complètent, ni l'un ni l'autre ne suffit seul.

---

## Aide rapide

| Symptôme | Piste |
|---|---|
| `nginx -t` échoue | Indentation conf, `;` manquant, ou conflit sur 80/443 — `sudo nginx -T` pour voir tout |
| `certbot` rate le challenge | Vérifier que port 80 répond AVANT le HTTPS (pare-feu, autre nginx ?) |
| `/readyz` renvoie 503 | `docker logs chatbot-elisfa-v2-staging` → KB pas chargée ou ANTHROPIC_API_KEY vide |
| Tout marche, smoke test KO sur `/api/ask` | Quota Anthropic atteint — voir [console.anthropic.com](https://console.anthropic.com) |
| HTTPS marche, mais `/api/ask/stream` se fige | `proxy_buffering off` pas appliqué — relire conf nginx, reload |
