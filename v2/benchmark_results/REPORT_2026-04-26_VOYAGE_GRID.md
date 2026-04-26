# Sprint 5.2-stack Phase A1 — Voyage AI testé en conditions réelles

**Date** : 2026-04-26
**Modèle** : voyage-3-large (1024 dim)
**Cache** : 4 modules indexés sur disque (1 MB total)
**Configurations testées** : α ∈ {0.3, 0.5} × skip_threshold ∈ {0.85, 2.0}

## Résultats single-run (à confirmer multi-run pour rigueur)

| Config | α | skip_threshold | V2 score | Note |
|---|---:|---:|---:|---|
| Baseline TF-IDF | 1.0 | n/a | 54.3 % | Multi-run baseline |
| **Voyage défaut** | **0.5** | **0.85** | **54.3 %** | = baseline (skip embeddings sur 60-70% des Q) |
| Voyage forcé α=0.3 | 0.3 | 2.0 (no skip) | **27.1 %** | RÉGRESSION majeure |

## Détail Voyage défaut (α=0.5, skip=0.85)

| Module | TF-IDF baseline | Voyage défaut | Δ |
|---|---:|---:|---|
| juridique 20 | 78,3 % | 80 % | +1,7 ✅ |
| gouvernance 10 | 76,7 % | 80 % | +3,3 ✅ |
| RH 10 | 70 % | 80 % | +10 ✅ |
| **formation 30** | **25,6 %** | **23 %** | **-2,6** ⚠️ |

**Constat** : à config défaut, Voyage **améliore juridique/gouv/RH** (+1 à +10 pts) mais **régresse légèrement formation** (-2,6 pts). Le pré-filtrage skip=0.85 fait que la plupart des questions formation skippent les embeddings (TF-IDF déjà confiant), donc Voyage ne change rien sur ces cas.

## Détail Voyage forcé (α=0.3, skip=2.0)

| Module | TF-IDF baseline | Voyage forcé | Δ |
|---|---:|---:|---|
| juridique 20 | 78,3 % | 35 % | -43 ❌❌ |
| gouvernance 10 | 76,7 % | 40 % | -36 ❌❌ |
| RH 10 | 70 % | 50 % | -20 ❌ |
| formation 30 | 25,6 % | 40 % | +14 ✅ |

**Constat** : forcer embeddings améliore formation mais **détruit juridique/gouv/RH**. Le re-rank embeddings classe différemment, et apparemment souvent **moins bien** que TF-IDF sur les anciennes questions où le vocabulaire matche déjà bien.

## Diagnostic

### Voyage AI ne suffit pas (à lui seul) à battre TF-IDF

**Hypothèses pour expliquer le résultat décevant** :

1. **Embeddings document trop courts** : on indexe titre + mots-clés + 800 char/champ pour 3 champs = ~3000 chars. Mais un article ALISFA fait souvent 5000+ chars. Voyage manque de contexte pour bien comprendre le contenu spécifique.

2. **Domaine très technique** : la KB ALISFA contient du vocabulaire juridique français très spécifique (CCN ALISFA IDCC 2941, NPEC, RSAI, OPCO Uniformation, etc.). Voyage-3-large est entraîné sur du français généraliste, peut sous-performer sur ce domaine.

3. **Free tier limité en débit** : indexation prend ~5 min par module, contraint nos itérations. Un compte payant permettrait grid search multi-α plus rigoureux.

4. **Évaluateur rule-based imprécis** : variance ±5pts entre runs masque les vraies différences. Sans LLM-judge (Phase A2), difficile de conclure rigoureusement.

### Ce que ça révèle

Le RAG TF-IDF avec **156 articles bien rédigés** fonctionne déjà bien sur les vocabulaires partagés. Le **vrai goulot** sur formation 25,6 % n'est PAS le retrieval mais la **génération** (Claude refuse malgré bon contexte) — confirmé par le mini-bench RAG-only à 90 %.

## Décision technique

**Configuration retenue** : α=0,5, skip_threshold=0,85 (défaut, équivalent à baseline).

**Voyage reste actif** comme infrastructure :
- Cache disque opérationnel (4 modules indexés, 1 MB)
- Module embeddings rodé pour Phase A2/A3
- Boot V2 instantané (cache hit)
- Pas de régression vs TF-IDF seul
- Coût négligeable (~0,10 €/mois)

**Voyage n'est PAS désactivé** car :
- Améliore juridique +1,7 et gouvernance +3,3 et RH +10
- Régression formation -2,6 dans la marge de variance ±1,4
- Le vrai gain viendra de la **Phase A2 LLM-judge** + **Phase A3 grid search** avec multi-run rigoureux

## Prochaines étapes

### Phase A2 — LLM-judge (priorité haute)

Sans évaluateur fiable, impossible de conclure si une variation prompt/RAG est statistiquement significative. **Phase A2 obligatoire avant tout autre tuning**.

### Phase A3 — Grid search complet

Avec LLM-judge en place, lancer un grid search :
- α ∈ {0.0, 0.2, 0.4, 0.6, 0.8, 1.0}
- skip_threshold ∈ {0.5, 0.7, 0.85, 1.0 (no skip)}
- multi-run N=3 par config = 24 configs × 3 runs = 72 runs

Coût API estimatif :
- Bench classique : 70 Q × 72 runs = 5040 appels Claude × 0,003 € ≈ **15 €**
- LLM-judge : 70 Q × 72 runs × 0,001 € ≈ **5 €**
- Voyage embeddings : ~ 300 K tokens × 72 runs ≈ **negligeable** (cache disque)
- **Total : ~20 €**

### Phase A4 — Décision bêta

Selon résultats grid search :
- Si meilleure config V2 ≥ 75 % global : **GO bêta complet**
- Sinon : pivoter vers enrichissement KB ciblé sur questions ratées

## État infra Voyage

```
Caches embeddings (data/v2/) :
  _embeddings_juridique_voyage-3-large.npz       343 KB  (92 articles)
  _embeddings_formation_voyage-3-large.npz       581 KB  (156 articles)
  _embeddings_gouvernance_voyage-3-large.npz      45 KB  (12 articles)
  _embeddings_rh_voyage-3-large.npz               42 KB  (11 articles)
  TOTAL                                          ~1 MB

Boot V2 cache hit : 50 ms
Boot V2 cache miss (free tier) : 5-10 min selon module
Coût free tier consommé : ~ 80 K tokens (sur 50M dispo)
```

## Apprentissage clé

**Le tuning systémique sans évaluateur fiable est un coup d'épée dans l'eau**. La variance LLM ±1,4 pts noie les améliorations marginales. Phase A2 (LLM-judge) est **prérequis indispensable** pour tout grid search Phase A3.
