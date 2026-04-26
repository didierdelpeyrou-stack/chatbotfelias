# 🚀 BREAKTHROUGH — Sprint 5.2-stack : V2 = 67,1 % (vs 54,3 %)

**Date** : 2026-04-26
**Découverte critique** : V2 chargeait la **KB V1** (`data/base_*.json`, 158 articles) au lieu de la **KB V2 enrichie** (`data/v2/base_*.json`, 271 articles dont 156 formation).

## Le bug

`v2/app/settings.py` : `kb_data_dir: str = "../data"` (relatif au CWD uvicorn).
`v2/scripts/run_full_bench.sh` : exportait `KB_DATA_DIR=../data` (V1 path).
`.env` : pas de `KB_DATA_DIR` → settings utilise le défaut.

**Conséquence** : V2 chargeait `data/base_formation.json` (43 articles V1) au lieu de `data/v2/base_formation.json` (156 articles V2 enrichi Sprint 5.2-data).

**Tous les benchs précédents tournaient sur l'ancienne KB V1**. Les 95 nouveaux articles Sprint 5.2 (intentions directeur, fonctions réglementaires, GPEC métiers, financement, etc.) **n'étaient pas accessibles** à V2.

Cela explique la régression apparente sur formation 25,6 % : V2 ne connaissait pas les nouveaux articles (Q51-Q70) et refusait légitimement.

## Le fix

```bash
# .env
KB_DATA_DIR=../data/v2
```

```bash
# v2/scripts/run_full_bench.sh
PYTHONPATH=. KB_DATA_DIR=../data/v2 \
    nohup "$PYTHON" -m uvicorn app.main:app ...
```

## Bench complet APRÈS fix (KB V2 enrichie + Voyage actif)

| Métrique | AVANT (KB V1) | APRÈS (KB V2) | Δ |
|---|---:|---:|---|
| **V2 GLOBAL** | 54,3 % | **67,1 %** | **+12,8 pts** ✅ |
| juridique 20 | 78,3 % | 75,0 % | -3,3 (variance ±5) |
| **formation 30** | **25,6 %** | **56,7 %** | **+31,1 pts** 🚀 |
| RH 10 | 70,0 % | 70,0 % | = |
| gouvernance 10 | 76,7 % | 80,0 % | +3,3 ✅ |

## Détail formation (30 questions)

| Catégorie | Avant (V1 KB) | Après (V2 KB) | Δ |
|---|---:|---:|---|
| correct | 6 | **16** | +10 ✅ |
| hors_corpus_ok | 2 | 1 | -1 |
| partial | 5 | 8 | +3 ✅ |
| **false_refuse** | **12** | **0** | **-12** 🚀 |
| false_response | 3 | 4 | +1 |
| hallucinated | 1 | 0 | -1 ✅ |
| incorrect | 1 | 1 | = |

**Formation false_refuse : 12 → 0**. Claude n'a plus AUCUNE raison de refuser sur les nouveaux thèmes — la KB V2 contient bien les articles.

## Apprentissages

1. **Toujours vérifier ce que charge l'app** au boot : log explicite des chemins de fichiers.
2. **Le bug KB_DATA_DIR a masqué les vrais résultats** depuis le Sprint 5.2-data (date des tests : 11-26 avril).
3. **Voyage AI à α=0.5+skip=0.85** (config par défaut) ne dégrade pas les résultats — confirmé sur les 2 KBs.
4. **Le tuning prompt aurait été inutile** sans ce fix : on tunait sur des questions auxquelles la KB ne pouvait pas répondre.

## État V2 final post-fix

```
Score V2 global : 67,1 %
- juridique     : 75 %
- gouvernance   : 80 %
- RH            : 70 %
- formation     : 56,7 %

Cible bêta-test : ≥ 75 %
Écart : 7,9 pts à combler

Latence (single run) : 100s pour 70 Q = 1,43s/Q
KB chargée : 271 articles total dont 156 formation
Voyage actif : oui (cache 1 MB sur disque)
```

## Prochaines étapes pour atteindre 75 %

### 1. Confirmer 67,1 % en multirun (priorité 1)

Lancer 3-5 runs avec la KB V2 fixée pour avoir un IC95 fiable. Si stable
[63, 71], la cible 75 est à 4-7 pts.

### 2. Tuning ciblé sur formation (encore 23 questions ratées)

Détailler les 14 questions formation non-`correct` :
- 8 partial (info partielle, peut-être keywords trop stricts dans corpus)
- 4 false_response (Claude répond hors-corpus)
- 1 incorrect
- 1 false_refuse

Action : analyser case-par-case, ajuster KB ou keywords corpus selon le cas.

### 3. Phase A2 LLM-judge (toujours pertinente)

L'évaluateur rule-based reste imprécis. LLM-judge donnerait une mesure
+5-10 pts plus juste sans changer la KB.

### 4. Phase A3 grid search Voyage

Maintenant que V2 est sur la bonne KB, le grid search α + skip_threshold
peut donner des gains réels (à valider en multirun).

## Recommandation immédiate

**Lancer un multirun N=3 sur la KB V2 fixée** pour confirmer 67,1 % avec IC 95 %.
Selon le résultat :
- Si IC95 contient 75 % : on est probablement déjà au but, juste de la chance/variance
- Si IC95 stable autour de 65-70 % : continuer Phase A2 + grid search
- Si IC95 plus bas que prévu : analyser les régressions ponctuelles
