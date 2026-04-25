# Dashboard live — Pendant la session test

3 vues à garder ouvertes en parallèle pendant la session, en plus du Visio.
Objectif : repérer un blocage technique en temps réel et noter les patterns.

---

## Vue 1 — Stats feedback (rafraîchir toutes les 5 min)

Lien : `https://felias-reseau-eli2026-v2.duckdns.org/api/feedback/stats`

```bash
# Sur ton poste, dans un terminal séparé :
watch -n 30 'curl -s https://felias-reseau-eli2026-v2.duckdns.org/api/feedback/stats | python3 -m json.tool'
```

À surveiller :
- `total` qui augmente régulièrement = les gens utilisent le 👍/👎
- `success_rate < 50%` = signal d'alerte (problème massif)
- `by_module` : repérer un module qui prend tous les 👎

---

## Vue 2 — Logs serveur en direct

Pendant la session, garder un SSH ouvert sur le VPS :

```bash
ssh user@<vps-ip>

# Suivre les requêtes /api/ask en temps réel
docker logs -f chatbot-elisfa-v2-staging | grep -E '\[rag\]|\[claude\]|\[feedback\]'

# OU plus structuré : tail du JSONL
tail -F /var/lib/docker/volumes/elisfa-v2-logs/_data/feedback.jsonl | jq '.'
```

À surveiller :
- Erreurs `[claude] ClaudeRateLimitError` → quota Anthropic atteint, action immédiate
- Erreurs `[rag] top_score=0.00` répétées → problème de KB ou tokenizer
- Latences `>10s` répétées → ClaudeTimeoutError imminente

---

## Vue 3 — Métriques Prometheus (snapshot après session)

Pas besoin de Grafana pour la session 1. Juste un snapshot à la fin :

```bash
# Sur le VPS, après la session
curl -s http://127.0.0.1:8000/metrics > /tmp/session1_metrics.txt

# Extraire les chiffres clés
grep -E '^elisfa_v2_(requests_total|hors_corpus_total|claude_tokens_total)' /tmp/session1_metrics.txt
```

Tu calcules à la main :
- **Taux hors_corpus** : `hors_corpus_total / requests_total` — si > 30%, le seuil R1 est trop strict
- **Latence p50** : avec `claude_request_duration_seconds_bucket` et un peu d'arithmétique (ou lance `python3 v2/scripts/prom_quantile.py` que tu écriras Sprint 6.x)

---

## Pendant la session — Ce que tu notes EN LIVE dans un doc séparé

Ouvre un Google Doc partagé (avec toi seul) et note minute par minute :

| HH:MM | Qui (anonymisé) | Quoi | Action |
|---|---|---|---|
| 10:14 | P3 | a tapé "comment ça va" → fallback ok | rien |
| 10:18 | P5 | "préavis CDD" → réponse partielle | flag : enrichir KB juridique |
| 10:22 | P7 | clic 👎 sans commentaire | rappeler à voix haute "n'hésitez pas à mettre un mot" |

Ça te permet :
- De recouper les notes avec les logs JSONL après-coup
- De citer des moments précis dans le rapport (Sprint 4.5 part 2)
- De réagir en live si ça part en vrille

---

## Si ça plante en live

| Symptôme | Action immédiate (en visio, pour rassurer le groupe) |
|---|---|
| Le site ne répond pas | "On bascule sur V1 le temps que je relance" → annoncer URL V1, troubleshoot après |
| Une seule personne a un souci | "Continue, je regarde ton cas en privé après" — éviter de bloquer le groupe |
| Latence énorme (>20s) | "Anthropic a un pic, ça va revenir" — vérifier le statut sur status.anthropic.com |
| Bug reproductible | "Note précisément ce que tu as fait, je le corrige cette semaine" |

⚠️ **Ne JAMAIS** dire en live "ah c'est un bug, je sais" ou "oui c'est nul je sais aussi". Le groupe te juge sur ta posture autant que sur l'outil.
