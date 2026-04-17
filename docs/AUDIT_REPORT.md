# Rapport d'audit — Chatbot ELISFA

> Diagnostic technique réalisé le 16 avril 2026, la veille de la première présentation publique. Cadre : transition post-vibe-coding vers un système industriel stable.
>
> Auteur : Claude Code · Relecteur : Didier Delpeyrou

---

## TL;DR

Le site **fonctionne** et la démo est sécurisée. Mais l'architecture RAG reste un **faux RAG** (recherche par mots-clés, pas de vecteurs), avec **0 test automatisé**, **aucune sanitization** du contexte utilisateur, et une **température par défaut** (~1.0) qui favorise les dérivations. Rien de bloquant immédiat. Tout est corrigible sans tout reconstruire.

**Priorité 1 (après démo, semaine +1) :** injection prompt + temperature + tests ⟶ **risque juridique réel**.
**Priorité 2 (semaine +2-3) :** passer d'un scoring keyword à un vrai retrieval sémantique.
**Priorité 3 (mois +1-2) :** modulariser `app.py` (2981 lignes → core/ splitté).

---

## 1. Diagnostic — mécanismes de dérive observés

### 1.1 Dette technique structurelle ⚠️ MOYEN
- `app.py` : **2981 lignes, monolithe**. Routes Flask + RAG + prompts + escalade + logs + wizard + email + webhooks = tout mélangé.
- **82 erreurs ruff** dont :
  - `from config import * ` (ligne 21) → 63 × F405 "undefined name via star import" ⟶ masque la dépendance, casse le IDE
  - `math imported but unused` (ligne 5)
  - 4 × f-strings sans placeholder
  - 6 × `if cond: action` sur une ligne (E701) → illisible
  - 2 × variables non utilisées (`formation_type`, `e`)
  - `import` au milieu du fichier (ligne 17, 18, 21)
- **Duplication de prompts** : 4 variantes `SYSTEM_PROMPT_*` (≈ 400 lignes totales) partagent 80 % du contenu. Une modif = 4 endroits à synchroniser.
- Pas de séparation **infra / métier / IA**. Exemple : la fonction qui construit l'appel Claude contient aussi la logique d'escalade couleur, le logging, le post-traitement du wizard.

### 1.2 Instabilité RAG 🔴 CRITIQUE
Le système vendu comme "RAG" **n'en est pas un** au sens strict :

| Élément | État actuel | Attendu pour un vrai RAG |
|---|---|---|
| Embedding vectoriel | **Aucun** | sentence-transformers / OpenAI-ada / Voyage / Cohere |
| Store vectoriel | **Aucun** (JSON structuré) | Chroma / Qdrant / FAISS / pgvector |
| Chunking | **Aucun** (articles entiers, ≈300-500 mots) | Découpage sémantique 300-800 tokens |
| Scoring | **Keyword match simple** (+3 si token exact, +1 si substring) | Similarité cosinus + reranker |
| Seuil d'inclusion | **`score > 0`** (tout matche) | Threshold calibré (ex. > 0.7 cos) |
| Top-k | 5 hardcodé | Configurable, reranké |
| Re-ranking | Non | Cross-encoder (ms-marco-MiniLM…) |
| Citations vérifiées | Non | Validation post-génération |

**Conséquences pratiques :**
- Une question mal formulée (synonymes, paraphrase) rate les documents pertinents
- Le scoring retourne parfois 5 articles sans rapport sémantique avec la question
- Aucun garde-fou contre l'hallucination de citations inventées par Claude

### 1.3 Absence de cadre 🔴 CRITIQUE → CORRIGÉ PARTIELLEMENT CE SOIR
- Pas de `README.md` actualisé, pas de `CONTRIBUTING.md`, pas de règles d'architecture
- Pas de **spec** avant code : chaque modification a été faite "à vue"
- Aucun process de revue multi-niveaux
- **✅ Correctif livré ce soir :** `docs/agent.md` + `docs/AUDIT_REPORT.md` + `tests/rag_eval.py`

---

## 2. Risques classés par gravité

### 🔴 CRITIQUE (à traiter avant diffusion large)

| # | Risque | Fichier:ligne | Impact | Effort fix |
|---|---|---|---|---|
| R1 | **Injection prompt** : `user_context` (profil, historique) injecté brut dans le system prompt | `app.py:~1575` | Fuite du prompt système, exfiltration de logique métier | 2 h |
| R2 | **Hallucinations non détectées** : Claude invente des articles de loi / CCN inexistants sans alerte | `app.py:1709` (pas de post-check) | Conseil juridique erroné → responsabilité ELISFA | 1 jour |
| R3 | **Température par défaut (~1.0)** sur Claude → variance élevée sur tâche factuelle | `app.py:1709` | Réponses différentes pour même question | 5 min (fixer à 0.3) |
| R4 | **Aucun test automatisé** | global | Impossible de détecter une régression après refacto | 3 jours (setup + jeu complet) |
| R5 | **`from config import *`** | `app.py:21` | Dépendance invisible, 63 warnings, risque de renommage silencieux | 30 min |

### 🟠 MOYEN

| # | Risque | Impact | Effort |
|---|---|---|---|
| M1 | Scoring RAG keyword = faible rappel sur paraphrase | Réponses incomplètes sur questions formulées différemment | 2-3 jours (migration Chroma/FAISS + embeddings) |
| M2 | Monolithe `app.py` | Maintenance = éditer un fichier de 2981 lignes | 2-3 jours (split en `core/`) |
| M3 | CORS `*` | Quelqu'un peut embarquer le chatbot sur son site | 10 min |
| M4 | Pas de métriques RAG (precision, recall, hallucination rate) | On ne sait pas si la qualité se dégrade | Couvert par `rag_eval.py` livré ce soir |
| M5 | Rate limiting par IP seulement | Contournable via proxies | 1 jour (fingerprint + token) |

### 🟢 FAIBLE

| # | Risque | Impact | Effort |
|---|---|---|---|
| F1 | f-strings sans placeholder | Coquetterie | auto-fix ruff |
| F2 | `math` import inutilisé | Coquetterie | auto-fix ruff |
| F3 | Variables `e`, `formation_type` assignées mais inutilisées | Clutter | auto-fix ruff |
| F4 | `if x: action` sur une ligne | Lisibilité | 10 min |

---

## 3. Ce qui a été livré ce soir (non-régressif)

```
docs/
  ├── agent.md              ← Contrat de projet : architecture, conventions, règles RAG, sécurité
  └── AUDIT_REPORT.md       ← Ce rapport

tests/
  ├── __init__.py
  ├── rag_reference.json    ← 22 questions de référence (5 juridique + 5 RH + 5 formation + 5 gouv + 2 edge)
  └── rag_eval.py           ← Harness : lance les tests contre le serveur, produit un rapport JSON
```

**Utilisation immédiate :**
```bash
python tests/rag_eval.py --url https://felias-reseau-eli2026.duckdns.org
python tests/rag_eval.py --subset juridique --verbose
```

**Exit code :**
- `0` si taux de passage ≥ 80 %
- `1` sinon ⟶ intégrable en CI/CD

---

## 4. Plan d'action priorisé (après démo)

### Sprint 1 — Semaine +1 : sécuriser (2-3 j)

**Objectif : lever les 5 risques CRITIQUE avant toute nouvelle fonctionnalité.**

1. **Fixer la temperature à 0.3** (5 min) — `app.py:1709` ajouter `temperature=0.3` au `client.messages.create`
2. **Sanitization du `user_context`** (2 h) — fonction `escape_prompt_injection()` qui :
   - Balise le contenu utilisateur dans des tags dédiés (`<user_context>…</user_context>`)
   - Supprime les séquences suspectes : "ignore les instructions", "system:", "assistant:", balises XML non-user
   - Limite à 500 caractères
3. **Remplacer `from config import *`** par `import config` explicite (30 min) — 63 warnings éliminés, autocomplete restaurée
4. **Lancer `tests/rag_eval.py`** sur le serveur actuel pour établir la **baseline** (30 min)
5. **Corriger les auto-fixes ruff** (`ruff check --fix`) (10 min) — 8 erreurs triviales

**Livrables :** baseline métriques RAG, 0 erreur ruff critique, prompt injection testée.

### Sprint 2 — Semaines +2 à +3 : durcir le RAG (5-8 j)

**Objectif : passer du keyword-match au retrieval sémantique.**

1. **Renforcer le system prompt** (1 j) — insérer les clauses du `docs/agent.md §3.2` :
   - "Tu te fondes UNIQUEMENT sur les extraits fournis"
   - "Si l'information n'est pas trouvée : 'Je ne trouve pas cette information dans la base documentaire'"
   - "Ne complète JAMAIS avec des connaissances externes"
   - "Cite chaque affirmation avec sa source (n° d'article ou titre de fiche)"
2. **Ajouter une couche de validation post-réponse** (1-2 j) :
   - Parser les citations produites (regex sur `L1234-5`, `Article 18 CCN`, etc.)
   - Vérifier qu'elles existent dans `base_*.json`
   - Si citation inventée : remplacer par `[CITATION NON VÉRIFIÉE]` + drapeau orange automatique
3. **Migrer vers un vrai vector store** (3-5 j) :
   - Dépendance : `chromadb` ou `faiss-cpu` + `sentence-transformers`
   - Modèle d'embedding : `paraphrase-multilingual-MiniLM-L12-v2` (384 dim, gratuit, rapide, français OK) ou **Voyage AI fr** si budget
   - Re-chunking des JSON : découpage par paragraphe (300-500 tokens), préserver métadonnées
   - Script d'ingestion versionnable (`ingestion/index_build.py`)
   - Score cosinus > 0.5 comme seuil minimal
4. **Métriques continues** : intégrer `rag_eval.py` en GitHub Actions (ou cron) — bloquer le déploiement si pass rate < 80 %

### Sprint 3 — Mois +1 à +2 : modulariser (5-10 j)

**Objectif : passer de monolithe `app.py` à `core/` séparé.**

Découpe cible (cf. `docs/agent.md §5.3`) :
- `core/rag.py` : retrieval, scoring, reranking (~300 lignes)
- `core/llm.py` : client Claude, retry, timeout, sanitization (~200 lignes)
- `core/prompts.py` : tous les `SYSTEM_PROMPT_*` centralisés + templates (~500 lignes)
- `core/escalation.py` : logique vert/orange/rouge (~100 lignes)
- `core/logging.py` : interactions + métriques (~150 lignes)
- `ingestion/validate.py` : validation JSON pré-commit
- `app.py` : routes Flask uniquement (~500 lignes)

**Approche progressive recommandée** : extraire 1 module à la fois, garder les tests verts entre chaque step.

---

## 5. Ce que je vous propose de NE PAS FAIRE

- ❌ **Réécrire from scratch** — le site fonctionne, les utilisateurs vont s'y projeter, la mémoire utilisateur est dans le code actuel
- ❌ **Changer de modèle** (Sonnet/Opus) avant d'avoir mesuré la qualité actuelle avec `rag_eval.py` — 80 % des problèmes ne viennent pas du modèle mais du prompt/contexte
- ❌ **Introduire une DB relationnelle** tant que tout tient en JSON versionné Git — la complexité ajoutée est rarement justifiée
- ❌ **Multiplier les sous-agents IA** (reviewer + safety + fact-checker) avant d'avoir des tests. Chaque couche ajoute de la latence et du coût — il faut mesurer d'abord

---

## 6. Questions à arbitrer (arbitrage produit)

Avant le sprint 2, j'aurai besoin d'une décision sur :

1. **Budget embeddings** : on reste sur du local gratuit (MiniLM) ou on paie Voyage/OpenAI pour une meilleure qualité française ?
2. **Où stocker le vector store ?** Git (si < 50 Mo) ou volume Docker persistant ?
3. **Réponse en cas de trou documentaire** : Claude dit explicitement "pas trouvé dans la base" OU tente une réponse générique avec un disclaimer très fort ? (aujourd'hui = 2e option, le 1er option est plus sûr juridiquement)
4. **Qui valide les changements de prompt ?** Didier seul OU passage obligatoire par le pôle juridique ELISFA pour toute modif des `SYSTEM_PROMPT_*` ?
5. **CI/CD** : on met en place GitHub Actions pour faire tourner `rag_eval.py` à chaque push ? (gratuit pour repo privé ≤ 2 000 min/mois)

---

## 7. Changelog

| Date | Action | Effet |
|---|---|---|
| 2026-04-16 23h | Création `docs/agent.md` | Règles projet documentées |
| 2026-04-16 23h | Création `docs/AUDIT_REPORT.md` | Ce rapport |
| 2026-04-16 23h | Création `tests/rag_eval.py` + 22 questions de référence | Harness d'éval opérationnel |
| 2026-04-16 23h | Correction dark mode welcome-card | Cohérence visuelle |
| 2026-04-16 23h | Responsive mobile prompt bar | UX mobile corrigée |
| À faire | Baseline `rag_eval.py` sur production | Ligne de départ métriques |
| À faire | Sprint 1 (sécurisation) | 5 risques CRITIQUE levés |
