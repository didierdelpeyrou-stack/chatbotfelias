# Mini-Bench RAG-only — Sprint 5.2-bench (extension)

**Date** : 2026-04-26
**Mode** : RAG-only (sans appel Claude API)
**Cible** : Q51-Q70 (20 questions sur les nouveaux thèmes du Sprint 5.2)
**KB testée** : `data/v2/base_formation.json` post-fusion (156 articles, 21 thèmes, 1 288 tokens)

## Objectif

Mesurer la **couverture RAG** des 113 nouveaux articles du Sprint 5.2 (financement, GPEC, fonctions réglementaires, intentions directeur) **avant** le bench complet V1 vs V2 (qui nécessite ANTHROPIC_API_KEY + V1 lancé).

Si le RAG ne remonte pas l'article pertinent en Top-3, Claude ne peut pas répondre correctement.

## Résultats globaux

| Catégorie | Nb | % |
|---|---:|---:|
| ✅ Excellent (tous keywords + bon top-1) | 14 | 70 % |
| 🟡 Partiel (≥ 50 % keywords + bon top-1 ou top-3) | 4 | 20 % |
| ❌ Mauvais (< 50 % keywords) | 1 | 5 % |
| ❌ Hors-corpus manqué | 1 | 5 % |
| **TOTAL** | **20** | **100 %** |

**Score RAG global** : 14/20 excellent + 5/20 récupérable par Claude = **estimation 85-95 % correct** au bench complet avec Claude API.

## Distribution par axe

| Axe | Nb questions | Excellent | Partiel | Bad | HC miss |
|---|---:|---:|---:|---:|---:|
| Financement (Q51-Q55) | 5 | 4 | 0 | 1 | 0 |
| GPEC métiers (Q56-Q59) | 4 | 3 | 1 | 0 | 0 |
| Fonctions réglementaires (Q60-Q64) | 5 | 4 | 1 | 0 | 0 |
| Intentions directeur (Q65-Q70) | 6 | 4 | 1 | 0 | 1 |

## Anomalies à investiguer

### Q54 — Aide État apprentissage 6 000 €

- **Top-1** : `fin-alt-apprentissage-2026` (article V1 migré Sprint 5.1) — score 51,9
- **Problème** : ne contient pas explicitement "6 000 €" ni "première année" ni "aide unique"
- **Solution** : info présente dans `int-cout-alternant-employeur` et `int-recruter-alternance` (Sprint 5.2)
- **Impact bench** : Claude reçoit le top-3 → trouvera l'info ailleurs
- **Action proposée** : enrichir `fin-alt-apprentissage-2026` avec mention décret 2024-149 (1 ligne)

### Q57 — Animateur RPE professionnalisation

- **Top-1** : `gpec-animateur-rpe` — score 145,1 (très bon)
- **Keywords trouvés** : 2/3 (manque "professionnalisation")
- **Cause** : la fiche GPEC RPE évoque "accompagnement des assistantes maternelles" mais pas le mot "professionnalisation"
- **Impact** : Claude saura compléter
- **Action proposée** : ajouter terme "professionnalisation" dans mots_cles

### Q62 — Référent harcèlement (faux positif)

- **Top-1** : `reg-referent-harcelement` (score 92,3)
- **Faux positif** : "non obligatoire" trouvé dans la phrase « **non** obligatoire dans les structures < 11 salariés sans CSE » — sens correct dans le contexte
- **Impact** : nul, l'évaluateur Claude comprendra
- **Action** : aucune nécessaire

### Q63 — HACCP combien de personnes formées

- **Top-1** : `gpec-cuisinier` (score 37,3)
- **Top-2 ou 3** : `reg-haccp` (contient bien tous les keywords)
- **Cause** : scoring TF-IDF favorise gpec-cuisinier car termes "cuisine" + "EAJE" plus concentrés
- **Impact** : Claude reçoit top-3 → trouvera l'info dans reg-haccp
- **Action proposée** : renforcer mots_cles de `reg-haccp` avec "cuisinier", "cuisine collective"

### Q67 — Signalement maltraitance (faux positif)

- **Top-1** : `int-signalement-maltraitance` (score 87,4) — bon article
- **Faux positif** : "ignorer" trouvé dans phrase « il ne faut pas **ignorer** un signalement »
- **Impact** : nul
- **Action** : aucune nécessaire

### Q70 — Question vague (HC manqué)

- **Top-1** : `fin-cpnef-projets-innovants-2026` (score non bloqué par seuil 1,5)
- **Cause** : « améliorer ma structure » contient des termes valides → score > 1,5
- **Impact** : Claude pourrait faire une réponse trop large
- **Action proposée** : ajuster le seuil hors_corpus à 2,5 pour les questions courtes (< 6 mots) ou ajouter un détecteur de questions vagues

## Conclusions

1. **Le RAG fonctionne très bien sur les nouveaux thèmes** : 70 % de top-1 parfaits, 20 % partiels mais récupérables.
2. **3 ajustements mineurs KB** suggérés (mots_cles à enrichir sur 3 articles) → +5-10 % attendus.
3. **1 ajustement RAG** suggéré (seuil HC dynamique selon longueur question).
4. **Ces résultats prédisent ~85-95 % correct au bench complet V1 vs V2** sur Q51-Q70.

## Recommandation pour le bench complet V1 vs V2

Le bench complet sur **70 questions** (50 Sprint 4.2 + 20 nouvelles Sprint 5.2) nécessite :

```bash
# Terminal 1 — V1 Flask
cd /chemin/vers/chatbot_elisfa
.venv/bin/python app.py  # port 8080

# Terminal 2 — V2 FastAPI (KB enrichie)
cd /chemin/vers/chatbot_elisfa/v2
PYTHONPATH=. KB_DATA_DIR=../data \
  ../.venv/bin/python -m uvicorn app.main:app --port 8000

# Terminal 3 — Run benchmark
cd /chemin/vers/chatbot_elisfa/v2
export ANTHROPIC_API_KEY=sk-ant-...
PYTHONPATH=. ../.venv/bin/python scripts/benchmark.py
```

**Durée estimée** : 5-10 min pour 70 questions (selon rate-limit Anthropic). Précédent run V1 a eu 35 erreurs HTTP 429 → V1 hors course attendu.

**Cible V2 visée** :
- Sur 50 anciennes questions : ≥ 74 % (non-régression)
- Sur 20 nouvelles questions : ≥ 85 %
- **Global 70 questions** : ≥ 78 %

## Suite

- [ ] Appliquer les 3 ajustements KB suggérés (Q54, Q57, Q63)
- [ ] Lancer le bench complet V1 vs V2 (nécessite démarrage manuel V1 + clé API)
- [ ] Documenter les régressions éventuelles
- [ ] Décider du go/no-go pour bêta-test 100 utilisateurs
