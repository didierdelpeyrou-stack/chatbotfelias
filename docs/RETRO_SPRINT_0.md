# Rétro Sprint 0 — Stabilisation V1

**Période :** 2026-04-25 (1 session intensive)
**Branche :** `v2-dev`
**Commits :** 6 (de `342c803` à `<sprint_0.5>`)
**Auteur :** Didier Delpeyrou + Claude (pair programming)

---

## 🎯 Objectif initial

Passer la V1 du Chatbot ELISFA d'**état "fonctionnel mais fragile"** à **"prêt pour cohabitation V2"** :
- Code documenté et testé
- CI/CD automatique
- Logs structurés exploitables
- Améliorations UX visibles utilisateurs
- Fondations posées pour Sprint 2.x (V2 MVP)

---

## ✅ Ce qui a été livré (5 sprints, 6 commits)

| Sprint | Livrable | Métrique | Commit |
|--------|----------|----------|--------|
| **Sprint 0** (Préparation) | Git branches, venv, deps, serveur tournant | 3 branches GitHub | `342c803` |
| **Sprint 0.1** | 16 améliorations UX/télémétrie | +334 L sur 2 fichiers | `ec20819` |
| **Sprint 0.2** | CI/CD étendu à v2-dev + pre-commit | 4 jobs GitHub Actions verts | `72715c7` |
| **Sprint 0.4** | Logging structuré JSONL | 5 events typés | `bcc5699` |
| **Sprint 0.3** | 47 tests + coverage 71→74% | structured_logger 100% | `eced1f3` |
| **Sprint 0.5** | DEPLOYMENT.md + TROUBLESHOOTING.md + ce doc | 3 .md, ~700 lignes | `<this>` |

---

## 📊 État final V1 (sur `v2-dev`)

### UX

| Avant | Après |
|-------|-------|
| Banner juridique dépliés (73 px) | Mini-banner cliquable (26-31 px) |
| Layout 1920px : 384px de blanc à droite | max-width 1600px, marges 8% |
| Welcome card 640 px | 880 px avec « Bonjour [Nom] — » |
| 13 fiches PDF retournées | 5 max |
| Modal profil à chaque visite | Persisté localStorage |
| Pas de feedback UX | 👍/👎 en gradient bleu |
| Pas de signal de confiance | Badge **CONFIANCE FORTE · 87.4** |
| Pas de raccourcis | Cmd+K / Cmd+L / Esc |
| Pas de compteur session | "X questions • Ys en moyenne" |
| Pas d'outil debug | `?debug=1` panneau RAG |

### Code quality

| Métrique | Avant | Après |
|----------|-------|-------|
| Tests | 194 | **241** (+47) |
| Coverage globale | 71% | **74%** |
| Coverage `structured_logger` | n/a | **100%** |
| Coverage `observability` | 22% | **68%** |
| Lint (ruff) | manuel | **Auto** (CI + pre-commit) |
| CI sur v2-dev | ❌ | ✅ 4 jobs |
| Pre-commit hooks | ❌ | ✅ 9 hooks |

### Observabilité

| Source | État |
|--------|------|
| `logs/events.jsonl` | **Nouveau** — 5 events typés |
| Helpers analyse | `jq` + `python3 -c ...` (DEPLOYMENT.md §6) |
| Sentry | Optionnel (déjà existant) |
| Mode debug | `?debug=1` (Sprint 0.1) |

---

## 🎓 Concepts ML appris (5)

| # | Concept | Application |
|---|---------|-------------|
| 1 | **Threshold / Decision boundary** | Seuils confidence (high/medium/low/none) |
| 2 | **Calibrated probability output** | Le bot dit son niveau de confiance |
| 3 | **Human-in-the-loop / Feedback** | 👍/👎 → JSONL → reranker V2 |
| 4 | **CI as a safety net for ML** | Tests auto avant chaque push |
| 5 | **Observability for ML** | Logs JSONL = matière première pour calibrer V2 |

---

## 💡 Décisions clés et trade-offs

### ✅ Choix qui ont bien marché

1. **Travailler sur `v2-dev`, pas `main`** : aucun risque pour la prod, expérimentation libre.
2. **Pre-commit hooks excluant `data/`** : éviter les diffs énormes sur la KB.
3. **Confidence badge avec score visible** : transparence, prépare l'UX V2 sans casser V1.
4. **Logs JSONL au lieu de Prometheus** : commencer simple, migrer Sprint 3.3.
5. **Coverage 74% avec 100% sur les nouveautés** : honnête, pragmatique, pas de churn sur le legacy.

### 🟡 Trade-offs assumés

1. **Cible coverage 80% non atteinte** → 74%. Justification : les 706 lines manquantes sont dans `app.py` legacy qui sera réécrit V2. Tester du code condamné = travail jeté.
2. **Modal profil persistance déjà existante** : on a juste vérifié, pas re-codé. Gain de temps assumé.
3. **3 GUIDES_DEPLOIEMENT.docx legacy non supprimés** : on les garde pour traçabilité ELISFA mais on a créé les `.md` modernes en parallèle.
4. **Phase 3+4 reportées** (sidebar historique, streaming SSE, export PDF) : 16 features Sprint 0.1 c'était déjà beaucoup, mieux vaut commit + valider.

### ❌ Surprises (à retenir)

1. **L'endpoint `/api/feedback` existait déjà** côté backend → on a juste rendu l'UI plus visible.
2. **Le code de persistance profil existait déjà** → on a juste validé son fonctionnement.
3. **Le CI complet existait déjà** → on l'a juste étendu à `v2-dev`.

→ **Leçon** : avant de coder, **inspecter l'existant**. Le V1 ELISFA était plus mature qu'on ne le pensait.

---

## 🚦 Milestone Bloc A — Validé ?

Critères du plan initial :

| Critère | Statut | Notes |
|---------|--------|-------|
| V1 stable | ✅ | 241 tests verts, CI vert |
| Tests 80%+ | 🟡 | 74% — explication ci-dessus |
| Documentée | ✅ | DEPLOYMENT.md + TROUBLESHOOTING.md + RETRO |
| CI/CD live | ✅ | 4 jobs GitHub Actions |

**Verdict :** Bloc A **complété pragmatiquement**. Le 80% sera atteint naturellement Sprint 1.1 (refacto app.py).

---

## 📌 Reste à faire avant Bloc B (V2 MVP)

### Optionnels (peuvent être skippés)

- **Sprint 1.1** — Refactoring léger app.py (-50 L duplication, extract 3 fonctions)
- **Sprint 1.2** — Sentry monitoring + alerts basiques
- **Phase 3** — Sidebar historique
- **Phase 4** — Streaming SSE + Export PDF

### Bloc B (V2 MVP)

- **Sprint 2.1** — V2 FastAPI scaffold
- **Sprint 2.2** — V2 RAG + seuil hors_corpus (concept ML : thresholds)
- **Sprint 2.3** — KB Pydantic models
- **Sprint 2.4** — LLM wrapper Anthropic SDK

→ **Premier vrai code V2** = Sprint 2.x. Mon conseil : Sprint 2.1 directement après ce Bloc A, sans passer par Sprint 1.x.

---

## 🎉 Ce qui est mémorable

- **Première session** où on a **livré 16 features UX en une fois** sans casser la prod (grâce à `v2-dev`).
- **Le mode debug `?debug=1`** : un outil qui n'existait pas chez ELISFA et qui sera précieux pour Sprint 4 (benchmark).
- **Le commit message qui résume tout** : `feat(observability): logging structuré JSONL aux 5 points clés`.
- **La leçon majeure** : *les LLMs ne remplacent pas la rigueur — ils l'amplifient*. Sans tests + CI + logs, on aurait pu pousser n'importe quoi.

---

## 📝 À faire pour la prochaine session

1. **Email groupe test ELISFA** (Préparation #2) — repris à la rentrée 2026
2. **Décider si on fait Sprint 1.1 + 1.2** ou si on saute à Sprint 2.1
3. **Première session test ELISFA** prévue Sprint 4.5 (~ semaine 11) → confirmer 5-10 personnes

**À bientôt sur Sprint 2.1 ! 🚀**

---

*Rétro générée le 2026-04-25, basée sur les commits réels (vérifiables via `git log v2-dev`).*
