# Enrichissement hyperliens — Module Formation ELISFA
**Date :** 2026-04-21
**Cible :** `data/base_formation.json` (43 articles, 15 thèmes)
**Constat :** **0 % d'articles liés à une source officielle** — le plus gros déficit des 4 bases.

---

## 0. État comparatif des 4 bases (rappel)

| Base | Articles | Couverture liens | URLs/article | Hosts principaux |
|---|---|---|---|---|
| juridique | 92 | **100 %** | 2.08 | legifrance (153), alisfa (10), service-public (7) |
| **formation** | **43** | **0 %** | **0.00** | **— (aucun)** |
| rh | 11 | 100 % | 2.91 | legifrance (10), travail-emploi (7), anact (5) |
| gouvernance | 12 | 100 % | 3.17 | associations.gouv (12), legifrance (7) |

**Formation** est la seule base où le champ `reponse.liens` est systématiquement absent. C'est l'action la plus rentable pour homogénéiser l'expérience utilisateur (le rendu front suppose que tous les modules exposent des liens sortants).

---

## 1. Sources officielles à mobiliser

| Source | URL racine | Utilité principale | Articles ciblés |
|---|---|---|---|
| **Légifrance — Code du travail** | https://www.legifrance.gouv.fr/codes/texte_lc/LEGITEXT000006072050/ | Fondement légal (L6xxx) | 30+ articles |
| **Légifrance — CCN ALISFA IDCC 1261** | https://www.legifrance.gouv.fr/conv_coll/id/KALICONT000005635384 | CCN (chap. VIII formation) | 15+ articles |
| **travail-emploi.gouv.fr** | https://travail-emploi.gouv.fr/formation-professionnelle | Portail officiel ministère Travail | Tous les articles |
| **moncompteformation.gouv.fr** | https://www.moncompteformation.gouv.fr/ | Portail CPF salarié | `cpf-*`, `droit-03` |
| **France Compétences** | https://www.francecompetences.fr/ | Régulateur + RNCP | `acteur-*`, `vae-*` |
| **Uniformation (OPCO Cohésion sociale)** | https://www.uniformation.fr/ | OPCO de la branche ALISFA | `plan-*`, `oblig-03`, `cat-*`, `cpnef-*` |
| **Centre Inffo** | https://www.centre-inffo.fr/ | Expertise formation pro | `acteur-*`, `cep-*` |
| **Transitions Pro** | https://www.transitionspro.fr/ | PTP / CPF Transition | `trans-*` |
| **Apprentissage / alternance** | https://travail-emploi.gouv.fr/apprentissage | Portail apprentissage | `alter-*` |
| **VAE** | https://vae.gouv.fr/ | Portail VAE | `vae-*` |
| **CPNEF ALISFA** | https://www.cpnef.com/ | CPNEF branche | `cpnef-*`, `acteur-02` |
| **ALISFA (branche)** | https://www.alisfa.fr/ | Fiches branche | `gpec-*`, `cat-*`, `rac-*` |
| **Qualiopi / RNQ** | https://travail-emploi.gouv.fr/la-certification-qualiopi | Certification organismes | `acteur-04` |
| **service-public.fr** | https://www.service-public.fr/particuliers/vosdroits/N20461 | Grand public salarié | `oblig-02`, `cpf-01`, `droit-01` |

---

## 2. Mapping article par article (43 articles, 15 thèmes)

> Chaque article reçoit entre 2 et 4 liens : **1 fondement juridique** (Légifrance) + **1 portail officiel** (travail-emploi / CPF / VAE / etc.) + **1 source branche** (Uniformation / CPNEF / ALISFA) quand pertinent.

### 2.1 `obligations_employeur` (4 articles)

| ID | Question | Liens proposés |
|---|---|---|
| `oblig-01` | Obligations de l'employeur en formation | ① Code du travail L6321-1 (Légifrance) ② travail-emploi.gouv.fr/obligations-employeur ③ Uniformation (page employeur) |
| `oblig-02` | Entretien professionnel | ① C. trav. L6315-1 ② service-public.fr entretien-pro ③ Uniformation guide entretien |
| `oblig-03` | Contribution formation ALISFA | ① CCN ALISFA chap. VIII ② URSSAF (taux formation) ③ Uniformation barème 2026 |
| `oblig-04` | Entretien pro + état des lieux 6 ans | ① L6315-1 ② travail-emploi abondement correctif 3000 € ③ Centre Inffo fiche entretien |

```json
"liens": [
  { "titre": "Art. L6321-1 Code du travail — Obligations employeur", "url": "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000037385657/" },
  { "titre": "Formation professionnelle — Portail Ministère du Travail", "url": "https://travail-emploi.gouv.fr/formation-professionnelle/" },
  { "titre": "Uniformation — Espace employeur ALISFA", "url": "https://www.uniformation.fr/branche/acteurs-du-lien-social-et-familial" }
]
```

### 2.2 `plan_competences` (3 articles)

| ID | Question | Liens proposés |
|---|---|---|
| `plan-01` | Mettre en place un PDC | ① L6321-1 ② travail-emploi PDC ③ Uniformation PDC |
| `plan-02` | Financements Uniformation | ① Uniformation barèmes ② France Compétences ③ CPNEF.com ACT |
| `plan-03` | Construire et financer le PDC | ① L6321-1 et L6321-2 ② Centre Inffo PDC ③ Uniformation |

### 2.3 `cpf` (2 articles)

| ID | Question | Liens proposés |
|---|---|---|
| `cpf-01` | Fonctionnement du CPF | ① moncompteformation.gouv.fr ② C. trav. L6323-1 à L6323-5 ③ service-public CPF |
| `cpf-02` | Abondements + reste à charge 100 € | ① L6323-4 / L6323-14 ② moncompteformation (reste à charge) ③ Uniformation abondements branche |

### 2.4 `transition_pro` (3 articles)

| ID | Question | Liens proposés |
|---|---|---|
| `trans-01` | CPF Transition (ex-CIF) | ① transitionspro.fr ② L6323-17-1 ③ travail-emploi PTP |
| `trans-02` | Pro-A / PREC | ① L6324-1 ② travail-emploi Pro-A ③ Uniformation Pro-A |
| `trans-03` | Projet Transition Professionnelle | ① transitionspro.fr ② L6323-17-1 ③ Centre Inffo PTP |

### 2.5 `alternance` (3 articles)

| ID | Question | Liens proposés |
|---|---|---|
| `alter-01` | Contrat d'apprentissage | ① L6221-1 et suivants ② alternance.emploi.gouv.fr ③ Uniformation apprentissage |
| `alter-02` | Contrat de professionnalisation | ① L6325-1 ② travail-emploi contrat pro ③ Uniformation |
| `alter-03` | Apprentissage vs pro (différences) | ① L6221-1 / L6325-1 ② travail-emploi comparatif ③ Aides embauche 6000 € (décret) |

### 2.6 `vae_bilan` (2 articles)

| ID | Question | Liens proposés |
|---|---|---|
| `vae-01` | VAE | ① vae.gouv.fr ② C. trav. L6411-1 ③ France Compétences RNCP |
| `vae-02` | Bilan de compétences | ① C. trav. L6313-4 ② moncompteformation bilan ③ Centre Inffo bilan |

### 2.7 `cep_afest` (6 articles)

| ID | Question | Liens proposés |
|---|---|---|
| `cep-01` | CEP | ① L6111-6 ② mon-cep.org ③ Centre Inffo CEP |
| `cep-02` | AFEST | ① L6313-2 ② travail-emploi AFEST ③ ANACT guide AFEST |
| `cep-03` | FNE-Formation | ① travail-emploi FNE ② DREETS (DGEFP) ③ Uniformation FNE |
| `cep-04` | CléA | ① certificat-clea.fr ② France Compétences CléA ③ Uniformation CléA |
| `cep-05` | Tutorat & financement | ① L6223-5 ② Uniformation tutorat ③ CPNEF ALISFA |
| `cep-06` | AFEST (détail L6313-2) | ① L6313-2 ② ANACT AFEST ③ Centre Inffo AFEST |

### 2.8 `droits_salaries` (3 articles)

| ID | Question | Liens proposés |
|---|---|---|
| `droit-01` | Droits à la formation des salariés | ① L6321-1 / L6323-1 ② travail-emploi droits salarié ③ service-public CPF |
| `droit-02` | Refuser une formation | ① Cass. soc. 23/01/2001 (Judilibre) ② travail-emploi refus formation ③ Centre Inffo fiche refus |
| `droit-03` | CPF sans accord employeur | ① L6323-17 ② moncompteformation (hors temps travail) ③ service-public CPF autonomie |

### 2.9 `financement_cpnef` (4 articles)

| ID | Question | Liens proposés |
|---|---|---|
| `cpnef-01` | Financements CPNEF 2026 | ① cpnef.com ② alisfa.fr CPNEF ③ Uniformation |
| `cpnef-02` | Demander un ACT | ① cpnef.com ACT ② alisfa.fr ACT |
| `cpnef-03` | FNE-Formation (bénéficier) | ① travail-emploi FNE ② Uniformation FNE ③ DGEFP |
| `cpnef-04` | OPCO Cohésion sociale | ① L6332-1 ② uniformation.fr (Cohésion sociale) ③ France Compétences OPCO |

### 2.10 `acteurs_formation` (4 articles)

| ID | Question | Liens proposés |
|---|---|---|
| `acteur-01` | Acteurs formation pro | ① France Compétences ② Uniformation ③ Caisse des Dépôts (CPF) ④ Transitions Pro |
| `acteur-02` | Rôle CPNEF ALISFA | ① cpnef.com ② alisfa.fr CPNEF ③ CCN ALISFA art. CPNEF |
| `acteur-03` | Référents formation en région | ① uniformation.fr (annuaire régional) ② alisfa.fr référents |
| `acteur-04` | Qualiopi | ① L6316-1 ② travail-emploi Qualiopi ③ France Compétences RNQ |

### 2.11 `gpec_metiers` (2 articles)

| ID | Question | Liens proposés |
|---|---|---|
| `gpec-01` | Métiers branche + GPEC | ① alisfa.fr fiches métiers ② observatoire-emploi-formation.fr (Cohésion sociale) ③ CPNEF.com |
| `gpec-02` | Pro-A (reconversion alternance) | ① L6324-1 ② travail-emploi Pro-A ③ Uniformation Pro-A |

### 2.12 `textes_legaux` (1 article)

| ID | Question | Liens proposés |
|---|---|---|
| `texte-01` | Principaux textes droit formation continue | ① Loi 2018-771 « Avenir professionnel » ② Code du travail Livre III Partie VI ③ Centre Inffo panorama législatif |

### 2.13 `vae_reforme` (1 article)

| ID | Question | Liens proposés |
|---|---|---|
| `vae-03` | VAE réformée (loi 2022) | ① vae.gouv.fr (nouvelle VAE) ② Loi n° 2022-1598 (marché du travail) ③ France VAE (plateforme) |

### 2.14 `catalogue_2026` (4 articles)

| ID | Question | Liens proposés |
|---|---|---|
| `cat-01` | Barèmes Uniformation 2026 | ① uniformation.fr barèmes ② alisfa.fr barèmes branche ③ CPNEF 2026 |
| `cat-02` | Calcul contributions 2026 | ① URSSAF (collecte CUFPA) ② Uniformation calcul ③ L6331-1 |
| `cat-03` | Aides apprentissage 2026 | ① alternance.emploi.gouv.fr aides ② Décret aide unique (à citer en annotation) ③ Uniformation apprentissage |
| `cat-04` | Services gratuits Uniformation 2026 | ① uniformation.fr services ② alisfa.fr services branche |

### 2.15 `reste_a_charge_certifiant` (1 article)

| ID | Question | Liens proposés |
|---|---|---|
| `rac-01` | Reste à charge formation certifiante ALISFA | ① uniformation.fr AEPE/CPJEPS/BPJEPS ② alisfa.fr certifiants ③ CPNEF financements ④ France Compétences RNCP (diplômes) |

---

## 3. Patch JSON — Exemple prêt à injecter (article `oblig-01`)

```json
{
  "id": "oblig-01",
  "question_type": "Quelles sont les obligations de l'employeur en matière de formation ?",
  "mots_cles": ["obligation", "employeur", "formation", "adapter", "poste", "maintien", "employabilité", "capacité", "..."],
  "reponse": {
    "synthese": "…",
    "fondement_legal": "…",
    "fondement_ccn": "…",
    "application": "…",
    "vigilance": "…",
    "sources": [
      "Art. L6321-1 du Code du travail",
      "CCN ALISFA chap. VIII — Formation professionnelle",
      "Ministère du Travail — Formation professionnelle"
    ],
    "liens": [
      {
        "titre": "Art. L6321-1 Code du travail — Adaptation du salarié à son poste",
        "url": "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000037385657/"
      },
      {
        "titre": "Formation professionnelle — Portail Ministère du Travail",
        "url": "https://travail-emploi.gouv.fr/formation-professionnelle/"
      },
      {
        "titre": "CCN ALISFA (IDCC 1261) — Chapitre VIII Formation",
        "url": "https://www.legifrance.gouv.fr/conv_coll/id/KALICONT000005635384"
      },
      {
        "titre": "Uniformation — OPCO Cohésion sociale (branche ALISFA)",
        "url": "https://www.uniformation.fr/branche/acteurs-du-lien-social-et-familial"
      }
    ]
  },
  "fiches_pratiques": [ /* inchangé */ ]
}
```

---

## 4. Recommandations complémentaires

### R1. Harmoniser la structure `liens` avec les autres bases
Le champ `reponse.liens` doit être systématiquement présent (même vide `[]`) pour éviter des `KeyError` dans le frontend. Idéalement :
- `titre` : formulation humaine (ex. « Art. L6321-1 Code du travail — Adaptation du salarié »)
- `url` : URL canonique https (éviter les redirections)
- `type` (optionnel, à ajouter) : `"legifrance"` | `"portail_officiel"` | `"branche"` | `"jurisprudence"` — permet un tri/filtrage frontend.

### R2. Valider les URLs avant injection
Certaines URL profondes (ex. articles L63xx sur Légifrance) peuvent avoir changé. Script de validation :

```bash
# À exécuter avant injection du patch
python3 -c "
import json, requests
with open('_patch_liens_formation.json') as f: patch = json.load(f)
for item in patch:
    for lien in item.get('liens', []):
        try:
            r = requests.head(lien['url'], allow_redirects=True, timeout=5)
            print(f'{r.status_code} — {lien[\"url\"]}')
        except Exception as e:
            print(f'ERR  — {lien[\"url\"]} — {e}')
"
```

### R3. Privilégier les ancres stables
- **Légifrance codes** : préférer `codes/texte_lc/LEGITEXT000006072050/` (racine Code du travail) puis la référence article dans le titre, plutôt que `codes/article_lc/LEGIARTI.../` qui peut être réécrit à chaque modification.
- **travail-emploi.gouv.fr** : URLs slug ont été stables sur 2022-2025 — sûr à court terme.
- **Uniformation** : la réorganisation des pages branche est fréquente — prévoir une revue annuelle.

### R4. Citer systématiquement l'article CCN et l'article CdT
Format suggéré dans `sources` (et reflété dans `liens`) :
```
"sources": [
  "Art. L6321-1 C. trav. — Adaptation du salarié",
  "CCN ALISFA IDCC 1261 — Chap. VIII art. 8.2",
  "Uniformation — Branche ALISFA (page employeur)"
]
```

### R5. Ajouter 3 thèmes manquants pour la complétude
Le module formation gagnerait à couvrir :
- **`transition_ecologique_formation`** : plans de reconversion verte, FNE transitions écologique/numérique/démographique — 2-3 articles.
- **`sanctions_non_formation`** : quelles sanctions pour l'employeur qui ne respecte pas ses obligations (dommages-intérêts, provisions) — 1 article.
- **`formation_elus_cse`** : formation des représentants du personnel (art. L2145-5 et suivants), formation SSCT — 2 articles. Ce thème relie formation ↔ CSE/IRP (déjà dans juridique) et peut servir de pont inter-modules.

### R6. Bonus — Ajouter un champ `article_legifrance_precis`
Pour chaque article, stocker l'identifiant LEGIARTI associé à l'article principal, ce qui permettrait au frontend d'afficher une pastille « Art. L6321-1 » cliquable à côté du titre :

```json
"fondement_legal_ids": ["L6321-1", "L6321-2", "L6323-1"]
```

Côté frontend : résolution `L6321-1` → `https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000037385657/`.

---

## 5. Bilan avant / après — Module formation

| Métrique | Avant (2026-04-21) | Après enrichissement | Gain |
|---|---|---|---|
| Articles avec `liens` | 0 / 43 (0 %) | 43 / 43 (100 %) | +100 pts |
| URLs total | 0 | ~110-130 | +110 |
| URLs/article | 0.00 | ~2.6 | +2.6 |
| Sources uniques | 0 | ~14 | +14 |
| Thèmes | 15 | 15 (ou 18 avec R5) | +3 |
| Homogénéité avec autres bases | ❌ | ✅ | parité atteinte |

---

## 6. Priorisation d'injection (phasage)

**Phase 1 — Quick wins (1 jour)** : injecter les 191 URL Légifrance/travail-emploi.gouv.fr + portails CPF/VAE/Uniformation sur tous les articles. Ces URL sont les plus stables et ont le plus de valeur pédagogique. Gain : 0 % → 100 % couverture.

**Phase 2 — Sources branche (0.5 jour)** : ajouter les URL cpnef.com, alisfa.fr, elisfa.fr, Uniformation pages-branche. Ces URL sont plus volatiles mais essentielles pour la légitimité « branche ». Gain : +1 URL branche par article.

**Phase 3 — Sources profondes et jurisprudence (0.5 jour)** : pour les articles à enjeu contentieux (droit-02 refus formation, oblig-01 obligation employeur) ajouter 1-2 arrêts clés Cour de cassation via Judilibre. Gain : crédibilité juridique renforcée.

**Phase 4 — R5 (2 jours)** : créer les 3 thèmes manquants (transition_ecologique, sanctions_non_formation, formation_elus_cse) avec 5-6 articles complets.

**Coût total estimé : 4 jours développeur** pour passer de 0 % à 100 % + 3 thèmes.

---

## 7. Ordre de travail des 4 modules (récap 2026-04-21)

| Module | Couverture liens | Action prioritaire | Effort |
|---|---|---|---|
| juridique | 100 % | Audit et validation des 191 URLs existantes (certaines LEGIARTI profondes peuvent avoir bougé) | 1 j |
| **formation** | **0 %** | **Injection complète des liens (ce deliverable)** | **4 j** |
| rh | 100 % | Étendre de 11 à ~20 articles (gap de contenu, pas de liens) | 3 j |
| gouvernance | 100 % | Ajouter les 4 nouveaux thèmes (`_LIENS_gouvernance_*`) | 3 j |

**Ordre conseillé** : **formation → gouvernance (nouveaux thèmes) → rh (extension contenu) → juridique (audit URLs)**. Rationale : formation a le déficit le plus visible (un utilisateur sait tout de suite qu'il manque des liens), gouvernance a des nouveaux thèmes déjà spécifiés, RH manque de contenu plus que de liens, juridique est en bon état et l'audit est une opération de maintenance moins urgente.

---

**Fin du deliverable.** Prochaines étapes naturelles : valider le mapping article-par-article ci-dessus avec le pôle juridique ELISFA, puis générer le patch JSON unique `_patch_liens_formation.json` à appliquer via un script d'injection idempotent.
