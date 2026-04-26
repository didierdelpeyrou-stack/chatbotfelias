// Sprint 4.6 F4 — Configuration des wizards guidés (formulaires multi-étapes).
// Version V1 minimale (4-5 questions par module) — V2 complète à venir si bêta-testeurs en redemandent.
// Sur soumission : la synthèse des réponses est envoyée à /api/ask avec mode=wizard_<module>.

import type { Module } from './types';

export type WizardField =
  | { id: string; type: 'text'; label: string; help?: string; placeholder?: string; required?: boolean }
  | { id: string; type: 'choice'; label: string; help?: string; options: string[]; required?: boolean };

export interface WizardConfig {
  /** ID du mode wizard backend (wizard_juridique, etc.) */
  modeId: string;
  module: Module;
  title: string;
  subtitle: string;
  steps: WizardField[];
}

const WIZARDS: Record<Module, WizardConfig> = {
  juridique: {
    modeId: 'wizard_juridique',
    module: 'juridique',
    title: '⚖️ Diagnostic juridique guidé',
    subtitle: 'Méthode juridique : faits → qualification → règles → application → conclusion',
    steps: [
      {
        id: 'urgence',
        type: 'choice',
        label: 'Y a-t-il une urgence ou un délai légal qui court actuellement ?',
        help: 'En matière disciplinaire : 2 mois pour engager la procédure (L1332-4), 1 mois max entretien → notification.',
        options: ['Oui', 'Non', 'Je ne sais pas'],
        required: true,
      },
      {
        id: 'theme',
        type: 'choice',
        label: 'Dans quelle grande famille de droit se situe votre situation ?',
        options: [
          'Discipline / sanction',
          'Rupture du contrat',
          'Inaptitude / santé au travail',
          'Temps de travail / congés',
          'Rémunération / classification',
          'CSE / représentants',
          'Modification du contrat',
          'Contentieux Prud’hommes',
          'Autre',
        ],
        required: true,
      },
      {
        id: 'faits',
        type: 'text',
        label: 'Racontez les faits de façon chronologique : qui, quoi, quand ?',
        help: 'Restez sur les faits observables et datés, sans interprétation. Les juges apprécient à partir d’éléments factuels écrits.',
        placeholder: 'Ex : « Le 12 mars, Mme X, éducatrice embauchée en 2018, a refusé d’assurer un remplacement. Deux rappels écrits le 15 et 22 mars. »',
        required: true,
      },
      {
        id: 'preuves',
        type: 'choice',
        label: 'Disposez-vous d’écrits (mails, courriers, comptes-rendus, témoignages) ?',
        help: 'En droit du travail, la charge de la preuve de la matérialité de la faute pèse sur l’employeur.',
        options: ['Oui, solides', 'Oui, partielles', 'Non', 'Je ne sais pas'],
        required: true,
      },
      {
        id: 'protege',
        type: 'choice',
        label: 'Le salarié est-il protégé (RP, CSE, conseiller prud’homal, maternité, AT-MP) ?',
        help: 'Le statut protégé impose une autorisation préalable de l’inspection du travail (L2411-1 et s.).',
        options: ['Oui', 'Non', 'Je ne sais pas'],
      },
      {
        id: 'objectif',
        type: 'text',
        label: 'Au final, qu’aimeriez-vous obtenir, et quel risque voulez-vous éviter ?',
        placeholder: 'Ex : « Notifier un avertissement pour faire cesser le comportement, sans mettre en péril la relation. »',
        required: true,
      },
    ],
  },
  rh: {
    modeId: 'wizard_rh',
    module: 'rh',
    title: '👥 Diagnostic RH guidé',
    subtitle: 'Méthode socio-organisationnelle : Karasek · Hackman-Oldham · Crozier · Rousseau',
    steps: [
      {
        id: 'niveau',
        type: 'choice',
        label: 'À quel niveau pensez-vous que se joue principalement la situation ?',
        options: [
          'Un·e salarié·e en particulier',
          'Une équipe ou un collectif',
          'L’organisation entière',
          'L’interface manager / équipe',
        ],
        required: true,
      },
      {
        id: 'symptome',
        type: 'text',
        label: 'Que voit-on concrètement de l’extérieur ? Décrivez les signes visibles.',
        help: 'Listez simplement les faits et signaux qui vous alertent.',
        placeholder: 'Ex : « Trois démissions en 6 mois, ambiance pesante, 2 alertes CSE, absentéisme en hausse. »',
        required: true,
      },
      {
        id: 'karasek_lat',
        type: 'choice',
        label: 'Karasek — Autonomie : les personnes peuvent-elles choisir COMMENT elles font leur travail ?',
        help: 'Robert Karasek (1979) : l’autonomie (latitude décisionnelle) protège des RPS.',
        options: ['Plutôt forte', 'Moyenne', 'Plutôt faible', 'Je ne sais pas'],
        required: true,
      },
      {
        id: 'karasek_dem',
        type: 'choice',
        label: 'Karasek — Charge : comment qualifieriez-vous la charge de travail et la pression du temps ?',
        options: ['Forte', 'Moyenne', 'Faible', 'Je ne sais pas'],
        required: true,
      },
      {
        id: 'karasek_sup',
        type: 'choice',
        label: 'Karasek — Soutien : quel soutien reçoivent-ils des collègues et de l’encadrement ?',
        options: ['Fort', 'Moyen', 'Faible', 'Je ne sais pas'],
        required: true,
      },
      {
        id: 'objectif',
        type: 'text',
        label: 'Qu’aimeriez-vous obtenir au terme de cette démarche (3 à 6 mois) ?',
        placeholder: 'Ex : « Restaurer la confiance dans l’équipe et stabiliser la coordinatrice. »',
        required: true,
      },
    ],
  },
  formation: {
    modeId: 'wizard_formation',
    module: 'formation',
    title: '🎓 Diagnostic formation guidé',
    subtitle: 'Ingénierie pédagogique : besoin → dispositif → financement → évaluation',
    steps: [
      {
        id: 'origine',
        type: 'choice',
        label: 'D’où vient ce besoin de formation ?',
        options: [
          'Obligation légale',
          'Projet associatif / stratégique',
          'Demande individuelle',
          'Démarche GEPP collective',
          'Reconversion / mobilité',
          'Adaptation au poste',
        ],
        required: true,
      },
      {
        id: 'competence',
        type: 'text',
        label: 'Quelle compétence concrète voulez-vous développer ?',
        help: 'Pensez en 3 dimensions : savoir / savoir-faire / savoir-être.',
        placeholder: 'Ex : « Conduire un entretien annuel avec feedback bienveillant et objectifs SMART. »',
        required: true,
      },
      {
        id: 'public',
        type: 'choice',
        label: 'Qui est concerné par cette formation ?',
        options: [
          'Un·e salarié·e',
          'Une équipe (3 à 10 personnes)',
          'Tous les salariés',
          'Encadrants',
          'Nouveaux entrants',
          'Bénévoles',
        ],
        required: true,
      },
      {
        id: 'modalite',
        type: 'choice',
        label: 'Quelle modalité vous semble la plus adaptée ?',
        help: 'L’AFEST (formation en situation de travail) est très efficace en petite équipe.',
        options: ['Présentiel', 'Distanciel', 'Mixte / hybride', 'AFEST', 'Alternance', 'Sans préférence'],
        required: true,
      },
      {
        id: 'budget',
        type: 'text',
        label: 'Avez-vous un budget, un délai ou une période à éviter ?',
        placeholder: 'Ex : « Budget résiduel ~3 200 €, démarrage avant la rentrée de septembre. »',
      },
    ],
  },
  gouvernance: {
    modeId: 'wizard_gouvernance',
    module: 'gouvernance',
    title: '🏛️ Diagnostic gouvernance guidé',
    subtitle: 'Loi 1901 + sociologie des associations (Boltanski-Thévenot, Crozier)',
    steps: [
      {
        id: 'nature',
        type: 'choice',
        label: 'Quel est l’objet principal de votre questionnement ?',
        options: [
          'Statuts',
          'AG / CA / Bureau',
          'Responsabilité dirigeants',
          'Fiscalité (règle des 4P)',
          'RGPD',
          'Tension CA / direction',
          'Bénévolat',
          'Modèle économique',
          'Autre',
        ],
        required: true,
      },
      {
        id: 'asso',
        type: 'text',
        label: 'Présentez brièvement votre association : objet, taille, budget',
        placeholder: 'Ex : « Centre social loi 1901, agrément CAF, 18 ETP, 60 bénévoles, budget 1,2 M€. »',
        required: true,
      },
      {
        id: 'statuts',
        type: 'choice',
        label: 'Vos statuts ont-ils été révisés au cours des 5 dernières années ?',
        options: ['Oui', 'Non', 'Je ne sais pas'],
        required: true,
      },
      {
        id: 'ag',
        type: 'choice',
        label: 'Tenez-vous régulièrement une AG annuelle, des CA, avec des PV à jour ?',
        options: ['Oui, tout', 'En partie', 'Non', 'Je ne sais pas'],
        required: true,
      },
      {
        id: 'modele',
        type: 'choice',
        label: 'Comment décririez-vous votre modèle de gouvernance actuel ?',
        options: [
          'Centré sur les dirigeants élus',
          'Collégial / partagé',
          'Coopératif',
          'Hybride',
          'Je ne sais pas',
        ],
      },
      {
        id: 'objectif',
        type: 'text',
        label: 'Quel objectif aimeriez-vous atteindre dans 3 à 6 mois ?',
        placeholder: 'Ex : « Clarifier la délégation du CA à la direction salariée. »',
        required: true,
      },
    ],
  },
};

export function getWizard(module: Module): WizardConfig {
  return WIZARDS[module];
}

/** Construit une synthèse texte structurée des réponses pour envoi à /api/ask. */
export function buildWizardSynthesis(
  config: WizardConfig,
  answers: Record<string, string>,
): string {
  const lines: string[] = [
    `# Synthèse de diagnostic guidé — ${config.title.replace(/^[^\s]+\s/, '')}`,
    '',
  ];
  for (const step of config.steps) {
    const value = answers[step.id]?.trim();
    if (!value) continue;
    lines.push(`**${step.label}**`);
    lines.push(value);
    lines.push('');
  }
  return lines.join('\n').trim();
}
