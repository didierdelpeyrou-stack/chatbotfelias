# Modèle de consentement Felias — maquette technique

> Document de spécification pour le module "Rôles, consentement, pseudonymisation". À valider avec le pôle juridique ELISFA avant implémentation.
>
> Version : 0.1 (maquette, à valider) · Date : 16/04/2026

---

## 1. Rappel du contexte

- **Adhérents ELISFA** = utilisateurs (employeurs associatifs ALISFA)
- **Juristes ELISFA** = ~6 personnes qui peuvent consulter les demandes sur consentement
- Volumétrie cible : max quelques milliers d'adhérents, ~100 questions/jour
- Traitement hebdomadaire par le pôle juristes : mercredi matin (revue qualité)
- Pas de traçabilité miroir côté adhérent (il voit *qu'un* juriste a consulté, pas *lequel*)

---

## 2. Schéma de données (PostgreSQL)

### 2.1 Table `adherents`

```sql
CREATE TABLE adherents (
    id                  TEXT PRIMARY KEY,                   -- ex: "adh_a9f3b2" (stable, non-énumérable)
    email_hash          TEXT UNIQUE NOT NULL,               -- SHA-256 salé, sert à retrouver l'adhérent au login
    email_encrypted     BYTEA,                              -- email chiffré (AES-GCM), déchiffré uniquement au login et à la révélation
    nom_encrypted       BYTEA,
    prenom_encrypted    BYTEA,
    telephone_encrypted BYTEA,
    structure_nom       TEXT NOT NULL,                      -- en clair (contexte juridique nécessaire)
    structure_taille    TEXT,                               -- '<10', '10-49', '50-249', '250+'
    structure_ccn       TEXT DEFAULT 'ALISFA',
    profil              TEXT NOT NULL,                      -- 'president', 'direction', 'rh', 'raf', 'bureau'
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_active_at      TIMESTAMPTZ,
    deleted_at          TIMESTAMPTZ,                        -- soft delete, droit à l'oubli
    CONSTRAINT email_hash_format CHECK (email_hash ~ '^[a-f0-9]{64}$')
);

CREATE INDEX idx_adherents_active
    ON adherents(last_active_at) WHERE deleted_at IS NULL;
```

### 2.2 Table `juristes`

```sql
CREATE TABLE juristes (
    id              TEXT PRIMARY KEY,                       -- ex: "jur_dupont_m"
    email           TEXT UNIQUE NOT NULL,
    nom             TEXT NOT NULL,
    prenom          TEXT NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    password_hash   TEXT NOT NULL,                          -- Argon2id
    totp_secret     TEXT,                                   -- TOTP/2FA optionnel
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login_at   TIMESTAMPTZ
);
```

### 2.3 Table `consents` (déclaration, au présent)

```sql
CREATE TABLE consents (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    adherent_id             TEXT NOT NULL REFERENCES adherents(id) ON DELETE CASCADE,
    scope                   TEXT NOT NULL,                  -- 'contact_explicit' | 'session_for_rdv' | 'feedback_anonymized'
    granted                 BOOLEAN NOT NULL,               -- true = consenti, false = refusé explicitement
    granted_at              TIMESTAMPTZ NOT NULL,
    revoked_at              TIMESTAMPTZ,                    -- NULL si actif
    version_cgu             TEXT NOT NULL,                  -- 'cgu_v1.0_2026-04', pour traçabilité
    ip_at_action            INET,
    user_agent_at_action    TEXT,
    reason                  TEXT,                           -- contexte facultatif ('formulaire_rdv', 'parametres_compte', etc.)
    UNIQUE (adherent_id, scope, granted_at)
);

CREATE INDEX idx_consents_active
    ON consents(adherent_id, scope) WHERE revoked_at IS NULL;
```

### 2.4 Table `consent_events` (journal d'événements, immuable)

```sql
CREATE TABLE consent_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    adherent_id     TEXT NOT NULL REFERENCES adherents(id),
    juriste_id      TEXT REFERENCES juristes(id),           -- null si action adhérent
    actor_role      TEXT NOT NULL,                          -- 'adherent' | 'juriste' | 'system'
    event_type      TEXT NOT NULL,
        -- event_type valeurs :
        --   'consent_grant'     : adhérent donne un consentement
        --   'consent_revoke'    : adhérent retire un consentement
        --   'view_demande'      : juriste consulte une demande
        --   'view_historique'   : juriste consulte l'historique chat d'une session
        --   'reveal_identity'   : juriste révèle nom/prenom d'un adhérent
        --   'reveal_phone'      : juriste révèle le téléphone
        --   'annotation'        : juriste annote une réponse IA (revue mercredi)
        --   'feedback_use'      : une réponse IA est utilisée pour amélioration
        --   'soft_delete'       : adhérent demande suppression (droit à l'oubli)
    question_id     UUID,                                   -- id de la question concernée, si applicable
    scope_at_time   TEXT,                                   -- scope consenti au moment de l'événement
    reason          TEXT,                                   -- 'preparation_rdv' | 'revue_mercredi' | 'autre'
    ip              INET,
    at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- immutabilité : pas d'UPDATE, pas de DELETE (enforced via trigger)
    meta            JSONB
);

CREATE INDEX idx_events_adherent ON consent_events(adherent_id, at DESC);
CREATE INDEX idx_events_juriste  ON consent_events(juriste_id, at DESC);

-- Trigger empêchant toute modification
CREATE OR REPLACE FUNCTION forbid_changes() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'consent_events is append-only';
END; $$ LANGUAGE plpgsql;

CREATE TRIGGER consent_events_immutable
    BEFORE UPDATE OR DELETE ON consent_events
    FOR EACH ROW EXECUTE FUNCTION forbid_changes();
```

### 2.5 Table `questions` (demandes des adhérents)

```sql
CREATE TABLE questions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    adherent_id     TEXT NOT NULL REFERENCES adherents(id),
    module          TEXT NOT NULL,                          -- 'juridique' | 'rh' | 'formation' | 'gouvernance'
    channel         TEXT NOT NULL,                          -- 'chat_libre' | 'question_guidee' | 'rdv' | 'appel_15min'
    prompt_text     TEXT NOT NULL,
    answer_text     TEXT,
    answer_sources  JSONB,                                  -- [{article, ref, lien}, ...]
    niveau          TEXT,                                   -- 'vert' | 'orange' | 'rouge'
    confidence      NUMERIC(3,2),                           -- 0.00 - 1.00 (score du RAG + reranker)
    latency_ms      INT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- flag de revue (mode B, mercredi)
    reviewed_by     TEXT REFERENCES juristes(id),
    reviewed_at     TIMESTAMPTZ,
    review_verdict  TEXT,                                   -- 'correct' | 'to_correct' | 'to_recontact'
    review_notes    TEXT
);

CREATE INDEX idx_questions_adh    ON questions(adherent_id, created_at DESC);
CREATE INDEX idx_questions_review ON questions(niveau, reviewed_at) WHERE niveau IN ('orange', 'rouge');
```

---

## 3. Flux UX — 3 niveaux de consentement

### 3.1 Niveau 1 — Consentement d'accueil (onboarding)

**Quand** : après acceptation des mentions légales (modal welcome existant) et au premier message.
**Ce qui est demandé** : opt-in pour `feedback_anonymized` (le plus soft, le moins risqué).

```
┌─────────────────────────────────────────────────────────────┐
│  🤝  Participer à l'amélioration de l'assistant             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Souhaitez-vous que l'équipe juridique ELISFA puisse         │
│  consulter vos échanges pour améliorer la qualité des        │
│  réponses ?                                                  │
│                                                              │
│  Vos données sont toujours pseudonymisées (votre nom         │
│  n'apparaît jamais). La revue se fait chaque mercredi.       │
│  Vous pouvez retirer ce consentement à tout moment.          │
│                                                              │
│         [   Oui, j'accepte    ]   [   Plus tard   ]          │
│                                                              │
│              En savoir plus sur vos données                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Niveau 2 — Consentement contextuel (au moment utile)

**Quand** : l'adhérent demande un RDV juriste OU reçoit une réponse niveau `orange`/`rouge`.
**Ce qui est demandé** : opt-in pour `session_for_rdv`.

```
┌─────────────────────────────────────────────────────────────┐
│  📋  Préparer votre RDV                                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Pour préparer efficacement votre RDV avec un juriste,       │
│  souhaitez-vous l'autoriser à consulter les échanges         │
│  de cette session avec l'assistant ?                         │
│                                                              │
│  ☑️  Oui, le juriste peut consulter cette session            │
│  ☐  Non, je préfère recommencer à zéro au RDV                │
│                                                              │
│  Ce consentement s'applique uniquement aux messages          │
│  actuels. Vous pouvez le retirer à tout moment.              │
│                                                              │
│                    [   Continuer   ]                         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 3.3 Niveau 3 — Consentement explicite volontaire (formulaire RDV)

**Quand** : l'adhérent remplit volontairement le formulaire "Contacter un juriste" ou "Prendre RDV".
**Ce qui est demandé** : `contact_explicit` est implicite, mais on l'**enregistre explicitement** comme consentement daté.

Le formulaire existant envoie déjà nom/email/tel. On ajoute simplement la ligne :

> ☑️ *J'accepte que ces informations et ma question soient transmises aux juristes ELISFA pour le traitement de ma demande. Je peux retirer cette demande à tout moment en m'adressant à juridique@elisfa.fr.*

→ Case pré-cochée mais décochable. À la soumission, crée une ligne `consents` avec `scope = 'contact_explicit'`.

### 3.4 Écran de gestion — "Mon compte → Confidentialité"

```
┌──────────────────────────────────────────────────────────────┐
│  🔒 Confidentialité et consentement                         │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  VOS CONSENTEMENTS ACTIFS                                     │
│                                                               │
│  ✓ Amélioration du service (revue hebdomadaire)              │
│    Actif depuis le 16/04/2026                                 │
│    Vos prompts pseudonymisés peuvent être consultés           │
│    le mercredi par l'équipe juridique.                        │
│    [ Retirer ]                                                │
│                                                               │
│  ✓ Préparation de RDV                                         │
│    Actif depuis le 16/04/2026                                 │
│    Un juriste peut consulter vos échanges si vous             │
│    demandez un RDV.                                           │
│    [ Retirer ]                                                │
│                                                               │
│  ─────────────────────────────────────────────────────        │
│                                                               │
│  HISTORIQUE DES CONSULTATIONS                                 │
│                                                               │
│  • 15/04/2026 à 10h32 — Un juriste a consulté votre          │
│    demande de RDV #RDV-12345                                  │
│  • 09/04/2026 à 14h18 — Votre question #QJ-98765 a été       │
│    revue dans le cadre de l'amélioration du service          │
│                                                               │
│  ─────────────────────────────────────────────────────        │
│                                                               │
│  [ Télécharger toutes mes données (RGPD art. 20)  ]          │
│  [ Supprimer mon compte et mes données (art. 17)  ]          │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

---

## 4. Flux côté juriste (console admin)

### 4.1 Login nominatif
Remplacement du HTTP Basic Auth partagé par :
- Login email + mot de passe (Argon2id)
- Session avec cookie HttpOnly + SameSite=Lax
- Optionnellement 2FA (TOTP via authenticator app)

### 4.2 Mode A — Préparation de RDV

1. Le juriste ouvre un RDV dans la console.
2. Par défaut, les données personnelles sont **masquées** (`Utilisateur #adh_a9f3b2`).
3. Pour révéler : bouton `[Révéler l'identité]` → vérifie que `scope contact_explicit` est actif → crée `consent_events(event_type='reveal_identity')` → affiche.
4. Pour voir l'historique chat de la session : bouton `[Voir l'historique]` → vérifie que `scope session_for_rdv` est actif → si non, propose d'envoyer une demande à l'adhérent via email/in-app.

### 4.3 Mode B — Revue du mercredi

Nouvel onglet admin à créer : **"Revue qualité — semaine S-1"**.

```
┌──────────────────────────────────────────────────────────────┐
│  📊  Revue qualité — Semaine du 08 au 14 avril 2026          │
├──────────────────────────────────────────────────────────────┤
│  Modules :  [Tous] [Juridique] [RH] [Formation] [Gouvernance]│
│  Niveau  :  [Tous] [🟠 Orange]  [🔴 Rouge]                   │
│  Statut  :  [Non revu] [Revu] [À recontacter]                │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  Q-042  🟠 Juridique   Adh #adh_a9f3b2 · Centre social (X)   │
│  « Quelle durée de préavis pour un CDI de 8 ans ? »           │
│  → Réponse IA (extrait) : « Le préavis est de 2 mois… »       │
│  Sources : CCN ALISFA ch. III, L1234-1                       │
│                                                               │
│    [ ✓ Correct ]  [ ✗ À corriger ]  [ ⚠️ À recontacter ]     │
│                                                               │
│  ─────────────────────────────────────────────────────        │
│                                                               │
│  Q-043  🔴 RH         Adh #adh_b2c4e1 · EAJE (10-49 ETP)     │
│  « Ma directrice est en burn-out, que faire ? »               │
│  → Réponse IA (extrait) : « Contacter le médecin du… »        │
│  Sources : L4121-1, INRS                                     │
│                                                               │
│    [ ✓ Correct ]  [ ✗ À corriger ]  [ ⚠️ À recontacter ]     │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

**Règle** : dans le mode B, **pas de bouton "révéler identité"**. Si le juriste veut prendre contact avec l'adhérent, il doit passer par le mode A (avec vérification du scope).

---

## 5. Endpoints API (nouvelle couche)

### 5.1 Côté adhérent

```
POST   /api/consents                     Accorder un consentement
DELETE /api/consents/{scope}             Révoquer un consentement
GET    /api/consents                     Voir mes consentements actifs
GET    /api/consent-history              Voir les consultations sur mon compte
POST   /api/account/export               Télécharger toutes mes données (RGPD art. 20)
DELETE /api/account                      Supprimer mon compte (RGPD art. 17)
```

### 5.2 Côté juriste (à ajouter / refactorer depuis admin.html)

```
POST   /api/juriste/login                Authentification nominative
POST   /api/juriste/logout
GET    /api/juriste/me                   Profil juriste courant

GET    /api/admin/demandes               Liste des demandes (pseudonymisées par défaut)
GET    /api/admin/demande/{id}           Détail — déclenche consent_events
POST   /api/admin/demande/{id}/reveal    Révéler identité (vérifie scope + log)
GET    /api/admin/demande/{id}/history   Historique chat — vérifie session_for_rdv

GET    /api/admin/revue/{semaine}        Questions orange/rouge de la semaine
POST   /api/admin/revue/{q_id}/verdict   Poser un verdict (correct/à corriger/à recontacter)
```

---

## 6. Textes légaux à faire valider

### 6.1 Micro-texte "en savoir plus sur vos données" (onboarding)

> **Vos données chez ELISFA**
>
> Lorsque vous utilisez l'assistant Felias, vous créez un compte pseudonymisé identifié par un code unique (ex : `adh_a9f3b2`). Votre email, nom et téléphone sont chiffrés en base de données et ne sont jamais affichés par défaut aux juristes.
>
> **Ce qui est toujours consulté par l'équipe juridique ELISFA :**
> - Les demandes que vous envoyez explicitement via un formulaire (RDV, appel 15 min, question guidée).
>
> **Ce qui n'est jamais consulté sans votre accord :**
> - Vos échanges libres avec l'assistant (chat).
>
> **Ce qui peut être consulté si vous nous le permettez :**
> - Vos échanges chat, pour préparer un RDV (consentement révocable).
> - Vos échanges pseudonymisés, pour améliorer la qualité de l'assistant (revue hebdomadaire).
>
> Vous pouvez à tout moment retirer vos consentements, demander l'export ou la suppression de vos données depuis votre espace Confidentialité.
>
> *Base légale : RGPD art. 6.1.a (consentement) complété par art. 6.1.f (intérêt légitime du syndicat pour l'amélioration du service).*

### 6.2 Case à cocher formulaire "Contacter un juriste"

> ☑️ J'accepte que les informations de cette demande (mes coordonnées, ma question et le contexte) soient transmises aux juristes ELISFA pour le traitement. Je peux retirer cette demande ou mes consentements à tout moment depuis mon espace Confidentialité ou en écrivant à juridique@elisfa.fr.

### 6.3 Mention dans la politique de confidentialité (section dédiée)

> **Rôle des juristes ELISFA dans le traitement de vos données**
>
> Les juristes de l'ELISFA (6 personnes) peuvent accéder à vos données dans trois cas précis :
>
> 1. **Demandes explicites** : lorsque vous remplissez volontairement un formulaire pour une prise de RDV, un appel 15 min ou une question guidée, vos coordonnées et votre demande sont transmises aux juristes pour traitement.
> 2. **Préparation de RDV** : si vous y avez consenti, un juriste peut consulter l'historique de vos échanges chat en amont d'un RDV pour mieux préparer la réponse.
> 3. **Amélioration du service (revue hebdomadaire)** : si vous y avez consenti, vos échanges peuvent être revus de manière pseudonymisée (votre identité n'apparaît jamais) le mercredi de chaque semaine, dans le but d'améliorer la qualité des réponses de l'assistant.
>
> Chaque consultation par un juriste est enregistrée dans un journal consultable depuis votre espace Confidentialité, dans le respect de votre droit à l'information (RGPD art. 15).

---

## 7. Plan d'implémentation suggéré (2 semaines)

### Semaine 1 — Fondations
- [ ] Créer les tables Postgres (`adherents`, `juristes`, `consents`, `consent_events`, `questions`)
- [ ] Migrer la sélection de profil actuelle vers un vrai compte adhérent (magic link email)
- [ ] Ajouter login nominatif pour les juristes (remplacement HTTP Basic Auth)
- [ ] Créer les 6 comptes juristes ELISFA réels

### Semaine 2 — UX consentement
- [ ] Modal niveau 1 (onboarding) — opt-in `feedback_anonymized`
- [ ] Modal niveau 2 (contextuel) — opt-in `session_for_rdv`
- [ ] Case à cocher formulaire RDV — `contact_explicit`
- [ ] Écran "Mon compte → Confidentialité" avec gestion des consentements
- [ ] Journal public "qui a consulté mes données" (miroir anonymisé)
- [ ] Refonte de la console admin :
  - Pseudonymisation par défaut
  - Boutons "Révéler" avec traçabilité
  - Nouvel onglet "Revue qualité — mercredi"

### Semaine 3 — Validation & production
- [ ] Tests automatisés sur le modèle de consentement
- [ ] Rédaction + validation juridique des textes (section 6)
- [ ] Dry-run avec les 6 juristes ELISFA sur env de staging
- [ ] Déploiement production + communication aux adhérents existants

---

## 8. Questions ouvertes à trancher avec ELISFA

1. **Magic link vs. mot de passe adhérent** : le passwordless simplifie mais demande une infra email fiable.
2. **2FA juriste** : obligatoire ou recommandé ? (recommandé strictement)
3. **Rétroactivité** : les adhérents existants (ceux qui ont déjà posé des questions) doivent-ils :
   - (a) être considérés comme ayant donné `contact_explicit` pour leurs demandes existantes ?
   - (b) recevoir un email les invitant à confirmer leurs consentements ?
   - (c) voir toutes leurs anciennes données purgées tant qu'ils n'ont pas re-consenti ?
4. **Pseudonyme** : format visible du pseudo (`adh_a9f3b2` vs. `Utilisateur_0001` vs. `Centre social anonyme #X`) — à arbitrer avec les juristes (lisibilité vs. non-énumérabilité).
5. **Délégué à la protection des données (DPO)** : ELISFA en a-t-il un désigné ? Si oui, son email doit figurer dans la politique.
6. **Registre des traitements** : ELISFA a-t-il déjà un registre RGPD ? Sinon, il faut en créer une ligne pour ce traitement.

---

## 9. Changelog

| Date | Auteur | Changement |
|---|---|---|
| 2026-04-16 | Didier + Claude | Maquette initiale |
