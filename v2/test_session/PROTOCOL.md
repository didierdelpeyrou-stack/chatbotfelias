# Session test ELISFA #1 — Protocole (Sprint 4.5)

**Cible :** valider que V2 staging est utilisable par les animateurs ELISFA réels avant cutover prod.
**Format :** 45 min en visio (Teams ou autre), groupe de 5-10 personnes.
**Date cible :** mi-novembre 2026 (à fixer après déploiement Sprint 4.4 + Sprint 5/6).
**Animateur :** toi.

---

## Pourquoi cette session

Le benchmark Sprint 4.2 dit que V2 score 74% (vs V1 18%). C'est un bon signal **mais ça vient d'un dataset que j'ai écrit avec Claude** — pas de vraies questions terrain. La session sert à :

1. **Détecter le data drift** : les questions des animateurs ELISFA collent-elles au corpus ?
2. **Mesurer l'UX réelle** : la confiance affichée aide ou perturbe ? Les fiches sont-elles trouvables ?
3. **Détecter les blocages** : où le bot frustre, où il rassure ?
4. **Récolter du feedback qualitatif** : verbatims utilisateurs, plus parlants que des metrics seules.

---

## Déroulé minute par minute

| min | Contenu | Qui parle |
|---|---|---|
| 0–3 | Accueil + confidentialité (RGPD : pas d'IP loggée, hash question) | Toi |
| 3–8 | Démo live : 1 question juridique modèle, montrer la confiance + sources | Toi (partage écran) |
| 8–10 | Distribution du lien : `https://felias-reseau-eli2026-v2.duckdns.org` | Toi |
| 10–35 | **Scénarios guidés** (cf. scenarios.md) — chacun à son rythme | Participants |
| 35–43 | Debrief collectif : "qu'est-ce qui a marché / pas marché ?" | Tous |
| 43–45 | Lien du formulaire individuel (à remplir dans la semaine) | Toi |

---

## Avant la session (J-7 → J-1)

- [ ] **J-7** : envoyer l'invitation (cf. [email_invitation.md](email_invitation.md))
- [ ] **J-3** : confirmer staging V2 répond — `bash v2/scripts/smoke_test_staging.sh` doit être 10/10 ✅
- [ ] **J-1** : préparer un Google Form/Tally à partir de [feedback_form.md](feedback_form.md)
- [ ] **J-1** : tester soi-même les 5 scénarios une dernière fois
- [ ] **J-1** : vérifier que les logs JSONL tournent : `tail -f /var/lib/docker/volumes/elisfa-v2-logs/_data/feedback.jsonl`

## Pendant la session (toi côté animateur)

- [ ] **À J0** : ouvrir 2 onglets : Swagger UI (`/docs`) + tableau de bord live (cf. [dashboard_live.md](dashboard_live.md))
- [ ] Garder un doc ouvert pour noter les verbatims marquants (citations à reprendre dans le rapport)
- [ ] Surveiller `/api/feedback/stats` en temps réel (rafraîchir toutes les 5 min)
- [ ] Si quelqu'un est bloqué → l'aider en privé, ne pas casser le rythme du groupe

## Après la session (J+0 → J+7)

- [ ] **J+0** (le soir) : exporter `logs/feedback.jsonl` + extraire le rapport via `gh stats` ou un script
- [ ] **J+1** : envoyer le formulaire individuel à ceux qui n'auraient pas eu le temps en live
- [ ] **J+7** : compiler [SESSION_1_RAPPORT.md](#) (à créer après) avec :
  - Stats : taux 👍, par module, latence moyenne
  - Top 3 verbatims positifs / négatifs
  - 3-5 actions concrètes à mener (Sprint 6.x)

---

## Critères de succès Sprint 4.5

La session est **réussie** si :

- ✅ ≥5 utilisateurs ont participé en live + complété le formulaire
- ✅ ≥70% des feedbacks 👍 (vs ~50-60% V1 estimé)
- ✅ 0 bug bloquant détecté en session (sinon = blocker pour Sprint 5/6)
- ✅ Tu repars avec ≥3 actions concrètes priorisées pour les Sprints 6.x

---

## Concept ML inline — Online evaluation (human-in-the-loop)

Le benchmark Sprint 4.2 = **offline evaluation** : un dataset figé, des règles automatiques.
La session test = **online evaluation** : utilisateurs réels, ressenti subjectif.

Les deux sont complémentaires :

| | Offline (Sprint 4.2) | Online (Sprint 4.5) |
|---|---|---|
| Coût | Faible (un script Python) | Élevé (1h × 10 personnes = 10h-homme) |
| Reproductibilité | Parfaite (rerun = mêmes résultats) | Nulle (pas deux sessions identiques) |
| Couverture | Limitée à ce qu'on a écrit | Capture l'imprévu (questions inattendues) |
| Signal | Quantitatif (% correct, % halluciné) | Qualitatif (verbatims, frustration, confiance) |

**Règle de pouce industrie :**
> *Offline ne valide que ce qu'on a déjà pensé. Online seul te montre ce que t'as oublié.*

Pour ELISFA, les deux datasets vont nourrir T1 (formation/RH/gouvernance) — Sprints 6+.

---

## RGPD / Confidentialité — à dire dans l'intro

> *"Ce que vous tapez est loggé pour analyse. On ne stocke ni votre IP ni votre identité, juste un hash de la question. Aucune donnée ne sort du VPS Hostinger en France. Vous pouvez à tout moment me demander de supprimer toutes vos interactions a posteriori (en pratique : 1 ligne dans `logs/feedback.jsonl`). Vos commentaires écrits dans les feedbacks sont anonymes."*
