// Types alignés sur le schema FastAPI V2 (app/api/chat.py + feedback.py)

export type Module = 'juridique' | 'formation' | 'rh' | 'gouvernance';

/** Sprint 4.6 F1 — modes d'usage par module (urgence, analyse, rédaction, ...) */
export interface Mode {
  id: string;
  label: string;
  icon: string;
  module: Module;
  placeholder: string;
}

/** Sprint 4.6 F1.5 — profil utilisateur (porté de V1 USER_PROFILES). */
export type ProfileType = 'benevole' | 'professionnel';

export interface UserProfile {
  id: string;
  name: string;
  icon: string;
  type: ProfileType;
  modules: Module[];
  /** Aperçu court (1 phrase) pour affichage UI ; le contexte complet reste server-side. */
  summary: string;
}

/**
 * Sprint 4.6 — caractéristiques de la structure recueillies en 2e étape de
 * l'onboarding. Toutes optionnelles. Whitelist côté backend.
 */
/** Sprint 4.6 F6 — Annuaire d'orientation */
export type ActeurType =
  | 'elisfa'
  | 'federation'
  | 'syndicat'
  | 'opco'
  | 'etat'
  | 'deconcentre'
  | 'collectivite'
  | 'operateur'
  | 'vie_asso'
  | 'ressource'
  | 'urgence'
  | 'partenaire';

export interface Acteur {
  id: string;
  nom: string;
  type: ActeurType;
  role: string;
  description?: string;
  email?: string;
  phone?: string;
  url?: string;
}

export interface OrientationSummary {
  id: string;
  label: string;
  icon: string;
  description: string;
  n_acteurs: number;
}

export interface OrientationDetail {
  id: string;
  label: string;
  icon: string;
  description: string;
  acteurs: Acteur[];
}

export interface RegionInfo {
  region: string;
  code?: string;
  type?: 'metropole' | 'drom' | 'com';
  elisfa_referent: string;
  elisfa_email?: string;
  region_label?: string;
  region_url?: string;
  prefecture_url?: string;
  fcsf_federations: string[];
  acepp_federations: string[];
}

export interface ProfileExtras {
  type_structure?: string;       // EAJE / Centre social / ALSH / EVS / MJC / Autre
  type_structure_other?: string; // précision si "Autre"
  headcount?: string;            // < 11 / 11-49 / 50-249 / 250+
  statut_juridique?: string;     // Asso loi 1901 / SCIC / Autre
  public_principal?: string;     // Petite enfance / Enfance / Jeunesse / Adultes / Tous publics
  benevoles?: string;            // < 10 / 10-50 / 50+ / Pas de bénévoles
  region?: string;               // texte libre court
}

export interface Source {
  id: string | null;
  title: string | null;
  theme_label: string;
  score: number;
  score_normalized: number;
}

export interface AskResponse {
  answer: string;
  hors_corpus: boolean;
  sources: Source[];
  module: Module;
  question: string;
  duration_ms?: number;
  rag?: {
    score: number;
    score_normalized: number;
    threshold: number;
    hors_corpus: boolean;
  };
}

export interface ChatMessage {
  id: string;            // ulid client-side
  role: 'user' | 'assistant';
  content: string;       // markdown raw
  module?: Module;
  mode?: string | null;  // Sprint 4.6 F1 — id de mode utilisé (juridique_urgence, …)
  sources?: Source[];
  hors_corpus?: boolean;
  pending?: boolean;     // true pendant le streaming
  rating?: 1 | -1;       // feedback utilisateur (POST /api/feedback envoyé)
  duration_ms?: number;
  error?: string;        // si l'appel a échoué
}

export interface ModuleMeta {
  id: Module;
  label: string;
  short: string;
  emoji: string;
  accent: 'navy' | 'green' | 'orange' | 'blue';
  banner: string;
}

export const MODULES: ModuleMeta[] = [
  {
    id: 'juridique',
    label: 'Juridique',
    short: 'Juridique',
    emoji: '⚖️',
    accent: 'blue',
    banner:
      'Assistant juridique — Code du travail, CCN ALISFA, jurisprudence. Caractère informatif, pas un conseil juridique.',
  },
  {
    id: 'formation',
    label: 'Formation',
    short: 'Formation',
    emoji: '🎓',
    accent: 'orange',
    banner:
      "Vos obligations et opportunités en formation professionnelle (CCN ALISFA / Uniformation).",
  },
  {
    id: 'rh',
    label: 'Management & RH',
    short: 'RH',
    emoji: '👥',
    accent: 'green',
    banner:
      'Assistant Management & RH — diagnostic interactif, renvois vers ELISFA et votre fédération.',
  },
  {
    id: 'gouvernance',
    label: 'Gouvernance',
    short: 'Gouvernance',
    emoji: '🏛️',
    accent: 'navy',
    banner:
      "Assistant Gouvernance & Bénévolat — Loi 1901, CA, AG, engagement bénévole, ESS.",
  },
];
