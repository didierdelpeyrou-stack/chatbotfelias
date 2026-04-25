# DEVIS PRÉVISIONNEL — Reste à faire jusqu'au déploiement adhérents (janvier 2027)

**Devis n° :** 2026-002
**Date :** 25 avril 2026
**Validité :** 60 jours
**Périmètre temporel :** mai 2026 → janvier 2027 (9 mois)

---

## Prestataire

- **Nom / Raison sociale :** _[à compléter]_
- **Statut juridique :** Auto-entrepreneur
- **N° SIREN :** _[à compléter]_
- **TVA :** Franchise en base (pas de TVA)
- **Adresse :** _[à compléter]_

## Client

- **Nom :** ELISFA — Employeurs du Lien Social et FAmilial
- **Statut :** Syndicat employeur de la branche professionnelle ALISFA
- **Référent projet :** _[à compléter]_

---

## 1. Objet de la prestation

Faire suite au devis n° 2026-001 (travail réalisé du 11 → 25 avril 2026, **5 305 € HT**) en finalisant la chaîne complète du chatbot V2 jusqu'au **déploiement effectif auprès des adhérents** prévu en janvier 2027, après une **phase de bêta-test impliquant 100 utilisateurs** d'octobre à novembre 2026.

Le projet comprend 8 phases techniques + 1 phase d'expérimentation utilisateur, sur une durée de 9 mois.

---

## 2. Chronologie prévisionnelle

```
Mai 2026  ─┬─ Phase 1 : KB enrichie (sprint 5.2-data F4 → F6)
            │
Juin 2026 ─┼─ Phase 2 : Wizard financement (sprint 5.3)
            │
Juill 2026 ┼─ Phase 3 : Interface admin KB (sprint 5.4)
            │
Août 2026 ─┼─ Phase 4 : Déploiement staging (sprint 5.5 + 4.4 exec)
            │           Session test interne 10 utilisateurs (sprint 4.5)
            │
Sept 2026 ─┼─ Phase 5 : Légifrance + enrichissements + fixes (sprint 6.x)
            │
Oct 2026  ─┐
            │   Phase 6 : BÊTA-TEST 100 UTILISATEURS
Nov 2026  ─┤              - 5-7 sessions de présentation
            │              - Suivi quotidien support
            │              - Compilation feedback
Déc 2026  ─┴─ Phase 7 : CUTOVER progressif (sprint 7.x)
                          - Canary 10 % (mi-déc)
                          - Gradual 50 % (fin déc)
                          - Full 100 % (début janv 2027)

Janv 2027 ─── Phase 8 : Monitoring prod + docs + plan T1 (sprint 8.x)
              ↓
              ✅ Déploiement effectif auprès des adhérents ALISFA
```

---

## 3. Détail des phases — temps et livrables

### Phase 1 — Sprint 5.2-data : KB enrichie (mai 2026)

**Objectif** : finaliser la base de connaissances avec ~99 nouveaux articles (au-delà des 34 déjà rédigés).

| Livrable | Heures |
|---|---:|
| F4 — 25 articles métiers GPEC (cartographie ALISFA + diplômes RNCP + passerelles) | 10-12 h |
| F5 — 27 articles fonctions réglementaires (CNAF/Code action sociale/EAJE/ALSH/RSAI/médiation/SST...) | 14-18 h |
| F6 — ~12 articles intentions directeur (scénarios opérationnels) | 6-8 h |
| Fusion finale dans `data/v2/base_formation.json` + tests Pydantic stricts | 4-6 h |
| **Sous-total Phase 1** | **34-44 h** |

### Phase 2 — Sprint 5.3 : Wizard financement (juin 2026)

**Objectif** : interface conversationnelle guidée à 6 axes (type structure / métier / fonds / EMA / stagiaires / durée) pour un calcul de devis automatique.

| Livrable | Heures |
|---|---:|
| Backend FastAPI : 6 endpoints `/api/wizard/...` + arbre de décision | 6-8 h |
| Frontend : composants wizard + UX progressive (step indicator) | 5-7 h |
| Tests unitaires + intégration | 3-5 h |
| **Sous-total Phase 2** | **14-20 h** |

### Phase 3 — Sprint 5.4 : Interface admin KB (juillet 2026)

**Objectif** : permettre à l'équipe ELISFA de mettre à jour les 4 KB sans intervention dev.

| Livrable | Heures |
|---|---:|
| Backend : endpoints `/admin/kb/upload`, `/admin/kb/download`, `/admin/kb/delete` + auth admin | 5-7 h |
| Frontend : page admin avec drag-drop + listing des articles + bouton delete | 4-6 h |
| Validation Pydantic stricte avant écriture (rollback automatique si KO) | 2-3 h |
| Tests sécurité + audit log + tests E2E | 3-4 h |
| **Sous-total Phase 3** | **14-20 h** |

### Phase 4 — Sprints 5.5 + 4.4 + 4.5 : Déploiement staging et test interne (août 2026)

**Objectif** : V2 staging accessible publiquement, validation par 10 utilisateurs internes ELISFA.

| Livrable | Heures |
|---|---:|
| Sprint 5.5 — Blue-green deploy infra (VPS Hostinger, configuration nginx + certbot) | 6-8 h |
| Sprint 4.4 exécution VPS — DNS DuckDNS `felias.duckdns.org`, certif Let's Encrypt, deploy Docker compose | 3-5 h |
| Sprint 4.5 — Animation session test 10 utilisateurs internes ELISFA (préparation + visio + débrief) | 8-10 h |
| Compilation feedback + ajustements urgents | 4-6 h |
| **Sous-total Phase 4** | **21-29 h** |

### Phase 5 — Sprint 6.x : Enrichissements écosystème (septembre 2026)

**Objectif** : intégrer les sources officielles et corriger les bugs détectés en session interne.

| Livrable | Heures |
|---|---:|
| 6.1 — Intégration API Légifrance (référencement automatique articles Code travail / Code action sociale) | 10-14 h |
| 6.2 — Enrichissement liens vérifiés sur 20 articles juridique critiques (Légifrance, gouv.fr) | 6-8 h |
| 6.3 — Corrections bugs identifiés en roulage interne ELISFA (estimation 8-12 fixes) | 6-10 h |
| **Sous-total Phase 5** | **22-32 h** |

### Phase 6 — Bêta-test 100 utilisateurs (octobre-novembre 2026)

**Objectif** : valider à grande échelle avant cutover production. Identifier les 80/20 cas réels d'usage.

| Livrable | Heures |
|---|---:|
| Préparation : courriers d'invitation, segmentation des testeurs (par module : juridique, formation, RH, gouvernance) | 6-8 h |
| Animation : 5-7 sessions visio de présentation (groupes de 15-20 personnes) | 14-18 h |
| Suivi quotidien : support utilisateurs sur 6-8 semaines (~2-3h/semaine) | 14-20 h |
| Compilation feedback : analyse des 100 questionnaires + extraction des verbatims | 8-10 h |
| Identification des bugs critiques + correctifs prioritaires (~10-15 fixes) | 12-16 h |
| **Sous-total Phase 6** | **54-72 h** |

### Phase 7 — Sprint 7.x : CUTOVER progressif (décembre 2026 → début janvier 2027)

**Objectif** : déploiement production sécurisé avec rollback à chaque étape.

| Livrable | Heures |
|---|---:|
| 7.1 — Validation finale + rédaction CUTOVER.md (procédure d'urgence et rollback) | 4-6 h |
| 7.2 — Cutover Canary 10 % (mi-décembre) avec monitoring intensif | 4-6 h |
| 7.3 — Cutover Gradual 50 % (fin décembre) | 4-6 h |
| 7.4 — Cutover Full 100 % + V1 en fallback (début janvier 2027) | 4-6 h |
| **Sous-total Phase 7** | **16-24 h** |

### Phase 8 — Sprint 8.x : Stabilisation post-cutover (janvier 2027)

**Objectif** : production opérationnelle, monitoring, plan d'évolution.

| Livrable | Heures |
|---|---:|
| 8.1 — Monitoring prod + alerts Sentry/Prometheus configurés | 6-8 h |
| 8.2 — Documentation post-cutover (livret animateur ELISFA, manuel admin, README à jour) | 4-6 h |
| 8.3 — Plan T1 — extension progressive Formation/RH/Gouvernance (roadmap 2027) | 4-6 h |
| **Sous-total Phase 8** | **14-20 h** |

---

## 4. Synthèse temps

| Phase | Période | Heures min | Heures max | Heures médiane |
|---|---|---:|---:|---:|
| Phase 1 — KB enrichie | mai 2026 | 34 | 44 | 39 |
| Phase 2 — Wizard | juin 2026 | 14 | 20 | 17 |
| Phase 3 — Admin KB | juillet 2026 | 14 | 20 | 17 |
| Phase 4 — Staging + test interne | août 2026 | 21 | 29 | 25 |
| Phase 5 — Enrichissements | septembre 2026 | 22 | 32 | 27 |
| **Phase 6 — Bêta-test 100 users** | **oct-nov 2026** | **54** | **72** | **63** |
| Phase 7 — CUTOVER | décembre 2026 | 16 | 24 | 20 |
| Phase 8 — Post-cutover | janvier 2027 | 14 | 20 | 17 |
| **TOTAL** | | **189** | **261** | **225** |

**En jours équivalents (8 h/jour)** : **23,6 → 32,6 jours** (médiane 28 jours)

---

## 5. Tarif et coût total

### Hypothèse retenue (cohérent avec devis 2026-001)

- **Tarif jour HT** : 500 € (auto-entrepreneur — franchise en base de TVA)
- **Tarif horaire HT** : 62,50 €

### Calcul

| Hypothèse | Heures | Coût HT prestation |
|---|---:|---:|
| **Basse** (efficacité optimale) | 189 h | **11 813 €** |
| **Médiane** (estimation réaliste) | 225 h | **14 063 €** |
| **Haute** (couvre imprévus) | 261 h | **16 313 €** |

### Frais techniques refacturables sur la période (mai 2026 → janv 2027 = 9 mois)

| Poste | Estimation 9 mois | Statut |
|---|---:|---|
| API Anthropic Claude (prod 100 users en bêta + cutover progressif) | ~400-600 € | sur factures Anthropic |
| VPS Hostinger (V1 prod existant + V2 staging puis prod) | ~90-180 € | déjà en place pour V1 |
| Domaine `felias.duckdns.org` | 0 € | gratuit |
| Certificats Let's Encrypt | 0 € | gratuit |
| GitHub Actions CI | 0 € | gratuit (compte public ou inclus Free) |
| Sentry plan dev (optionnel) | 0 € → 240 € (26 €/mois × 9) | si activation paid |
| Outil monitoring (Better Stack ou Grafana Cloud free) | 0-200 € | optionnel |
| **Sous-total frais techniques 9 mois** | **490-1 220 €** | refacturables au coût réel sur justificatifs |

### Total HT prévisionnel

| Hypothèse | Prestation HT | Frais techniques | **Total HT** |
|---|---:|---:|---:|
| Basse | 11 813 € | 490 € | **12 303 €** |
| **Médiane (recommandée)** | 14 063 € | 850 € | **14 913 €** |
| Haute | 16 313 € | 1 220 € | **17 533 €** |

### TVA

Auto-entrepreneur en franchise en base : **0 € de TVA collectée** (mention sur facture : « TVA non applicable, art. 293 B du CGI »).

### Total TTC

**Identique au montant HT** dans le cadre de la franchise en base.

---

## 6. Modalités proposées

### Échelonnement de paiement — 4 tranches alignées sur les jalons projet

Compte tenu de la durée de 9 mois et du caractère progressif du livrable, paiement en **4 tranches** correspondant à 4 jalons techniques majeurs :

| Tranche | Période couverte | Échéance | Montant (option médiane) | Livrable conditionnel |
|---|---|---|---:|---|
| **Tranche 1 — Construction** | Phases 1 + 2 + 3 (mai → juillet 2026) | fin juillet 2026 | **4 563 €** | KB enrichie (~99 articles) + Wizard financement + Interface admin KB déployés en staging |
| **Tranche 2 — Test interne** | Phases 4 + 5 (août → septembre 2026) | fin septembre 2026 | **3 250 €** | V2 staging accessible publiquement + 10 utilisateurs internes ELISFA ont testé + Légifrance intégrée + bugs corrigés |
| **Tranche 3 — Bêta 100 users** | Phase 6 + démarrage Phase 7 (octobre → décembre 2026) | mi-décembre 2026 | **3 938 €** | Bêta-test 100 utilisateurs réalisé + bilan qualitatif/quantitatif livré + cutover canary 10 % engagé |
| **Tranche 4 — Cutover & stabilisation** | Phases 7 (suite) + 8 (décembre 2026 → janvier 2027) | fin janvier 2027 | **2 313 €** | Cutover production 100 % réussi + monitoring opérationnel + documentation finale livrée |
| **TOTAL prestation seule** | | | **14 063 €** | |
| Frais techniques refacturables au coût réel | sur factures | | **~850 €** | API Anthropic + VPS + monitoring |
| **TOTAL HT (option médiane)** | | | **14 913 €** | |

### Délai de paiement de chaque tranche

30 jours fin de mois à réception de facture de la tranche (à confirmer avec ELISFA).

---

## 6 bis. Renfort dev recommandé — novembre 2026 → janvier 2027

**Pourquoi un renfort sur cette période ?**

La fenêtre **novembre 2026 → janvier 2027** concentre les **3 phases les plus critiques et les plus consommatrices en temps** du projet :

1. **Bêta-test 100 utilisateurs** (suite de la phase 6, novembre) :
   - Suivi quotidien support sur 6-8 semaines
   - Compilation de 100 retours qualitatifs
   - Itérations correctives en temps réel
2. **Cutover progressif** (phase 7, décembre 2026 → début janvier 2027) :
   - Canary 10 % avec monitoring intensif
   - Gradual 50 %
   - Full 100 % avec V1 en fallback
   - Disponibilité 24/7 pendant les bascules sensibles
3. **Stabilisation post-cutover** (phase 8, janvier 2027) :
   - Premier mois de production avec 100 % du trafic adhérents
   - Réactivité élevée en cas d'incident

Sur cette période d'environ **12 semaines**, le volume de travail à abattre est de **70-100 h** côté prestataire principal (tranches 3 + 4). **Travailler seul présente un risque** : un imprévu personnel ou un bug critique peut décaler le cutover prévu en janvier 2027.

**Recommandation** : prévoir un **renfort dev sur ces 3 mois** pour sécuriser la livraison.

### Profils possibles pour le renfort

| Profil | Tarif jour HT indicatif | Cas d'usage |
|---|---:|---|
| Dev senior Python + FastAPI (équivalent) | **500 €/jour** | Pair-programmer sur fixes critiques, prise d'astreinte cutover, support technique 100 bêta |
| Dev mid-level Python | **400 €/jour** | Soutien sur les corrections de bugs, scripts d'analyse feedback, documentation |
| Dev junior accompagné | **350 €/jour** | Tâches répétitives : enrichissement KB, tests manuels, support utilisateur niveau 1 |

### Volume de renfort estimatif (3 mois novembre → janvier)

| Niveau de renfort | Jours sur 3 mois | Coût total HT (selon profil) |
|---|---:|---|
| **Léger** (10 jours) — astreinte cutover seule | 10 j | 3 500 € (junior) → **4 000 € (mid)** → 5 000 € (senior) |
| **Moyen** (15 jours) — recommandé | 15 j | 5 250 € → **6 000 €** → 7 500 € |
| **Intensif** (20 jours) — couvre tous les imprévus | 20 j | 7 000 € → **8 000 €** → 10 000 € |

### Hypothèse recommandée

**Renfort dev mid-level sur 15 jours répartis novembre → janvier 2027** :
- 5 j en novembre (support bêta-test 100 users)
- 5 j en décembre (cutover canary + gradual)
- 5 j en janvier (cutover full + premières semaines de production)

**Coût HT renfort** : **6 000 €** (15 j × 400 €/j HT mid-level)

Soit en hypothèse médiane :
- Prestation principale + frais techniques : **14 913 €**
- Renfort dev recommandé : **6 000 €**
- **TOTAL HT projet (devis 2026-002) : 20 913 €**

> Le renfort dev est **OPTIONNEL** mais **fortement recommandé** pour sécuriser le cutover de janvier 2027. Si refusé, prévoir le risque d'un décalage du cutover sur février-mars 2027 en cas d'imprévu.

### Conditions

- **Pénalités de retard** : taux légal (BCE + 10 points minimum, soit ~13 % en 2026) selon Code de commerce L441-10
- **Indemnité forfaitaire pour frais de recouvrement** : 40 € par facture en retard (Décret 2012-1115)
- **Clause de revoyure** : possibilité d'ajuster les tranches 5 et 6 selon les retours des bêta-testeurs (impact prévisible sur Phase 6 et Phase 7)
- **Maintenance évolutive post-déploiement** : non incluse — facturable au tarif jour HT mentionné en cas de demande spécifique
- **Confidentialité** : engagement sur les données métiers ALISFA traitées
- **Propriété intellectuelle** : code livré sous licence cédée à ELISFA pour usage interne. Code source hébergé sur GitHub `0xZ1337/chatbot_elisfa`.

---

## 7. Récapitulatif financier

### Engagement existant (devis 2026-001)

- Travail réalisé du 11 au 25 avril 2026 : **5 305 € HT TTC**
- Statut : à facturer dès accord ELISFA

### Engagement à venir (présent devis 2026-002)

| Composant | Montant HT TTC |
|---|---:|
| Prestation principale (4 tranches mai 2026 → janvier 2027) | 14 063 € |
| Frais techniques 9 mois (API Anthropic + VPS + monitoring) | 850 € |
| **Sous-total prestation principale** | **14 913 €** |
| Renfort dev recommandé (15 j × 400 €/j HT — novembre 2026 → janvier 2027) | **6 000 €** |
| **TOTAL devis 2026-002** | **20 913 €** |

Statut : conditionné à l'accord ELISFA et planifié en 4 tranches + renfort dev sur 3 mois.

### Coût total du projet (devis 1 + devis 2 médiane + renfort dev)

| Hypothèse | Devis 2026-001 (réalisé) | Devis 2026-002 (à venir) | Renfort dev (recommandé) | **Total projet** |
|---|---:|---:|---:|---:|
| Sans renfort | 5 305 € | 14 913 € | 0 € | **20 218 €** |
| **Avec renfort recommandé (15 j mid)** | 5 305 € | 14 913 € | 6 000 € | **26 218 €** |
| Avec renfort intensif (20 j senior) | 5 305 € | 14 913 € | 10 000 € | **30 218 €** |

**Tous montants TTC en franchise de TVA AE.**

---

## 8. Ce qui est inclus dans ce devis

✅ Compléter les 99 articles KB restants (Sprint 5.2-data F4-F6)
✅ Wizard financement (Sprint 5.3)
✅ Interface admin KB (Sprint 5.4)
✅ Déploiement staging V2 sur `felias.duckdns.org` (Sprint 4.4 + 5.5)
✅ Session test 10 utilisateurs internes ELISFA (Sprint 4.5)
✅ Intégration Légifrance + enrichissement liens (Sprint 6.1 + 6.2)
✅ Corrections bugs roulage interne (Sprint 6.3)
✅ **Bêta-test 100 utilisateurs sur 6-8 semaines** (Phase 6 — nouvelle)
✅ Cutover production progressif (Sprint 7.1 → 7.4)
✅ Monitoring prod + documentation finale (Sprint 8.1 → 8.3)

## 9. Ce qui n'est PAS inclus

❌ Maintenance évolutive après cutover (facturable séparément au jour)
❌ Création de nouveaux modules (ex. juridique étendu, formation T1+) — nécessite avenant
❌ Formation des animateurs / animateurs ELISFA à l'utilisation du chatbot (peut être ajouté en option)
❌ Hébergement long terme du VPS Hostinger (à la charge d'ELISFA si reprise par leurs soins)
❌ Support utilisateur après janvier 2027 (à définir en contrat de maintenance séparé)

## 10. Options additionnelles facturables séparément

| Option | Description | Estimation |
|---|---|---:|
| Formation animateurs ELISFA (visio 2h × 5 sessions) | Tutoriels d'usage du chatbot | ~600-800 € HT |
| Module additionnel (ex. droit du travail étendu) | ~50 nouveaux articles juridiques | ~3 000-4 000 € HT |
| Maintenance évolutive 12 mois | 1 jour/mois en moyenne (corrections + petites évolutions) | ~6 000 € HT/an |
| Audit IA externe annuel | Validation indépendante par cabinet IA externe | ~2 000-3 000 € HT |

---

## Annexes

- Lien repo GitHub : https://github.com/0xZ1337/chatbot_elisfa (branche `v2-dev`)
- URL prod V1 : https://felias-reseau-eli2026.duckdns.org
- URL staging V2 cible : https://felias.duckdns.org
- URL prod V2 cible (cutover janv 2027) : https://felias-reseau-eli2026.duckdns.org (substitution V1)
- Devis n° 2026-001 (travail réalisé) : `DEVIS_ELISFA_2026-04-25.md`
- Documentation : `DEPLOYMENT.md`, `v2/STAGING.md`, `v2/test_session/`

---

_Devis prévisionnel établi le 25 avril 2026, valable 60 jours._
