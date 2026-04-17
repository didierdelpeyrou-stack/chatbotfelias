#!/usr/bin/env python3
"""
Enrichit base_formation.json avec des articles clés issus des sources officielles :
- Code du travail (Legifrance)
- travail-emploi.gouv.fr / moncompteformation.gouv.fr
- France compétences (https://www.francecompetences.fr/)
- OPCO Cohésion sociale (https://www.opco-cohesion-sociale.fr/)
- Centre Inffo (https://www.centre-inffo.fr/)

Couvre : entretien professionnel & état des lieux, plan de développement,
CPF co-construit, Projet de Transition Professionnelle, Pro-A, AFEST,
Qualiopi, OPCO Cohésion sociale, apprentissage vs contrat pro, abondements CPF.

Sauvegarde base_formation.json.bak avant modification.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "base_formation.json"
BAK = ROOT / "data" / "base_formation.json.bak"

LEGIFRANCE_CT = "https://www.legifrance.gouv.fr/codes/texte_lc/LEGITEXT000006072050/"
TRAVAIL_GOUV = "https://travail-emploi.gouv.fr/"
MONCOMPTE = "https://www.moncompteformation.gouv.fr/"
FRANCE_COMP = "https://www.francecompetences.fr/"
OPCO_CS = "https://www.opco-cohesion-sociale.fr/"
CENTRE_INFFO = "https://www.centre-inffo.fr/"


NEW_ARTICLES = {
    "obligations_employeur": [
        {
            "id": "oblig-04",
            "question_type": "Quelles sont les règles de l'entretien professionnel et de l'état des lieux à 6 ans ?",
            "mots_cles": [
                "entretien professionnel", "L6315-1", "état des lieux", "6 ans",
                "abondement correctif", "3000 euros", "sanction", "obligation employeur",
                "évolution professionnelle", "certification",
            ],
            "reponse": {
                "synthese": "L'entretien professionnel est obligatoire tous les 2 ans pour tous les salariés, quel que soit leur contrat (CDI, CDD, temps partiel, apprentissage). Il est consacré exclusivement aux perspectives d'évolution professionnelle. Tous les 6 ans, un état des lieux récapitulatif vérifie que le salarié a bénéficié des entretiens et d'au moins une action de formation non obligatoire. À défaut, les entreprises de 50 salariés et plus doivent verser un abondement correctif de 3 000 € sur le CPF du salarié.",
                "minimum_legal": "Article L6315-1 du Code du travail (créé par la loi du 5 mars 2014, réformé par la loi du 5 septembre 2018). Article L6315-1 II : état des lieux à 6 ans. Article L6323-13 : abondement correctif de 3 000 € (décret n° 2014-1120 du 2 octobre 2014, modifié par le décret n° 2018-1171). Sanction : jusqu'au 30 septembre 2021, l'employeur pouvait choisir entre l'ancien critère (2 des 3 items) et le nouveau (formation non obligatoire) ; depuis le 1er octobre 2021, seul le nouveau critère s'applique.",
                "plus_formation": "La branche ALISFA recommande une trame écrite d'entretien professionnel signée des deux parties. Le Cepex (Certificat d'employeur public éligible) et les outils Uniformation/OPCO Cohésion sociale proposent des modèles d'entretien adaptés à la branche. Les aides de l'OPCO financent l'accompagnement RH des petites structures (< 50 salariés) pour sécuriser leur dispositif. La loi n° 2018-771 a distingué les formations obligatoires (sécurité, adaptation au poste) — qui ne comptent PAS pour l'état des lieux — des formations non obligatoires.",
                "sources": [
                    "Art. L6315-1 C. trav.",
                    "Art. L6323-13 C. trav.",
                    "Loi n° 2014-288 du 5 mars 2014",
                    "Loi n° 2018-771 du 5 septembre 2018 (Avenir professionnel)",
                    "Décret n° 2018-1171 du 18 décembre 2018",
                    "OPCO Cohésion sociale — guides entretien professionnel",
                ],
            },
            "fiches_pratiques": [],
        },
    ],
    "plan_competences": [
        {
            "id": "plan-03",
            "question_type": "Comment construire et financer le plan de développement des compétences ?",
            "mots_cles": [
                "plan de développement des compétences", "PDC",
                "formations obligatoires", "formations non obligatoires",
                "L6321-1", "L6321-2", "temps de travail", "OPCO",
                "consultation CSE", "catalogue formation",
            ],
            "reponse": {
                "synthese": "Le plan de développement des compétences (PDC, anciennement plan de formation) regroupe toutes les actions de formation décidées par l'employeur pour ses salariés. Il distingue deux catégories d'actions : les formations obligatoires (découlant d'une disposition légale ou conventionnelle, sécurité, habilitations) qui se déroulent sur le temps de travail avec maintien de rémunération, et les formations non obligatoires qui peuvent, par accord individuel écrit, se dérouler en tout ou partie hors temps de travail (dans la limite de 30 h/an ou 2 % du forfait jours).",
                "minimum_legal": "Articles L6321-1 à L6321-13 du Code du travail. Article L6321-1 : obligation d'adaptation au poste et de maintien de l'employabilité. Article L6321-2 : formations obligatoires. Article L6321-6 : formations non obligatoires (accord écrit individuel). Article L2312-24 : consultation annuelle du CSE sur la politique sociale, qui inclut le PDC. Financement : contribution unique à la formation professionnelle et à l'alternance (CUFPA) collectée par l'URSSAF (art. L6131-1 et s.), redistribuée via France compétences aux OPCO.",
                "plus_formation": "Pour les structures ALISFA < 50 salariés, l'OPCO Cohésion sociale (ex-Uniformation) prend en charge une partie importante du PDC (coûts pédagogiques, rémunération, frais annexes) dans le cadre des enveloppes mutualisées. Les entreprises ≥ 50 salariés financent leur PDC sur leur propre budget mais bénéficient de cofinancements sur projets (abondements CPF, POE, projets collectifs). La CPNEF ALISFA définit chaque année des priorités de branche (publics prioritaires, certifications cibles) qui ouvrent des financements renforcés. Consultation CSE obligatoire ≥ 50 salariés.",
                "sources": [
                    "Art. L6321-1 à L6321-13 C. trav.",
                    "Art. L6131-1 et s. C. trav. (CUFPA)",
                    "Loi n° 2018-771 du 5 septembre 2018 (Avenir professionnel)",
                    "OPCO Cohésion sociale — guide PDC",
                    "France compétences — Répertoire National des Certifications Professionnelles",
                ],
            },
            "fiches_pratiques": [],
        },
    ],
    "cpf": [
        {
            "id": "cpf-02",
            "question_type": "Comment fonctionnent les abondements du CPF et le reste à charge de 100 € ?",
            "mots_cles": [
                "CPF", "abondement", "L6323-4", "L6323-14",
                "reste à charge", "participation 100 euros", "forfait",
                "co-construction", "employeur abondement", "moncompteformation",
                "loi finances 2024",
            ],
            "reponse": {
                "synthese": "Le Compte Personnel de Formation (CPF) est alimenté annuellement de 500 € (800 € pour les peu qualifiés) avec un plafond de 5 000 € (8 000 € pour les peu qualifiés). Quand le solde du CPF est insuffisant pour financer une formation, des abondements complémentaires peuvent provenir du salarié, de l'employeur, de l'OPCO, de France Travail, de la Région ou du dispositif de branche. Depuis le 2 mai 2024, une participation forfaitaire du salarié de 102,23 € (2026) s'applique à toute inscription (hors salariés demandeurs d'emploi et hors abondement employeur).",
                "minimum_legal": "Articles L6323-1 à L6323-23 du Code du travail. Article L6323-4 : alimentation annuelle du CPF. Article L6323-11 : plafond. Article L6323-14 : abondements complémentaires. Article L6323-7 II (loi de finances 2024 n° 2023-1322 du 29 décembre 2023, art. 212) : participation obligatoire du titulaire indexée sur le SMIC, sauf exceptions. Décret n° 2024-394 du 29 avril 2024 (participation forfaitaire). Article L6323-4 IV : possibilité d'abondement volontaire de l'employeur via le portail EDEF.",
                "plus_formation": "Co-construction CPF : l'employeur peut abonder le CPF d'un salarié via le portail EDEF (Espace des employeurs et financeurs) pour financer une formation stratégique pour l'entreprise, ce qui exonère le salarié du reste à charge. Dans la branche ALISFA, l'OPCO Cohésion sociale dispose d'une enveloppe annuelle pour abonder les CPF sur les certifications de branche prioritaires (Cepex, CQP Animateur périscolaire, CAP AEPE...). Pour bénéficier d'une formation CPF sur le temps de travail, l'accord de l'employeur est requis si elle se déroule pendant les heures habituelles.",
                "sources": [
                    "Art. L6323-1 à L6323-23 C. trav.",
                    "Loi n° 2023-1322 du 29 décembre 2023 (LF 2024), art. 212",
                    "Décret n° 2024-394 du 29 avril 2024",
                    "Portail Mon compte formation — moncompteformation.gouv.fr",
                    "OPCO Cohésion sociale — abondements CPF",
                ],
            },
            "fiches_pratiques": [],
        },
    ],
    "transition_pro": [
        {
            "id": "trans-03",
            "question_type": "Qu'est-ce que le Projet de Transition Professionnelle (PTP / ex-CIF) ?",
            "mots_cles": [
                "PTP", "Projet transition professionnelle", "CIF",
                "L6323-17-1", "changement de métier", "reconversion",
                "transitions pro", "AT Pro", "commission paritaire",
                "24 mois", "salaire maintenu",
            ],
            "reponse": {
                "synthese": "Le Projet de Transition Professionnelle (PTP), créé par la loi du 5 septembre 2018, remplace l'ancien CIF (Congé Individuel de Formation). Il permet au salarié de s'absenter de son poste pour suivre une formation certifiante en vue de changer de métier ou de profession. Le PTP est mobilisé via le CPF, avec prise en charge du salaire et des frais de formation par l'association Transitions Pro (AT Pro) de la région du salarié, sous réserve de validation du projet par la commission paritaire régionale.",
                "minimum_legal": "Articles L6323-17-1 à L6323-17-6 du Code du travail. Article L6323-17-1 : PTP ouvert aux salariés justifiant de 24 mois d'activité salariée (consécutifs ou non) dont 12 mois dans l'entreprise actuelle. Article L6323-17-2 : autorisation d'absence et procédure. Article L6323-17-4 : prise en charge par AT Pro (plafond = 2 SMIC pour la rémunération). Décret n° 2018-1332 du 28 décembre 2018. La demande d'absence doit être adressée à l'employeur 120 jours avant le début si absence > 6 mois, 60 jours sinon.",
                "plus_formation": "Dans la branche ALISFA, le PTP est notamment utilisé pour les reconversions vers les métiers en tension (petite enfance → animation, ou inversement) ou vers des métiers porteurs (coordination, direction). L'OPCO Cohésion sociale et les structures AT Pro (15 associations régionales depuis 2020, sous France compétences) accompagnent le salarié dans la construction du dossier. Le salarié conserve son contrat de travail, sa rémunération (maintien total jusqu'à 2 SMIC, puis dégressif) et son ancienneté. À l'issue du PTP, il retrouve son poste ou un poste équivalent, sauf s'il démissionne.",
                "sources": [
                    "Art. L6323-17-1 à L6323-17-6 C. trav.",
                    "Loi n° 2018-771 du 5 septembre 2018",
                    "Décret n° 2018-1332 du 28 décembre 2018",
                    "Transitions Pro — portail national",
                    "France compétences — PTP",
                ],
            },
            "fiches_pratiques": [],
        },
    ],
    "alternance": [
        {
            "id": "alter-03",
            "question_type": "Quelles sont les différences entre contrat d'apprentissage et contrat de professionnalisation ?",
            "mots_cles": [
                "apprentissage", "contrat professionnalisation",
                "L6221-1", "L6325-1", "aide à l'embauche", "aide 6000 euros",
                "CFA", "OPCO", "NPEC", "niveau de prise en charge",
                "jeune", "16-29 ans",
            ],
            "reponse": {
                "synthese": "Deux contrats en alternance coexistent : le contrat d'apprentissage (formation initiale, certificat/diplôme RNCP, 16-29 ans hors dérogations, régime social et fiscal très avantageux) et le contrat de professionnalisation (formation continue, 16-25 ans ou demandeur d'emploi de 26 ans et +, diplôme RNCP, CQP de branche ou bloc de compétences). L'apprentissage bénéficie depuis 2018 d'aides uniques à l'employeur, d'un financement au contrat via les OPCO selon les Niveaux de Prise en Charge (NPEC) fixés par France compétences.",
                "minimum_legal": "APPRENTISSAGE : Articles L6221-1 à L6227-12 du Code du travail. Aide unique à l'apprentissage L6243-1 et s. : 6 000 € la première année pour les contrats signés en 2024-2025 (décret n° 2023-1354 du 29 décembre 2023, prolongé par décret annuel). CONTRAT PRO : Articles L6325-1 à L6325-24 C. trav. Article L6325-5 : durée 6 à 12 mois (24 mois pour CQP ou publics prioritaires). Article L6332-14 : prise en charge par l'OPCO selon les forfaits définis par la branche. Article L6211-1 : l'apprenti est salarié à part entière.",
                "plus_formation": "Dans la branche ALISFA, le contrat d'apprentissage est privilégié pour préparer un CAP AEPE, un BPJEPS, un Cepex ou un DEJEPS (via un CFA partenaire de l'OPCO Cohésion sociale). Le contrat de professionnalisation est souvent utilisé pour des CQP de branche (CQP Animateur périscolaire). L'OPCO publie chaque année les NPEC applicables par certification. Les petites structures (< 11 salariés) bénéficient en outre d'exonérations de cotisations salariales sur la rémunération de l'apprenti (art. L6243-2), et les apprentis sont exclus du décompte de l'effectif (sauf AT/MP).",
                "sources": [
                    "Art. L6221-1 à L6227-12 C. trav. (apprentissage)",
                    "Art. L6325-1 à L6325-24 C. trav. (contrat pro)",
                    "Décret n° 2023-1354 du 29 décembre 2023 (aide 6000 €)",
                    "France compétences — NPEC publiés",
                    "OPCO Cohésion sociale — offre alternance ALISFA",
                ],
            },
            "fiches_pratiques": [],
        },
    ],
    "cep_afest": [
        {
            "id": "cep-06",
            "question_type": "Qu'est-ce qu'une Action de Formation En Situation de Travail (AFEST) ?",
            "mots_cles": [
                "AFEST", "action formation situation travail",
                "L6313-2", "parcours pédagogique", "analyse activité",
                "mise en situation", "phases réflexives", "évaluation",
                "formateur interne", "tuteur",
            ],
            "reponse": {
                "synthese": "L'AFEST est une modalité pédagogique reconnue par la loi du 5 septembre 2018 : elle permet de former un salarié directement à partir et sur son poste de travail. C'est une action de formation à part entière (éligible au PDC et aux financements OPCO), à condition de respecter un cadre pédagogique structuré : (1) analyse de l'activité de travail, (2) désignation d'un formateur/référent (interne ou externe), (3) mise en situation évaluative, (4) phases réflexives distinctes des phases productives, (5) évaluation des acquis.",
                "minimum_legal": "Article L6313-2 du Code du travail (issu de la loi n° 2018-771 du 5 septembre 2018). Article D6313-3-1 (décret n° 2018-1341 du 28 décembre 2018) : conditions cumulatives de l'AFEST. Article L6313-1 : l'AFEST est l'une des 4 catégories d'actions concourant au développement des compétences, avec les formations en salle, les formations à distance et les actions mixtes. Article L6351-1 : l'AFEST doit être déclarée comme action de formation par un organisme déclaré.",
                "plus_formation": "L'AFEST est particulièrement adaptée aux structures ALISFA qui ont peu de ressources pour envoyer des salariés en formation externe. L'OPCO Cohésion sociale finance à la fois l'ingénierie AFEST (analyse du travail, construction du référentiel, formation de tuteurs) et la mise en œuvre (temps du formateur et du salarié). Le Centre Inffo et l'ANACT ont publié des guides méthodologiques officiels. Attention : une simple formation « sur le tas » sans cadre formalisé n'est PAS une AFEST et ne peut être financée comme action de formation.",
                "sources": [
                    "Art. L6313-1 et L6313-2 C. trav.",
                    "Art. D6313-3-1 C. trav.",
                    "Loi n° 2018-771 du 5 septembre 2018",
                    "Décret n° 2018-1341 du 28 décembre 2018",
                    "ANACT / Centre Inffo — guides AFEST",
                    "OPCO Cohésion sociale — ingénierie AFEST",
                ],
            },
            "fiches_pratiques": [],
        },
    ],
    "acteurs_formation": [
        {
            "id": "acteur-04",
            "question_type": "Qu'est-ce que la certification Qualiopi et qui est concerné ?",
            "mots_cles": [
                "Qualiopi", "certification qualité", "L6316-1",
                "organisme formation", "RNQ", "référentiel national qualité",
                "7 critères", "audit", "décret 2019-565", "financement public",
            ],
            "reponse": {
                "synthese": "Qualiopi est la marque de certification qualité des prestataires d'actions concourant au développement des compétences. Depuis le 1er janvier 2022, elle est OBLIGATOIRE pour tout organisme qui souhaite faire financer ses actions sur fonds publics ou mutualisés (OPCO, CPF, Pôle emploi devenu France Travail, État, Régions, AGEFIPH). La certification repose sur le Référentiel National Qualité (RNQ) structuré en 7 critères et 32 indicateurs, audités par un organisme certificateur accrédité par le COFRAC.",
                "minimum_legal": "Article L6316-1 du Code du travail (loi n° 2018-771 du 5 septembre 2018). Décret n° 2019-564 du 6 juin 2019 (obligation de certification). Décret n° 2019-565 du 6 juin 2019 (RNQ). Arrêté du 6 juin 2019 modifié (modalités d'audit). Sont concernés : les organismes de formation, les CFA, les bilans de compétences, les opérateurs VAE. Audit initial, audit de surveillance à 18 mois, renouvellement tous les 3 ans.",
                "plus_formation": "Les structures ALISFA qui disposent d'un organisme de formation interne ou portent un projet de CFA (crèche école, centre social école de devoirs, etc.) doivent obtenir Qualiopi pour faire financer leurs actions par l'OPCO Cohésion sociale ou la branche. L'OPCO propose des accompagnements collectifs pour préparer la certification et, le cas échéant, un cofinancement de l'audit. Alternative : utiliser un organisme certifié externe comme sous-traitant. Liste officielle des organismes certificateurs sur le site data.gouv.fr.",
                "sources": [
                    "Art. L6316-1 C. trav.",
                    "Décret n° 2019-564 et n° 2019-565 du 6 juin 2019",
                    "Arrêté du 6 juin 2019 (RNQ)",
                    "travail-emploi.gouv.fr — Qualiopi",
                    "data.gouv.fr — liste organismes certifiés",
                ],
            },
            "fiches_pratiques": [],
        },
    ],
    "financement_cpnef": [
        {
            "id": "cpnef-04",
            "question_type": "Comment fonctionne l'OPCO Cohésion sociale pour les structures ALISFA ?",
            "mots_cles": [
                "OPCO Cohésion sociale", "Uniformation", "opérateur de compétences",
                "L6332-1", "contribution formation", "CUFPA", "mutualisation",
                "plan de développement", "branche ALISFA", "3 millions de salariés",
            ],
            "reponse": {
                "synthese": "L'OPCO Cohésion sociale (marque historique Uniformation) est l'opérateur de compétences désigné par arrêté du 29 mars 2019 pour couvrir la branche ALISFA (IDCC 1261) parmi une vingtaine de branches de l'économie sociale, du logement social et du sanitaire/social. Il collecte indirectement la contribution unique à la formation professionnelle et à l'alternance (CUFPA, collectée par l'URSSAF depuis 2022) et la redistribue sous forme d'aides aux entreprises pour le plan de développement des compétences, l'alternance, les POE et les projets collectifs.",
                "minimum_legal": "Articles L6332-1 à L6332-14 du Code du travail. Article L6332-1-2 : missions des OPCO (conseil aux TPE/PME < 50 salariés, financement alternance, appui technique). Article L6131-1 : CUFPA collectée par URSSAF. Article L6131-2 : répartition France compétences / OPCO. Arrêté du 29 mars 2019 portant agrément de l'OPCO Cohésion sociale. Loi n° 2018-771 du 5 septembre 2018 (Avenir professionnel) — refonte des OPCA en 11 OPCO.",
                "plus_formation": "L'OPCO Cohésion sociale finance en priorité les structures de moins de 50 salariés de la branche ALISFA sur : (1) le PDC à 100 % des coûts pédagogiques + frais annexes dans la limite d'enveloppes individualisées, (2) l'alternance (contrat d'apprentissage et contrat pro) au NPEC fixé par France compétences, (3) les actions collectives (projets de branche CPNEF), (4) les abondements CPF sur certifications prioritaires, (5) la préparation opérationnelle à l'emploi (POEI et POEC). Contact via le conseiller sectoriel ALISFA de l'OPCO — demande à déposer sur l'extranet adhérent.",
                "sources": [
                    "Art. L6332-1 à L6332-14 C. trav.",
                    "Arrêté du 29 mars 2019 (agrément OPCO Cohésion sociale)",
                    "Loi n° 2018-771 du 5 septembre 2018",
                    "OPCO Cohésion sociale — site officiel",
                    "CPNEF ALISFA — priorités de branche",
                ],
            },
            "fiches_pratiques": [],
        },
    ],
    "gpec_metiers": [
        {
            "id": "gpec-02",
            "question_type": "Qu'est-ce que le dispositif Pro-A (reconversion ou promotion par alternance) ?",
            "mots_cles": [
                "Pro-A", "reconversion alternance", "promotion",
                "L6324-1", "accord de branche étendu", "qualification",
                "alternance", "OPCO", "changement métier", "dispositif Pro-A",
            ],
            "reponse": {
                "synthese": "La Reconversion ou Promotion par Alternance (Pro-A) est un dispositif qui permet à un salarié en CDI d'accéder, pendant son temps de travail, à une formation qualifiante dispensée en alternance, afin de changer de métier ou d'accéder à une promotion. Elle est réservée aux salariés dont le niveau de qualification est inférieur à une licence (bac+2 depuis la loi du 5 septembre 2018) et aux certifications visées par un accord de branche étendu. Elle est financée par l'OPCO.",
                "minimum_legal": "Articles L6324-1 à L6324-9 du Code du travail. Article L6324-1 : publics et conditions. Article L6324-3 : les certifications éligibles sont fixées par accord collectif de branche étendu. Loi n° 2018-771 du 5 septembre 2018 + loi n° 2020-734 du 17 juin 2020 (ajout de l'enjeu de mutation de l'activité). Article L6324-5 : contrat de travail maintenu, alternance entre formation et travail effectif (15 à 25 % minimum de la durée du contrat pour la formation).",
                "plus_formation": "Pour les structures ALISFA, la Pro-A est un outil précieux pour accompagner la montée en qualification des salariés sans maîtrise des diplômes cibles (auxiliaire de puériculture, éducateur de jeunes enfants, animateur BPJEPS, coordinateur...). Elle nécessite un accord de branche étendu listant les certifications éligibles. La CPNEF ALISFA a négocié en 2020 un accord Pro-A (vérifier la liste à jour sur le site ELISFA). L'OPCO Cohésion sociale prend en charge les coûts pédagogiques, la rémunération du salarié pendant les heures de formation, et les frais annexes.",
                "sources": [
                    "Art. L6324-1 à L6324-9 C. trav.",
                    "Loi n° 2018-771 du 5 septembre 2018",
                    "Loi n° 2020-734 du 17 juin 2020",
                    "Accord de branche ALISFA sur la Pro-A",
                    "OPCO Cohésion sociale — guide Pro-A",
                ],
            },
            "fiches_pratiques": [],
        },
    ],
    "droits_salaries": [
        {
            "id": "droit-03",
            "question_type": "Le salarié peut-il mobiliser son CPF sans l'accord de l'employeur ?",
            "mots_cles": [
                "CPF", "accord employeur", "temps de travail",
                "L6323-17", "hors temps de travail", "refus",
                "absence formation", "droit à la formation",
            ],
            "reponse": {
                "synthese": "Le CPF appartient au salarié : il peut le mobiliser librement HORS temps de travail sans avoir à en informer ni à demander l'accord de son employeur. Sur le temps de travail, en revanche, l'accord de l'employeur est obligatoire pour autoriser l'absence (portant sur le calendrier et la durée). L'employeur peut refuser mais doit motiver sa décision ; un refus abusif répété peut engager sa responsabilité vis-à-vis de l'obligation de maintien de l'employabilité (L6321-1).",
                "minimum_legal": "Article L6323-17 du Code du travail (CPF mobilisé sur le temps de travail = autorisation préalable). Article L6323-16 : CPF hors temps de travail = aucun accord requis. Article L6323-17-1 : PTP = procédure spécifique. Article L6321-1 : obligation employeur d'adaptation et d'employabilité. L'employeur dispose de 30 jours calendaires pour répondre à une demande de CPF sur temps de travail (absence de réponse = accord tacite).",
                "plus_formation": "Bonne pratique ALISFA : intégrer l'information CPF dans l'entretien professionnel, et recenser les besoins CPF en lien avec le plan de développement des compétences. L'employeur peut abonder le CPF d'un salarié via le portail EDEF pour co-financer une formation stratégique (formation qualifiante, reconversion, certification de branche) : cet abondement exonère alors le salarié du reste à charge légal et peut constituer une alternative intéressante au PDC pour les petites structures. L'OPCO Cohésion sociale peut également abonder sur des certifications de branche prioritaires (Cepex, CQP).",
                "sources": [
                    "Art. L6323-16 et L6323-17 C. trav.",
                    "Art. L6321-1 C. trav.",
                    "Mon compte formation — guide pratique",
                    "Portail EDEF — Espace des employeurs et financeurs",
                    "OPCO Cohésion sociale — abondements",
                ],
            },
            "fiches_pratiques": [],
        },
    ],
}


def main() -> int:
    data = json.loads(SRC.read_text(encoding="utf-8"))
    shutil.copy(SRC, BAK)

    themes = {t["id"]: t for t in data["themes"]}
    added = 0
    for theme_id, articles in NEW_ARTICLES.items():
        theme = themes.get(theme_id)
        if not theme:
            print(f"  ⚠ thème inconnu : {theme_id}")
            continue
        existing = {a["id"] for a in theme["articles"]}
        for art in articles:
            if art["id"] in existing:
                print(f"  ⏭  déjà présent : {art['id']}")
                continue
            theme["articles"].append(art)
            added += 1
            print(f"  ✅ {theme_id} :: {art['id']} — {art['question_type'][:70]}")

    data.setdefault("metadata", {})["date_consolidation"] = "2026-04-15"
    data["metadata"].setdefault("enrichissements", []).append(
        {
            "date": "2026-04-15",
            "source": "Legifrance, travail-emploi.gouv.fr, France compétences, OPCO Cohésion sociale, Centre Inffo",
            "ajouts": [a["id"] for arts in NEW_ARTICLES.values() for a in arts],
            "note": "Entretien pro + état 6 ans, PDC, CPF abondements, PTP, Pro-A, AFEST, Qualiopi, OPCO Cohésion sociale, apprentissage vs contrat pro, CPF sans accord employeur.",
        }
    )

    SRC.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{added} article(s) ajouté(s). Sauvegarde : {BAK}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
