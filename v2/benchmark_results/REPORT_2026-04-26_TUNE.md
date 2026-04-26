# Sprint 5.2-tune — Rapport honnête des 4 itérations

**Date** : 2026-04-26
**Objectif** : passer V2 de 55,7 % à 75 % via tuning prompt + RAG.
**Résultat** : **objectif non atteint** (max 57,1 %, variance ±5 pts).

## Ce qui a été tenté

### Itération 1 — Relâcher R11 + max_articles 5→3

**Modifications** :
- Prompt commun R11 #2 : `"PAS d'article pertinent"` → `"AUCUN article ne traite la question"`
- R11 #3 ajouté : « Tu peux et dois synthétiser les éléments présents même partiels »
- `max_articles` de 5 → 3 dans `build_rag_context`
- `[ART_xxx]` accepté avec format souple

**Résultat** : V2 = **57,1 %** (+1,4 pt vs baseline 55,7 %)
- false_refuse : 16 → 13 (-3) ✅
- correct : 25 → 27 (+2) ✅
- formation : 30 % → 30 % (=) — pas mieux

### Itération 2 — Enrichir prompt FORMATION

**Modifications** : prompt FORMATION enrichi avec routage explicite (financement /
métier / situation opérationnelle), niveaux d'escalade ROUGE pour signalement
maltraitance / inaptitude.

**Résultat** : V2 = 57,1 % (=) — pas d'amélioration sur formation.

### Itération 3 — Simplifier prompt FORMATION

**Modifications** : remplacer le prompt FORMATION détaillé par un prompt
minimaliste type prompt JURIDIQUE (qui marche à 85 %).

**Résultat** : V2 = **52,9 %** (régression de -4,2 pts)
- formation : 30 % → 26,7 % (régression)
- Sans la consigne directive, Claude perd ses repères et refuse plus.

### Itération 4 — Retirer thème + score du contexte

**Modifications** : `format_article` ne renvoie plus la ligne `_Thème : XXX —
score Y_` qui pouvait suggérer à Claude un mismatch domaine/article.

**Résultat** : V2 = **54,3 %** (-1,4 pt vs baseline)
- juridique : 85 % → 80 % (légère régression)
- formation : 30 % → 26,7 %

## Constat

**Variance entre runs : ±5 pts** sur les mêmes prompts. Le LLM (avec caching prompt
5 min + temperature non-zero) introduit du bruit qui rend impossible la
comparaison de petites variations de prompt en single-run.

**Le tuning prompt en isolation ne suffit pas**. Pour passer V2 de 55 % à 75 %,
il faut :
1. **Évaluer statistiquement** (3-5 runs par configuration, calculer moyenne + écart-type)
2. **Investir dans le RAG** : embeddings sémantiques au lieu de TF-IDF (E5-small,
   BGE-M3) pour mieux distinguer questions vagues vs précises
3. **Utiliser un évaluateur LLM-judge** plus fiable que rule-based keyword matching
4. **Routage par thème explicite** : modifier l'API pour utiliser le `theme_id`
   du top-1 et choisir le prompt adapté (au-delà du module client)

## Décision

**Revert** de toutes les modifications du Sprint 5.2-tune. Retour à la baseline
post-Sprint 5.2-bench (55,7 %).

Les 4 itérations sont gardées en historique git pour traçabilité (commits non
poussés, diff dans `git stash`).

## Apprentissages opérationnels

1. **Le RAG TF-IDF retrouve correctement** les articles pertinents (90 % top-1 sur
   les nouveaux thèmes — mini-bench RAG-only).
2. **Le contexte envoyé à Claude est complet** (synthèse, fondement, sources).
3. **Mais Claude refuse** sur les nouveaux thèmes (formation) malgré le contexte
   parfait. Cause non-identifiée précisément :
   - H1 (format ID) infirmée
   - H2 (saturation contexte) testée par max_articles=3 → marginal
   - H3 (R11 strict) testée → marginal
   - H4 (mismatch thème/module) testée → régression
   - **H5 (variance LLM caching)** : la plus probable, non corrigeable par tuning prompt
4. **L'A/B testing rigoureux** sur LLM nécessite multi-run + statistiques. C'est
   un sprint à part entière (Sprint 5.2-stats).

## Recommandations pour la suite

### Court terme (avant bêta-test)

**Option A — Investir 1-2 semaines dans le tuning systémique** :
- Implémenter un harness multi-run (3-5 runs par configuration)
- Tester routage par theme_id explicite
- Tester embeddings sémantiques (E5-small, BGE-M3) en parallèle TF-IDF
- Tester évaluateur LLM-judge (Claude juge la réponse, plus fiable que keywords)
- **Coût estimatif** : 8-15 jours dev + ~50 € API Anthropic pour multi-runs

**Option B — Bêta-test maintenant avec V2 = 55 %** :
- Lancer le bêta-test 100 utilisateurs avec V2 dans son état actuel
- Collecter le feedback réel (pas le bench artificiel)
- Investir le tuning sur les vraies questions ratées
- **Risque** : satisfaction utilisateur faible sur formation, désengagement
- **Bénéfice** : feedback utilisateur réel > bench artificiel

**Option C — Périmètre bêta-test focalisé juridique** :
- Lancer le bêta-test sur les **20 utilisateurs** prioritaires intéressés par
  les questions juridiques (V2 marche à 85 %)
- Différer formation/RH au bêta-test 2 (post-tune Q3 2026)
- **Bénéfice** : qualité haute sur le périmètre testé

### Moyen terme (Sprint 6.x)

- Embeddings sémantiques en addition au TF-IDF
- Évaluateur LLM-judge (couple Claude répondeur + Claude juge)
- Routage par theme_id explicite
- Multi-run statistique pour décider chaque modification de prompt
- Outils de monitoring continu post-bêta-test

## Recommandation actuelle

**Option C** : démarrer le bêta-test focalisé juridique (20 utilisateurs), pendant
qu'on investit progressivement le tuning sur formation. C'est la voie la plus
sécurisée pour le calendrier bêta novembre 2026.

Si le calendrier presse, **Option B** (bêta complet à 55 %) reste viable mais
risque de générer un retour mitigé qui pourrait freiner la confiance des partenaires
ELISFA.
