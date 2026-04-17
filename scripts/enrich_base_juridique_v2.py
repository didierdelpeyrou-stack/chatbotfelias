#!/usr/bin/env python3
"""
Enrichit base_juridique.json avec des articles transverses manquants,
sourcés sur Legifrance (Code du travail, Code de la sécurité sociale),
travail-emploi.gouv.fr et la jurisprudence Cour de cassation.

Couvre les thèmes : rupture, cse_irp, egalite, sante_securite, contrat_travail,
contentieux, remuneration, conges, formation, harcelement, prevoyance.

Sauvegarde base_juridique.json.bak2 avant modification.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "base_juridique.json"
BAK = ROOT / "data" / "base_juridique.json.bak2"

LEGIFRANCE_CT = "https://www.legifrance.gouv.fr/codes/texte_lc/LEGITEXT000006072050/"
LEGIFRANCE_CSS = "https://www.legifrance.gouv.fr/codes/texte_lc/LEGITEXT000006073189/"
LEGIFRANCE_CCN = "https://www.legifrance.gouv.fr/conv_coll/id/KALICONT000005635384"
TRAVAIL_GOUV = "https://travail-emploi.gouv.fr/"
SERVICE_PUBLIC = "https://www.service-public.fr/particuliers/vosdroits/"
COURCASS = "https://www.courdecassation.fr/"


def L(article: str) -> str:
    """Lien direct Legifrance vers un article du Code du travail."""
    return f"https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI{article}"


NEW_ARTICLES = {
    "rupture": [
        {
            "id": "rupt-10",
            "question_type": "Comment procéder à une rupture conventionnelle individuelle ?",
            "mots_cles": [
                "rupture conventionnelle", "rupture amiable", "homologation DREETS",
                "indemnité spécifique", "Cerfa 14598", "délai rétractation",
                "L1237-11", "L1237-13", "L1237-14", "TéléRC",
            ],
            "reponse": {
                "synthese": "La rupture conventionnelle individuelle est le seul mode de rupture amiable du CDI. Elle suppose : (1) un ou plusieurs entretiens entre employeur et salarié, (2) la signature d'une convention de rupture fixant la date de fin de contrat et le montant de l'indemnité spécifique, (3) un délai de rétractation de 15 jours calendaires pour chaque partie, (4) l'homologation par la DREETS (via TéléRC) dans un délai d'instruction de 15 jours ouvrables. Silence = homologation tacite. L'indemnité ne peut être inférieure à l'indemnité légale de licenciement (ou conventionnelle si plus favorable).",
                "fondement_legal": "Articles L1237-11 à L1237-16 du Code du travail (créés par la loi du 25 juin 2008). Article L1237-13 : contenu obligatoire de la convention. Article L1237-14 : homologation administrative. Article R1237-3 : délai d'instruction DREETS. Article L1234-9 : indemnité légale de licenciement (référence plancher).",
                "fondement_ccn": "CCN ALISFA (IDCC 1261) — l'indemnité conventionnelle de licenciement de la branche (si plus favorable que l'indemnité légale) s'applique comme plancher à l'indemnité spécifique de rupture conventionnelle (Cass. soc. 27 juin 2018 n° 17-15.948).",
                "application": "Étapes : (1) proposer et mener au moins un entretien (le salarié peut être assisté), (2) compléter le Cerfa 14598*01 sur TéléRC (téléservice obligatoire depuis avril 2022), (3) signer la convention en double exemplaire daté, (4) respecter le délai de rétractation de 15 jours calendaires démarrant le lendemain de la signature, (5) transmettre la demande d'homologation à la DREETS à l'issue du délai, (6) la rupture ne peut prendre effet avant le lendemain de l'homologation. Le salarié perçoit l'allocation chômage dans les conditions de droit commun.",
                "vigilance": "Nullité prononcée en cas de vice du consentement, de pression, de harcèlement ou de contexte conflictuel caractérisé (Cass. soc. 30 janvier 2013 n° 11-22.332). La rupture conventionnelle est interdite pour contourner un licenciement économique collectif ou un PSE. Depuis le 1er septembre 2023, le régime fiscal et social a été aligné : l'employeur verse une contribution patronale unique de 30 % sur la part exonérée de cotisations (loi de financement de la SS 2023).",
                "sources": [
                    "Art. L1237-11 à L1237-16 C. trav.",
                    "Cerfa 14598*01 — TéléRC",
                    "Cass. soc. 30 janvier 2013 n° 11-22.332",
                    "Cass. soc. 27 juin 2018 n° 17-15.948",
                    "LFSS 2023 — contribution patronale unique 30 %",
                ],
                "liens": [
                    {"titre": "TéléRC — service de saisie en ligne", "url": "https://www.telerc.travail.gouv.fr/"},
                    {"titre": "Code du travail — art. L1237-11 et s.", "url": LEGIFRANCE_CT},
                    {"titre": "Fiche pratique travail-emploi.gouv.fr", "url": "https://travail-emploi.gouv.fr/la-rupture-conventionnelle-du-contrat-de-travail-a-duree-indeterminee"},
                    {"titre": "Service-public.fr — rupture conventionnelle", "url": "https://www.service-public.fr/particuliers/vosdroits/F1072"},
                ],
            },
            "fiches_pratiques": [],
        },
    ],
    "cse_irp": [
        {
            "id": "cse-03",
            "question_type": "Quelles sont les obligations de la BDESE (base de données économiques, sociales et environnementales) ?",
            "mots_cles": [
                "BDESE", "base de données", "consultation CSE", "L2312-18",
                "L2312-21", "transition écologique", "indicateurs",
                "consultation annuelle", "orientation stratégique",
            ],
            "reponse": {
                "synthese": "La BDESE (base de données économiques, sociales et environnementales) est obligatoire dans toute entreprise de 50 salariés et plus. Elle centralise les informations nécessaires aux trois consultations récurrentes du CSE (orientations stratégiques, situation économique et financière, politique sociale/conditions de travail/emploi). Depuis la loi Climat & Résilience du 22 août 2021, elle intègre obligatoirement un volet environnemental.",
                "fondement_legal": "Articles L2312-18 à L2312-21 du Code du travail. Article R2312-8 à R2312-10 : contenu supplétif de la BDESE en l'absence d'accord. Loi n° 2021-1104 du 22 août 2021 (Climat & Résilience) — ajout obligatoire d'indicateurs environnementaux. Décret n° 2022-678 du 26 avril 2022.",
                "fondement_ccn": "Pas de disposition spécifique ALISFA. À défaut d'accord d'entreprise, le contenu supplétif du Code du travail s'applique (R2312-9 pour < 300 salariés, R2312-10 pour ≥ 300).",
                "application": "La BDESE couvre 9 thèmes : investissement social, investissement matériel et immatériel, égalité professionnelle F/H, fonds propres/endettement/impôts, rémunération des salariés et dirigeants, activités sociales et culturelles, rémunération des financeurs, flux financiers vers l'entreprise, sous-traitance et transferts, conséquences environnementales. Elle doit être accessible en permanence aux élus du CSE (support numérique préféré). Un accord collectif peut adapter son contenu et son architecture.",
                "vigilance": "Le défaut de mise à disposition ou le caractère incomplet de la BDESE constitue un délit d'entrave (L2317-1 C. trav.) sanctionné de 7 500 € d'amende. La jurisprudence exige une information réelle et actualisée, pas une simple liste de documents (Cass. soc. 28 mars 2018 n° 17-13.081).",
                "sources": [
                    "Art. L2312-18 à L2312-21 C. trav.",
                    "Art. R2312-8 à R2312-10 C. trav.",
                    "Loi n° 2021-1104 du 22 août 2021",
                    "Décret n° 2022-678 du 26 avril 2022",
                    "Cass. soc. 28 mars 2018 n° 17-13.081",
                ],
                "liens": [
                    {"titre": "Code du travail — BDESE (L2312-18)", "url": LEGIFRANCE_CT},
                    {"titre": "Fiche DGT — BDESE", "url": "https://travail-emploi.gouv.fr/la-base-de-donnees-economiques-sociales-et-environnementales-bdese"},
                    {"titre": "Loi Climat & Résilience — Légifrance", "url": "https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000043956924"},
                ],
            },
            "fiches_pratiques": [],
        },
    ],
    "egalite": [
        {
            "id": "egal-02",
            "question_type": "Quelles sont les obligations de l'index égalité femmes-hommes ?",
            "mots_cles": [
                "index égalité", "index F/H", "L1142-8", "L1142-9",
                "décret 2019-15", "note sur 100", "écart rémunération",
                "publication", "pénalité 1%", "augmentation après congé maternité",
            ],
            "reponse": {
                "synthese": "Toute entreprise d'au moins 50 salariés doit calculer et publier chaque année (au 1er mars) un index égalité professionnelle femmes-hommes, sur une note de 100 points. Les résultats doivent être publiés de façon visible et lisible sur le site internet de l'entreprise (ou à défaut, portés à la connaissance des salariés) et transmis à la DREETS via l'outil Egapro. En-dessous de 75/100, l'entreprise dispose de 3 ans pour se mettre en conformité, sous peine de pénalité financière pouvant atteindre 1 % de la masse salariale.",
                "fondement_legal": "Articles L1142-7 à L1142-10 du Code du travail (loi Avenir professionnel du 5 septembre 2018). Articles D1142-2 à D1142-14. Décret n° 2019-15 du 8 janvier 2019 (calcul des indicateurs). Décret n° 2022-243 du 25 février 2022 (publication détaillée des notes par indicateur + mesures de correction). Article L1142-8 : obligation de publication.",
                "fondement_ccn": "La CCN ALISFA (IDCC 1261) ne déroge pas au dispositif. Dans la branche, majoritairement composée de structures féminisées, l'indicateur n° 4 (augmentation au retour de congé maternité) est particulièrement surveillé.",
                "application": "Indicateurs pour 50-250 salariés (sur 100) : (1) écart de rémunération – 40 points, (2) écart de taux d'augmentations individuelles – 35 points, (4) pourcentage de salariées augmentées au retour de congé maternité – 15 points, (5) nombre de femmes dans les 10 plus hautes rémunérations – 10 points. Pour ≥ 250 salariés, l'indicateur n° 3 (taux de promotions) s'ajoute. Publication via www.egapro.travail.gouv.fr.",
                "vigilance": "Une note < 75/100 pendant 3 années consécutives expose à une pénalité pouvant atteindre 1 % de la masse salariale (L2242-8 C. trav.). Le défaut de publication est lui-même sanctionné. La publication doit être visible et accessible au moins jusqu'à la publication suivante.",
                "sources": [
                    "Art. L1142-7 à L1142-10 C. trav.",
                    "Décret n° 2019-15 du 8 janvier 2019",
                    "Décret n° 2022-243 du 25 février 2022",
                    "Loi n° 2018-771 du 5 septembre 2018 (Avenir professionnel)",
                ],
                "liens": [
                    {"titre": "Egapro — déclaration en ligne", "url": "https://egapro.travail.gouv.fr/"},
                    {"titre": "Index égalité — travail-emploi.gouv.fr", "url": "https://travail-emploi.gouv.fr/index-egalite-professionnelle-obligation-de-transparence-des-entreprises-sur-les-inegalites"},
                    {"titre": "Code du travail — L1142-8", "url": LEGIFRANCE_CT},
                ],
            },
            "fiches_pratiques": [],
        },
    ],
    "sante_securite": [
        {
            "id": "sante-04",
            "question_type": "Le document unique d'évaluation des risques professionnels (DUERP) est-il obligatoire et quelles sont les nouvelles règles 2022 ?",
            "mots_cles": [
                "DUERP", "document unique", "évaluation risques", "L4121-3",
                "R4121-1", "loi 2 août 2021", "santé au travail",
                "prévention", "plan annuel", "PAPRIPACT", "conservation 40 ans",
            ],
            "reponse": {
                "synthese": "Le DUERP est obligatoire dès le premier salarié. Il transcrit et met à jour les résultats de l'évaluation des risques pour la santé et la sécurité des travailleurs. Depuis la loi du 2 août 2021 (santé au travail), les versions successives doivent être conservées pendant 40 ans et déposées sur un portail numérique national (ouverture progressive à partir du 1er juillet 2023 pour ≥ 150 salariés, 1er juillet 2024 pour < 150).",
                "fondement_legal": "Article L4121-3 du Code du travail (obligation d'évaluation). Article R4121-1 à R4121-4 (DUERP, mise à jour annuelle minimum). Loi n° 2021-1018 du 2 août 2021 (renforcement de la prévention en santé au travail). Décret n° 2022-395 du 18 mars 2022. Article L4121-3-1 : conservation 40 ans et portail numérique.",
                "fondement_ccn": "Pas de disposition spécifique ALISFA. La branche recommande un appui via le service de prévention et de santé au travail interentreprises (SPSTI) auquel l'entreprise est adhérente.",
                "application": "Obligations : (1) évaluation des risques par unité de travail, (2) transcription dans le DUERP, (3) mise à jour au moins annuelle et lors de toute modification importante (nouvel équipement, réorganisation, AT/MP), (4) pour ≥ 50 salariés, élaboration d'un Programme annuel de prévention des risques professionnels et d'amélioration des conditions de travail (PAPRIPACT) — L4121-3 III, (5) consultation du CSE, (6) mise à disposition des salariés et de la médecine du travail.",
                "vigilance": "L'absence de DUERP est sanctionnée d'une contravention de 5e classe (1 500 €, 3 000 € en récidive) par unité de travail. En cas d'AT/MP, l'absence ou l'insuffisance du DUERP est un indice fort de manquement à l'obligation de sécurité de résultat (Cass. soc. 28 février 2006 n° 05-41.555, arrêts amiante).",
                "sources": [
                    "Art. L4121-3 et L4121-3-1 C. trav.",
                    "Art. R4121-1 à R4121-4 C. trav.",
                    "Loi n° 2021-1018 du 2 août 2021",
                    "Décret n° 2022-395 du 18 mars 2022",
                    "Cass. soc. 28 février 2006 n° 05-41.555",
                ],
                "liens": [
                    {"titre": "Portail national DUERP", "url": "https://www.portail-duerp.fr/"},
                    {"titre": "INRS — dossier DUERP", "url": "https://www.inrs.fr/demarche/evaluation-risques-professionnels/document-unique.html"},
                    {"titre": "Code du travail — L4121-3", "url": LEGIFRANCE_CT},
                    {"titre": "Loi santé au travail 2021 — Légifrance", "url": "https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000043884445"},
                ],
            },
            "fiches_pratiques": [],
        },
    ],
    "contentieux": [
        {
            "id": "content-02",
            "question_type": "Comment fonctionne la saisine du Conseil de prud'hommes et le barème Macron ?",
            "mots_cles": [
                "conseil prud'hommes", "CPH", "saisine", "R1452-1",
                "barème Macron", "L1235-3", "licenciement sans cause réelle et sérieuse",
                "indemnité", "plafond", "plancher", "bureau conciliation",
            ],
            "reponse": {
                "synthese": "Le Conseil de prud'hommes (CPH) est compétent pour tous les litiges individuels entre employeurs et salariés liés à l'exécution ou à la rupture du contrat de travail. La procédure débute par une conciliation obligatoire (bureau de conciliation et d'orientation — BCO), puis à défaut un jugement au fond. Depuis les ordonnances Macron de 2017, l'indemnité pour licenciement sans cause réelle et sérieuse est encadrée par un barème obligatoire (L1235-3) fonction de l'ancienneté et de la taille de l'entreprise.",
                "fondement_legal": "Articles L1411-1 à L1411-6 (compétence CPH). Articles R1452-1 à R1453-6 (saisine et procédure). Article L1235-3 C. trav. (barème Macron, ordonnance n° 2017-1387 du 22 septembre 2017). Article L1235-3-1 (exceptions au barème : nullité, harcèlement, discrimination → indemnité minimum 6 mois sans plafond).",
                "fondement_ccn": "Pas de disposition spécifique ALISFA sur la procédure CPH. L'ancienneté s'apprécie à la date de la rupture, selon les règles de la CCN si plus favorables.",
                "application": "Saisine : par requête (formulaire Cerfa 15586*04) adressée au greffe du CPH du lieu de travail ou du domicile du salarié. La prescription est de 12 mois pour contester un licenciement (L1471-1), 2 ans pour l'exécution du contrat, 3 ans pour les salaires (L3245-1). Barème (indemnité en mois de salaire) : 1 an d'ancienneté → min 0,5 / max 1 (ou 2 si < 11 salariés) ; 5 ans → min 3 / max 6 ; 10 ans → min 3 / max 10 ; 20 ans → min 3 / max 15,5 ; 30+ ans → min 3 / max 20.",
                "vigilance": "Le barème Macron est validé par le Conseil constitutionnel (decision 2018-761 DC) et la Cour de cassation (Ass. plén. 11 mai 2022 n° 21-14.490 et 21-15.247). Il ne s'applique PAS en cas de licenciement nul (harcèlement, discrimination, maternité, lanceur d'alerte...) — indemnité minimale de 6 mois sans plafond. La conciliation peut aboutir à une indemnité forfaitaire (barème de conciliation R1235-22).",
                "sources": [
                    "Art. L1411-1 à L1411-6 C. trav.",
                    "Art. L1235-3 et L1235-3-1 C. trav.",
                    "Ordonnance n° 2017-1387 du 22 septembre 2017",
                    "Cons. const. 2018-761 DC",
                    "Cass. Ass. plén. 11 mai 2022 n° 21-14.490",
                ],
                "liens": [
                    {"titre": "Service-public.fr — saisir le CPH", "url": "https://www.service-public.fr/particuliers/vosdroits/F1782"},
                    {"titre": "Cerfa 15586*04 — requête CPH", "url": "https://www.service-public.fr/particuliers/vosdroits/R50578"},
                    {"titre": "Code du travail — barème L1235-3", "url": LEGIFRANCE_CT},
                    {"titre": "Cour de cassation — arrêts 11 mai 2022", "url": COURCASS},
                ],
            },
            "fiches_pratiques": [],
        },
    ],
    "harcelement": [
        {
            "id": "harc-03",
            "question_type": "Quelle est la protection des lanceurs d'alerte depuis la loi Waserman ?",
            "mots_cles": [
                "lanceur d'alerte", "loi Waserman", "loi Sapin 2",
                "L1132-3-3", "protection", "procédure de signalement",
                "défenseur des droits", "référent alerte", "représailles",
            ],
            "reponse": {
                "synthese": "La loi Waserman du 21 mars 2022 (entrée en vigueur le 1er septembre 2022) a profondément renforcé le statut du lanceur d'alerte issu de la loi Sapin 2 du 9 décembre 2016. Tout salarié (ou collaborateur extérieur/occasionnel) qui signale ou divulgue de bonne foi des informations sur un crime, un délit, une menace ou un préjudice pour l'intérêt général, ou une violation du droit, bénéficie d'une protection absolue contre les représailles.",
                "fondement_legal": "Loi n° 2016-1691 du 9 décembre 2016 (Sapin 2). Loi n° 2022-401 du 21 mars 2022 (Waserman) — transposition de la directive (UE) 2019/1937. Articles L1132-3-3, L1152-2, L1152-3 du Code du travail (interdiction des représailles). Décret n° 2022-1284 du 3 octobre 2022 (procédures de recueil et de traitement des signalements).",
                "fondement_ccn": "Pas de disposition spécifique ALISFA. Toute structure de la branche d'au moins 50 salariés doit mettre en place une procédure interne de recueil et de traitement des signalements (art. 8 loi Sapin 2 modifiée).",
                "application": "Obligations pour ≥ 50 salariés : (1) procédure interne écrite de signalement, (2) information des salariés (affichage, note de service), (3) désignation d'un référent (peut être externe), (4) garantie de confidentialité stricte, (5) traitement dans un délai raisonnable avec accusé de réception sous 7 jours et retour sous 3 mois. Le lanceur d'alerte peut aussi saisir directement le Défenseur des droits, l'autorité compétente ou la justice, et dans certaines conditions divulguer publiquement.",
                "vigilance": "Les représailles (licenciement, sanction, refus d'embauche, discrimination, harcèlement...) sont nulles de plein droit (L1132-4). Le lanceur d'alerte bénéficie d'un renversement de la charge de la preuve. Sanction pour l'employeur : jusqu'à 3 ans d'emprisonnement et 45 000 € d'amende pour entrave ; 60 000 € d'amende civile pour procédure bâillon.",
                "sources": [
                    "Loi n° 2016-1691 du 9 décembre 2016 (Sapin 2)",
                    "Loi n° 2022-401 du 21 mars 2022 (Waserman)",
                    "Directive (UE) 2019/1937",
                    "Décret n° 2022-1284 du 3 octobre 2022",
                    "Art. L1132-3-3 C. trav.",
                ],
                "liens": [
                    {"titre": "Défenseur des droits — lanceur d'alerte", "url": "https://www.defenseurdesdroits.fr/fr/lanceurs-dalerte"},
                    {"titre": "Loi Waserman — Légifrance", "url": "https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000045388745"},
                    {"titre": "Décret du 3 octobre 2022", "url": "https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000046365565"},
                ],
            },
            "fiches_pratiques": [],
        },
    ],
    "prevoyance": [
        {
            "id": "prev-03",
            "question_type": "Comment fonctionne la portabilité de la complémentaire santé et de la prévoyance (ANI) ?",
            "mots_cles": [
                "portabilité", "ANI 2008", "L911-8 CSS", "santé",
                "prévoyance", "chômage", "mutuelle", "maintien garanties",
                "12 mois", "gratuit",
            ],
            "reponse": {
                "synthese": "Tout salarié dont le contrat est rompu (hors faute lourde) et qui bénéficie de l'assurance chômage a droit au maintien gratuit de ses garanties complémentaire santé et prévoyance, pendant une durée égale à son dernier contrat, dans la limite de 12 mois. Ce dispositif, appelé portabilité ANI, est financé par la mutualisation entre les salariés actifs de l'entreprise.",
                "fondement_legal": "Article L911-8 du Code de la sécurité sociale (créé par l'ANI du 11 janvier 2008, étendu par l'avenant du 18 mai 2009 et généralisé par la loi du 14 juin 2013 pour la santé, effective au 1er juin 2014). Article L911-8 3° : durée maximale 12 mois. Article L911-8 5° : financement mutualisé.",
                "fondement_ccn": "Avenants successifs ALISFA sur la complémentaire santé et la prévoyance (02-15, 03-17, 06-18, 04-19, 06-20, 07-22, 01-25, 02-25) reprennent le dispositif de portabilité de droit commun sans dérogation défavorable.",
                "application": "Conditions cumulatives : (1) rupture du contrat (hors faute lourde), (2) ouverture des droits au chômage, (3) adhésion au régime collectif au jour de la cessation. L'employeur informe le salarié de son droit dans le certificat de travail. Le maintien prend effet à la date de cessation du contrat et cesse à l'épuisement des droits, à la reprise d'un emploi, au non-respect des conditions, ou au bout de 12 mois. L'organisme assureur peut demander au salarié un justificatif mensuel de sa situation (attestation France Travail).",
                "vigilance": "Le défaut d'information de l'employeur sur le droit à portabilité engage sa responsabilité contractuelle (Cass. soc. 20 janvier 2021 n° 19-13.645) et ouvre droit à dommages-intérêts équivalents au coût des soins non couverts. La portabilité s'applique aux couvertures « frais de santé » (article L911-8) ET « prévoyance lourde » (décès, incapacité, invalidité) depuis le 1er juin 2015.",
                "sources": [
                    "Art. L911-8 Code de la sécurité sociale",
                    "ANI du 11 janvier 2008",
                    "Loi n° 2013-504 du 14 juin 2013",
                    "Cass. soc. 20 janvier 2021 n° 19-13.645",
                ],
                "liens": [
                    {"titre": "Code SS — L911-8", "url": LEGIFRANCE_CSS},
                    {"titre": "Service-public.fr — portabilité", "url": "https://www.service-public.fr/particuliers/vosdroits/F36483"},
                    {"titre": "Loi du 14 juin 2013 — Légifrance", "url": "https://www.legifrance.gouv.fr/loda/id/JORFTEXT000027546648"},
                ],
            },
            "fiches_pratiques": [],
        },
    ],
    "remuneration": [
        {
            "id": "remun-07",
            "question_type": "Quel est le SMIC 2026 et comment s'articule-t-il avec les salaires minima de la CCN ALISFA ?",
            "mots_cles": [
                "SMIC", "SMIC 2026", "salaire minimum", "L3231-2",
                "valeur du point", "minima conventionnels", "complément différentiel",
                "revalorisation", "indice du point",
            ],
            "reponse": {
                "synthese": "Le SMIC est le salaire horaire minimum légal en-dessous duquel aucun salarié ne peut être rémunéré. Il est revalorisé chaque 1er janvier selon l'inflation des 20 % de ménages aux revenus les plus modestes, et peut faire l'objet d'une revalorisation anticipée si l'inflation dépasse 2 % depuis la dernière revalorisation. Dans la branche ALISFA, les minima conventionnels (valeur du point × coefficient) doivent systématiquement être comparés au SMIC : si le salaire mensuel conventionnel devient inférieur au SMIC mensualisé, l'employeur verse un complément différentiel garantissant au moins le SMIC.",
                "fondement_legal": "Articles L3231-1 à L3231-12 du Code du travail (définition et fonctionnement du SMIC). Article L3231-2 : revalorisation automatique au 1er janvier. Article L3231-10 : revalorisation anticipée. Article L2241-10 : obligation pour les branches de négocier au moins une fois par an sur les salaires pour que les minima ne soient pas inférieurs au SMIC.",
                "fondement_ccn": "Accords salariaux de branche ALISFA — négociation annuelle obligatoire sur la valeur du point et la grille des coefficients. Quand la grille conventionnelle décroche du SMIC, un accord de rattrapage est négocié. À défaut, l'employeur applique le SMIC pour les coefficients les plus bas.",
                "application": "Vérification à chaque revalorisation : (1) calculer le salaire mensuel conventionnel = valeur du point × coefficient du poste × nombre d'heures contractuelles, (2) comparer au SMIC mensuel brut (SMIC horaire × heures contractuelles), (3) si inférieur → verser un complément différentiel sur une ligne dédiée du bulletin de paie, (4) mettre à jour les bulletins de paie dès la prise d'effet de la nouvelle valeur (1er janvier ou date de l'accord de branche).",
                "vigilance": "Le paiement en-dessous du SMIC est une infraction pénale (contravention de 5e classe par salarié concerné, L3232-5 C. trav.) et expose à un rappel de salaire avec intérêts de retard. La prescription des salaires est de 3 ans (L3245-1). Consulter la dernière valeur SMIC officielle sur Legifrance / service-public.fr — elle est révisée au 1er janvier de chaque année et peut l'être en cours d'année.",
                "sources": [
                    "Art. L3231-1 à L3231-12 C. trav.",
                    "Art. L2241-10 C. trav.",
                    "Décret annuel de revalorisation du SMIC (JORF de décembre)",
                    "Accords salariaux de branche ALISFA",
                ],
                "liens": [
                    {"titre": "Service-public.fr — SMIC en vigueur", "url": "https://www.service-public.fr/particuliers/vosdroits/F2300"},
                    {"titre": "Code du travail — L3231-1 et s.", "url": LEGIFRANCE_CT},
                    {"titre": "CCN ALISFA — Legifrance", "url": LEGIFRANCE_CCN},
                    {"titre": "DARES — chiffres du SMIC", "url": "https://dares.travail-emploi.gouv.fr/"},
                ],
            },
            "fiches_pratiques": [],
        },
    ],
    "conges": [
        {
            "id": "conge-06",
            "question_type": "Quels sont les congés pour événements familiaux dans la CCN ALISFA ?",
            "mots_cles": [
                "congés événements familiaux", "L3142-1", "mariage", "PACS",
                "naissance", "décès", "enfant malade", "jours ouvrés",
                "congé paternité", "congé maternité",
            ],
            "reponse": {
                "synthese": "Tout salarié a droit à des jours de congé rémunérés pour certains événements familiaux (mariage, naissance, décès, etc.). Ces jours sont assimilés à du temps de travail effectif. Le Code du travail fixe des minima (L3142-4) que la CCN ALISFA peut améliorer. La plupart des conventions collectives — dont ALISFA — retiennent un dispositif plus favorable, notamment pour le décès d'un enfant.",
                "fondement_legal": "Articles L3142-1 à L3142-5 du Code du travail. Article L3142-4 : durées minimales (mariage/PACS : 4 jours ; naissance/adoption : 3 jours ; mariage enfant : 1 jour ; décès conjoint/enfant : 5 jours porté à 12 jours si enfant < 25 ans ou personne à charge, loi 8 juin 2020 ; décès père/mère/beau-père/belle-mère/frère/sœur : 3 jours ; annonce handicap/pathologie chronique/cancer enfant : 5 jours).",
                "fondement_ccn": "CCN ALISFA (IDCC 1261) — Chapitre Congés : l'annexe conventionnelle peut majorer les durées légales. Vérifier l'accord applicable pour le coefficient et l'ancienneté du salarié. La branche applique au minimum le Code du travail.",
                "application": "Justification par pièce d'état civil (acte de mariage, naissance, décès...). Le congé est pris au moment de l'événement ou dans une période raisonnable proche (jurisprudence constante). Il n'a pas à être posé sur les congés payés légaux. Le salaire est maintenu intégralement. Le congé naissance (3 jours) s'ajoute au congé paternité (25 jours calendaires depuis le 1er juillet 2021, 32 jours pour naissances multiples).",
                "vigilance": "Le refus injustifié de l'employeur constitue une sanction illégale ouvrant droit à dommages-intérêts. Le décès d'un enfant bénéficie en outre d'un congé de deuil supplémentaire de 8 jours fractionnables (L3142-1-1, loi du 8 juin 2020 n° 2020-692). Ne pas confondre avec le congé de présence parentale (L1225-62), ni avec le congé proche aidant (L3142-16).",
                "sources": [
                    "Art. L3142-1 à L3142-5 C. trav.",
                    "Art. L3142-1-1 C. trav. (congé de deuil enfant)",
                    "Loi n° 2020-692 du 8 juin 2020",
                    "CCN ALISFA — Chapitre Congés",
                ],
                "liens": [
                    {"titre": "Service-public.fr — congés familiaux", "url": "https://www.service-public.fr/particuliers/vosdroits/F2272"},
                    {"titre": "Code du travail — L3142-1", "url": LEGIFRANCE_CT},
                    {"titre": "CCN ALISFA — Legifrance", "url": LEGIFRANCE_CCN},
                ],
            },
            "fiches_pratiques": [],
        },
    ],
    "contrat_travail": [
        {
            "id": "contrat-07",
            "question_type": "Quelles sont les durées maximales de la période d'essai en CDI ?",
            "mots_cles": [
                "période d'essai", "CDI", "L1221-19", "L1221-25",
                "renouvellement", "cadre", "non-cadre", "rupture essai",
                "délai de prévenance",
            ],
            "reponse": {
                "synthese": "En CDI, la période d'essai a une durée maximale fixée par le Code du travail selon la catégorie professionnelle : 2 mois pour les ouvriers et employés, 3 mois pour les agents de maîtrise et techniciens, 4 mois pour les cadres. Elle peut être renouvelée une fois si un accord de branche étendu le prévoit et si la possibilité figure au contrat de travail et dans la lettre d'embauche. La durée totale ne peut excéder 4, 6 ou 8 mois respectivement.",
                "fondement_legal": "Articles L1221-19 à L1221-26 du Code du travail. Article L1221-19 : durées maximales initiales. Article L1221-21 : durées maximales avec renouvellement. Article L1221-25 : délai de prévenance en cas de rupture à l'initiative de l'employeur (24h < 8j, 48h entre 8j et 1 mois, 2 semaines < 3 mois, 1 mois au-delà). Article L1221-23 : interdiction de renouveler si pas prévu par accord de branche étendu.",
                "fondement_ccn": "CCN ALISFA (IDCC 1261) — les durées d'essai applicables sont celles de la loi. Vérifier dans la lettre d'embauche et le contrat si le renouvellement est prévu : à défaut, il est impossible. L'accord de branche doit être étendu pour autoriser le renouvellement.",
                "application": "Mentions obligatoires au contrat : durée initiale, possibilité (ou non) de renouvellement, durée maximale du renouvellement. La rupture pendant l'essai n'a pas à être motivée mais doit respecter le délai de prévenance. Elle ne doit pas être abusive ni discriminatoire. Le renouvellement doit être écrit et signé par le salarié AVANT l'expiration de la période initiale (Cass. soc. 25 février 2009 n° 07-44.920).",
                "vigilance": "Rupture abusive pendant l'essai (discrimination, détournement de l'objet de l'essai comme test sur un poste différent, harcèlement) → requalification en licenciement sans cause réelle et sérieuse avec indemnités. Le non-respect du délai de prévenance donne droit à une indemnité compensatrice (L1221-25 al. 4). Pour un jeune salarié déjà en stage dans l'entreprise dans les mêmes fonctions, la durée du stage s'impute sur la période d'essai dans la limite de la moitié (L1221-24).",
                "sources": [
                    "Art. L1221-19 à L1221-26 C. trav.",
                    "Cass. soc. 25 février 2009 n° 07-44.920",
                    "Cass. soc. 23 janvier 2013 n° 11-23.428 (rupture abusive)",
                ],
                "liens": [
                    {"titre": "Service-public.fr — période d'essai", "url": "https://www.service-public.fr/particuliers/vosdroits/F31957"},
                    {"titre": "Code du travail — L1221-19", "url": LEGIFRANCE_CT},
                    {"titre": "travail-emploi.gouv.fr — période d'essai", "url": "https://travail-emploi.gouv.fr/la-periode-d-essai"},
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

    data["metadata"]["date_consolidation"] = "2026-04-15"
    data["metadata"].setdefault("enrichissements", []).append(
        {
            "date": "2026-04-15",
            "source": "Legifrance (C. trav., C. séc. soc.), travail-emploi.gouv.fr, Cour de cassation",
            "ajouts": [a["id"] for arts in NEW_ARTICLES.values() for a in arts],
            "note": "Ajouts transverses : rupture conventionnelle, BDESE, index égalité F/H, DUERP, barème Macron, lanceur d'alerte Waserman, portabilité ANI, SMIC/minima, congés familiaux, période d'essai CDI.",
        }
    )

    SRC.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{added} article(s) ajouté(s). Sauvegarde : {BAK}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
