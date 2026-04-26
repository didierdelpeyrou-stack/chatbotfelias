// Types alignés sur le schema FastAPI V2 (app/api/chat.py + feedback.py)

export type Module = 'juridique' | 'formation' | 'rh' | 'gouvernance';

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
