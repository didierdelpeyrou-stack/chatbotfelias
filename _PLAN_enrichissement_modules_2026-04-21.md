# Plan d'enrichissement consolidé — Bases de connaissances ELISFA
**Date :** 2026-04-21
**Portée :** dashboard récapitulatif des 4 modules ELISFA (juridique, formation, rh, gouvernance), état actuel, gaps identifiés, priorisation d'action.

Ce document consolide les findings des audits produits le 2026-04-21 :
- `_AUDIT_RAG_performance_2026-04-21.md` — architecture RAG & limites (R1-R12)
- `_LIENS_gouvernance_associations_gouv_2026-04-21.md` — enrichissement 4 nouveaux thèmes + 30 liens guides pratiques
- `_LIENS_formation_officiel_2026-04-21.md` — injection de 110-130 URLs sur 43 articles (0 % → 100 %)

---

## 1. État des 4 modules (2026-04-21)

| Module | Articles | Thèmes | Couverture liens | URLs/art | Poids | Fiches PDF | Niveaux (vert/orange/rouge) | Escalade | Millésimes 2026 |
|---|---|---|---|---|---|---|---|---|---|
| **juridique** | 92 | 21 | **100 %** | 2.08 | 316 KB | 16 | ✅ (8/8/5) | ✅ | 23 |
| **formation** | 43 | 15 | **0 %** | 0.00 | 116 KB | ? | ❌ | ❌ | 84 (saturé) |
| **rh** | 11 | 5 | 100 % | 2.91 | 41 KB | ? | ❌ | ❌ | ~10 |
| **gouvernance** | 12 | 5 | 100 % | 3.17 | 46 KB | 12 | ❌ | ❌ | ~15 |

**Constats marquants :**
1. **Juridique** est la base la plus mature sur tous les axes (volume, liens, niveaux, escalade). Doit servir de **schéma de référence** pour les 3 autres.
2. **Formation** a un paradoxe : c'est la deuxième base en volume (116 KB) mais la seule avec 0 % de liens sortants. Gap « invisible » quand on lit le contenu, très visible quand le frontend tente d'afficher les `liens`.
3. **RH** est sous-dotée en contenu (11 articles) par rapport aux topics couverts (5 thèmes RH/QVCT/GPEC/CSE/recrutement — chacun mériterait 5-8 articles).
4. **Gouvernance** couvre bien son périmètre associatif de base mais **n'a aucun thème sur le financement public, le RGPD, ou la dissolution** — trous majeurs pour un chatbot employeur associatif.

---

## 2. Findings transverses (du `_AUDIT_RAG_performance`)

| # | Limite identifiée | Gravité | Correctif proposé |
|---|---|---|---|
| L1 | Pas de seuil `hors_corpus` sur les scores TF-IDF | 🔴 | **R1** — seuil SCORE_MIN_HORS_CORPUS = 2.5 |
| L2 | Pas de normalisation des scores entre articles | 🟠 | **R2** — score normalisé = score / max_score_possible_article |
| L3 | Pas de rerank sémantique (contrairement à Félias avec BGE-m3) | 🟠 | **R3** — rerank optionnel via Cohere ou cross-encoder |
| L4 | Matching substring bruyant (`1.0 * tf` sans idf quand `tf` faible) | 🟡 | **R4** — filtrer substring si token < 3 caractères ou dans stopwords |
| L5 | Mots-clés curés insuffisants (10-13 par article) pour couvrir la variabilité des questions | 🟠 | **R5** — expansion auto via WordNet ou Spacy + vérification humaine |
| L6 | Pas de rerank sur les résultats TF-IDF top-k | 🟠 | **R6** — rerank BM25 ou semantic top-20 → top-5 |
| L7 | Pas de contrainte de verbatim dans le prompt (risque de réécriture) | 🔴 | **R11** — prompt anti-hallucination + citations obligatoires |

**Phase 1 minimale (R1 + R11) = 3 j dev** et résout 80 % du gap véracité/perspicacité.

---

## 3. Gaps par module — menu d'actions prioritaires

### 🟦 Module `formation` (priorité 1)

**Problème :** 0 % de couverture liens, rupture d'homogénéité avec les 3 autres bases.

**Actions :**
| Action | Effort | Gain | Statut |
|---|---|---|---|
| **A-FORM-1** : Injecter ~110 URLs (Légifrance + travail-emploi + Uniformation + moncompteformation + etc.) sur les 43 articles | 4 j | 0 % → 100 % couverture liens | 📋 Spécifié dans `_LIENS_formation_officiel_*` |
| **A-FORM-2** : Ajouter 3 thèmes (`transition_ecologique_formation`, `sanctions_non_formation`, `formation_elus_cse`) | 2 j | +5-7 articles | 📋 Spécifié |
| **A-FORM-3** : Ajouter niveau (vert/orange/rouge) et escalade sur les 43 articles | 1 j | Parité avec juridique | ❌ |
| **A-FORM-4** : Nettoyer les 84 millésimes 2026 pour éviter la péremption rapide | 0.5 j | Longévité base | ❌ |

### 🟩 Module `gouvernance` (priorité 2)

**Problème :** couverture thématique incomplète, absence de thèmes critiques (financement, RGPD, dissolution).

**Actions :**
| Action | Effort | Gain | Statut |
|---|---|---|---|
| **A-GOUV-1** : Ajouter 4 nouveaux thèmes (`financement_public` 5 art, `numerique_rgpd` 3 art, `egalite_gouvernance` 1 art, `dissolution` 3 art) | 3 j | +12 articles (×2 volume) | 📋 Spécifié dans `_LIENS_gouvernance_associations_gouv_*` |
| **A-GOUV-2** : Enrichir les 5 thèmes existants avec +7 liens (cadre_legal), +3 (instances), +6 (benevolat), +4 (patronat), +1 (doctrine) | 1 j | 30 nouveaux liens qualifiés | 📋 Spécifié |
| **A-GOUV-3** : Ajouter niveau + escalade | 0.5 j | Parité juridique | ❌ |
| **A-GOUV-4** : Ajouter `fiches_pratiques` PDF (absentes pour la plupart des articles) | 1 j | 0 % → 80 % | 📋 Spécifié |

### 🟧 Module `rh` (priorité 3)

**Problème :** volume insuffisant (11 articles pour 5 thèmes) + recouvrement significatif avec `juridique`.

**Actions :**
| Action | Effort | Gain | Statut |
|---|---|---|---|
| **A-RH-1** : Densifier chaque thème (de 2 → 5-8 articles) : +25 articles viser 35-40 au total | 5 j | +×3 volume | ❌ |
| **A-RH-2** : Définir le périmètre RH vs juridique (pratiques de management ≠ obligations légales). Éviter les doublons. | 1 j | Routing mieux défini | 🟡 Documenté ici |
| **A-RH-3** : Nouveaux thèmes à prévoir : `teletravail_hybride` (1-2 art), `remuneration_globale_nvo_bareme_2024` (2-3 art), `handicap_qvct` (2 art) | 2 j | +5 articles | ❌ |
| **A-RH-4** : Ajouter niveau + escalade | 0.5 j | Parité juridique | ❌ |

⚠️ **Recouvrement RH ↔ juridique à arbitrer** : recrutement (rh-01) ↔ contrat_travail (juridique), entretiens (rh-02) ↔ formation/oblig-02, QVCT (rh-04) ↔ sante_securite (juridique), CSE (rh-05) ↔ cse_irp (juridique), négociation accord (rh-11) ↔ droit_syndical (juridique). **Rôle du routage CRITIQUE** : un même question type peut donner des réponses contradictoires selon le module choisi.

### 🟥 Module `juridique` (priorité 4 — maintenance)

**Problème :** aucun gap majeur. Base mature. Maintenance recommandée.

**Actions :**
| Action | Effort | Gain | Statut |
|---|---|---|---|
| **A-JUR-1** : Audit de validité des 191 URLs (certaines LEGIARTI profondes peuvent avoir bougé depuis 2024) | 1 j | URLs sans 404 | ❌ |
| **A-JUR-2** : Ajout des avenants 2026 (si signés entre avril et décembre 2026) | ad hoc | Actualité | 🕐 En attente |
| **A-JUR-3** : Étendre les `escalade` au-delà de `niveau=rouge` (actuellement seulement 5 articles) | 1 j | Escalade sur 15-20 articles | ❌ |

---

## 4. Findings architecture RAG — rappels priorisés

| # | Reco | Impact véracité | Impact vélocité | Effort | Phase |
|---|---|---|---|---|---|
| **R1** | Seuil hors_corpus | 🔴🔴 élevé | = | 1 j | **Phase 1** |
| **R11** | Prompt anti-hallucination (verbatim obligatoire) | 🔴🔴 élevé | = | 2 j | **Phase 1** |
| **R6** | Rerank top-20 → top-5 | 🟠 moyen | -100 ms | 2 j | Phase 2 |
| **R4** | Filtrer matching substring bruyant | 🟡 faible | = | 0.5 j | Phase 2 |
| **R2** | Normalisation scores | 🟡 faible | = | 1 j | Phase 3 |
| **R5** | Expansion mots-clés | 🟠 moyen | = | 3 j | Phase 3 |
| **R3** | Rerank sémantique (Cohere/cross-encoder) | 🔴 élevé | +150-300 ms | 2 j | Phase 4 |

**Recommandation** : **Phase 1 (R1 + R11) = 3 j dev** doit être fait **AVANT** d'enrichir le contenu (A-FORM-1, A-GOUV-1, etc.). Sinon, le bruit RAG contaminera le nouveau contenu dès son injection.

---

## 5. Séquencement recommandé — sprint d'avril-mai 2026

### Sprint 1 (semaine 1, 5 j dev) — Blindage véracité
- **J1-J2** : R1 (seuil hors_corpus) + tests sur questions hors-sujet (prédictif vs observé)
- **J3-J4** : R11 (prompt anti-hallucination) + reformulation système prompt + tests adversarials
- **J5** : R4 (filtre substring bruyant — bonus rapide)

**Livrable** : commit `chore(rag): add hors_corpus threshold + verbatim prompt` + tests unitaires + canary déployé en préprod ELISFA.

### Sprint 2 (semaines 2-3, 10 j dev) — Injection liens formation
- **S2.1 (3 j)** : implémentation patch JSON formation (A-FORM-1 Phase 1 : 110 URLs Légifrance/travail-emploi/CPF)
- **S2.2 (1 j)** : validation HEAD HTTP des 110 URLs + correction 404
- **S2.3 (4 j)** : injection Phase 2 + 3 (sources branche CPNEF/ALISFA + jurisprudence)
- **S2.4 (2 j)** : tests E2E front (affichage liens) + déploiement

**Livrable** : `base_formation.json v1.1` avec 100 % couverture liens, déployé en prod ELISFA.

### Sprint 3 (semaines 4-5, 10 j dev) — Extension gouvernance + RH
- **S3.1 (3 j)** : A-GOUV-1 (4 nouveaux thèmes, 12 articles)
- **S3.2 (1 j)** : A-GOUV-2 (30 liens sur les 5 thèmes existants)
- **S3.3 (5 j)** : A-RH-1 (densification 11 → 35 articles)
- **S3.4 (1 j)** : A-RH-2 (arbitrage périmètre RH vs juridique — document de spec routage)

**Livrable** : `base_gouvernance.json v2.0` + `base_rh.json v2.0` déployés.

### Sprint 4 (semaine 6, 5 j dev) — Parité schéma + maintenance juridique
- **J1-J3** : ajouter niveau + escalade sur formation, rh, gouvernance (A-FORM-3, A-RH-4, A-GOUV-3)
- **J4** : A-JUR-1 (audit URLs juridique)
- **J5** : A-FORM-4 (nettoyage millésimes 2026 saturés)

**Livrable** : schéma uniforme cross-modules + commit `feat(kb): unify schema across modules`.

### Sprint 5 (semaine 7, optionnel) — Rerank sémantique
- Décision go/no-go selon mesures de véracité post-Sprint 1-4.
- Si go : R3 (2 j) + bench latence (2 j) + tests A/B (1 j).

---

## 6. Coûts et gains synthétiques

| Sprint | Effort (j dev) | Véracité | Vélocité | Couverture | Commentaire |
|---|---|---|---|---|---|
| Sprint 1 | 5 | +++ | = | = | **Must-do avant tout enrichissement** |
| Sprint 2 | 10 | + | = | formation 0→100% | Visible utilisateur |
| Sprint 3 | 10 | ++ | = | gouvernance+100 %, rh+×3 | Volume × 1.4 |
| Sprint 4 | 5 | + | = | parité schéma | Qualité interne |
| Sprint 5 | 5 | ++ | –100 ms | = | Option tardive |
| **Total** | **35 j** | **+++++++** | **= (ou -100 ms)** | **+~50 articles, +~250 URLs** | **~7 semaines dev** |

---

## 7. Hypothèses de réorientation (du `_AUDIT_velocite_veracite_*`) — rappel

Les 5 hypothèses de réorientation Félias ↔ ELISFA restent applicables **en parallèle** du plan ci-dessus :

| # | Hypothèse | Cible | Effort | Phase |
|---|---|---|---|---|
| **HYPO-1** | ONNX int8 BGE-m3 (Félias vélocité sans compromis véracité) | Félias | 5-7 j | Indépendant |
| HYPO-2 | Fusion Félias + ELISFA sous un même backend FastAPI | Unification | 15-20 j | Long terme |
| **HYPO-3** | Claude Haiku rerank (remplacer BGE-m3 par un appel LLM) | Félias | 3 j | Expérimentation |
| HYPO-4 | Migration ELISFA vers SQLite-vec + embeddings | ELISFA | 10 j | Lourd |
| HYPO-5 | ~~Céder juridique à ELISFA~~ — **ABANDONNÉE** (ELISFA est fantaisiste, Félias reste plus rigoureux) | — | — | — |

---

## 8. Résumé — trois décisions immédiates à prendre

1. **Valider la Phase 1 RAG (R1 + R11)** avant tout enrichissement de contenu. Sans ça, le nouveau contenu amplifiera le bruit existant.
2. **Prioriser `formation` (A-FORM-1)** sur les enrichissements, car c'est le seul module avec 0 % de couverture liens et l'impact est immédiatement visible utilisateur.
3. **Arbitrer le périmètre RH vs juridique** (A-RH-2) avant de densifier RH. Densifier sans arbitrer créerait 25 articles qui doublonneraient juridique et polluerait le routage.

---

**Fin du plan consolidé.** Les 3 deliverables produits aujourd'hui (_AUDIT_RAG_performance, _LIENS_gouvernance, _LIENS_formation) sont autoportants et directement exploitables par un développeur sans contexte supplémentaire.
