# Troubleshooting — Chatbot ELISFA

Ce document liste les pannes les plus courantes et leur résolution. Mis à jour au fil des incidents — n'hésite pas à enrichir quand tu rencontres un nouveau cas.

---

## ⚠️ Au démarrage

### `ModuleNotFoundError: No module named 'X'`

```bash
# Le venv n'est pas activé ou les deps ne sont pas installées
source .venv/bin/activate
pip install -r requirements.txt
```

### `WARNING:root:[security] Ni ADMIN_PASS_HASH ni ADMIN_PASS défini`

✅ **Pas une erreur** — juste un warning. Endpoint `/admin` désactivé en local. Pour activer :

```bash
python scripts/generate_admin_hash.py "monMotDePasse"
# Copie la sortie dans .env :
# ADMIN_PASS_HASH=$2b$12$....
```

### Server démarre sur le mauvais port

Le port par défaut est **8080** (pas 5000 comme Flask par défaut). Vérifie dans `.env` :
```
PORT=8080
```
Ou via env var : `PORT=8080 python app.py`

### `Address already in use`

Un autre process écoute déjà sur le port :

```bash
lsof -i :8080         # voir qui occupe
kill <PID>            # libérer
# ou changer de port :
PORT=8081 python app.py
```

---

## 🤖 Côté Claude API

### `RuntimeError: Authentication error`

Clé API invalide ou expirée :

```bash
# Vérifier la valeur dans .env (ne pas la coller dans le terminal !)
grep ANTHROPIC_API_KEY .env

# Tester avec curl directement
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-haiku-4-5-20251001","max_tokens":10,"messages":[{"role":"user","content":"hi"}]}'
```

→ Si 401, regénérer une clé sur [console.anthropic.com](https://console.anthropic.com/settings/keys).

### `RuntimeError: Rate limit exceeded`

Tu as dépassé le quota par minute. Pause + retry :
- Vérifier l'usage : [console.anthropic.com](https://console.anthropic.com/settings/usage)
- Réduire `RATE_LIMIT_PER_MINUTE` dans `.env` pour throttler côté serveur

### Latence Claude > 15 secondes

Diagnostic :

```bash
# 1. Vérifier la taille du contexte (prompt cache désactivé si KB modifiée)
jq 'select(.event=="claude_call") | {input_tokens, cache_read_tokens}' logs/events.jsonl | tail -5

# 2. Si cache_read_tokens = 0 systématiquement → cache miss
#    → Probablement KB rechargée trop souvent (vérifier mtime)
ls -la data/base_*.json
```

Solution : éviter de toucher aux JSON KB pendant qu'un trafic actif tourne.

---

## 📚 Côté KB / RAG

### Réponse "je ne sais pas" sur question évidente

Diagnostic via mode debug :

```
http://localhost:8080?debug=1
```

Le panneau latéral montre :
- `Sources count: 0` → la KB n'a rien trouvé (top_score = 0)
- `Theme RAG: inconnu` → idem

Causes possibles :
1. Mots-clés de l'article ne couvrent pas la formulation utilisateur
2. KB non chargée correctement → vérifier `logs/events.jsonl` pour `kb_loaded` au boot
3. Faute de frappe dans la question (substring match cassé)

### "kb_load_failed" dans events.jsonl

Au boot, une base ne s'est pas indexée :

```bash
jq 'select(.event=="kb_load_failed")' logs/events.jsonl
# → te donne le nom de la base + l'erreur
```

Causes typiques :
- JSON malformé : `python3 -m json.tool data/base_juridique.json`
- Champ obligatoire manquant : vérifier le schéma dans la KB

### Scores RAG anormalement bas (toutes les questions < 1.5)

```bash
# Distribution des scores
jq 'select(.event=="rag_retrieval") | .top_score' logs/events.jsonl | \
  sort -n | uniq -c | head -20
```

Si presque tout est `0` ou `<1.5`, c'est probablement :
- L'index n'a pas été reconstruit après modif KB (rebooter app.py)
- Tokenizer cassé (vérifier `_tokenize` dans `app.py`)

---

## 🌐 Côté UI / Frontend

### Le banner "Avertissement" reste déployé

Sprint 0.1 a mis tous les banners en `class="banner collapsed"` par défaut. Si visible déployé :

1. Hard refresh navigateur : `Cmd+Shift+R` (macOS) / `Ctrl+Shift+R` (Linux)
2. Vider localStorage :
   ```js
   localStorage.removeItem('elisfa_banner_collapsed');
   ```

### Modal profil apparaît à chaque visite

C'est attendu **uniquement à la première visite**. Si ça revient à chaque fois :
- localStorage bloqué (mode incognito) → impossible de persister
- Le navigateur efface localStorage à la fermeture (paramètre privacy)

### Bouton 📋 Copier ne fonctionne pas

Permission Clipboard nécessaire (HTTPS ou localhost uniquement) :
- En `http://` non-localhost : navigator.clipboard.writeText() bloqué
- Solution : déployer en HTTPS ou tester sur `http://localhost:8080`

### Raccourci `Cmd+K` n'ouvre rien

Le raccourci focus le textarea — il ne crée pas de modal. Vérifie :
1. Tu ne tapes pas déjà dans un autre input (le focus reste sur lui)
2. La page est bien chargée (DOMContentLoaded)
3. Console : `document.getElementById('inputField')` doit retourner un élément

---

## 🔧 Côté tests / CI

### Tests passent localement, échouent sur CI

Différences typiques :
1. **Variables d'env** : CI utilise `ANTHROPIC_API_KEY=test-key-not-real`. Si un test fait un vrai appel, il faut le mocker.
2. **Python version** : CI teste sur 3.11 et 3.12. Si tu utilises une feature 3.13+, ça casse.
3. **Locale** : CI est en `en_US.UTF-8` par défaut. Pour les tests qui dépendent du français : `os.environ['LC_ALL'] = 'fr_FR.UTF-8'`

### `ruff check` passe en local mais échoue en CI

Versions différentes de ruff. Aligne :

```bash
pip install --upgrade ruff
ruff --version  # comparer avec ce que CI affiche
```

### Pre-commit auto-fix des fichiers data/

C'était un bug Sprint 0.2. Solution déjà en place : `.pre-commit-config.yaml` exclut `data/` globalement.

Si tu vois encore le souci :
```bash
git checkout -- data/
pre-commit run --all-files  # doit ne plus toucher data/
```

---

## 🐳 Côté Docker / production

### `docker-compose up` échoue avec "no space left on device"

```bash
docker system prune -a --volumes  # nettoie images/containers/volumes inutilisés
docker-compose up -d --build
```

### Container démarre mais `/api/health` renvoie 502

Le proxy nginx/Caddy ne route pas correctement. Vérifie :

```bash
# Dans le container
docker-compose exec chatbot sh
curl http://localhost:8080/api/health  # doit marcher en interne

# Hors container
docker-compose ps  # vérifier que le port est bien mappé
```

### Logs vides après déploiement

Volume `logs/` non monté :

```yaml
# docker-compose.yml
services:
  chatbot:
    volumes:
      - ./logs:/app/logs    # ← cette ligne doit être présente
```

---

## 📞 Quand tout échoue

1. **Rollback** : voir [DEPLOYMENT.md §5](./DEPLOYMENT.md) — retour à `v1-stable` en 3 min
2. **Logs Sentry** : si `SENTRY_DSN` configuré, [sentry.io](https://sentry.io) montre la stack trace
3. **Issue GitHub** : ouvre une issue avec les events JSONL pertinents (anonymisés via `question_hash`)
4. **Contact support** :
   - Hostinger : panel client
   - Anthropic : [support.anthropic.com](https://support.anthropic.com)
