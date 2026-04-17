#!/usr/bin/env python3
"""
Enrichit base_rh.json avec des articles clés issus des sources officielles :
- Code du travail (Legifrance)
- ANACT — Agence nationale pour l'amélioration des conditions de travail
- INRS — Institut national de recherche et de sécurité
- ANDRH — Association nationale des DRH
- ANI QVT 2013 et ANI QVCT 2020
- travail-emploi.gouv.fr / service-public.fr

Couvre : onboarding, entretien annuel/professionnel, QVCT, RPS, GEPP,
accord d'entreprise, négociation obligatoire.

Sauvegarde base_rh.json.bak avant modification.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "base_rh.json"
BAK = ROOT / "data" / "base_rh.json.bak"

LEGIFRANCE_CT = "https://www.legifrance.gouv.fr/codes/texte_lc/LEGITEXT000006072050/"
ANACT = "https://www.anact.fr/"
INRS = "https://www.inrs.fr/"
TRAVAIL_GOUV = "https://travail-emploi.gouv.fr/"


NEW_ARTICLES = {
    "recrutement_integration": [
        {
            "id": "rh-06",
            "question_type": "Comment structurer un parcours d'intégration (onboarding) efficace ?",
            "mots_cles": [
                "onboarding", "intégration", "accueil", "nouveau salarié",
                "période d'essai", "parrain", "livret d'accueil",
                "ANDRH", "rétention", "déperdition",
            ],
            "reponse": {
                "synthese": "L'onboarding (parcours d'intégration) est la période qui s'étend de l'accueil physique d'un nouveau salarié jusqu'à sa pleine autonomie opérationnelle (généralement 3 à 6 mois). Un parcours structuré divise le risque de rupture prématurée par 3 selon les études ANDRH. Il articule : préparation en amont (pré-boarding), accueil du 1er jour, formation au poste, intégration sociale et culturelle, points réguliers, bilan de fin de période d'essai.",
                "fondement_legal": "Aucune obligation légale globale d'onboarding, mais plusieurs obligations ponctuelles s'y rattachent : Articles L4141-1 à L4141-4 du Code du travail (formation à la sécurité au poste de travail, obligatoire dès l'embauche), Article R4224-15 (secours), Article L4121-1 (obligation de sécurité de résultat). Article L1221-19 : période d'essai. Loi Informatique et Libertés : information du salarié sur les traitements RH.",
                "fondement_ccn": "CCN ALISFA (IDCC 1261) — aucune disposition spécifique sur l'onboarding. Certains accords d'entreprise de la branche prévoient un livret d'accueil et un tutorat.",
                "application": "Check-list recommandée : (1) avant l'arrivée : envoi du contrat, confirmation de la date, préparation du poste matériel, annonce à l'équipe ; (2) J1 : accueil personnalisé, présentation des locaux et de l'équipe, remise du livret d'accueil, démarches administratives, formation sécurité, désignation d'un parrain/marraine ; (3) Semaine 1 : objectifs de la période d'essai formalisés par écrit ; (4) Mois 1-3 : points hebdomadaires puis bimensuels, formation au poste, retour d'étonnement ; (5) Fin de période d'essai : entretien de bilan et confirmation.",
                "vigilance": "L'absence de formation à la sécurité lors de l'embauche constitue un manquement à l'obligation de sécurité engageant la responsabilité civile ET pénale de l'employeur en cas d'accident. Le retour d'étonnement est un outil précieux mais sa confidentialité doit être préservée pour qu'il soit sincère. Ne pas confondre l'onboarding avec la période d'essai juridique : l'intégration peut durer au-delà.",
                "sources": [
                    "Art. L4141-1 à L4141-4 C. trav.",
                    "Art. L4121-1 C. trav.",
                    "ANDRH — guide de l'onboarding (2023)",
                    "ANACT — kit d'accueil des nouveaux salariés",
                    "INRS — formation à la sécurité au poste",
                ],
                "liens": [
                    {"titre": "INRS — formation à la sécurité du nouveau salarié", "url": "https://www.inrs.fr/demarche/formation-securite/ce-qu-il-faut-retenir.html"},
                    {"titre": "ANACT — accueillir un nouveau salarié", "url": ANACT},
                    {"titre": "Code du travail — L4141-1", "url": LEGIFRANCE_CT},
                ],
            },
            "fiches_pratiques": [],
        },
    ],
    "entretiens_evaluation": [
        {
            "id": "rh-07",
            "question_type": "Quelle est la différence entre l'entretien annuel d'évaluation et l'entretien professionnel ?",
            "mots_cles": [
                "entretien annuel", "entretien professionnel",
                "L6315-1", "évaluation", "objectifs", "performance",
                "évolution", "carrière", "distinction",
            ],
            "reponse": {
                "synthese": "Ce sont deux entretiens distincts qui ne doivent pas être confondus. L'entretien annuel d'évaluation n'est pas imposé par la loi : il relève du pouvoir de direction de l'employeur et porte sur la performance du salarié au regard des objectifs fixés, en vue d'une rémunération variable, d'une prime ou d'une décision RH. L'entretien professionnel, lui, est OBLIGATOIRE (L6315-1) tous les 2 ans et porte exclusivement sur les perspectives d'évolution professionnelle, en excluant toute évaluation de la performance.",
                "fondement_legal": "Entretien professionnel : Article L6315-1 du Code du travail (loi du 5 mars 2014). Entretien annuel d'évaluation : aucun texte spécifique, mais encadré par la jurisprudence (Cass. soc. 28 novembre 2007 n° 06-21.964 : obligation de consultation préalable du CSE et d'information individuelle en cas d'introduction), la Loi Informatique et Libertés (CNIL, délibération du 10 mars 2005) et l'obligation de loyauté contractuelle.",
                "fondement_ccn": "CCN ALISFA (IDCC 1261) — pas de disposition contraignante sur l'entretien annuel. L'entretien professionnel est souvent formalisé par une trame de branche ou d'OPCO.",
                "application": "Distinctions clés : (1) PÉRIODICITÉ : entretien pro tous les 2 ans minimum ; entretien annuel, annuel ou semestriel ; (2) OBJET : entretien pro = projet d'évolution, formation, VAE, bilan de compétences ; entretien annuel = performance, atteinte des objectifs ; (3) OBLIGATION : entretien pro obligatoire sous peine d'abondement correctif de 3 000 € sur le CPF (L6323-13) ; entretien annuel facultatif ; (4) TRAÇABILITÉ : les deux doivent être écrits et signés par les deux parties ; (5) USAGE DES DONNÉES : l'évaluation ne peut servir que pour des décisions RH justifiées et proportionnées.",
                "vigilance": "Il est possible de mener les deux entretiens à la suite mais ils doivent rester clairement distincts avec deux supports séparés. Mélanger les deux expose à un risque juridique : annulation de l'évaluation (Cass. soc. 17 mars 2015 n° 13-20.452) ou non-reconnaissance de l'entretien professionnel avec abondement correctif à la clé. Informer et consulter le CSE avant la mise en place d'un dispositif d'évaluation (L2312-38).",
                "sources": [
                    "Art. L6315-1 C. trav.",
                    "Art. L2312-38 C. trav.",
                    "Cass. soc. 28 novembre 2007 n° 06-21.964",
                    "Cass. soc. 17 mars 2015 n° 13-20.452",
                    "CNIL — délibération du 10 mars 2005",
                ],
                "liens": [
                    {"titre": "Code du travail — L6315-1", "url": LEGIFRANCE_CT},
                    {"titre": "CNIL — évaluation des salariés", "url": "https://www.cnil.fr/fr/lemployeur-peut-il-organiser-un-entretien-individuel-devaluation"},
                    {"titre": "ANDRH — guide entretien professionnel", "url": TRAVAIL_GOUV},
                ],
            },
            "fiches_pratiques": [],
        },
    ],
    "qvct_sante_travail": [
        {
            "id": "rh-08",
            "question_type": "Comment mettre en place une démarche QVCT (qualité de vie et des conditions de travail) ?",
            "mots_cles": [
                "QVCT", "qualité de vie", "ANI QVCT",
                "L2242-17", "négociation annuelle", "ANACT",
                "6 thématiques", "diagnostic", "plan d'action",
                "télétravail", "droit à la déconnexion",
            ],
            "reponse": {
                "synthese": "La Qualité de Vie et des Conditions de Travail (QVCT) remplace depuis l'ANI du 9 décembre 2020 la notion de QVT issue de l'ANI du 19 juin 2013. Elle désigne l'ensemble des actions permettant de concilier l'amélioration des conditions de travail et la performance. Dans les entreprises de 50 salariés et plus disposant d'au moins un délégué syndical, elle fait l'objet d'une négociation obligatoire (L2242-17) au moins tous les 4 ans.",
                "fondement_legal": "Article L2242-17 du Code du travail : négociation obligatoire sur l'égalité professionnelle et la qualité de vie et des conditions de travail (≥ 50 salariés avec DS). Article L4121-1 : obligation générale de sécurité et de préservation de la santé physique et mentale. ANI du 19 juin 2013 (QVT). ANI du 9 décembre 2020 (QVCT) — élargissement aux conditions de travail. Loi n° 2021-1018 du 2 août 2021 (santé au travail) — renforcement de la prévention.",
                "fondement_ccn": "CCN ALISFA — pas de dispositif spécifique de branche sur la QVCT, mais les accords d'entreprise peuvent prévoir des mesures adaptées : télétravail, droit à la déconnexion, flexibilité horaire, articulation vie pro/vie perso.",
                "application": "Démarche recommandée ANACT (6 étapes) : (1) engagement de la direction et du dialogue social, (2) constitution d'un groupe de travail paritaire, (3) diagnostic partagé (questionnaire, entretiens, données RH), (4) identification des thématiques prioritaires (parmi les 6 thèmes ANI : contenu du travail, organisation, santé, management, relations au travail, égalité pro), (5) expérimentation et plan d'action, (6) évaluation et pérennisation. Les 6 thématiques de l'ANI 2020 structurent l'analyse.",
                "vigilance": "Ne pas réduire la QVCT à des avantages « cosmétiques » (baby-foot, fruits frais...) sans agir sur l'organisation du travail et le management — c'est une cause majeure d'échec des démarches. L'ANACT met à disposition des outils gratuits (GPS QVCT, baromètres). L'absence de négociation QVCT obligatoire est sanctionnée par une pénalité financière pouvant aller jusqu'à 1 % de la masse salariale (L2242-8).",
                "sources": [
                    "Art. L2242-17 C. trav.",
                    "Art. L4121-1 C. trav.",
                    "ANI QVT du 19 juin 2013",
                    "ANI QVCT du 9 décembre 2020",
                    "Loi n° 2021-1018 du 2 août 2021",
                    "ANACT — kit méthode QVCT",
                ],
                "liens": [
                    {"titre": "ANACT — démarche QVCT", "url": ANACT + "qualite-de-vie-et-des-conditions-de-travail-qvct"},
                    {"titre": "ANI QVCT 2020 — Légifrance", "url": "https://www.legifrance.gouv.fr/"},
                    {"titre": "Code du travail — L2242-17", "url": LEGIFRANCE_CT},
                ],
            },
            "fiches_pratiques": [],
        },
        {
            "id": "rh-09",
            "question_type": "Comment prévenir les risques psychosociaux (RPS) : stress, harcèlement, burn-out ?",
            "mots_cles": [
                "RPS", "risques psychosociaux", "burn-out", "stress",
                "L4121-1", "DUERP RPS", "ANI 2 juillet 2008",
                "INRS", "harcèlement moral", "souffrance au travail",
            ],
            "reponse": {
                "synthese": "Les risques psychosociaux (RPS) désignent les risques pour la santé mentale, physique et sociale engendrés par les conditions d'emploi et les facteurs organisationnels et relationnels. Ils recouvrent le stress, le harcèlement moral et sexuel, les violences internes et externes, le burn-out. L'employeur a une obligation de prévention (L4121-1) incluant l'évaluation des RPS dans le DUERP, la mise en place de mesures préventives et la prise en compte dans l'organisation.",
                "fondement_legal": "Articles L4121-1 à L4121-5 du Code du travail (obligation de sécurité et démarche de prévention). Article L4121-2 : principes généraux de prévention (éviter les risques, les combattre à la source, adapter le travail à l'homme). Article L1152-1 à L1152-6 (harcèlement moral) et L1153-1 à L1153-6 (harcèlement sexuel). ANI du 2 juillet 2008 sur le stress au travail (étendu le 23 avril 2009). ANI du 26 mars 2010 sur le harcèlement et la violence au travail.",
                "fondement_ccn": "CCN ALISFA — pas de dispositif spécifique RPS de branche. Les services de prévention et de santé au travail interentreprises (SPSTI) accompagnent les structures dans l'évaluation et la prévention.",
                "application": "Démarche INRS (6 facteurs de RPS du rapport Gollac 2011) : (1) intensité et temps de travail, (2) exigences émotionnelles, (3) autonomie, (4) rapports sociaux au travail, (5) conflits de valeurs, (6) insécurité de la situation de travail. Intégration obligatoire des RPS dans le DUERP (L4121-3). Outils INRS disponibles : Faire le point, RPS-DU. Mesures préventives : clarification des missions, charge de travail maîtrisée, soutien managérial, dispositif d'alerte, formation des managers.",
                "vigilance": "Le burn-out n'est PAS reconnu comme maladie professionnelle dans les tableaux officiels mais peut être reconnu au titre du système complémentaire (art. L461-1 CSS) après passage en CRRMP. La responsabilité civile et pénale de l'employeur peut être engagée en cas de carence dans la prévention (Cass. soc. 28 février 2006 n° 05-41.555, arrêts amiante — principe étendu aux RPS). La CNIL encadre strictement les questionnaires de diagnostic RPS (anonymat, finalité, proportionnalité).",
                "sources": [
                    "Art. L4121-1 à L4121-5 C. trav.",
                    "Art. L1152-1 et s. C. trav. (harcèlement)",
                    "ANI du 2 juillet 2008 (stress)",
                    "ANI du 26 mars 2010 (harcèlement/violence)",
                    "Rapport Gollac 2011",
                    "INRS — dossier RPS",
                ],
                "liens": [
                    {"titre": "INRS — risques psychosociaux", "url": "https://www.inrs.fr/risques/psychosociaux/ce-qu-il-faut-retenir.html"},
                    {"titre": "ANACT — agir sur les RPS", "url": ANACT},
                    {"titre": "Outil INRS Faire le point (PME)", "url": "https://www.inrs.fr/publications/outils/faire-le-point-rps.html"},
                    {"titre": "Code du travail — L4121-1", "url": LEGIFRANCE_CT},
                ],
            },
            "fiches_pratiques": [],
        },
    ],
    "gpec_mobilite": [
        {
            "id": "rh-10",
            "question_type": "Qu'est-ce que la GEPP (Gestion des Emplois et Parcours Professionnels) et quand est-elle obligatoire ?",
            "mots_cles": [
                "GEPP", "GPEC", "L2242-20", "négociation",
                "parcours professionnels", "mixité des métiers",
                "triennale", "300 salariés", "strates",
                "compétences", "mobilité",
            ],
            "reponse": {
                "synthese": "La GEPP (Gestion des Emplois et Parcours Professionnels, anciennement GPEC) est une démarche prospective de gestion anticipée des compétences dans l'entreprise. Elle fait l'objet d'une négociation obligatoire au moins une fois tous les 4 ans dans les entreprises et groupes d'au moins 300 salariés, et dans les entreprises et groupes communautaires de dimension européenne comportant au moins un établissement de 150 salariés en France (L2242-20).",
                "fondement_legal": "Articles L2242-20 à L2242-22 du Code du travail. Article L2242-20 : obligation de négocier tous les 4 ans sur la GEPP (≥ 300 salariés). Article L2242-21 : thèmes obligatoires (mise en place d'un dispositif de GEPP, mesures d'accompagnement, qualifications, mixité des métiers, conditions de mobilité, déroulement de carrière des représentants du personnel, information des sous-traitants). Ordonnance n° 2017-1385 du 22 septembre 2017 : renommage GEPP + périodicité 4 ans.",
                "fondement_ccn": "La CPNEF ALISFA a engagé des travaux prospectifs sur les métiers de la branche (cartographie, observatoire). Ces travaux nourrissent les GEPP d'entreprise des plus grandes structures. Pour les structures < 300 salariés, la démarche reste recommandée mais facultative.",
                "application": "Étapes d'une démarche GEPP : (1) diagnostic de l'existant (pyramide des âges, mobilité, turnover, compétences détenues), (2) projection (analyse des évolutions métiers, besoins futurs), (3) identification des écarts entre ressources actuelles et besoins, (4) plan d'action RH (recrutement, mobilité, formation, reclassement, départs), (5) suivi et évaluation. L'accord GEPP peut prévoir des mesures comme le congé de mobilité, la rupture conventionnelle collective, l'abondement du CPF.",
                "vigilance": "Le défaut de négociation GEPP n'est pas sanctionné pénalement mais peut fragiliser un licenciement économique ultérieur : les juges examinent si l'entreprise a anticipé les mutations via une GEPP (Cass. soc. 23 septembre 2015 n° 14-15.702). Les entreprises < 300 salariés peuvent bénéficier d'un accompagnement financier de l'État via une prestation de conseil en ressources humaines (PCRH) ou du dispositif EDEC porté par les branches.",
                "sources": [
                    "Art. L2242-20 à L2242-22 C. trav.",
                    "Ordonnance n° 2017-1385 du 22 septembre 2017",
                    "Cass. soc. 23 septembre 2015 n° 14-15.702",
                    "ANACT — kit GEPP",
                    "CPNEF ALISFA — observatoire des métiers",
                ],
                "liens": [
                    {"titre": "Code du travail — L2242-20", "url": LEGIFRANCE_CT},
                    {"titre": "travail-emploi.gouv.fr — GEPP", "url": TRAVAIL_GOUV + "la-gestion-des-emplois-et-des-parcours-professionnels-gepp"},
                    {"titre": "ANACT — démarche GEPP", "url": ANACT},
                ],
            },
            "fiches_pratiques": [],
        },
    ],
    "dialogue_social_local": [
        {
            "id": "rh-11",
            "question_type": "Comment négocier un accord d'entreprise dans une structure ALISFA ?",
            "mots_cles": [
                "accord entreprise", "L2232-11", "L2232-21",
                "délégué syndical", "CSE", "négociation",
                "référendum", "ratification 2/3", "dépôt DREETS",
                "TéléAccords", "accord majoritaire",
            ],
            "reponse": {
                "synthese": "La procédure de négociation d'un accord d'entreprise dépend de la taille et de la représentation syndicale de la structure : en présence d'un délégué syndical, négociation avec les DS et accord majoritaire à 50 % ; sans DS, la négociation peut se faire avec le CSE (11-50 salariés : avec les élus mandatés ou non), ou par consultation directe des salariés (< 11 salariés, projet ratifié aux 2/3). L'accord doit être déposé sur la plateforme TéléAccords pour entrer en vigueur.",
                "fondement_legal": "Articles L2232-11 à L2232-33 du Code du travail. Article L2232-12 : accord majoritaire à 50 % des syndicats représentatifs (avec DS). Article L2232-23-1 : entreprises < 11 salariés (projet unilatéral, ratification aux 2/3). Article L2232-24 : entreprises 11-20 salariés sans DS (projet unilatéral, ratification aux 2/3). Article L2232-25 : entreprises 21-50 salariés sans DS (négociation avec CSE ou salarié mandaté). Ordonnances Macron du 22 septembre 2017. Article L2231-6 : dépôt sur TéléAccords.",
                "fondement_ccn": "CCN ALISFA (IDCC 1261) : l'accord d'entreprise peut compléter la CCN dans les matières ouvertes à la négociation d'entreprise par la loi (temps de travail, rémunération variable, etc.). La primauté de l'accord d'entreprise sur la CCN s'applique dans les domaines définis par l'article L2253-3 du Code du travail, sauf pour les 13 thèmes verrouillés (L2253-1) où la CCN prime.",
                "application": "Procédure en 5 étapes : (1) identification du thème et de la modalité applicable selon l'effectif et la représentation, (2) rédaction du projet et négociation, (3) signature (DS majoritaires, ou élus mandatés/non, ou ratification salariés selon le cas), (4) notification du texte aux syndicats représentatifs (si DS), (5) dépôt sur TéléAccords (https://www.teleaccords.travail-emploi.gouv.fr/) + un exemplaire au greffe du Conseil de prud'hommes. L'accord entre en vigueur à la date fixée ou, à défaut, au lendemain du dépôt.",
                "vigilance": "Les 13 thèmes verrouillés où la CCN prime sur l'accord d'entreprise (L2253-1) : salaires minima conventionnels, classifications, mutualisation des fonds formation, mutualisation des fonds de branche, garanties collectives de prévoyance, temps partiel (10 h minimum), CDD d'usage, périodes d'essai (durées), transfert d'entreprise, égalité F/H, pénibilité, handicap, surveillance médicale. Un accord d'entreprise moins favorable est nul dans ces matières.",
                "sources": [
                    "Art. L2232-11 à L2232-33 C. trav.",
                    "Art. L2253-1 à L2253-3 C. trav.",
                    "Art. L2231-6 C. trav.",
                    "Ordonnances Macron n° 2017-1385 à 2017-1388 du 22 septembre 2017",
                ],
                "liens": [
                    {"titre": "TéléAccords — plateforme dépôt", "url": "https://www.teleaccords.travail-emploi.gouv.fr/"},
                    {"titre": "Code du travail — L2232-11", "url": LEGIFRANCE_CT},
                    {"titre": "travail-emploi.gouv.fr — négociation collective", "url": TRAVAIL_GOUV + "la-negociation-collective-en-entreprise"},
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
            "source": "Legifrance, ANACT, INRS, ANDRH, ANI QVT/QVCT, travail-emploi.gouv.fr",
            "ajouts": [a["id"] for arts in NEW_ARTICLES.values() for a in arts],
            "note": "Onboarding, entretien annuel vs entretien pro, QVCT, RPS, GEPP, accord d'entreprise.",
        }
    )

    SRC.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{added} article(s) ajouté(s). Sauvegarde : {BAK}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
