# DEVIS — Développement Chatbot Juridique ELISFA (V1 + V2)

**Devis n° :** 2026-001
**Date :** 25 avril 2026
**Validité :** 60 jours

---

## Prestataire

> _À compléter avec tes coordonnées :_
- **Nom / Raison sociale :** _[à compléter]_
- **Statut juridique :** _[Auto-entrepreneur / EI / EURL / SASU / association]_
- **N° SIREN :** _[à compléter]_
- **TVA :** _[Franchise en base / Assujetti — à préciser]_
- **Adresse :** _[à compléter]_
- **Email / Téléphone :** _[à compléter]_

## Client

- **Nom :** ELISFA — Employeurs du Lien Social et FAmilial
- **Statut :** Syndicat employeur de la branche professionnelle ALISFA
- **Adresse :** _[à compléter avec l'adresse postale du siège]_
- **Référent projet :** _[Nom du référent ELISFA]_

---

## 1. Objet de la prestation

Conception, développement et déploiement d'un **assistant juridique conversationnel** (chatbot) pour les structures adhérentes à la branche ALISFA, articulé en deux temps :

- **V1 (production)** : Application Flask/Python avec moteur RAG TF-IDF, intégration Claude (Anthropic), interface web responsive, accessible sur `https://felias-reseau-eli2026.duckdns.org`.
- **V2 (staging puis cutover)** : Refonte complète sur stack FastAPI/Pydantic v2 avec amélioration de la fiabilité (+56 points de score sur le benchmark interne 50 questions), streaming temps réel, observabilité Prometheus, cible de déploiement `https://felias.duckdns.org`.

Le projet inclut **4 modules de connaissances** (juridique CCN ALISFA, formation, RH, gouvernance), un **système d'escalade** vert/orange/rouge vers le pôle juridique, et un **dispositif d'enrichissement éditorial 2026** sur les barèmes de financement formation (PDF CPNEF du 13 mars 2026).

---

## 2. Périmètre fonctionnel livré

### 2.1 Application V1 (en production)

| Composant | Description | Statut |
|---|---|---|
| Backend Flask + Gunicorn | API REST `/api/ask`, `/api/feedback`, `/api/rdv`, `/api/appels`, `/admin` | ✅ |
| Streaming SSE V1 | Endpoint `/api/ask/stream` — premier token <1s vs 8-12s en JSON | ✅ |
| Frontend SPA single-file | 8 331 lignes — chat, modules, debug panel, historique, export PDF | ✅ |
| Moteur RAG TF-IDF | Index inversé, score normalisé, seuil hors_corpus | ✅ |
| Intégration Claude (Anthropic) | Wrapper avec retry, prompt caching ephemeral, logging structuré | ✅ |
| Sécurité | Rate limiting, ADMIN_PASS_HASH bcrypt, scrub des secrets | ✅ |
| Observabilité | Logs JSONL structurés (5 events) + Sentry conditionnel + endpoint test | ✅ |
| Validation Pydantic | 5 modèles de requêtes (`AskRequest`, `RdvRequest`, `AppelRequest`, `EmailJuristeRequest`, `FeedbackRequest`) | ✅ |
| UX Phase 3 — Historique | 10 dernières questions en localStorage, FAB flottant | ✅ |
| UX Phase 4 — Export PDF | `window.print()` + `@media print`, header/footer dynamique | ✅ |
| **URL de production** | https://felias-reseau-eli2026.duckdns.org | en ligne |

### 2.2 Application V2 (en staging — déploiement à finaliser)

| Composant | Description | Statut |
|---|---|---|
| Scaffold FastAPI/Uvicorn | App factory, lifespan async, settings Pydantic-Settings | ✅ |
| Endpoints `/healthz`, `/readyz`, `/docs`, `/metrics` | Production-ready | ✅ |
| Moteur RAG TF-IDF V2 | Tokenizer FR avec stopwords, score normalisé, MIN_TOKEN_LEN=3 | ✅ |
| Schémas Pydantic v2 stricts | `KnowledgeBase`, `Theme`, `Article`, `Reponse`, `Lien`, `Revision` | ✅ |
| KBStore avec hot-reload | Détection mtime des 4 KB, `asyncio.Lock` par module | ✅ |
| LLM wrapper Anthropic async | Retry avec backoff, R11 (citations verbatim), erreurs typées 401/429/502/504 | ✅ |
| Endpoint `/api/ask` + SSE `/api/ask/stream` | Streaming natif `client.messages.stream()` | ✅ |
| 5 métriques Prometheus | `requests_total`, `rag_score`, `hors_corpus_total`, `request_latency`, `claude_tokens` | ✅ |
| Endpoint feedback `/api/feedback` + stats | 👍/👎, agrégation par module, JSONL persisté | ✅ |
| Image Docker multi-stage | ~180 MB final, USER non-root, HEALTHCHECK | ✅ |
| Benchmark V1 vs V2 | 50 questions corpus, évaluateur rule-based, **V2 = 74 % vs V1 = 18 %** (+56 pts) | ✅ |
| Artefacts staging | Compose, nginx (HTTPS, SSE proxy_buffering off), runbook, smoke tests | ✅ |
| Migration KB V1 → V2 | Script idempotent, validation Pydantic stricte, 158 articles enrichis | ✅ |
| **URL de staging cible** | https://felias.duckdns.org | à déployer |

### 2.3 Bases de connaissances (V1 et V2)

| Module | Articles V1 | Thèmes | Articles V2 enrichis (Sprint 5.2-data) | Total cible |
|---|---:|---:|---:|---:|
| Juridique (CCN ALISFA) | 92 | 21 | inchangé | 92 |
| Formation | 43 | 15 | + 34 articles (financement 2026, fiches métiers, fonctions réglementaires) → cible ~120 | 120 |
| RH | 11 | 5 | inchangé | 11 |
| Gouvernance | 12 | 5 | inchangé | 12 |
| **Total** | **158** | **46** | **+ 34 livrés / + ~64 planifiés** | **~235** |

### 2.4 Documentation et qualité

- **Documentation** : `DEPLOYMENT.md` (V1), `TROUBLESHOOTING.md`, `v2/STAGING.md` (runbook 10 étapes), `v2/test_session/` (5 fichiers : protocole, scénarios, formulaire, dashboard, email d'invitation), `docs/RETRO_SPRINT_0.md`
- **Tests automatisés** : **424 tests** (243 V1 + 181 V2) — pytest + pytest-asyncio + pytest-cov
- **CI/CD** : GitHub Actions — pytest Python 3.11/3.12 + ruff + Docker build (V1 + V2), pre-commit hooks (9 vérifications)
- **Audits** intégrés au repo : audit RAG performance, plan d'enrichissement modules, liens formation officiel, liens gouvernance associations.gouv.fr

---

## 3. Détail du travail réalisé — chronologie par sprint

### Bloc préliminaire (V1 — réalisé avant le 17 avril 2026)
Reprise du chatbot V1 existant, mise en condition pour la suite : refactoring, sécurisation des paiements admin, alignement CI.

### Bloc A — Stabilisation V1 (Sprint 0.1 → 0.5 + 1.1 + 1.2)
Cible : V1 stable, testée, documentée, observable.

| Sprint | Livrable | Commit |
|---|---|---|
| 0.1 | 16 améliorations UX/télémétrie (banner, layout 1600px, Cmd+K/L, debug, …) | ec20819 |
| 0.2 | CI/CD étendu à v2-dev + pre-commit hooks (9 hooks) | 72715c7 |
| 0.3 | +47 tests, coverage 71 % → 74 % | eced1f3 |
| 0.4 | Logging structuré JSONL aux 5 points clés | bcc5699 |
| 0.5 | Docs DEPLOYMENT + TROUBLESHOOTING + Retro | 23b6f10 |
| 1.1 | Refactoring `_error_response` + `_validate_request` (28 sites uniformisés) | 8cb3fdc |
| 1.2 | Endpoint `/api/sentry/test` admin-only + docs Sentry alerts | 8cb3fdc |

### Bloc V2 — Refonte FastAPI (Sprint 2.1 → 3.4)
Cible : nouvelle stack production-ready.

| Sprint | Livrable | Commit |
|---|---|---|
| 2.1 | Scaffold FastAPI + lifespan + healthchecks | 091c235 |
| 2.2 | RAG TF-IDF + seuil hors_corpus + score normalisé | a65f295 |
| 2.3 | KB Pydantic models + validation stricte au boot | 83a8b14 |
| 2.4 | LLM wrapper Anthropic async + R11 + prompt caching | 4f9d195 |
| 3.1 | KBStore + hot-reload mtime des 4 bases | 1b1a996 |
| 3.2 | Endpoint `/api/ask` + `/api/ask/stream` SSE — V2 fonctionnel bout-en-bout | ed7dc37 |
| 3.3 | 5 métriques Prometheus + endpoint `/metrics` | d6e02b7 + a17718a |
| 3.4 | Docker multi-stage + docker-compose dev | b9d39d5 |

### Bloc B prep — Validation V2 (Sprint 4.1 → 4.5)
Cible : preuve que V2 > V1 + préparation déploiement.

| Sprint | Livrable | Commit |
|---|---|---|
| 4.1 | Corpus benchmark 50 questions + évaluateur rule-based | a2250fb |
| 4.2 | **Benchmark V1 vs V2 — V2 = 74 % vs V1 = 18 % (+56 pts)** | 2d7ce59 |
| 4.3 | Feedback collection 👍/👎 + stats agrégées | 0ffd1c2 |
| 4.4 | Artefacts deploy staging (compose, nginx, runbook 10 étapes, smoke tests) | 2b6b781 |
| 4.5 | Protocole + scénarios + invitation + formulaire session test ELISFA | db92257 |

### Bloc UX V1 + Sprint 5.x (en cours)
Cible : ergonomie V1 finalisée + KB V2 enrichie + cible staging fixée.

| Sprint | Livrable | Commit |
|---|---|---|
| Phase 3 | Historique 10 dernières questions (localStorage) | 881361d |
| Phase 4 pt 1 | Export PDF de la conversation (window.print + @media print) | 95275e2 |
| Phase 4 pt 2 | Streaming SSE V1 + frontend progressif | 895b466 |
| Phase 4 fix | Fix PDF Q+R sur même page + bandeau scintillement | 8667ed3 |
| 5.1 | Migration KB V1→V2 + 158 articles enrichis (niveau/escalade/revision) | fa28d10 |
| 5.2-data | Cible staging `felias.duckdns.org` + KB_DATA_DIR=/app/data/v2 | 90c1c35 |
| 5.2-data F2-F3 | **34 articles JSON validés Pydantic V2** (financement 2026 CPNEF) — drafts | en cours |

### Bloc 5.2-data restant (en cours)
- F4 — 25 articles métiers GPEC (depuis 25 fiches PDF ALISFA + Excel matrice)
- F5 — 27 articles fonctions réglementaires (CNAF, Code action sociale, EAJE/ALSH, RSAI, médiation, SST...) + 6 contrats aidés
- F6 — ~12 articles intentions directeur (scénarios opérationnels)

### Sprints à venir (planifiés)
- 5.3 — Wizard financement (back V2 + front) — 6 axes
- 5.4 — Interface admin KB (upload/download/delete + auth)
- 5.5 — Blue-green deploy infra
- 6.x — Légifrance API + roulage interne ELISFA + fixes
- 7.x — CUTOVER (canary 10 % → 50 % → 100 %)
- 8.x — Monitoring prod + docs + plan T1

---

## 4. Indicateurs techniques

| Indicateur | Valeur |
|---|---|
| Période de développement intensif | 17 avril → 25 avril 2026 (8 jours) + travail antérieur |
| Commits git | **32** (branche v2-dev) |
| Lignes de code V1 (`app.py` + templates + modules) | **13 693** |
| Lignes de code V2 (app/ + tests/) | **4 548** |
| Tests automatisés | **424** (243 V1 + 181 V2) |
| Articles KB livrés | **158** (V1) + **34** drafts validés Pydantic V2 (Sprint 5.2-data) |
| Diplômes RNCP cartographiés | 12 (table CPNEF p.26) |
| Fiches métiers ALISFA intégrées | 25 (PDF + Excel GPEC) |
| Documentation | ~30 fichiers Markdown |
| Pages PDF source CPNEF traitées | 28 (règles financement 2026-03-13) |

---

## 5. Estimation du temps passé

> **À ajuster avec ton estimation réelle.** Voici 3 fourchettes selon l'intensité réelle :

| Hypothèse | Heures | Jours-équivalents (8h) | Commentaire |
|---|---:|---:|---|
| **Basse** | 60 h | 7,5 j | Estimation conservatrice — sessions courtes |
| **Moyenne** | 90 h | 11,5 j | Réaliste compte tenu du volume livré |
| **Haute** | 120 h | 15 j | Si on inclut audits, recherches, formations parallèles |

**Indicateurs de validation** :
- 32 commits sur 8 jours = ~4 commits/jour ouvré → activité soutenue
- ~18 000 LOC produites + 192 articles KB enrichis → volume conséquent
- 424 tests automatisés écrits → qualité industrielle

---

## 6. Tarifs proposés

> **À ajuster avec ton tarif cible.** Voici 3 grilles de référence pour le secteur ESS / associatif :

| Profil | Tarif jour HT | Tarif horaire HT | Justification |
|---|---:|---:|---|
| **Auto-entrepreneur dev ESS** | 350 € | 44 € | Tarif planché secteur associatif |
| **Freelance dev senior ESS** | 500 € | 63 € | Profil expérimenté (recommandé) |
| **Prestataire dev senior + IA** | 650 € | 81 € | Spécialisation Anthropic / RAG / FastAPI |

### Calcul selon hypothèse moyenne (90 h)

| Tarif | Total HT (90 h) |
|---:|---:|
| 44 €/h | **3 960 €** |
| 63 €/h | **5 670 €** |
| 81 €/h | **7 290 €** |

### Calcul selon hypothèse haute (120 h)

| Tarif | Total HT (120 h) |
|---:|---:|
| 44 €/h | **5 280 €** |
| 63 €/h | **7 560 €** |
| 81 €/h | **9 720 €** |

---

## 7. Frais techniques refacturables

| Poste | Estimation 8 jours | Statut |
|---|---:|---|
| API Anthropic Claude (Haiku 4.5 + Opus 4.7) — dev intensif | ~150 € | sur factures Anthropic à conserver |
| VPS Hostinger (existant V1) | ~5 € (prorata) | déjà en place |
| Domaines DuckDNS | 0 € | gratuit |
| Certificats Let's Encrypt | 0 € | gratuit |
| GitHub Actions CI | 0 € | gratuit (compte public ou inclus Free) |
| **Sous-total frais techniques** | **~155 € HT** | refacturables au coût réel sur justificatifs |

> Ces montants sont indicatifs. Prévoir de joindre les factures Anthropic au devis final pour transparence.

---

## 8. Ce qui n'est PAS inclus (hors devis actuel)

Si tu veux les chiffrer en option, voici les sprints planifiés mais non encore réalisés :

| Sprint | Description | Estimation |
|---|---|---:|
| 5.2-data F4 | 25 articles métiers GPEC | 8-12 h |
| 5.2-data F5 | 27 articles fonctions réglementaires + 6 contrats aidés | 12-16 h |
| 5.2-data F6 | ~12 articles intentions directeur | 6-8 h |
| 5.3 | Wizard financement back V2 + front | 8-12 h |
| 5.4 | Interface admin KB (upload/download/delete + auth) | 10-14 h |
| 5.5 | Blue-green deploy infra | 6-10 h |
| 6.1 | Intégration API Légifrance | 10-14 h |
| 6.2 | Enrichissement liens 20 articles juridique | 6-8 h |
| 6.3 | Fixes bugs roulage interne | 4-8 h |
| 7.1-7.4 | Procédure CUTOVER (canary 10 % → 50 % → 100 %) | 12-16 h |
| 8.1-8.3 | Monitoring prod + docs + plan T1 | 8-12 h |
| **Total reste à faire** | | **~90-130 h** soit ~12-17 jours |

---

## 9. Conditions

- **Modalités de paiement** : _[à compléter — ex. 30 % à la commande, 70 % à la livraison]_
- **Délai de paiement** : _[à compléter — ex. 30 jours fin de mois]_
- **Acompte** : _[à compléter selon politique]_
- **Propriété intellectuelle** : code livré sous licence cédée à ELISFA pour usage interne. Le code source reste hébergé sur GitHub (`0xZ1337/chatbot_elisfa`) avec accès collaborateur ELISFA.
- **Garantie** : 60 jours sur les bugs bloquants identifiés à compter de la livraison V1 / V2 staging.
- **Maintenance évolutive** : non incluse dans ce devis — facturable au tarif jour HT mentionné §6.
- **Confidentialité** : engagement de confidentialité sur les données métiers ALISFA traitées.

---

## 10. Récapitulatif financier proposé

> **À choisir parmi les options selon hypothèse de temps × tarif retenue** :

### Option A — minimale (60 h × 350 €/j ÷ 8) + frais
- Prestation : 60 × 44 € = **2 640 € HT**
- Frais techniques : **155 € HT**
- **Total HT : 2 795 €**
- TVA : selon ton statut (0 € si franchise, 559 € si TVA 20 %)
- **Total TTC : 2 795 € (franchise) ou 3 354 € (TVA 20 %)**

### Option B — recommandée (90 h × 500 €/j ÷ 8) + frais
- Prestation : 90 × 63 € = **5 670 € HT**
- Frais techniques : **155 € HT**
- **Total HT : 5 825 €**
- TVA : 0 € (franchise) ou 1 165 € (TVA 20 %)
- **Total TTC : 5 825 € (franchise) ou 6 990 € (TVA 20 %)**

### Option C — haute (120 h × 650 €/j ÷ 8) + frais
- Prestation : 120 × 81 € = **9 720 € HT**
- Frais techniques : **155 € HT**
- **Total HT : 9 875 €**
- TVA : 0 € (franchise) ou 1 975 € (TVA 20 %)
- **Total TTC : 9 875 € (franchise) ou 11 850 € (TVA 20 %)**

---

## Annexes

- Lien repo GitHub : https://github.com/0xZ1337/chatbot_elisfa (branche `v2-dev`)
- URL prod V1 : https://felias-reseau-eli2026.duckdns.org
- URL staging V2 cible : https://felias.duckdns.org
- Documentation technique : `DEPLOYMENT.md`, `v2/STAGING.md`, `v2/README.md`
- Audits intégrés : `_AUDIT_RAG_performance_2026-04-21.md`, `_PLAN_enrichissement_modules_2026-04-21.md`

---

_Devis établi le 25 avril 2026, valable 60 jours._
