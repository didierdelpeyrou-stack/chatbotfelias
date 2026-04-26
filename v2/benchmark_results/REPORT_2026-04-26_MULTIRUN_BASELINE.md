# Sprint 5.2-tune systémique — Baseline statistique multi-run

**Date** : 2026-04-26
**Configuration** : routage par theme_id explicite + multi-run harness
**Runs** : 3 × 70 questions = 210 évaluations en 4 minutes

## Résultats statistiques

### Global

| Métrique | V1 | V2 |
|---|---:|---:|
| Mean | 0,0 % | **54,3 %** |
| Stdev | 0,0 | ±1,4 |
| Min | 0,0 % | 52,9 % |
| Max | 0,0 % | 55,7 % |
| **IC 95 %** | [0,0, 0,0] | **[51,5, 57,1]** |

**V1** : 70 erreurs HTTP 429 sur tous les runs → 0 % stable. V1 = hors course.

### Par module (V2)

| Module | Mean | Stdev | IC 95 % | État |
|---|---:|---:|---|---|
| juridique | **78,3 %** | ±2,9 | [72,6, 84,1] | ✅ Excellent |
| gouvernance | 76,7 % | ±5,8 | [65,1, 88,2] | ✅ Bon |
| RH | 70,0 % | 0,0 | [70, 70] | ✅ Stable |
| **formation** | **25,6 %** | ±2,0 | **[21,6, 29,5]** | ⚠️ Bas |

## Apprentissages clés

### 1. La variance LLM est plus faible que prévue

Initialement estimée à ±5 pts, la variance réelle V2 = **±1,4 pts** (sur 3 runs).
Cela rend les comparaisons single-run **partiellement fiables** dans la marge
[-2, +2]. Pour valider rigoureusement une amélioration, il faut **multi-run
N=3 minimum** (5+ recommandé).

### 2. Le routage theme_id seul ne suffit pas pour formation

Routage implémenté :
- `fonctions_reglementaires` → prompt JURIDIQUE
- `metiers_gpec` → prompt JURIDIQUE
- `intentions_directeur` → prompt FORMATION
- `contrats_aides` → prompt FORMATION
- `financement_uniformation/cpnef_0_2` → prompt FORMATION

Résultat : formation reste à **25,6 % ± 2,0**. Le routage n'a pas fait basculer
les questions Q56-Q70 vers la qualité juridique (78,3 %).

**Hypothèse** : Claude considère le contenu comme « hors-domaine » non pas à
cause du prompt mais à cause du **mismatch entre la question (formation continue
classique CPF/Uniformation) et l'article (fonctions réglementaires détaillées)**.
Le mismatch sémantique est trop fort pour être résolu par changement de prompt.

### 3. Juridique et gouvernance sont solides

V2 sur juridique : **78,3 %** (IC95 [72,6, 84,1]) — confortablement au-dessus
de 75 %. Sur gouvernance : 76,7 % avec stdev plus élevée (5,8) suggérant
sensibilité aux questions vagues.

### 4. RH est étrangement stable (stdev 0,0)

3 runs identiques sur RH = même 7/10 questions correctes à chaque fois. Indique
que les réponses Claude sur ce module sont déterministes (pas de variance) →
soit le prompt RH est très contraint, soit le caching capture parfaitement les
mêmes décisions.

## Ce qui reste à investir pour atteindre 75 % global

D'après les IC 95 % :
- Si on monte formation de **25,6 % à 65 %**, V2 global passerait à **~70 %**
- Si on monte formation à **80 %**, V2 global = **~75 %** ✅

**Leviers à explorer** (ordonnés par ROI estimé) :

### Priorité 1 — Embeddings sémantiques (impact attendu +20-30 pts formation)

- E5-small ou BGE-M3 en complément TF-IDF
- Permet de matcher questions/articles sur le sens, pas juste le vocabulaire
- Coût : 5-8 jours dev + ~1 GB modèle local + retrofit pipeline RAG
- **Impact attendu** : formation 25 % → 50-60 %

### Priorité 2 — LLM-judge évaluateur (impact attendu : +5-10 pts via meilleure mesure)

- Claude juge la réponse de Claude (couple répondeur + évaluateur)
- Plus fiable que keyword matching (tolère les paraphrases, comprend les négations)
- Coût : 2-3 jours dev + ~10 €/run × multi-run
- **Impact attendu** : élimine les faux positifs/négatifs de l'évaluateur rule-based
  (estimation 5-10 % des classifications actuelles imprécises)

### Priorité 3 — Tuning prompt par theme_id (impact attendu : marginal)

- Créer un prompt dédié par theme_id au-delà du routage
- Coût : 1-2 jours dev + multi-run validation
- **Impact attendu** : +2-3 pts (déjà testé partiellement, marginal)

## Recommandations stratégiques

### Pour le bêta-test novembre 2026

**Option A** (intensive) : investir 1-2 semaines avant bêta sur priorité 1+2.
Cible : V2 ≥ 75 %.

**Option C** (focalisée, recommandée) : bêta-test sur les **20 utilisateurs
prioritaires juridique** où V2 est solide (78,3 % avec IC95 [72,6, 84,1]).
Différer formation/RH au bêta-test 2 (Q1 2027 post-tune systémique).

### Pour le tuning futur

**Méthode obligatoire** : multi-run N=3 minimum AVANT et APRÈS chaque
modification. Comparer les IC 95 %. Une amélioration <σ n'est pas
statistiquement significative.

## Outils mis en place

- `v2/scripts/benchmark_multirun.py` : wrapper N runs + agrégation stats
- Routage `theme_id` → prompt dans `v2/app/llm/prompts.py` (`resolve_module_for_theme`)
- Évaluateur rule-based avec matching contextuel forbidden (Sprint 5.2-bench)
- Corpus 70 questions (50 originaux + 20 ALISFA)

## État final V2

| Indicateur | Valeur statistique |
|---|---|
| Score global | **54,3 % ± 1,4** (IC95 [51,5, 57,1]) |
| Score juridique | **78,3 %** (IC95 [72,6, 84,1]) |
| Score formation | **25,6 %** (IC95 [21,6, 29,5]) |
| Variance LLM | ±1,4 pts |
| Erreurs techniques | 0 |
| Latence moyenne | ~80 s pour 70 Q |

**Verdict** : V2 est **prête pour bêta focalisé juridique** (Option C). Pour
bêta complet, investir 1-2 semaines en priorité 1 (embeddings) + priorité 2
(LLM-judge) avant.
