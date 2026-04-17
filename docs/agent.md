# Agent.md — Règles et conventions du projet Chatbot ELISFA

> Ce fichier est le **contrat** que tout agent IA (Claude Code, ChatGPT, Copilot, Gemini) doit lire **avant** toute modification du projet. Il encode l'architecture, les conventions et les garde-fous non négociables.
>
> Mainteneur : Didier Delpeyrou · Dernière mise à jour : 16/04/2026

---

## 1. Nature du projet

**Assistant ELISFA** — Chatbot IA (Flask + Claude Haiku 4.5) à destination des employeurs associatifs de la branche des Acteurs du Lien Social et Familial (ALISFA). Fournit des réponses **informatives** sur :
- Juridique (Code du travail, CCN ALISFA)
- RH / management
- Formation (CPF, Pro-A, apprentissage, etc.)
- Gouvernance associative

**Architecture :** Flask → recherche RAG sur base JSON structurée → appel Claude API → réponse formatée → journalisation.

**Règle n°1 de sécurité :** Cet outil ne constitue **jamais** un avis juridique. Toute réponse comporte une réserve d'usage (voir `/static/priorites.html` et les 8 articles dans `templates/index.html`).

---

## 2. Architecture cible (référence)

```
Utilisateur
    ↓
[Flask routes] — app.py (à modulariser, voir §9)
    ↓
[search_knowledge_base] — TF-IDF sur base_*.json
    ↓ top-k articles pertinents
[System prompt enrichi] — SYSTEM_PROMPT_{MODULE}
    ↓
[Claude Haiku 4.5] — max_tokens=8000, timeout=60s
    ↓
[Post-traitement] — injection sources, escalade, format
    ↓
[Réponse utilisateur] + log JSONL
```

**Stockage :**
- Sources : `data/base_{juridique,rh,formation,gouvernance}.json`
- Sources brutes : `data/alisfa_docs/`, `data/cpnef_docs/`, `data/sources_ext/`
- Logs : `logs/chatbot.log` + `logs/interactions.jsonl`

---

## 3. Règles RAG non négociables

### 3.1 Sources autorisées
Les **seules** sources à indexer et référencer sont :
- Code du travail (Légifrance)
- Convention Collective Nationale ALISFA (IDCC 1261)
- Fiches pratiques officielles ELISFA (validées par le pôle juridique)
- CPNEF et ANACT (pour formation et RPS)
- Service-Public.fr (administratif)
- Rapports officiels (INRS, DARES, CEREQ)

**Interdit :** blogs, forums, contenu non sourcé, Wikipédia, sites commerciaux.

### 3.2 Prompt système — clauses obligatoires
Tout `SYSTEM_PROMPT_*` **doit** contenir :
```
Tu te fondes UNIQUEMENT sur les extraits de la base documentaire fournis ci-dessous.
Si l'information n'est pas trouvée dans les sources, dis explicitement : "Je ne trouve pas cette information dans la base documentaire ELISFA."
Ne complète JAMAIS avec des connaissances externes non sourcées.
Cite chaque affirmation avec sa source (article de loi, article CCN, fiche pratique).
```

### 3.3 Escalade automatique
Chaque article de la base doit porter un `niveau` :
- `vert` → réponse autonome
- `orange` → vérification juriste recommandée, rappel 48h ouvrées
- `rouge` → RDV juriste obligatoire sous 5 jours

Le backend propage ce niveau dans la réponse (badge + action suggérée).

### 3.4 Actualisation
- Date de dernière indexation exposée dans `EM_RAG_UPDATED` (actuellement `T1 2026`)
- Re-indexation trimestrielle minimum
- À chaque ré-indexation : bumper `EM_RAG_UPDATED` et `EM_LEGAL_VERSION` si les règles changent

---

## 4. Modèle IA

**Modèle de production :** `claude-haiku-4-5-20251001` (rapide, économique, suffisant pour le RAG).
- `max_tokens` : 8000
- `timeout` : 60s
- `temperature` : non précisée (défaut ~1.0) → **à fixer à 0.3-0.5** pour limiter les hallucinations (TODO)

**Ne pas migrer vers Sonnet/Opus sans benchmark** (coût ×5 à ×15, latence ×2-3).

---

## 5. Conventions de code Python

### 5.1 Style
- **PEP 8** strict
- Lignes max **120 caractères** (tolérance pour f-strings)
- **Pas de one-liner** complexes (lisibilité > concision)
- Type hints sur toute fonction publique

### 5.2 Nommage
- Fonctions / variables : `snake_case`
- Constantes : `UPPER_SNAKE_CASE`
- Classes : `PascalCase`
- Constantes de configuration : préfixe module (`EM_`, `SYSTEM_PROMPT_`, `RAG_`)

### 5.3 Organisation (cible post-refactor)
```
app.py              → entrée Flask uniquement (routes, init)
core/
  ├── rag.py        → search_knowledge_base, scoring
  ├── llm.py        → appel Claude, retry, timeout
  ├── prompts.py    → SYSTEM_PROMPT_* (centralisés)
  ├── escalation.py → logique niveau vert/orange/rouge
  └── logging.py    → log_interaction, metrics
ingestion/
  ├── enrich.py     → (existe déjà dans scripts/)
  └── validate.py   → validation des JSON avant commit
tests/
  ├── test_rag.py
  ├── test_llm.py
  └── rag_eval.py   → jeu de questions de référence
```

### 5.4 Interdits (garde-fous)
- `from anthropic import *` — toujours imports explicites
- `eval()` / `exec()` sur entrée utilisateur
- Injection de `user_context` **brut** dans le system prompt (sanitization obligatoire)
- Suppression de fichiers sans confirmation explicite

---

## 6. Conventions JavaScript (frontend `templates/index.html`)

### 6.1 Préfixes namespace
- `EM_*` : tout ce qui concerne la matrice Eisenhower / mentions légales
- `wz_*` / `wizard*` : wizard de diagnostic
- `pending*` : attachements OCR

### 6.2 Stockage client
- `localStorage` pour persistance longue (profil, welcome accepté, préférences)
- `sessionStorage` pour session courante (acceptation non persistante)
- **Jamais** de données sensibles (identifiants, données RGPD)

### 6.3 Clés localStorage en production
| Clé | Usage | Expiration |
|---|---|---|
| `elisfa_profile` | profil sélectionné | jamais |
| `elisfa_welcome_accepted_v1` | acceptation réserves d'usage | 30 j ou changement de version |
| `elisfa_theme` | light / dark | jamais |
| `elisfa_priorites_v1` | tâches outil priorisation | jamais |

---

## 7. Sécurité

### 7.1 Secrets
- `ANTHROPIC_API_KEY` → variable d'env uniquement, **jamais** dans le repo
- `SECRET_KEY` → variable d'env
- `SMTP_PASS` → variable d'env
- `WEBHOOK_SECRET` → variable d'env

### 7.2 Injection prompt
**Ne JAMAIS** injecter du texte utilisateur brut dans le system prompt.
Toujours échapper ou encapsuler dans une section clairement balisée :
```python
user_context_safe = escape_prompt_injection(user_context)
prompt = f"{SYSTEM_PROMPT}\n\n<contexte_utilisateur>{user_context_safe}</contexte_utilisateur>"
```

### 7.3 CORS & rate limiting
- CORS : whitelister les origines en production (actuellement `*` → à restreindre)
- Rate limit : 20/min, 100/h par IP (config.py)

---

## 7-BIS. Rôles, permissions et consentement (RGPD)

### 7-BIS.1 Les trois rôles du système

| Rôle | Population | Droits principaux | Authentification cible |
|---|---|---|---|
| **Adhérent** | Employeurs associatifs ALISFA (président, direction, RH, RAF, trésorier…). Max 3 personnes par structure adhérente. | Utilise le chatbot, pose des questions, gère son historique, **contrôle ses consentements** | Passwordless par email (magic link) + profil persisté |
| **Juriste ELISFA** | Équipe juridique / accompagnement ELISFA (~6 personnes). | Consulte les demandes qui lui sont adressées (RDV, appels 15 min, questions guidées), prépare les RDV, annote/valide les réponses IA lors de la revue hebdomadaire du mercredi | Compte individuel nominatif (email + mot de passe ou SSO) |
| **Admin technique** | Mainteneurs du système (Didier, équipe technique). | Configuration, re-indexation, purge, déploiement | Compte distinct, 2FA obligatoire |

### 7-BIS.2 Règle de séparation des rôles

- Un **juriste n'a JAMAIS les droits admin technique** (ne peut pas recharger la base, modifier la configuration, accéder aux logs techniques bruts)
- Un **admin technique n'a JAMAIS accès aux prompts adhérents** sans avoir également le rôle juriste
- Un **adhérent n'a JAMAIS accès aux données d'un autre adhérent**, même par inadvertance (pagination cachée, ID énumérable…)

### 7-BIS.3 Principe de consentement — fondement RGPD

Base légale retenue : **consentement explicite** (RGPD art. 6.1.a) — complété par l'**intérêt légitime du syndicat** (art. 6.1.f) pour les traitements strictement nécessaires (feedback anonyme agrégé, amélioration continue).

**Trois périmètres de consentement distincts :**

| Scope | Ce que le juriste peut voir | Par défaut | Révocable |
|---|---|---|---|
| `contact_explicit` | Prompts et contexte des demandes explicitement envoyées par l'adhérent (question guidée, RDV, appel 15 min) | ✅ Implicite (l'adhérent a volontairement rempli un formulaire) | Retrait de la demande |
| `session_for_rdv` | Historique des échanges chat de la session pour préparer un RDV | ❌ Opt-in explicite | Oui, à tout moment |
| `feedback_anonymized` | Prompt et réponse **pseudonymisés** pour revue hebdomadaire du mercredi (amélioration continue) | ❌ Opt-in explicite (ou base légale intérêt légitime si strictement anonyme) | Oui, à tout moment |

### 7-BIS.4 Pseudonymisation obligatoire

Côté console juriste (admin.html), **aucune donnée directement identifiante** ne doit apparaître par défaut :

| Champ source | Affichage juriste par défaut | Révélable ? |
|---|---|---|
| `email` | hash masqué (ex: `j****@****.fr`) | Non |
| `nom` + `prenom` | masqués (`Utilisateur #adh_a9f3b2`) | Oui, **uniquement** si scope `contact_explicit` + clic explicite "Révéler l'identité" avec log |
| `telephone` | masqué (`06 ** ** ** 42`) | Oui, si scope `contact_explicit` + clic "Révéler" |
| `structure_nom` | visible (nécessaire au contexte juridique) | — |
| `structure_taille`, `profil`, `module` | visibles | — |
| Contenu de la question | visible selon scope consenti | — |

La "révélation" d'une donnée masquée est **un événement tracé** (qui, quand, quelle donnée, pour quel ID adhérent).

### 7-BIS.5 Traçabilité des consultations

Chaque accès d'un juriste aux données d'un adhérent génère une entrée immuable dans `consent_events` :

```
{
  "id": "evt_a1b2c3",
  "adherent_id": "adh_a9f3b2",
  "juriste_id": "jur_dupont_m",
  "event_type": "view",           // view | reveal_identity | reveal_phone | annotation | feedback_use
  "question_id": "q_7x8y9z",      // null si accès liste générale
  "scope": "contact_explicit",    // scope consenti au moment de l'accès
  "reason": "preparation_rdv",    // preparation_rdv | revue_mercredi | autre
  "at": "2026-04-16T23:14:32+02:00",
  "ip": "192.0.2.1"
}
```

**Droit d'accès RGPD** : un adhérent qui demande "qui a consulté mes données ?" reçoit la liste filtrée de `consent_events` pour son `adherent_id`.

### 7-BIS.6 Workflow de consultation juriste — règles

**Mode A — Préparation de RDV (usage ponctuel, sur demande)**
1. Le juriste ouvre la console, cherche un adhérent qui a demandé un RDV.
2. Les demandes visibles sont **uniquement** celles où `scope contact_explicit` est actif (c'est toujours le cas : remplir le formulaire RDV = consentement).
3. Si le juriste a besoin de voir **l'historique chat** avant le RDV, il ne peut le faire **que si l'adhérent a activé `scope session_for_rdv`** — sinon, le juriste doit demander à l'adhérent le consentement via la console (notification in-app ou email).
4. Chaque consultation est loggée.

**Mode B — Revue hebdomadaire du mercredi**
1. Vue "Revue semaine S-1" : liste des questions **orange + rouge** traitées par l'IA la semaine précédente.
2. Toutes les données sont **pseudonymisées par défaut** — pas de révélation possible dans ce mode (c'est de l'amélioration système, pas de l'aide à un adhérent identifié).
3. Actions juriste :
   - ✓ Réponse IA correcte → validé (compte dans les métriques qualité)
   - ✗ Réponse IA erronée → annote + propose la correction → devient une donnée de calibrage
   - ⚠️ Cas à rappeler → met l'adhérent (ID seulement) dans la file "à contacter"
4. Le juriste ne peut pas révéler l'identité depuis le mode B — s'il veut contacter l'adhérent, il doit passer en mode A (qui repasse par les règles de consentement).

### 7-BIS.7 Révocation du consentement

L'adhérent doit pouvoir à tout moment, depuis son espace :
- Voir les consentements actifs (quelles données, quelle portée, depuis quand)
- Révoquer un consentement en un clic
- Voir l'historique des consultations (miroir anonymisé : "un juriste a consulté votre demande RDV le X", sans nommer le juriste — conformément à la décision produit de ce soir)
- Demander la suppression complète de ses données (droit à l'oubli, RGPD art. 17)

### 7-BIS.8 Conservation des données

| Type de donnée | Durée de conservation |
|---|---|
| Profil adhérent actif | Tant que le compte est actif |
| Profil adhérent inactif | 3 ans après la dernière activité, puis purge |
| Questions / prompts | 1 an (ou moins si révocation) |
| Logs de consentement | 5 ans (obligation de preuve RGPD) |
| Logs techniques anonymes | 6 mois |
| Données de RDV, appels | Tant que le dossier est actif + 3 ans |

### 7-BIS.9 Changelog rôles & consentement

| Date | Auteur | Changement |
|---|---|---|
| 2026-04-16 | Didier + Claude | Formalisation initiale des rôles, scopes de consentement, règles de pseudonymisation |

---

## 8. Tests (obligatoires avant production)

### 8.1 Couverture minimale
- `tests/test_rag.py` — au minimum 1 test par fonction publique de `core/rag.py`
- `tests/rag_eval.py` — jeu de **30 questions de référence** (10 par module) avec réponses + sources attendues
- `tests/test_llm.py` — mock Anthropic, vérifie retry, timeout, format

### 8.2 Métriques cibles RAG
| Métrique | Cible | Méthode |
|---|---|---|
| Précision top-1 (source correcte) | > 80 % | `rag_eval.py` |
| Rappel top-5 | > 95 % | idem |
| Hallucination rate (citation introuvable) | < 2 % | vérif post-réponse |
| Latence P95 (bout-en-bout) | < 8 s | logs |

### 8.3 Commande standard
```bash
pytest tests/ -v --tb=short
python tests/rag_eval.py --report
```

---

## 9. Process de modification

### 9.1 Avant toute modification significative
1. **Lire ce fichier.**
2. Lire `docs/AUDIT_REPORT.md` pour l'état actuel des risques.
3. Proposer un **plan** (spec driven) avant d'écrire du code.
4. Si nouveau pattern ou nouvelle dépendance → ajout explicite à ce fichier.

### 9.2 Commits
Format : `[module] action courte`
Exemples :
- `[rag] ajout BM25 scoring`
- `[front] fix dark mode welcome card`
- `[docs] agent.md initial`

### 9.3 Revue
Toute modification du RAG, des prompts ou de la logique d'escalade **doit** passer par :
1. Revue IA automatique (plan généré par Claude / ChatGPT)
2. Relecture humaine (Didier ou mainteneur désigné)
3. Si impact juridique : validation pôle juridique ELISFA avant merge

---

## 10. Contacts & responsabilités

| Rôle | Personne | Périmètre |
|---|---|---|
| Product Owner | Didier Delpeyrou | Fonctionnel, priorités |
| Responsable RAG | Didier Delpeyrou | Qualité sources, chunking |
| Responsable juridique | juridique@elisfa.fr | Validation contenus légaux |
| Responsable DPO / RGPD | à désigner | Conformité données |

---

## 11. Changelog de ce fichier

| Date | Auteur | Changement |
|---|---|---|
| 2026-04-16 | Didier + Claude | Création initiale — encodage des règles existantes, cadrage post-démo |
