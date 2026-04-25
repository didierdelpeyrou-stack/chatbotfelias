# Scénarios guidés — Session test ELISFA #1

5 scénarios à faire individuellement, ~5 min chacun = 25 min total.
Volontairement réalistes (≠ benchmark Sprint 4.2 qui est calibré).
Chaque scénario teste **une dimension produit** différente.

---

## Scénario 1 — Question juridique précise (test : exactitude)

**Module :** juridique
**Profil :** salarié
**Question à poser :** *"Quelle est la durée de la période d'essai pour un CDI sous la CCN ALISFA ?"*

**Ce qu'on attend :**
- Réponse mentionne **2 mois** (ou 4 mois selon coefficient) avec citation `[ART_xxx]`
- Confiance : "high" ou "medium"
- Au moins 1 source citée

**Ce qu'on teste :**
- L'exactitude factuelle sur une question fréquente
- Le format de citation `[ART_xxx]` (R11) est-il lisible par un humain non-tech ?

À noter : si la réponse dit *"je n'ai pas l'info"* → c'est un faux refus (régression vs benchmark).

---

## Scénario 2 — Question vague / hors corpus (test : refus poli)

**Module :** juridique
**Profil :** au choix
**Question à poser :** *"Bonjour, comment ça va ?"* puis *"Et la météo aujourd'hui ?"*

**Ce qu'on attend :**
- Réponse fallback : *"Je n'ai pas d'information fiable dans la base ELISFA pour répondre précisément à cette question..."*
- PAS d'invention, pas d'hallucination ("Il fait beau à Paris")

**Ce qu'on teste :**
- Le seuil hors_corpus (R1, Sprint 2.2) tient-il en pratique ?
- Le ton du refus est-il acceptable ou frustrant ?

---

## Scénario 3 — Question RH ouverte (test : KB pauvre)

**Module :** rh
**Profil :** dirigeant associatif
**Question à poser :** *"Comment recruter un.e animateur.ice quand on n'a pas encore de processus ?"*

**Ce qu'on attend :**
- Soit : réponse partielle avec quelques pistes + suggestion d'aller voir le module formation
- Soit : refus poli avec contact pôle juridique/RH

**Ce qu'on teste :**
- Le module RH a 11 articles seulement (densification prévue Sprint 6) — la couverture tient-elle ?
- L'utilisateur sent-il que c'est volontaire ("on n'a pas tout") ou que le bot est nul ?

---

## Scénario 4 — Question gouvernance avec sous-question (test : structure réponse)

**Module :** gouvernance
**Profil :** au choix
**Question à poser :** *"On veut dissoudre l'association, quelles sont les étapes et où trouver les modèles de PV ?"*

**Ce qu'on attend :**
- Étapes listées (AG extraordinaire, déclaration prefecture, dévolution actif)
- Au moins un lien vers `associations.gouv.fr` ou modèle PV
- Boutons d'action : "Prendre RDV avec un juriste", "Voir fiche pratique"

**Ce qu'on teste :**
- La capacité à articuler **plusieurs informations** dans une seule réponse
- La présence et la qualité des **liens externes** (lacune connue, audit Sprint 6.2)

---

## Scénario 5 — Test de l'expérience feedback (test : 👍/👎)

**Module :** au choix
**Profil :** au choix
**Question à poser :** une question de votre quotidien réel (improvisée, pas dans cette liste)

**Ce qu'on attend :**
- Réponse pertinente OU non
- L'utilisateur clique 👍 ou 👎 selon son ressenti
- Si 👎 : commentaire libre obligatoire ("pourquoi ?")

**Ce qu'on teste :**
- Le bouton feedback est-il visible et facile à utiliser ?
- Le commentaire écrit est-il intuitif ?
- Le feedback arrive-t-il bien dans `logs/feedback.jsonl` côté serveur ?

---

## Pour l'animateur (toi)

À la fin des 5 scénarios, demander à voix haute :

1. *"Sur lequel des 5 vous a frustré ? Pourquoi ?"*
2. *"Si vous deviez recommander cet outil à un.e collègue d'un autre centre social, vous diriez quoi ?"*
3. *"Qu'est-ce qui manque qu'on n'a pas vu ?"*

Ces 3 questions ouvertes = matière qualitative la plus riche du débrief.
