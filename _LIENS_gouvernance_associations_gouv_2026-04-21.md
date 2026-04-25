# Liens officiels associations.gouv.fr → module Gouvernance
## Intégration dans `base_gouvernance.json` — 30 guides structurés

Source : [Guides pratiques pour la vie associative — associations.gouv.fr](https://associations.gouv.fr/retrouvez-tous-les-guides-pratiques-pour-la-vie-associative)

Tous les URLs relatifs `/sites/default/...` sont préfixés par `https://associations.gouv.fr` ci-dessous (ainsi les liens sont autoporteurs pour insertion directe dans le champ `liens` des articles).

---

## 1. Mapping des 30 guides aux 5 thèmes existants

### 🏛️ `cadre_legal` (4 articles existants → +7 liens de référence)

À injecter dans le champ `liens` des articles `cadre_legal/*` :

- [Guide pratique des associations (portail général)](https://guidepratiqueasso.org/)
- [Guide pratique du contrat d'engagement républicain (FAQ CER 2023)](https://associations.gouv.fr/sites/default/files/2025-10/faq_cer_fevrier_2023_vf.pdf) — obligatoire pour toute association recevant des subventions publiques
- [Guide du tronc commun d'agrément (2022)](https://associations.gouv.fr/sites/default/files/2025-06/guide_tronc_commun_agrement_2022%20%281%29.pdf) — critères & procédures d'agrément
- [Guide AFA — gouvernance et gestion du don (probité)](https://associations.gouv.fr/sites/default/files/2025-10/guideafa_arupfrup_web.pdf) — prévention des risques d'atteinte à la probité pour dirigeants
- [Guide CNIL — sensibilisation RGPD pour les associations](https://associations.gouv.fr/sites/default/files/2025-10/cnil-guide_association.pdf)
- [LOLF appliquée aux associations](https://associations.gouv.fr/sites/default/files/2025-10/guide_LOLF_vie_associative_2014.pdf) — encadrement du financement public
- [Guide de la Côte d'Or (gestion administrative complète)](https://associations.gouv.fr/sites/default/files/2025-10/guidepratique.pdf)

### 🗳️ `instances` (2 articles existants → +3 liens + 4 articles proposés ci-dessous)

Liens à injecter dans les articles `instances/*` :

- [Guide IDEAS — 90 bonnes pratiques](https://ideas.asso.fr/le-guide-ideas/) — référentiel sur la gouvernance, l'évaluation, le pilotage (PDF téléchargeable)
- [Guide pratique des associations](https://guidepratiqueasso.org/) — fonctionnement AG / CA / bureau
- [Développons l'égalité F/H dans les associations](https://associations.gouv.fr/sites/default/files/2025-10/asso_egalite_hf_guide_2016v2.pdf) — parité dans les instances

### 🤝 `benevolat` (2 articles existants → +6 liens riches)

Liens à injecter dans les articles `benevolat/*` :

- [Guide du bénévolat 2024-2025 (référence)](https://associations.gouv.fr/sites/default/files/2025-05/guide_benevolat_2024-2025.pdf) — le document de référence à citer en première intention
- [Le compte d'engagement citoyen (CEC)](https://associations.gouv.fr/sites/default/files/2025-06/le_compte_d_engagement_citoyen-2.pdf) — dispositif de valorisation de l'engagement
- [S'engager dans la vie associative en tant que mineur (2025)](https://associations.gouv.fr/sites/default/files/2025-10/engagement_associatif_des_mineur_es.pdf)
- [Fiches du portefeuille de compétences bénévoles](https://associations.gouv.fr/sites/default/files/2025-10/DOC1portefeuilleliens.pdf)
- [Valorisation comptable du bénévolat](https://associations.gouv.fr/sites/default/files/2025-10/valorisation_comptable_benevolat%20%281%29.pdf) — méthodes pour traduire le bénévolat en comptabilité
- [Guide pratique du mécénat de compétences (2021)](https://associations.gouv.fr/sites/default/files/2025-10/guide-pratique-mecenat-competences-novembre2021.pdf) — articulation salarié d'entreprise / bénévole

### 🏢 `patronat_associatif` (2 articles existants → +4 liens)

- [Association & protection sociale — guide URSSAF](https://associations.gouv.fr/sites/default/files/2025-10/guide_protection_sociale.pdf) — obligations sociales employeurs
- [Les groupements d'employeurs du secteur non-marchand (Avise)](https://associations.gouv.fr/sites/default/files/2025-10/Groupement-employeurs_2014_Avise_Reperes_.pdf)
- [Accompagner les groupements d'employeurs associatifs](https://associations.gouv.fr/sites/default/files/2025-10/GuideGE.pdf)
- [Structurer une offre territoriale d'accompagnement PMAE (Avise/RNMA)](https://associations.gouv.fr/sites/default/files/2025-10/Guide_Structurer_une_offre_territoriale_d_accompagnement_PMAE_2013_RNMA_AVISE-2.pdf) — développement d'accompagnement régional
- [Guide sur le Contrat Unique et les contrats aidés (DREETS IdF)](https://associations.gouv.fr/sites/default/files/2025-10/guide_employeur_paris_actualise_120814-2.pdf)

### 🎓 `doctrine_recherche` (2 articles existants → rien à ajouter)

Les guides pratiques gouv.fr sont **opérationnels**, pas académiques. Ce thème reste alimenté par la littérature recherche et ses 2 articles existants. **Proposition** : ajouter en `liens` une simple référence vers le portail associations.gouv.fr :

- [Portail officiel de la vie associative (associations.gouv.fr)](https://associations.gouv.fr/retrouvez-tous-les-guides-pratiques-pour-la-vie-associative) — centralise l'ensemble des guides pratiques ressources

---

## 2. Nouveaux thèmes à créer (4 thèmes, ~12 articles)

Les 30 guides officiels rendent possibles **4 nouveaux thèmes** que la KB actuelle ne couvre pas — c'est le principal gain de valeur :

### 💰 Nouveau thème : `financement_public`

Couverture manquante critique : aucun article actuel ne traite le financement d'une association. Proposition : **5 articles** adossés aux guides officiels.

| article_id | question_type | Guides sources |
|---|---|---|
| `fp-01-subventions` | Comment solliciter une subvention publique en 2025-2026 ? | [Guide d'usage de la subvention 2025-2026](https://associations.gouv.fr/sites/default/files/2025-09/Guide_Subventions2025_HD.pdf) |
| `fp-02-cpo-eval` | Comment se déroule l'évaluation d'une convention pluriannuelle d'objectifs ? | [Guide de l'évaluation des CPO](https://associations.gouv.fr/sites/default/files/2025-10/guide_evaluation_v2012.pdf) |
| `fp-03-generosite-publique` | Comment organiser un appel à la générosité du public ? | [Guide de l'appel à la générosité du public](https://associations.gouv.fr/sites/default/files/2025-09/guide_agp.pdf) |
| `fp-04-mecenat` | Comment mettre en place un mécénat association/entreprise ? | [Le mécénat associations / entreprises](https://associations.gouv.fr/sites/default/files/2025-10/asso_mecenat_24-25.pdf) + [Guide juridique du mécénat](https://associations.gouv.fr/sites/default/files/2025-09/guide_juridique_mecenat.pdf) |
| `fp-05-investissement` | Comment placer les ressources financières d'une association ? | [Investir quand on est une association (AMF)](https://associations.gouv.fr/sites/default/files/2025-10/Investir-2.pdf) |

### 💻 Nouveau thème : `numerique_rgpd`

Couverture manquante critique : le RGPD et la transition numérique sont absents. Proposition : **3 articles**.

| article_id | question_type | Guides sources |
|---|---|---|
| `num-01-rgpd-base` | Quelles sont les obligations RGPD d'une association ? | [Guide CNIL — RGPD associations](https://associations.gouv.fr/sites/default/files/2025-10/cnil-guide_association.pdf) |
| `num-02-rgpd-sport` | Comment s'auto-évaluer sur le RGPD (secteur sport) ? | [Auto-évaluation CNIL sport amateur](https://www.cnil.fr/fr/sport-amateur-hors-contrat/tester-votre-conformite-au-rgpd) + [FAQ RGPD sport](https://www.cnil.fr/fr/sport-amateur-hors-contrat/questions-reponses) |
| `num-03-transition` | Comment évaluer la maturité numérique de mon association ? | [Autodiagnostic transition numérique (Solidatech)](https://associations.gouv.fr/sites/default/files/2026-03/solidatech-20190114-outil-auto-diagnostic-interactif.pdf) |

### ⚖️ Nouveau thème : `egalite_gouvernance`

Distinct du thème juridique `egalite` (droit du travail) : ici, il s'agit d'**égalité F/H dans les instances associatives** (bureau, CA, présidence). Proposition : **1 article**.

| article_id | question_type | Guides sources |
|---|---|---|
| `eg-01-parite-instances` | Comment promouvoir l'égalité F/H dans la gouvernance associative ? | [Développons l'égalité F/H dans les associations](https://associations.gouv.fr/sites/default/files/2025-10/asso_egalite_hf_guide_2016v2.pdf) |

### 🚪 Nouveau thème : `dissolution`

Couverture manquante critique : aucun article sur la fin de vie d'une association. Proposition : **3 articles**.

| article_id | question_type | Guides sources |
|---|---|---|
| `dis-01-procedure` | Comment dissoudre une association loi 1901 ? | [Guide pratique de la dissolution (2022)](https://associations.gouv.fr/sites/default/files/2025-10/guide_dissolution_association_loi_1901-2022.pdf) |
| `dis-02-liquidation` | Quelle est la procédure de liquidation des actifs ? | (même guide) |
| `dis-03-transmission` | Comment transmettre l'activité d'une association à une autre structure ? | (à enrichir — littérature ESS complémentaire) |

---

## 3. Snippet JSON à injecter dans `base_gouvernance.json`

### 3.1 Patch pour le thème existant `benevolat` (exemple complet, le plus enrichi)

À ajouter dans `reponse.liens` de l'article `benevolat/ben-01-statut` (ou équivalent) :

```json
"liens": [
  {
    "titre": "Guide du bénévolat 2024-2025 (référence)",
    "url": "https://associations.gouv.fr/sites/default/files/2025-05/guide_benevolat_2024-2025.pdf",
    "type": "pdf_officiel",
    "source": "associations.gouv.fr"
  },
  {
    "titre": "Le compte d'engagement citoyen (CEC)",
    "url": "https://associations.gouv.fr/sites/default/files/2025-06/le_compte_d_engagement_citoyen-2.pdf",
    "type": "pdf_officiel",
    "source": "associations.gouv.fr"
  },
  {
    "titre": "S'engager dans la vie associative en tant que mineur",
    "url": "https://associations.gouv.fr/sites/default/files/2025-10/engagement_associatif_des_mineur_es.pdf",
    "type": "pdf_officiel",
    "source": "associations.gouv.fr"
  },
  {
    "titre": "Fiches du portefeuille de compétences bénévoles",
    "url": "https://associations.gouv.fr/sites/default/files/2025-10/DOC1portefeuilleliens.pdf",
    "type": "pdf_officiel",
    "source": "associations.gouv.fr"
  },
  {
    "titre": "Valorisation comptable du bénévolat",
    "url": "https://associations.gouv.fr/sites/default/files/2025-10/valorisation_comptable_benevolat%20%281%29.pdf",
    "type": "pdf_officiel",
    "source": "associations.gouv.fr"
  },
  {
    "titre": "Guide pratique du mécénat de compétences (2021)",
    "url": "https://associations.gouv.fr/sites/default/files/2025-10/guide-pratique-mecenat-competences-novembre2021.pdf",
    "type": "pdf_officiel",
    "source": "associations.gouv.fr"
  }
]
```

### 3.2 Nouveau thème `financement_public` — squelette JSON complet

Pour copie directe dans `themes: [...]` de `base_gouvernance.json` :

```json
{
  "id": "financement_public",
  "label": "Financement public & mécénat",
  "chapitre": "Ressources financières de l'association",
  "niveau": "orange",
  "articles": [
    {
      "id": "fp-01-subventions",
      "question_type": "Comment solliciter une subvention publique en 2025-2026 ?",
      "mots_cles": [
        "subvention", "subventions", "financement public", "aide publique",
        "CERFA 12156", "Le Compte Asso", "dossier subvention",
        "DRJSCS", "DREETS", "collectivité", "mairie", "région",
        "montage dossier", "notification", "justificatif"
      ],
      "reponse": {
        "synthese": "Toute demande de subvention passe par le portail Le Compte Asso ou le CERFA 12156. Le Guide d'usage de la subvention 2025-2026 détaille : constitution du dossier, RIB, budget prévisionnel, rapport d'activité, obligations de redevabilité.",
        "application": "…",
        "fondement_ccn": "",
        "fondement_legal": "Loi 2000-321 du 12 avril 2000, décret 2001-495 du 6 juin 2001 (convention obligatoire > 23 000 €).",
        "sources": [
          "Guide d'usage de la subvention 2025-2026 (associations.gouv.fr)"
        ],
        "liens": [
          {
            "titre": "Guide d'usage de la subvention 2025-2026",
            "url": "https://associations.gouv.fr/sites/default/files/2025-09/Guide_Subventions2025_HD.pdf",
            "type": "pdf_officiel",
            "source": "associations.gouv.fr"
          },
          {
            "titre": "Portail Le Compte Asso",
            "url": "https://lecompteasso.associations.gouv.fr/",
            "type": "portail_officiel",
            "source": "associations.gouv.fr"
          }
        ],
        "vigilance": "Le contrat d'engagement républicain (CER) doit être signé avant toute attribution. Non-respect = restitution possible."
      },
      "fiches_pratiques": []
    }
  ]
}
```

---

## 4. Recommandations d'intégration

1. **Harmoniser le champ `liens`** : aujourd'hui c'est une liste de strings dans les articles existants, passer à une liste d'objets `{titre, url, type, source}` → permet un rendu cliquable côté frontend + filtrage par type (`pdf_officiel`, `portail_officiel`, `article_cnil`, etc.).
2. **Enrichir le frontend ELISFA** pour afficher ces liens en « Ressources officielles » sous chaque réponse → plus utile qu'une simple URL plaintext au milieu du markdown.
3. **Lier l'escalade gouvernance aux guides** : pour les questions sensibles (RGPD, CER, probité), si le score retrieval est faible, proposer le guide officiel correspondant plutôt que d'extrapoler.
4. **Mettre à jour les versions millésimées** :
   - Guide bénévolat 2024-2025 → remplacer par 2025-2026 dès disponibilité
   - Guide subvention 2025-2026 → surveiller la version 2026-2027 fin T4 2026
5. **Considérer un thème 5e `evaluation_partenariats`** adossé à [LOLF](https://associations.gouv.fr/sites/default/files/2025-10/guide_LOLF_vie_associative_2014.pdf) + [Guide évaluation CPO](https://associations.gouv.fr/sites/default/files/2025-10/guide_evaluation_v2012.pdf) si les questions sur l'évaluation partenariat État remontent.

---

## 5. Récapitulatif : gouvernance après intégration

| | Avant | Après intégration |
|---|---:|---:|
| Thèmes | 5 | **9** (+4 nouveaux : `financement_public`, `numerique_rgpd`, `egalite_gouvernance`, `dissolution`) |
| Articles | 12 | **~24** (+12 nouveaux articles) |
| Liens officiels structurés | ~0 | **30 liens vers guides gouv.fr** + 2 portails |
| Fiches PDF téléchargeables | 0 % | **~80 %** des nouveaux articles |
| Couverture du périmètre gouvernance | ~40 % | **~75 %** |

Le module gouvernance passe ainsi de « doctrine académique érudite mais déconnectée » à « doctrine + ressources officielles téléchargeables » — aligné sur la richesse fiches pratiques du module formation (51 %).
