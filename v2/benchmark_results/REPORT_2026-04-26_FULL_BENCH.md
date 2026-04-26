# Bench complet V1 vs V2 — Sprint 5.2-bench (final)

**Date** : 2026-04-26
**Corpus** : 70 questions (50 Sprint 4.2 + 20 ajoutées Sprint 5.2)
**Durée** : 107 secondes (1m47s)
**KB V2** : `data/v2/base_formation.json` enrichie (156 articles, 21 thèmes)

## 1. Synthèse globale

| Catégorie | V1 | V2 | Δ |
|---|---:|---:|---:|
| correct | 9 | 25 | +16 |
| hors_corpus_ok | 0 | 14 | +14 |
| **false_refuse** | 0 | **16** | **+16** ⚠️ |
| false_response | 21 | 7 | -14 |
| hallucinated | 3 | 2 | -1 |
| incorrect | 34 | 1 | -33 |
| partial | 3 | 5 | +2 |
| **TOTAL** | **70** | **70** | — |

**Taux de succès** (correct + hors_corpus_ok) :
- V1 : **12,9 %** (50 erreurs HTTP 429 — rate limit Anthropic massif)
- V2 : **55,7 %** (0 erreur)
- Δ : +42,8 pts

## 2. Détail par module

| Module | N | V1 succès | V2 succès | Δ vs Sprint 4.2 |
|---|---:|---:|---:|---|
| juridique | 20 | 40,0 % | **85,0 %** | **+10 pts ✅** |
| gouvernance | 10 | 0,0 % | 70,0 % | = |
| RH | 10 | 0,0 % | 60,0 % | -10 pts |
| **formation** | **30** | 3,3 % | **30,0 %** | **régression** |

## 3. Constat majeur : régression V2 sur formation

Les **30 questions formation** (10 anciennes + 20 nouvelles Sprint 5.2) donnent
**seulement 30 %** sur V2 :
- 7 correct
- 5 partial
- **12 false_refuse** ← le problème
- 3 false_response
- 2 hors_corpus_ok
- 1 hallucinated

**12 false_refuse sur les nouvelles questions Q51-Q70** : V2 répond
systématiquement « Je n'ai pas d'information fiable dans la base ELISFA »
alors que :
- ✅ Le RAG-only retrouve les bons articles en top-1 (mini-bench 90 %)
- ✅ Le contexte envoyé à Claude est complet (synthèse, fondement, sources)
- ✅ Score TF-IDF élevé (130 pour Q60 RSAI, 90 pour Q67 maltraitance, etc.)

## 4. Diagnostic de la régression

### 4.1. Le RAG fonctionne

Vérifié sur Q60 (RSAI) : le top-1 est `reg-rsai-eaje` avec score 130, le contexte
envoyé à Claude commence par :
```
## [reg-rsai-eaje] Comment désigner un·e Référent·e Santé et Accueil Inclusif (RSAI) en EAJE en 2026 ?
**Synthese** : Le ou la **Référent·e Santé et Accueil Inclusif (RSAI)** est
OBLIGATOIRE dans tout EAJE depuis le 1er septembre 2022...
```
Le contenu est **parfait**. Pourtant V2 répond « Je n'ai pas d'information fiable ».

### 4.2. Hypothèses

**H1 — Format des IDs incompatible avec le prompt R11** :
- Prompt R11 : « cite avec `[ART_xxx]` »
- Nouveaux articles : IDs au format `reg-xxx`, `int-xxx`, `gpec-xxx`, `fin-xxx`, `contrat-xxx`
- Hypothèse partiellement infirmée : Q01 (juridique) a aussi un ID format `juri-rupt-01` et marche

**H2 — Contexte saturé** :
- 5 articles × 3000-4000 chars = ~17 000 chars (~4 000 tokens)
- Avec 156 articles dans la KB, le top-5 contient parfois 4 articles vraiment
  pertinents et 1 articulièrement bruité → Claude perd confiance et refuse

**H3 — Prompt R11 trop strict** :
- « Si le contexte RAG ne contient PAS d'article pertinent, réponds
  UNIQUEMENT : "Je n'ai pas d'information fiable..." »
- Le seuil de Claude pour décider « pas d'article pertinent » s'est resserré
  avec le caching Anthropic (5 min TTL) — apprentissage in-context excessif

**H4 — Module formation déclenche un prompt FORMATION qui paralyse** :
- Prompt FORMATION : « Distinguer TOUJOURS minimum LÉGAL / enrichissements
  ALISFA / opportunités »
- Pour des questions sur les **fonctions réglementaires** (RSAI, direction ACM,
  référent harcèlement) ou **GPEC métiers**, cette consigne est inadaptée et
  peut faire refuser

## 5. Régressions ponctuelles vs V1

Seulement **2 régressions** où V1 fait mieux que V2 :
- **Q55** PEC : V1=partial → V2=false_refuse
- **Q56** EJE : V1=correct → V2=false_refuse

Les deux sont dans formation et confirment H4 (le prompt formation rejette
les questions de fonctions réglementaires / métiers).

## 6. Forces de V2

Malgré la régression formation, V2 **excelle** sur :
- ✅ **Juridique 85 %** (vs 75 % Sprint 4.2) — les nouveaux articles enrichissent positivement
- ✅ **Hors-corpus** : 14/14 questions vagues correctement refusées (Q13, Q16-Q20, etc.)
- ✅ **0 erreur technique** vs V1 = 50 erreurs HTTP 429
- ✅ **Hallucinations** : 2 vs V1 = 3
- ✅ **Performance** : 70 questions en 107 secondes

## 7. Recommandations Sprint 5.2-tune

**Priorité 1 — Relâcher la contrainte R11** (à tester) :
- Remplacer « Si le contexte RAG ne contient PAS d'article pertinent » par
  « Si AUCUN article du contexte ne traite directement la question »
- Ajouter : « Tu peux synthétiser les éléments présents même partiels »
- Cible : faire passer Q60 (RSAI), Q66 (fermeture EAJE) de false_refuse à correct

**Priorité 2 — Réduire `max_articles` à 3** dans `build_rag_context` :
- Moins de bruit dans le top-K, contexte mieux focalisé
- Économie tokens (5 → 3 articles = -40 % contexte)
- Risque : perdre des cas où l'info est en top-4 ou top-5

**Priorité 3 — Adapter le prompt formation** :
- Distinguer « formation continue » (CPF, plan, OPCO) des « fonctions réglementaires »
- Pour fonctions réglementaires (RSAI, direction ACM, etc.) : utiliser le
  prompt juridique-like (qui fonctionne bien à 85 %)
- Routage par `_theme_target` plutôt que par module

**Priorité 4 — Test A/B sur prompt** :
- Garder R11 strict pour juridique (où ça marche)
- Assouplir pour formation (où Claude refuse trop)

**Cible Sprint 5.2-tune** : passer V2 de 55,7 % à 75-80 % sans dégrader juridique/RH/gouvernance.

## 8. État final pour le bêta-test

**Go ?** Pas encore — la régression formation 30 % est trop pénalisante pour
un bêta-test 100 utilisateurs où la majorité des questions porteront
probablement sur la formation (cible directeur·trice ESS).

**Plan recommandé** :
1. Sprint 5.2-tune (1-3 jours) : ajustements prompts/RAG selon recommandations
2. Re-bench 70 questions
3. Cible : V2 ≥ 75 % global, ≥ 65 % sur formation
4. Si atteint : déploiement staging VPS (Sprint 4.4) puis bêta-test (Sprint 4.5)

## 9. Données brutes

- Données JSON : `v2/benchmark_results/run_20260426_091319.json` (gitignored)
- Logs serveurs : `v2/benchmark_results/v1_*.log`, `v2_*.log` (gitignored)
- Script reproductible : `v2/scripts/run_full_bench.sh`
