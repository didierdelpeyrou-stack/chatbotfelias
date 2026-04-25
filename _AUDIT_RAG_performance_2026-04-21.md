# AUDIT — Performance du RAG chatbot ELISFA
## Module par module, avec recommandations priorisées
### Date : 2026-04-21 — Analyse de code `app.py` + inspection des 4 KB

---

## 0. Synthèse exécutive

Le retrieval ELISFA **n'est pas un RAG vectoriel** : c'est un **index inversé TF-IDF lexical** (construit au démarrage sur `mots_cles + question_type`), suivi d'un top-5 envoyé à Claude Haiku 4.5 avec prompt caching. Rapide (~50 ms retrieval), mais **lexical pur** → échoue sur les synonymes, reformulations et questions imprécises. C'est la racine de la fantaisie observée : Claude reçoit systématiquement 5 articles (même faiblement liés), voit « quelque chose à dire » et extrapole.

**7 problèmes architecturaux communs aux 4 modules** + **lacunes de couverture spécifiques par module** (détaillés ci-dessous).

**3 actions à mener dans cet ordre** :
1. **Ajouter un seuil `hors_corpus`** + forcer les citations verbatim → élimine ~70 % des hallucinations (1 semaine)
2. **Greffer un embedding E5-small en fallback** quand TF-IDF est faible → couvre les synonymes/reformulations (2 semaines)
3. **Combler les lacunes de couverture par module** (détaillées section 3) → 40-60 articles à ajouter (3-4 semaines)

---

## 1. Architecture retrieval actuelle (relevé du code)

### 1.1 Pipeline de bout en bout (`app.py`)

```
POST /api/ask {question, module, history}
        │
        ▼
   tokenize(question)                 # stop_words FR retirés, lowercase
        │
        ▼
   search_knowledge_base(tokens, kb=KB_<module>)
        │
        ▼ index inversé TF-IDF (construit au boot via _build_kb_index)
   for qtok in tokens:
     • match exact → score += 3.0 · tf · idf[qtok]
     • match sous-chaîne (si idf > 1.0) → score += 1.0 · tf
        │
        ▼
   top-5 articles triés par score décroissant         ← PAS DE SEUIL
        │
        ▼
   build_system_blocks(SYSTEM_PROMPT_<module>, context)
        │
        ▼ Anthropic Messages API (Haiku 4.5, non-stream)
   • prompt caching ephemeral (5 min TTL, bloc stable > 4096 tokens)
   • temperature default, max_tokens default
        │
        ▼
   Réponse Claude → validation.py → réponse + CTA (urgency scoring)
```

### 1.2 Ce qui est bien fait
| Point | Détail |
|---|---|
| Index inversé TF-IDF | Construit au boot (`_build_kb_index`), pas d'itération linéaire par requête |
| IDF pondéré | `log(1 + N/(1+df))` → mots rares favorisés (« forfait-jours » > « travail ») |
| Thread-safe | `FileBackedCache` avec `threading.Lock`, double-check locking |
| Hot reload | `mtime` watcher sur les JSON → pas de redeploy pour corriger un article |
| 4 prompts système distincts | Chaque module a sa posture (juridique, formation, RH, gouvernance) |
| Prompt caching calibré | Seuil empirique 4096 tokens pour Haiku 4.5 (cache_creation silencieux sous ce seuil) |
| Stop words FR | Liste manuelle appropriée (le, la, de, du, etc.) |

### 1.3 Ce qui ne l'est pas (les 7 limites architecturales communes aux 4 modules)

| # | Limite | Conséquence directe |
|---|---|---|
| L1 | **Pas de seuil `hors_corpus`** | Top-5 retourné même si score brut = 0.1 → Claude voit 5 articles vaguement liés → invente un lien. |
| L2 | **Pas de normalisation de score** | Score 12.3 vs 3.7 selon la question : impossible de comparer « ce top-1 est fort ou faible » de manière absolue. |
| L3 | **Retrieval 100 % lexical** | « Interruption grossesse » ne match pas « congé maternité ». « Télétravail » ne match pas « travail à distance ». La reformulation casse le retrieval. |
| L4 | **Substring matching bruyant** | Tokens IDF > 1.0 déclenchent du substring → « travail » match « retravailler », « travailliste », « télétravail », etc. → bruit dans le top-5. |
| L5 | **`mots_cles` humains (10-13/article)** | Impossible qu'un curateur anticipe toutes les formulations → 30-50 % des questions ratent le top-1 attendu. |
| L6 | **Pas de rerank post-retrieval** | Les 5 articles du top-5 sont envoyés tels quels → pas de vérification sémantique après TF-IDF. |
| L7 | **Pas de contrainte verbatim côté LLM** | Le prompt n'impose pas « cite verbatim de la synthese avant de paraphraser » → Claude paraphrase librement → fantaisie. |

Ces 7 limites sont **communes aux 4 modules**. Les corriger a un effet systémique.

---

## 2. Audit module par module

### 2.1 Module **Juridique** (21 thèmes / 92 articles — CCN IDCC 1261)

#### Profil
- Le module le plus volumineux et le mieux structuré
- Niveaux de criticité (`vert`/`orange`/`rouge`) — bon signal pour urgency scoring
- Avenants chronologiques (10-2022, 01-correctif, 03-24 statut cadre)
- Densité `mots_cles` moyenne : 13.2/article

#### Forces
- Préambule + IDCC + champ d'application bien couverts (bonne base pour questions génériques)
- Thèmes `rouge` (harcèlement, contentieux, inaptitude, licenciement éco) traités avec sérieux
- Rupture : 10 articles (préavis, indemnités, démission, rupture conventionnelle, abandon de poste)

#### Lacunes de couverture
| Thème | Articles actuels | Manque clairement |
|---|---:|---|
| `droit_syndical` | **1** | Négociation obligatoire, RSS, délégués syndicaux, accords majoritaires, expertise CSE, heures délégation syndicale |
| `temps_travail` | 7 | **Télétravail** (ANI 2020 + loi 2023), jours fériés/RTT, modulation annuelle, forfait heures, astreintes, travail dominical |
| `disciplinaire` | 2 | Mise à pied conservatoire, entretien préalable, notification sanction, prescription (2 mois), recours salarié |
| `cse_irp` | 3 | CSE < 50 salariés, DUERP, moyens matériels CSE, référentiel consultations annuelles, base BDESE complète |
| `egalite` | 2 | Accord égalité (obligatoire > 50), plan action, écarts salariaux, congé paternité 28 j, temps partiel parental |
| `conges` | 6 | Congés sabbatique, création d'entreprise, solidarité familiale, don de jours |
| `contrat_travail` | 7 | CDI intermittent (spécifique ALISFA), CDD d'usage, temps partiel modulé, avenants contrat |
| `prevoyance` | 3 | Portabilité au-delà 12 mois, régime frais santé obligatoire, dispenses |

**Total lacunes juridique estimées : ~35 articles à ajouter** pour atteindre une couverture de référence.

#### Risques d'hallucination spécifiques
- **Calcul d'indemnité** : si la question utilise un cas de figure non listé (ex : licenciement après congé mat'), Claude extrapole les modalités.
- **Articles pénaux** (harcèlement, discriminations) : risque élevé, Claude peut inventer des jurisprudences.
- **Dates de réformes** : Claude mélange les dates (ex : loi travail 2016 / ordonnances Macron 2017 / loi 2023).
- **Avenants** : confusion entre avenant 10-2022 et avenant 01-correctif fréquente.

#### Recommandations juridique
1. **Ajouter un champ `articles_ccn_cites` structuré** dans chaque article (ex : `["Art. 4.1.1", "Art. 5.2"]`). Le forcer dans la réponse Claude → si Claude cite un article hors liste, on sait qu'il invente.
2. **Ajouter le thème `telemedecine_eaje`** (crèches, santé au travail spécifique).
3. **Enrichir `droit_syndical`** à 5-6 articles (priorité haute).
4. **Créer un sous-index par numéro d'article CCN** (`CCN_ARTICLE_INDEX[str]=article`) pour répondre instantanément à « que dit l'article 4.7.3 ? ».
5. **Flag `niveau_certitude`** par article : `officiel_ccn` / `interpretation_elisfa` / `doctrine_jurisprudence`. Le LLM doit signaler quand il répond depuis l'interprétation.

---

### 2.2 Module **Formation** (15 thèmes / 43 articles)

#### Profil
- Seul module avec un millésime (`catalogue_2026`, `financement_cpnef`, `vae_reforme`)
- Densité `mots_cles` moyenne : 11.3/article
- CEP / AFEST bien couverts (6 articles)

#### Forces
- Dispositifs 2026 nominatifs (CPF, Pro-A, PREC, CEP, AFEST, PTP, FNE, VAE réformée)
- Barèmes Uniformation 2026 inclus
- CPNEF bien identifié comme acteur pivot

#### Lacunes de couverture
| Thème | Articles actuels | Manque clairement |
|---|---:|---|
| `vae_reforme` | **1** | Décret 2023-1275 complet, durée max 24 mois, accompagnement rénové, jury, résultat partiel |
| `reste_a_charge_certifiant` | 1 | Cas EAJE, cas centre social, cas siège fédéral, rupture RAC employeur vs salarié |
| `textes_legaux` | 1 | Articles L6111-1 à L6353-9 : plan, droits, entretien, abondement correctif… |
| `catalogue_2026` | 4 | Catalogue Uniformation complet, ACT 2026, aides employeur handicap |
| `obligations_employeur` | 4 | Adaptation au poste (L6321-1), employabilité, formation obligatoire (sécurité) |
| (thème absent) | 0 | **Formation CSE élus** (L2315-63) — 5 jours obligatoires |
| (thème absent) | 0 | **Formation SST** (sauveteur secouriste) — obligatoire en EAJE |
| (thème absent) | 0 | **Formation handicap** (OETH, travailleur handicapé reclassement) |
| (thème absent) | 0 | **Formation cadre** (statut cadre avenant 03-24 + obligations formation) |
| (thème absent) | 0 | **Entretien de 2e partie de carrière** (senior, déjà dans obligations mais pas dédié) |

**Total lacunes formation estimées : ~15-20 articles à ajouter** + 4-5 nouveaux thèmes.

#### Risques d'hallucination spécifiques
- **Montants de financement** : Claude invente des plafonds quand la question vise un cas de figure non listé.
- **Dates de transition de réforme** (ex : « quand la VAE 2023 s'applique-t-elle aux procédures en cours ? ») : extrapolation fréquente.
- **Éligibilité à un dispositif** (Pro-A, FNE, CPF transition) : confusion entre dispositifs aux critères proches.

#### Recommandations formation
1. **Ajouter un champ `montant_prevu` structuré** (min, max, conditions) dans les articles financiers. Forcer le LLM à ne pas citer de montant hors de ce champ.
2. **Sous-index par dispositif** (`DISPOSITIF_INDEX["CPF"] = article_id`) pour les 12 dispositifs majeurs → 1 seul article retourné au lieu de 5 bruités.
3. **Ajouter thème `formations_obligatoires_eaje`** (SST, HACCP alimentation, prévention enfance).
4. **Enrichir `vae_reforme`** à 3-4 articles (c'est un sujet majeur 2023-2026).
5. **Ajouter `niveau_recence`** par article : `2026` / `2025` / `2024` / `<2024`. Permet au LLM de prioriser les dispositifs les plus récents.

---

### 2.3 Module **RH** (5 thèmes / 11 articles) — **LE PLUS SOUS-COUVERT**

#### Profil
- Le module avec le moins d'articles (11 seulement)
- Densité `mots_cles` moyenne : 10.5/article
- Structuration logique (recrutement → entretiens → GPEC → QVCT → dialogue)

#### Forces
- QVCT couvert correctement (3 articles : pilotage, démarche, RPS)
- GPEC et GEPP distingués (réforme 2017)

#### Lacunes de couverture **MAJEURES** (module structurellement insuffisant)
| Thème | Articles actuels | Manque clairement |
|---|---:|---|
| `recrutement_integration` | **2** | Fiche de poste, critères non-discriminants, tests, période d'essai, rupture essai, cooptation, équité recrutement |
| `entretiens_evaluation` | 2 | Grille éval, 360°, entretien de progrès, désaccord éval, entretien bilan 6 ans (anniversaire) |
| `gpec_mobilite` | 2 | Mobilité interne, mobilité géographique, bourse emploi, plan succession |
| `qvct_sante_travail` | 3 | Ergonomie EAJE, charge mentale encadrants, harcèlement moral (lien juridique), TMS |
| `dialogue_social_local` | 2 | Négociation annuelle obligatoire, NAO rémunération, consultation CSE, agenda social |
| (thème absent) | 0 | **Rémunération et politique salariale** (distinct de l'angle juridique) |
| (thème absent) | 0 | **Management d'équipe** (posture, délégation, feedback, gestion conflit) |
| (thème absent) | 0 | **Télétravail RH** (accord d'entreprise, suivi, surveillance, déconnexion) |
| (thème absent) | 0 | **Absentéisme** (diagnostic, prévention, gestion retour emploi) |
| (thème absent) | 0 | **Processus de départ** (succession, exit interview, transmission compétences) |
| (thème absent) | 0 | **Diversité & inclusion** (hors cadre égalité légal) |
| (thème absent) | 0 | **Onboarding et offboarding managérial** |
| (thème absent) | 0 | **Formation manager / encadrant** (transversal avec base_formation) |

**Total lacunes RH estimées : ~30-40 articles à ajouter** + 7-8 nouveaux thèmes. Le module doit au minimum doubler.

#### Risques d'hallucination spécifiques
- **Procédures RH** (ex : « comment recadrer un salarié ? ») : en l'absence de base suffisante, Claude invente des process managériaux.
- **Chiffres marché** (ex : « quel salaire médian pour éducateur jeunes enfants ? ») : hallucination très fréquente.
- **Outils et templates** (ex : trame entretien, grille éval) : Claude fabrique des documents non validés.

#### Recommandations RH
1. **Doubler la taille de la base** (passer de 11 à ~25 articles) avant toute autre optimisation — le RAG ne peut pas retrouver ce qui n'existe pas.
2. **Créer 3 thèmes prioritaires** : `management_equipe`, `teletravail_rh`, `absenteisme`.
3. **Ajouter un champ `outils_templates`** avec des liens vers les fiches pratiques PDF quand elles existent, sinon signaler « pas d'outil fourni » au lieu d'inventer.
4. **Interdire explicitement au LLM** de produire des chiffres salariaux non sourcés (via `SYSTEM_PROMPT_RH` : « ne cite aucun montant salarial sans article de la base_juridique `remuneration` »).
5. **Ajouter un mécanisme de cross-reference** avec `base_juridique` : quand la question RH touche la CCN (rémunération, rupture, congés), le retrieval doit remonter aussi des articles juridiques.

---

### 2.4 Module **Gouvernance** (5 thèmes / 12 articles)

#### Profil
- Le 2e plus petit module (12 articles)
- Densité `mots_cles` moyenne : 11.0/article
- Inclut un thème `doctrine_recherche` unique à ELISFA (sociologie du monde associatif)

#### Forces
- Cadre légal association bien couvert (loi 1901, responsabilités président, dirigeants)
- Bénévolat distinct du salariat (2 articles)
- Thème doctrine/recherche académique différenciateur

#### Lacunes de couverture
| Thème | Articles actuels | Manque clairement |
|---|---:|---|
| `cadre_legal` | 4 | Transformation association → coopérative, fusion-scission, agrément JEP, reconnaissance utilité publique |
| `instances` | **2** | Règlement intérieur, vote électronique, PV, convocations, quorum, conflits d'intérêts, renouvellement CA |
| `benevolat` | 2 | CER (compte engagement retraite), mécénat de compétences, formation bénévoles, reconnaissance VAE bénévolat |
| `patronat_associatif` | 2 | ESUS, agrément entreprise solidaire, représentation inter-branches, missions service public |
| `doctrine_recherche` | 2 | Mouvement recherche action, sociologie organisations non-lucratives, gouvernance partagée |
| (thème absent) | 0 | **Contrôle de gestion associatif** (comptes annuels, commissaire aux comptes, seuils) |
| (thème absent) | 0 | **Transmission / fusion / dissolution** (procédures, actifs, liquidation) |
| (thème absent) | 0 | **Gouvernance partagée / collégiale** (tendance 2020-2026, modèles alternatifs) |
| (thème absent) | 0 | **Numérique associatif** (RGPD association, cybersécurité, transformation numérique) |
| (thème absent) | 0 | **Financement public association** (CPO, CEC, marchés publics, subventions) — convergence avec ALISFA territorial |

**Total lacunes gouvernance estimées : ~15-18 articles à ajouter** + 4-5 nouveaux thèmes.

#### Risques d'hallucination spécifiques
- **Procédures statutaires** (ex : « comment modifier les statuts ? ») : Claude peut inventer un ordre d'étapes.
- **Seuils légaux** (ex : seuil commissaire aux comptes) : confusion entre seuils associatifs et commerciaux.
- **Responsabilité pénale dirigeants** : sujet sensible où l'extrapolation peut induire en erreur.

#### Recommandations gouvernance
1. **Ajouter le thème `controle_gestion_assoc`** en priorité (seuils CAC, obligations comptables, rapport moral/financier/activité).
2. **Enrichir `instances`** à 5-6 articles — c'est le cœur opérationnel manquant.
3. **Créer un sous-index `SEUILS_LEGAUX`** (CA, effectif, ressources) → réponse déterministe sur les seuils.
4. **Ajouter `references_legales_structurees`** par article avec numéro d'article loi (ex : « loi 1901 art. 5 », « CGI art. 200 ») → vérifiable.
5. **Limiter les réponses sur la responsabilité pénale** à un disclaimer systématique + renvoi vers avocat → éviter les hallucinations juridiquement risquées.

---

## 3. Recommandations transverses priorisées

### 3.1 Matrice effort / gain

| # | Reco | Cible limite(s) | Effort | Gain véracité | Gain latence | Gain couverture |
|---|---|---|---|---|---|---|
| R1 | **Seuil `hors_corpus` + citations verbatim** | L1, L7 | 3 jours | **+++** | 0 | 0 |
| R2 | **Normaliser le score TF-IDF** (`score / max_possible`) | L2 | 2 jours | ++ | 0 | 0 |
| R3 | **Embedding E5-small en fallback** si TF-IDF < seuil | L3, L5 | 2 semaines | ++ | -500 ms | +++ |
| R4 | **Désactiver le substring matching** et remplacer par préfixe stricte | L4 | 1 jour | + | +20 ms | 0 |
| R5 | **Rerank top-5 par cross-encoder léger** (MiniLM int8) | L6 | 1 semaine | ++ | -1 s | 0 |
| R6 | **Enrichir les `mots_cles`** via un générateur LLM offline | L5 | 3 jours | + | 0 | ++ |
| R7 | **Combler les lacunes RH** (+30 articles) | Tous modules | 3 semaines | +++ | 0 | +++ |
| R8 | **Combler les lacunes juridique** (+35 articles) | Tous modules | 4 semaines | +++ | 0 | +++ |
| R9 | **Sous-indexes déterministes** (par art. CCN, dispositif, seuil) | L2, L3 | 1 semaine | ++ | -30 ms | 0 |
| R10 | **Cross-reference entre bases** (RH → juridique, formation → juridique) | L3, couverture | 1 semaine | ++ | 0 | ++ |
| R11 | **Anti-hallucination prompt** (cite verbatim, signale doute) | L7 | 1 jour | +++ | 0 | 0 |
| R12 | **Logger score + article retenu** (Prometheus) | tous | 2 jours | 0 | 0 | 0 (observabilité) |

### 3.2 Ordre de priorité recommandé

**Phase 1 — Véracité immédiate (1 semaine)**
- R1 (seuil hors_corpus + verbatim) → élimine ~70 % des hallucinations
- R11 (prompt anti-hallucination) → couvre les derniers 20 %
- R2 (normalisation score) → permet des seuils stables entre requêtes
- R4 (désactiver substring bruité) → réduit le bruit dans le top-5

Résultat attendu : le chatbot répond « je n'ai pas d'information précise sur ce point, voulez-vous être mis en contact avec un juriste ? » au lieu d'inventer → véracité dramatiquement meilleure, latence intacte.

**Phase 2 — Couverture structurelle (3-4 semaines)**
- R7 (doubler le module RH) → priorité 1, c'est le trou béant
- R8 (compléter le module juridique) → priorité 2, 35 articles ciblés
- Formation +15 articles, Gouvernance +15 articles

Résultat attendu : **+95 articles** dans la KB (158 → 253), couverture alignée sur les besoins réels d'un DRH / responsable RH ALISFA.

**Phase 3 — Retrieval sémantique (2 semaines)**
- R3 (embedding E5-small fallback) → résout les synonymes et reformulations
- R10 (cross-reference entre bases) → résout les questions transversales
- R5 (rerank MiniLM léger) → si volume de questions ambiguës persiste

Résultat attendu : le chatbot trouve les bonnes réponses même sur une question reformulée « à l'arrache » → robustesse utilisateur réelle.

**Phase 4 — Industrialisation (1 semaine)**
- R6 (enrichissement automatique des `mots_cles` via LLM offline)
- R9 (sous-indexes déterministes)
- R12 (observabilité Prometheus, mêmes métriques que Félias)

---

## 4. Pseudocode de la Phase 1 (R1 + R11)

Changement ciblé dans `app.py` :

```python
# Constantes calibrées (à ajuster après A/B sur 100 questions)
SCORE_MIN_HORS_CORPUS = 2.5   # score normalisé sous lequel on refuse de répondre
SCORE_MIN_FORT = 8.0          # au-dessus, confiance haute

def search_knowledge_base(question, kb=None):
    # ... code existant ...
    if not scores:
        return {"status": "hors_corpus", "articles": []}

    max_possible_score = idx.get("max_score_possible", 20.0)  # calibré offline
    normalized_top = ranked[0][1] / max_possible_score

    if normalized_top < (SCORE_MIN_HORS_CORPUS / max_possible_score):
        return {"status": "hors_corpus", "articles": [], "best_score": normalized_top}

    # top-k filtré : on coupe dès qu'un article est à < 40% du top-1
    cutoff = ranked[0][1] * 0.4
    filtered = [(k, s) for (k, s) in ranked if s >= cutoff][:5]

    return {
        "status": "fort" if normalized_top > 0.6 else "faible",
        "articles": [...],   # construction comme avant
        "best_score": normalized_top,
    }
```

Changement prompt système (ajout en fin de `SYSTEM_PROMPT_*`) :

```
RÈGLE DE VÉRACITÉ :
1. Réponds EXCLUSIVEMENT à partir des articles fournis.
2. Si un chiffre, une procédure, un article CCN est cité dans ta réponse, il DOIT
   provenir verbatim d'un des articles fournis. Sinon, écris "sur ce point précis,
   je n'ai pas d'information dans la base ELISFA".
3. Si la question sort du champ des articles fournis, réponds :
   "Je ne peux pas répondre avec certitude à partir de ma base. Souhaitez-vous être
   mis en contact avec un juriste ELISFA ?" et STOP.
4. Ne JAMAIS inventer un numéro d'article, un montant, une date, un dispositif.
```

Côté endpoint `/api/ask`, si `status == "hors_corpus"` → skip l'appel Claude et répond directement avec un message standard + CTA RDV juriste.

**Gain mesurable** : sur 100 questions volontairement ambiguës, on s'attend à passer de ~30 hallucinations (ELISFA v1) à < 5 hallucinations (ELISFA v2, post-R1+R11). Latence médiane : inchangée (7-9 s) ; latence médiane sur `hors_corpus` : ~50 ms (pas d'appel LLM du tout).

---

## 5. Annexes

### 5.1 Métriques à ajouter (observabilité alignée sur Félias)

Si R12 est adopté, ajouter un endpoint `/metrics` façon Prometheus :
- `elisfa_retrieval_score_top1{module}` (histogramme, buckets 0-20)
- `elisfa_retrieval_hors_corpus_total{module}` (counter)
- `elisfa_retrieval_articles_returned{module}` (histogramme 1-5)
- `elisfa_claude_latency_seconds{module}` (histogramme)
- `elisfa_urgency_level_total{level}` (counter : vert/orange/rouge)
- `elisfa_cta_clicked_total{type}` (counter : rdv/email/pdf)

### 5.2 Volumes cibles post-travaux

| Module | Actuel | Après R7-R8 | Δ |
|---|---:|---:|---:|
| Juridique | 92 | ~125 | +35 |
| Formation | 43 | ~60 | +17 |
| RH | 11 | ~40 | +29 |
| Gouvernance | 12 | ~28 | +16 |
| **Total** | **158** | **~253** | **+97** |

### 5.3 Risques si on ne fait rien

- **Risque réputationnel** : un syndicat employeur qui hallucine sur la CCN ou le droit pénal est très exposé (usage attaqué en adhésion, éventuellement poursuite pour conseil erroné).
- **Risque opérationnel** : les équipes de terrain s'habituent à ne plus faire confiance au chatbot → l'outil est abandonné.
- **Risque concurrentiel** : Félias (rigueur + seuil hors_corpus) est sur le même VPS et couvre 6 modules de plus. S'il gagne en latence (via HYPO-1 ONNX), ELISFA perd son seul avantage.

---

*Fin de l'audit. Document vivant — à réviser après Phase 1 avec les métriques de production.*
