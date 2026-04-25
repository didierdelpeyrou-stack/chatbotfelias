# Formulaire post-session — Template

À recréer dans **Google Forms** ou **Tally** (gratuits, anonymes par défaut).
Lien à partager à la fin de la session live.
~5 min à remplir.

---

## Page 1 — Identification (facultatif)

> *"Ces infos m'aident à corréler les retours avec les profils. Si tu préfères répondre anonyme, laisse vide."*

1. **Prénom (facultatif)** — texte libre
2. **Centre social / structure (facultatif)** — texte libre
3. **Ton rôle principal** — choix unique :
   - Animateur.ice
   - Coordinateur.ice
   - Dirigeant.e associatif
   - Bénévole
   - Autre : ___

---

## Page 2 — Expérience globale

4. **Tu utiliserais cet outil dans ton quotidien ?** — échelle 1-5
   - 1 = Jamais — 5 = Tous les jours

5. **Tu le recommanderais à un.e collègue ?** — échelle 1-5 (NPS-like)
   - 1 = Jamais — 5 = Carrément

6. **Compare à V1 (`felias-reseau-eli2026.duckdns.org`) que tu connaissais peut-être** — choix unique :
   - V2 est nettement meilleure
   - V2 est un peu meilleure
   - C'est pareil
   - V2 est moins bien
   - Je ne connaissais pas V1

---

## Page 3 — Ressenti scénario par scénario

Pour CHAQUE scénario (1 à 5), 2 questions :

### Scénario [N] — Question : *"[texte du scénario]"*

7.[N]. **La réponse était fiable ?** — choix unique :
   - Oui, exacte et complète
   - Partiellement (manque qq éléments)
   - Non, à côté de la plaque
   - Le bot a refusé de répondre (et c'était justifié)
   - Le bot a refusé de répondre (mais il aurait dû)

8.[N]. **Verbatim libre** (1 phrase max) :
   - *"Ce qui m'a marqué c'est ___"*

---

## Page 4 — Ouvertures

9. **Le pire moment de la session** (texte libre, 100 mots max) :
   - *"À ce moment-là j'ai pensé que..."*

10. **Le meilleur moment** (texte libre, 100 mots max) :
    - *"À ce moment-là j'ai trouvé que..."*

11. **Si tu avais une seule chose à demander pour la prochaine version, ce serait quoi ?** (texte libre, 1 ligne) :

12. **Tu acceptes que [Prénom] te recontacte pour un retour individuel approfondi ?** — oui / non

---

## Pour toi (animateur) — Comment exploiter les retours

**Quantitatif** :
- Q4-Q5 : NPS-like → si moyenne ≥ 4/5, c'est un signal vert pour le cutover.
- Q7.[N] : taux de "Oui, exacte et complète" par scénario → corrèle avec le `top_score` RAG côté logs.

**Qualitatif** :
- Q9-Q10-Q11 : verbatims → extraire 3 citations marquantes pour le rapport ELISFA management.
- Q12 = oui : prioriser ces personnes pour Sprint 5.3 (roulage interne 2 semaines).

**Concept ML inline — Likert scales et biais**

Les échelles 1-5 (Likert) ont 2 biais connus :
- **Acquiescence bias** : les gens cochent plutôt 4-5 par politesse, surtout si l'auteur est dans la salle.
- **Central tendency** : les gens évitent les extrêmes (1 et 5).

Mitigation Sprint 4.5 :
- Formulaire **rempli après la session**, pas pendant (laisse mûrir).
- Verbatim obligatoire (Q8) → casse l'effet "je coche n'importe quoi".
- Q11 ouverte = signal bcp plus fort que les notes (les gens se forcent à formuler).
