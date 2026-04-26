// Sprint 4.6 — Suggestions de questions par module (empty-state ChatWindow).
// 6 questions par module = 24 au total. Adaptées du contenu V1
// (GUIDE_QUESTIONS, WIZARD_HINTS, exemples welcome modal).
//
// Critères :
//  - questions courtes, formulables en 1 phrase
//  - couvrent les sujets les plus fréquents en bêta-test
//  - contiennent les bons mots-clés pour le RAG ALISFA

import type { Module } from './types';

export const SUGGESTIONS: Record<Module, string[]> = {
  juridique: [
    "Quelle durée de préavis pour un CDI de 8 ans d'ancienneté ?",
    "Comment fonctionne le RSAI en EAJE ?",
    "Mon salarié est en arrêt depuis 6 mois, que faire ?",
    "Calculer une indemnité de licenciement",
    "Procédure pour une mise à pied conservatoire ?",
    "Comment rédiger un avertissement écrit ?",
  ],
  formation: [
    "Comment financer une formation BAFA ?",
    "Qu'est-ce que le CPF de transition ?",
    "Quel dispositif pour reconvertir un animateur ?",
    "Le plan de développement des compétences est-il obligatoire ?",
    "AFEST : comment la mettre en place ?",
    "Entretien professionnel : quelle est l'obligation ?",
  ],
  rh: [
    "Combien d'emplois repères dans la branche ALISFA ?",
    "Comment calculer une indemnité de licenciement ?",
    "Gérer un signalement de harcèlement",
    "3 démissions en 2 mois, que faire ?",
    "Différence entre faute simple, grave et lourde ?",
    "Mon équipe est en surcharge, comment réagir ?",
  ],
  gouvernance: [
    "Quelles obligations RGPD pour mon association ?",
    "Comment fonctionne une CPO avec une mairie ?",
    "Responsabilité civile et pénale du président bénévole ?",
    "Mes statuts datent de 10 ans, faut-il les modifier ?",
    "Fiscalité associative : règle des 4P ?",
    "Comment recruter et fidéliser des bénévoles ?",
  ],
};
