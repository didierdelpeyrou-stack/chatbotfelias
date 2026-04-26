"""Annuaire d'orientation — Sprint 4.6 F6.

Cœur de l'outil ELISFA : l'utilisateur arrive avec une SITUATION/PROBLÈME et
veut savoir QUI CONTACTER. Tous les acteurs ont des URLs cliquables et des
contacts directs. La rubrique régionale couvre métropole + DROM + COM.

Structure :
  1. ACTEURS — fiches contacts typées (URL obligatoire)
  2. ORIENTATIONS — natures de problème → liste d'acteurs prioritaires
  3. FEDERATIONS_BY_REGION — référents ELISFA + fédérations FCSF/ACEPP
     + conseil régional + préfecture par région (métropole + DROM + COM)
"""
from __future__ import annotations

from typing import Literal, TypedDict

# ────────────────────────── Types ──────────────────────────

ActeurType = Literal[
    "elisfa", "federation", "syndicat", "opco",
    "etat", "deconcentre", "collectivite",
    "operateur", "vie_asso", "ressource",
    "urgence", "partenaire",
]


class Acteur(TypedDict, total=False):
    id: str
    nom: str
    type: ActeurType
    role: str
    description: str
    email: str
    phone: str
    url: str           # OBLIGATOIRE (sauf urgence)


class Orientation(TypedDict):
    id: str
    label: str
    icon: str
    description: str
    acteurs: list[str]


class RegionInfo(TypedDict, total=False):
    region: str
    code: str                          # code INSEE région
    type: Literal["metropole", "drom", "com"]
    elisfa_referent: str
    elisfa_email: str
    region_url: str                    # URL conseil régional
    region_label: str                  # ex: "Île-de-France Région"
    prefecture_url: str                # URL préfecture de région
    fcsf_federations: list[str]
    acepp_federations: list[str]


# ────────────────────────── Acteurs ──────────────────────────

ACTEURS: dict[str, Acteur] = {
    # ════════════════════════════
    # ELISFA — Branche ALISFA
    # ════════════════════════════
    "elisfa_siege": {
        "id": "elisfa_siege",
        "nom": "ELISFA — Siège national",
        "type": "elisfa",
        "role": "Syndicat employeur de la branche ALISFA (IDCC 1261)",
        "description": (
            "Représentation et défense des employeurs du lien social et familial. "
            "Pilote la CCN ALISFA, l'avenant 10-2022. ELISFA est un syndicat "
            "employeur — PAS une fédération."
        ),
        "email": "contact@elisfa.fr",
        "phone": "01 58 46 13 40",
        "url": "https://www.elisfa.fr",
    },
    "elisfa_juridique": {
        "id": "elisfa_juridique",
        "nom": "Pôle juridique ELISFA",
        "type": "elisfa",
        "role": "Conseil juridique de branche pour adhérents",
        "description": "Sanction, rupture, contentieux, application CCN ALISFA, jurisprudence.",
        "email": "rdv-juriste@elisfa.fr",
        "url": "https://www.elisfa.fr/representer-l-employeur/le-pole-juridique/",
    },
    "elisfa_social": {
        "id": "elisfa_social",
        "nom": "Pôle social / RH ELISFA",
        "type": "elisfa",
        "role": "Conseil RH, RPS, harcèlement, dialogue social",
        "description": "Accompagnement des situations RH sensibles. Permanences téléphoniques.",
        "email": "contact@elisfa.fr",
        "url": "https://www.elisfa.fr",
    },
    "alisfa": {
        "id": "alisfa",
        "nom": "ALISFA — site de la branche",
        "type": "elisfa",
        "role": "Site officiel de la branche ALISFA",
        "description": "Convention collective, GPEC, fiches métiers CPNEF, emplois repères.",
        "url": "https://www.alisfa.fr",
    },
    "ccn_alisfa": {
        "id": "ccn_alisfa",
        "nom": "CCN ALISFA — texte officiel Légifrance",
        "type": "elisfa",
        "role": "Convention Collective Nationale (IDCC 1261)",
        "description": "Texte intégral consolidé sur Légifrance.",
        "url": "https://www.legifrance.gouv.fr/conv_coll/id/KALICONT000005635161/",
    },

    # ════════════════════════════
    # Fédérations partenaires
    # ════════════════════════════
    "fcsf": {
        "id": "fcsf",
        "nom": "FCSF — Fédération des Centres Sociaux de France",
        "type": "federation",
        "role": "Fédération nationale des centres sociaux",
        "description": "Réseau national + 22 unions régionales. Pacte de Coopération CNAF/FCSF.",
        "url": "https://www.centres-sociaux.fr",
    },
    "acepp": {
        "id": "acepp",
        "nom": "ACEPP — Collectifs Enfants Parents Professionnels",
        "type": "federation",
        "role": "Fédération nationale petite enfance associative",
        "description": "Réseau des EAJE associatifs et participatifs.",
        "url": "https://acepp.asso.fr",
    },
    "ffec": {
        "id": "ffec",
        "nom": "FFEC — Fédération Française des Entreprises de Crèches",
        "type": "federation",
        "role": "Fédération employeurs crèches multi-statuts",
        "description": "Représentation des structures d'accueil petite enfance.",
        "url": "https://www.ff-entreprises-creches.fr",
    },

    # ════════════════════════════
    # OPCO et formation
    # ════════════════════════════
    "uniformation": {
        "id": "uniformation",
        "nom": "Uniformation — OPCO Cohésion sociale",
        "type": "opco",
        "role": "OPCO de la branche ALISFA",
        "description": "Plan de Développement, CPF, Pro-A, alternance, AFEST.",
        "phone": "01 53 02 13 13",
        "url": "https://www.uniformation.fr",
    },
    "cpnef_alisfa": {
        "id": "cpnef_alisfa",
        "nom": "CPNEF Branche ALISFA",
        "type": "elisfa",
        "role": "Commission Paritaire Nationale Emploi Formation",
        "description": "Politique formation de branche, certifications, fiches métiers.",
        "url": "https://www.cpnef-branche-alisfa.fr",
    },
    "centre_inffo": {
        "id": "centre_inffo",
        "nom": "Centre Inffo",
        "type": "ressource",
        "role": "Information formation professionnelle",
        "description": "Décryptage juridique formation pro + actualités.",
        "url": "https://www.centre-inffo.fr",
    },
    "moncompteformation": {
        "id": "moncompteformation",
        "nom": "Mon Compte Formation",
        "type": "etat",
        "role": "Portail officiel CPF",
        "description": "Mobiliser son CPF, rechercher une formation, financer.",
        "url": "https://www.moncompteformation.gouv.fr",
    },
    "france_competences": {
        "id": "france_competences",
        "nom": "France Compétences",
        "type": "etat",
        "role": "Régulation formation professionnelle et apprentissage",
        "description": "RNCP, RS, OPCO, niveaux de prise en charge alternance.",
        "url": "https://www.francecompetences.fr",
    },

    # ════════════════════════════
    # État central — sites officiels
    # ════════════════════════════
    "service_public": {
        "id": "service_public",
        "nom": "Service-Public.fr",
        "type": "etat",
        "role": "Portail officiel administration française",
        "description": "Démarches, droits, fiches juridiques particuliers et professionnels.",
        "url": "https://www.service-public.fr",
    },
    "service_public_pro": {
        "id": "service_public_pro",
        "nom": "Entreprendre — Service-Public.fr (associations)",
        "type": "etat",
        "role": "Démarches employeurs et associations",
        "description": "Obligations employeur, contrats, RH, fiscalité associative.",
        "url": "https://entreprendre.service-public.fr/vosdroits/N31137",
    },
    "associations_gouv": {
        "id": "associations_gouv",
        "nom": "Associations.gouv.fr",
        "type": "vie_asso",
        "role": "Portail officiel de la vie associative",
        "description": "Compte Asso, agréments JEP/FDVA, modèles statuts, démarches préfecture.",
        "url": "https://www.associations.gouv.fr",
    },
    "compte_asso": {
        "id": "compte_asso",
        "nom": "Le Compte Asso",
        "type": "vie_asso",
        "role": "Plateforme officielle de démarches associatives",
        "description": "Modifications statuts, dirigeants, demandes subventions FDVA.",
        "url": "https://lecompteasso.associations.gouv.fr",
    },
    "rna": {
        "id": "rna",
        "nom": "RNA — Répertoire National des Associations",
        "type": "etat",
        "role": "Registre officiel des associations loi 1901",
        "description": "Vérifier la situation administrative d'une association.",
        "url": "https://www.journal-officiel.gouv.fr/associations/",
    },
    "legifrance": {
        "id": "legifrance",
        "nom": "Légifrance",
        "type": "etat",
        "role": "Service public de diffusion du droit",
        "description": "Code du travail, CCN ALISFA, lois, décrets, jurisprudence.",
        "url": "https://www.legifrance.gouv.fr",
    },
    "bofip": {
        "id": "bofip",
        "nom": "BOFiP — Bulletin Officiel des Finances Publiques",
        "type": "etat",
        "role": "Doctrine fiscale officielle",
        "description": "Règle des 4P (non-lucrativité), mécénat, fiscalité associative.",
        "url": "https://bofip.impots.gouv.fr",
    },
    "demarches_simplifiees": {
        "id": "demarches_simplifiees",
        "nom": "Démarches Simplifiées",
        "type": "etat",
        "role": "Plateforme de dépôt de dossiers administratifs",
        "description": "Dépôt FDVA, FONJEP, agréments, subventions territoriales.",
        "url": "https://www.demarches-simplifiees.fr",
    },
    "djepva": {
        "id": "djepva",
        "nom": "DJEPVA — Direction Jeunesse, Éducation Populaire, Vie Associative",
        "type": "etat",
        "role": "Direction du ministère en charge de la vie associative",
        "description": "Politique nationale jeunesse + vie associative + agréments JEP.",
        "url": "https://www.jeunes.gouv.fr",
    },
    "ministere_travail": {
        "id": "ministere_travail",
        "nom": "Ministère du Travail",
        "type": "etat",
        "role": "Politique du travail et de l'emploi",
        "description": "Code du travail, négociations branches, égalité, RPS.",
        "url": "https://travail-emploi.gouv.fr",
    },
    "ministere_solidarites": {
        "id": "ministere_solidarites",
        "nom": "Ministère des Solidarités",
        "type": "etat",
        "role": "Politiques familles, autonomie, action sociale",
        "description": "Politique petite enfance, parentalité, lutte exclusion.",
        "url": "https://solidarites.gouv.fr",
    },
    "hcva": {
        "id": "hcva",
        "nom": "HCVA — Haut Conseil à la Vie Associative",
        "type": "etat",
        "role": "Instance consultative auprès du Premier ministre",
        "description": "Avis, études et recommandations sur le cadre juridique associatif.",
        "url": "https://www.associations.gouv.fr/le-hcva.html",
    },

    # ════════════════════════════
    # Pouvoirs déconcentrés (services de l'État en région/département)
    # ════════════════════════════
    "prefecture": {
        "id": "prefecture",
        "nom": "Préfecture / Sous-préfecture",
        "type": "deconcentre",
        "role": "Représentant local de l'État",
        "description": "Déclaration association loi 1901, agréments, autorité préfectorale.",
        "url": "https://lannuaire.service-public.fr/navigation/prefectures",
    },
    "dreets": {
        "id": "dreets",
        "nom": "DREETS — Direction Économie, Emploi, Travail, Solidarités (régional)",
        "type": "deconcentre",
        "role": "Inspection du travail + politiques emploi/social régionales",
        "description": "Application droit du travail, signalements harcèlement, PSE.",
        "url": "https://lannuaire.service-public.fr/navigation/dreets",
    },
    "ddets": {
        "id": "ddets",
        "nom": "DDETS / DDETS-PP — Direction départementale (Économie, Emploi, Travail, Solidarités)",
        "type": "deconcentre",
        "role": "Services déconcentrés départementaux",
        "description": "Inspection du travail, jeunesse, sport, vie associative locale.",
        "url": "https://lannuaire.service-public.fr/navigation/ddets",
    },
    "drajes": {
        "id": "drajes",
        "nom": "DRAJES — Délégations régionales Académiques Jeunesse Engagement Sport",
        "type": "deconcentre",
        "role": "Politique jeunesse, sport, vie associative régionale",
        "description": "Agréments JEP, FONJEP, FDVA, soutien projets jeunesse.",
        "url": "https://www.education.gouv.fr/les-services-deconcentres-de-l-etat-au-coeur-des-projets-de-jeunesse-d-engagement-et-de-sport-326336",
    },
    "ars": {
        "id": "ars",
        "nom": "ARS — Agence Régionale de Santé",
        "type": "deconcentre",
        "role": "Politique de santé en région",
        "description": "Autorisations EAJE santé, médico-social, prévention.",
        "url": "https://www.ars.sante.fr",
    },
    "pmi": {
        "id": "pmi",
        "nom": "PMI — Protection Maternelle et Infantile (Conseil départemental)",
        "type": "collectivite",
        "role": "Service départemental de protection de l'enfance",
        "description": "Autorisation et contrôle EAJE, agrément assistantes maternelles.",
        "url": "https://lannuaire.service-public.fr/navigation/conseils-departementaux",
    },

    # ════════════════════════════
    # Collectivités territoriales — sites institutionnels nationaux
    # ════════════════════════════
    "amf": {
        "id": "amf",
        "nom": "AMF — Association des Maires de France",
        "type": "collectivite",
        "role": "Représentation des communes et intercommunalités",
        "description": "Plus de 35 000 communes adhérentes, ressources juridiques.",
        "url": "https://www.amf.asso.fr",
    },
    "intercommunalites_france": {
        "id": "intercommunalites_france",
        "nom": "Intercommunalités de France (AdCF)",
        "type": "collectivite",
        "role": "Représentation communautés de communes / agglomérations / métropoles",
        "description": "Politiques territoriales, mutualisations, projet de territoire.",
        "url": "https://www.intercommunalites.fr",
    },
    "departements_france": {
        "id": "departements_france",
        "nom": "Départements de France (ADF)",
        "type": "collectivite",
        "role": "Assemblée des Départements de France",
        "description": "Politiques sociales (ASE, PMI, RSA), jeunesse départementale.",
        "url": "https://www.departements.fr",
    },
    "regions_france": {
        "id": "regions_france",
        "nom": "Régions de France",
        "type": "collectivite",
        "role": "Association des présidents de Régions",
        "description": "Formation pro, ESS, FSE+/FEDER, politique jeunesse régionale.",
        "url": "https://regions-france.org",
    },
    "annuaire_collectivites": {
        "id": "annuaire_collectivites",
        "nom": "Annuaire des collectivités (Service-Public)",
        "type": "etat",
        "role": "Trouver mairie, communauté, département, région",
        "description": "Recherche par code postal ou nom de commune.",
        "url": "https://lannuaire.service-public.fr",
    },
    "data_gouv_collectivites": {
        "id": "data_gouv_collectivites",
        "nom": "data.gouv.fr — Bases collectivités",
        "type": "etat",
        "role": "Données ouvertes des collectivités",
        "description": "Liste communes/EPCI/départements avec subventions et données budget.",
        "url": "https://www.data.gouv.fr/fr/topics/collectivites/",
    },

    # ════════════════════════════
    # Vie associative — opérateurs et accompagnement
    # ════════════════════════════
    "guid_asso": {
        "id": "guid_asso",
        "nom": "Guid'Asso",
        "type": "vie_asso",
        "role": "Réseau public d'accompagnement de la vie associative",
        "description": "Premier accueil, orientation, conseil 1er niveau dans tous les départements.",
        "url": "https://www.associations.gouv.fr/guid-asso.html",
    },
    "dla": {
        "id": "dla",
        "nom": "DLA — Dispositif Local d'Accompagnement",
        "type": "vie_asso",
        "role": "Accompagnement gratuit des structures d'utilité sociale",
        "description": "Diagnostic + 2-5 jours conseil expert (modèle économique, RH, gouvernance).",
        "url": "https://www.avise.org/dla",
    },
    "avise": {
        "id": "avise",
        "nom": "Avise",
        "type": "vie_asso",
        "role": "Agence d'ingénierie pour acteurs ESS",
        "description": "Pilote DLA national, ressources évaluation impact social, financements ESS.",
        "url": "https://www.avise.org",
    },
    "le_mouvement_associatif": {
        "id": "le_mouvement_associatif",
        "nom": "Le Mouvement Associatif",
        "type": "vie_asso",
        "role": "Coordination des associations en France",
        "description": "Plaidoyer, études, ressources sur la vie associative.",
        "url": "https://lemouvementassociatif.org",
    },
    "france_benevolat": {
        "id": "france_benevolat",
        "nom": "France Bénévolat",
        "type": "vie_asso",
        "role": "Promotion et reconnaissance du bénévolat",
        "description": "Passeport Bénévole®, Compte d'Engagement Citoyen, plateforme nationale.",
        "url": "https://www.francebenevolat.org",
    },
    "institut_monde_associatif": {
        "id": "institut_monde_associatif",
        "nom": "Institut français du Monde Associatif",
        "type": "vie_asso",
        "role": "Centre de recherche et de soutien aux travaux sur le fait associatif",
        "description": "Études sociologiques, économie de la vie associative.",
        "url": "https://institut-isbl.fr",
    },
    "recherches_solidarites": {
        "id": "recherches_solidarites",
        "nom": "Recherches & Solidarités",
        "type": "vie_asso",
        "role": "Recherche associative — chiffres clés du secteur",
        "description": "Bilans annuels emploi, finances, bénévolat associatifs.",
        "url": "https://recherches-solidarites.org",
    },
    "ess_france": {
        "id": "ess_france",
        "nom": "ESS France",
        "type": "vie_asso",
        "role": "Confédération nationale de l'Économie Sociale et Solidaire",
        "description": "Plaidoyer ESS, loi Hamon 2014, agrément ESUS.",
        "url": "https://www.ess-france.org",
    },
    "cress": {
        "id": "cress",
        "nom": "CRESS — Chambres Régionales de l'ESS",
        "type": "vie_asso",
        "role": "Représentation territoriale de l'ESS",
        "description": "Mois de l'ESS (novembre), promotion ESS dans la région.",
        "url": "https://www.ess-france.org/les-cress",
    },

    # ════════════════════════════
    # Acteurs sociaux et travail
    # ════════════════════════════
    "medecine_travail": {
        "id": "medecine_travail",
        "nom": "Médecine du travail (SPST)",
        "type": "operateur",
        "role": "Service de Prévention et Santé au Travail",
        "description": "Visite d'embauche, suivi, alerte RPS, inaptitude.",
        "url": "https://travail-emploi.gouv.fr/sante-au-travail/services-de-prevention-et-de-sante-au-travail-spst",
    },
    "agefiph": {
        "id": "agefiph",
        "nom": "AGEFIPH",
        "type": "operateur",
        "role": "Insertion professionnelle des personnes handicapées",
        "description": "OETH 6%, aides à l'embauche, aménagements de poste.",
        "url": "https://www.agefiph.fr",
    },
    "cap_emploi": {
        "id": "cap_emploi",
        "nom": "Cap emploi",
        "type": "operateur",
        "role": "Réseau emploi spécialisé handicap",
        "description": "Recrutement, maintien dans l'emploi, accompagnement personnalisé.",
        "url": "https://www.capemploi.com",
    },
    "france_travail": {
        "id": "france_travail",
        "nom": "France Travail (ex-Pôle emploi)",
        "type": "etat",
        "role": "Service public de l'emploi",
        "description": "CSP, recrutement, accompagnement chômage, aides à l'embauche.",
        "url": "https://www.francetravail.fr",
    },

    # ════════════════════════════
    # Financement
    # ════════════════════════════
    "caf": {
        "id": "caf",
        "nom": "CAF — Caisse d'Allocations Familiales",
        "type": "etat",
        "role": "Financement structures petite enfance / parentalité / vie sociale",
        "description": "PSU EAJE, agrément Centre Social, EVS, CTG, CLAS, REAAP.",
        "url": "https://www.caf.fr/partenaires",
    },
    "france_active": {
        "id": "france_active",
        "nom": "France Active",
        "type": "vie_asso",
        "role": "Financement solidaire des entreprises de l'ESS",
        "description": "Prêts à taux zéro, garanties bancaires, transition écologique.",
        "url": "https://www.franceactive.org",
    },
    "fonjep": {
        "id": "fonjep",
        "nom": "FONJEP",
        "type": "vie_asso",
        "role": "Cofinancement de postes JEP en associations",
        "description": "~7 000 €/an/poste, durée 3 ans renouvelable.",
        "url": "https://www.fonjep.org",
    },
    "fdva": {
        "id": "fdva",
        "nom": "FDVA — Fonds pour le Développement de la Vie Associative",
        "type": "etat",
        "role": "Soutien financier aux associations",
        "description": "Volet 1 (formation bénévoles) + volet 2 (fonctionnement et innovation).",
        "url": "https://www.associations.gouv.fr/le-fdva.html",
    },
    "bpifrance": {
        "id": "bpifrance",
        "nom": "Bpifrance",
        "type": "etat",
        "role": "Banque publique d'investissement",
        "description": "Prêts ESS, garanties pour structures associatives employeuses.",
        "url": "https://www.bpifrance.fr",
    },

    # ════════════════════════════
    # RGPD / Numérique
    # ════════════════════════════
    "cnil": {
        "id": "cnil",
        "nom": "CNIL — Commission Nationale Informatique et Libertés",
        "type": "etat",
        "role": "Protection des données personnelles",
        "description": "Guides RGPD associations, modèles registres, désignation DPO.",
        "url": "https://www.cnil.fr",
    },
    "anssi": {
        "id": "anssi",
        "nom": "Cybermalveillance.gouv.fr (ANSSI)",
        "type": "etat",
        "role": "Cybersécurité",
        "description": "Guide cybersécurité TPE/PME/associations, assistance attaque.",
        "url": "https://www.cybermalveillance.gouv.fr",
    },

    # ════════════════════════════
    # Justice / Tribunal
    # ════════════════════════════
    "tribunal_judiciaire": {
        "id": "tribunal_judiciaire",
        "nom": "Tribunal judiciaire",
        "type": "etat",
        "role": "Procédures collectives + contentieux",
        "description": "Cessation des paiements, sauvegarde, redressement, liquidation.",
        "url": "https://www.justice.fr/recherche/annuaires?lang=fr",
    },
    "conseil_prudhommes": {
        "id": "conseil_prudhommes",
        "nom": "Conseil de Prud'hommes",
        "type": "etat",
        "role": "Juridiction du litige individuel du travail",
        "description": "Litiges contrat de travail employeur ↔ salarié.",
        "url": "https://www.justice.fr/themes/conseil-prudhommes",
    },
    "avocat_droit_social": {
        "id": "avocat_droit_social",
        "nom": "Avocat droit social / droit des associations",
        "type": "partenaire",
        "role": "Conseil et défense contentieux",
        "description": "Pour Prud'hommes, contentieux pénal, défense association.",
        "url": "https://www.avocat.fr",
    },

    # ════════════════════════════
    # Transition écologique
    # ════════════════════════════
    "ademe": {
        "id": "ademe",
        "nom": "ADEME — Agence de la transition écologique",
        "type": "etat",
        "role": "Transition énergétique et environnementale",
        "description": "Audits énergétiques, aides rénovation, EGalim, bilan carbone.",
        "url": "https://www.ademe.fr",
    },

    # ════════════════════════════
    # Urgence (téléphones)
    # ════════════════════════════
    "samu": {
        "id": "samu",
        "nom": "Numéros d'urgence",
        "type": "urgence",
        "role": "Danger vital",
        "description": (
            "15 SAMU · 17 Police · 18 Pompiers · 112 urgence européenne · "
            "3114 prévention suicide · 3919 violences femmes · 119 enfance en danger"
        ),
        "phone": "112",
        "url": "https://www.gouvernement.fr/risques/numeros-urgence",
    },
}


# ────────────────────────── Orientations par nature de problème ──────────────────────────

ORIENTATIONS: list[Orientation] = [
    {
        "id": "conflit_rps",
        "label": "Conflit, harcèlement, RPS, mal-être au travail",
        "icon": "🚨",
        "description": (
            "Tension dans l'équipe, signalement de harcèlement, alerte RPS, burn-out, "
            "absences répétées, démissions en série."
        ),
        "acteurs": [
            "elisfa_social", "medecine_travail", "dreets",
            "samu", "avocat_droit_social",
        ],
    },
    {
        "id": "discipline_rupture",
        "label": "Sanction, licenciement, fin de contrat",
        "icon": "⚖️",
        "description": (
            "Procédure disciplinaire, faute grave, licenciement éco, rupture "
            "conventionnelle, contestation Prud'hommes."
        ),
        "acteurs": [
            "elisfa_juridique", "service_public_pro", "legifrance",
            "conseil_prudhommes", "avocat_droit_social", "dreets",
        ],
    },
    {
        "id": "formation_dispositifs",
        "label": "Formation : CPF, plan, alternance, financement",
        "icon": "🎓",
        "description": (
            "Choisir un dispositif (CPF/Pro-A/PTP/AFEST), entretien pro, plan "
            "compétences, certifications branche."
        ),
        "acteurs": [
            "uniformation", "moncompteformation", "cpnef_alisfa",
            "centre_inffo", "france_competences",
        ],
    },
    {
        "id": "financement_subvention",
        "label": "Financer un projet, subvention, CPO",
        "icon": "💰",
        "description": (
            "Convention pluriannuelle CAF/Mairie, FONJEP, FDVA, FSE+, mécénat, "
            "trésorerie et investissement solidaire."
        ),
        "acteurs": [
            "caf", "fonjep", "fdva", "demarches_simplifiees",
            "france_active", "bpifrance", "dla", "avise",
        ],
    },
    {
        "id": "gouvernance_statuts",
        "label": "Statuts, AG, CA, modifs préfecture",
        "icon": "🏛",
        "description": (
            "Mise à jour statuts, déclaration en préfecture, organisation AG, "
            "responsabilité dirigeants, agrément JEP/RIG/RUP."
        ),
        "acteurs": [
            "associations_gouv", "compte_asso", "rna",
            "service_public", "prefecture", "guid_asso",
            "dla", "hcva",
        ],
    },
    {
        "id": "petite_enfance",
        "label": "EAJE, crèche, accueil petite enfance",
        "icon": "🍼",
        "description": (
            "Création/gestion EAJE, agrément PMI, PSU CAF, application CCN aux EJE/RPE."
        ),
        "acteurs": [
            "acepp", "caf", "pmi", "ars",
            "elisfa_juridique", "ffec",
        ],
    },
    {
        "id": "rgpd_numerique",
        "label": "RGPD, données, cybersécurité",
        "icon": "🔒",
        "description": (
            "Registre des traitements, photos d'enfants, hébergement souverain, "
            "newsletter et cookies, fuite de données, ransomware."
        ),
        "acteurs": ["cnil", "anssi"],
    },
    {
        "id": "benevoles_engagement",
        "label": "Recruter et fidéliser les bénévoles",
        "icon": "🤝",
        "description": (
            "Passeport Bénévole, CEC, congé d'engagement, mécénat de compétences, "
            "valorisation comptable, FDVA formation bénévoles."
        ),
        "acteurs": [
            "france_benevolat", "fdva", "fcsf", "acepp",
            "le_mouvement_associatif", "dla",
        ],
    },
    {
        "id": "handicap_oeth",
        "label": "Inclusion handicap, OETH 6%",
        "icon": "♿",
        "description": (
            "Recruter une personne handicapée, OETH, aménagement de poste, "
            "accueillir un enfant porteur de handicap en EAJE/ALSH."
        ),
        "acteurs": [
            "agefiph", "cap_emploi", "medecine_travail",
            "france_travail", "elisfa_juridique",
        ],
    },
    {
        "id": "transition_ecologique",
        "label": "Transition écologique, sobriété, EGalim",
        "icon": "🌱",
        "description": (
            "Restauration collective EGalim, rénovation thermique, mobilité durable, "
            "bilan carbone, financement transition."
        ),
        "acteurs": ["ademe", "france_active", "dla", "bpifrance"],
    },
    {
        "id": "crise_juridique_fiscale",
        "label": "Crise grave (mise en cause, contrôle URSSAF/fiscal)",
        "icon": "🆘",
        "description": (
            "Cessation des paiements, mise en cause des dirigeants, contrôle URSSAF, "
            "redressement fiscal, dissolution judiciaire."
        ),
        "acteurs": [
            "elisfa_juridique", "avocat_droit_social", "tribunal_judiciaire",
            "bofip", "fcsf", "acepp", "dla",
        ],
    },
    {
        "id": "vie_associative_general",
        "label": "Démarrage / question générale vie associative",
        "icon": "❓",
        "description": (
            "Première question, accompagnement général projet associatif, "
            "ne sait pas par où commencer."
        ),
        "acteurs": [
            "guid_asso", "associations_gouv", "service_public",
            "annuaire_collectivites", "dla", "fcsf", "acepp",
            "le_mouvement_associatif", "ess_france", "cress",
        ],
    },
    {
        "id": "fiscalite_associative",
        "label": "Fiscalité associative (4P, mécénat, IS, TVA)",
        "icon": "💼",
        "description": (
            "Règle des 4P pour la non-lucrativité, agrément RIG, mécénat 60-66%, "
            "TVA et IS sur activités lucratives."
        ),
        "acteurs": [
            "bofip", "service_public_pro", "elisfa_juridique",
            "ess_france", "dla",
        ],
    },
]


# ────────────────────────── Régions ELISFA + Conseil régional + Préfecture ──────────────────────────

FEDERATIONS_BY_REGION: list[RegionInfo] = [
    # ═══════════ MÉTROPOLE ═══════════
    {
        "region": "Île-de-France",
        "code": "11",
        "type": "metropole",
        "elisfa_referent": "Sabine Hamot",
        "elisfa_email": "sabine.hamot@elisfa.fr",
        "region_label": "Région Île-de-France",
        "region_url": "https://www.iledefrance.fr",
        "prefecture_url": "https://www.prefectures-regions.gouv.fr/ile-de-france",
        "fcsf_federations": [
            "Fédération des centres sociaux de Paris (75)",
            "Fédération des centres sociaux de Seine-et-Marne (77)",
            "Fédération des centres sociaux des Yvelines (78)",
            "Fédération des centres sociaux de l'Essonne (91)",
            "Fédération des centres sociaux des Hauts-de-Seine (92)",
            "Fédération des centres sociaux de Seine-Saint-Denis (93)",
            "Fédération des centres sociaux du Val-de-Marne (94)",
            "Fédération des centres sociaux du Val-d'Oise (95)",
            "Union Francilienne (UFFCS)",
        ],
        "acepp_federations": [
            "ACEPP Île-de-France — ACEPPRIF (75, 77, 78, 92, 93, 94, 95)",
            "ACEPP 91 — Essonne",
        ],
    },
    {
        "region": "Hauts-de-France",
        "code": "32",
        "type": "metropole",
        "elisfa_referent": "Agnès Stemler",
        "elisfa_email": "agnes.stemler@elisfa.fr",
        "region_label": "Région Hauts-de-France",
        "region_url": "https://www.hautsdefrance.fr",
        "prefecture_url": "https://www.prefectures-regions.gouv.fr/hauts-de-france",
        "fcsf_federations": [
            "Fédération Nord Pas-de-Calais",
            "Fédération des Pays Picards",
            "Union des centres sociaux des Hauts-de-France",
        ],
        "acepp_federations": ["COLLINE ACEPP — Hauts-de-France"],
    },
    {
        "region": "Grand Est",
        "code": "44",
        "type": "metropole",
        "elisfa_referent": "Agnès Stemler",
        "elisfa_email": "agnes.stemler@elisfa.fr",
        "region_label": "Région Grand Est",
        "region_url": "https://www.grandest.fr",
        "prefecture_url": "https://www.prefectures-regions.gouv.fr/grand-est",
        "fcsf_federations": [
            "Fédération des Ardennes (08)",
            "Fédération de la Marne (51)",
            "Fédération de la Meuse (55)",
            "Fédération de la Moselle (57)",
            "Fédération du Bas-Rhin (67)",
            "Union du Haut-Rhin (68)",
            "Union régionale Grand Est (URGE)",
        ],
        "acepp_federations": [],
    },
    {
        "region": "Auvergne-Rhône-Alpes",
        "code": "84",
        "type": "metropole",
        "elisfa_referent": "Valentin Chaix",
        "elisfa_email": "valentin.chaix@elisfa.fr",
        "region_label": "Région Auvergne-Rhône-Alpes",
        "region_url": "https://www.auvergnerhonealpes.fr",
        "prefecture_url": "https://www.prefectures-regions.gouv.fr/auvergne-rhone-alpes",
        "fcsf_federations": [
            "Fédération de l'Ain (01)",
            "Fédération de l'Allier (03)",
            "Fédération de l'Ardèche (07)",
            "Fédération de la Drôme (26)",
            "Fédération de l'Isère (38)",
            "Fédération Loire / Haute-Loire (42-43)",
            "Fédération du Rhône (69)",
            "Fédération des 2 Savoie (73-74)",
            "Union Rhône-Alpes",
        ],
        "acepp_federations": [
            "ACEPP Auvergne (03, 15, 43, 63)",
            "ACEPP ADeHL — Ardèche, Drôme, Haut-Lignon (07, 26)",
            "ACEPP 38 — Isère",
            "ACEPP 69 — Rhône",
            "ACEPP 74-73 — Savoie, Haute-Savoie",
        ],
    },
    {
        "region": "Provence-Alpes-Côte d'Azur",
        "code": "93",
        "type": "metropole",
        "elisfa_referent": "Isabelle Pudepiece",
        "elisfa_email": "isabelle.pudepiece@elisfa.fr",
        "region_label": "Région Sud (PACA)",
        "region_url": "https://www.maregionsud.fr",
        "prefecture_url": "https://www.prefectures-regions.gouv.fr/provence-alpes-cote-d-azur",
        "fcsf_federations": [
            "Union des Bouches-du-Rhône (13)",
            "Fédération Côte d'Azur (83)",
            "Fédération du Vaucluse (84)",
            "Union régionale PACA",
        ],
        "acepp_federations": [
            "ALPE ACEPP 04 — Alpes-de-Haute-Provence",
            "Alpaje-ACEPP 05 — Hautes-Alpes",
            "ACEPP 83 — Var",
        ],
    },
    {
        "region": "Corse",
        "code": "94",
        "type": "metropole",
        "elisfa_referent": "Isabelle Pudepiece",
        "elisfa_email": "isabelle.pudepiece@elisfa.fr",
        "region_label": "Collectivité de Corse",
        "region_url": "https://www.isula.corsica",
        "prefecture_url": "https://www.corse.gouv.fr",
        "fcsf_federations": [],
        "acepp_federations": [],
    },
    {
        "region": "Occitanie",
        "code": "76",
        "type": "metropole",
        "elisfa_referent": "Isabelle Pudepiece",
        "elisfa_email": "isabelle.pudepiece@elisfa.fr",
        "region_label": "Région Occitanie",
        "region_url": "https://www.laregion.fr",
        "prefecture_url": "https://www.prefectures-regions.gouv.fr/occitanie",
        "fcsf_federations": [
            "Fédération du Languedoc-Roussillon",
            "Fédération Garonne Occitanie — FIGO (09, 12, 31, 32, 46, 65, 81, 82)",
        ],
        "acepp_federations": [
            "Cocagne ACEPP 31 — Haute-Garonne",
            "FCP du Lot ACEPP 46 — Lot",
            "ACEPP 65 — Hautes-Pyrénées",
            "ACEPP 81 — Tarn",
        ],
    },
    {
        "region": "Nouvelle-Aquitaine",
        "code": "75",
        "type": "metropole",
        "elisfa_referent": "Siège ELISFA",
        "elisfa_email": "contact@elisfa.fr",
        "region_label": "Région Nouvelle-Aquitaine",
        "region_url": "https://www.nouvelle-aquitaine.fr",
        "prefecture_url": "https://www.prefectures-regions.gouv.fr/nouvelle-aquitaine",
        "fcsf_federations": [
            "Fédération de Charente (16)",
            "Fédération de Charente-Maritime (17)",
            "Fédération de Dordogne (24)",
            "Fédération de Gironde (33)",
            "Fédération des Pyrénées-Atlantiques (64)",
            "Fédération des Deux-Sèvres (79)",
            "Fédération de la Vienne (86)",
            "Union régionale Aquitaine",
            "Union régionale Poitou-Charentes (URECSO)",
        ],
        "acepp_federations": [
            "ACEPP 17 — Charente-Maritime",
            "ACEPP SO — Gironde, Lot-et-Garonne, Landes, Dordogne (33, 47, 40, 24)",
        ],
    },
    {
        "region": "Bretagne",
        "code": "53",
        "type": "metropole",
        "elisfa_referent": "Sandra Floch",
        "elisfa_email": "sandra.floch@elisfa.fr",
        "region_label": "Région Bretagne",
        "region_url": "https://www.bretagne.bzh",
        "prefecture_url": "https://www.prefectures-regions.gouv.fr/bretagne",
        "fcsf_federations": ["Fédération des centres sociaux de Bretagne"],
        "acepp_federations": ["ACEPP 29 — Finistère"],
    },
    {
        "region": "Pays de la Loire",
        "code": "52",
        "type": "metropole",
        "elisfa_referent": "Sandra Floch",
        "elisfa_email": "sandra.floch@elisfa.fr",
        "region_label": "Région Pays de la Loire",
        "region_url": "https://www.paysdelaloire.fr",
        "prefecture_url": "https://www.prefectures-regions.gouv.fr/pays-de-la-loire",
        "fcsf_federations": [
            "Fédération Loire-Atlantique (44)",
            "Fédération Maine-et-Loire / Mayenne (49-53)",
            "Fédération de la Sarthe (72)",
            "Fédération de Vendée (85)",
            "Union régionale Pays de la Loire",
        ],
        "acepp_federations": [],
    },
    {
        "region": "Normandie",
        "code": "28",
        "type": "metropole",
        "elisfa_referent": "Sandra Floch",
        "elisfa_email": "sandra.floch@elisfa.fr",
        "region_label": "Région Normandie",
        "region_url": "https://www.normandie.fr",
        "prefecture_url": "https://www.prefectures-regions.gouv.fr/normandie",
        "fcsf_federations": ["Fédération de Seine-Maritime (76)"],
        "acepp_federations": ["ACEPP Basse-Normandie (14, 50, 61)"],
    },
    {
        "region": "Bourgogne-Franche-Comté",
        "code": "27",
        "type": "metropole",
        "elisfa_referent": "Siège ELISFA",
        "elisfa_email": "contact@elisfa.fr",
        "region_label": "Région Bourgogne-Franche-Comté",
        "region_url": "https://www.bourgognefranchecomte.fr",
        "prefecture_url": "https://www.prefectures-regions.gouv.fr/bourgogne-franche-comte",
        "fcsf_federations": [
            "Union régionale de Bourgogne",
            "Fédération de Côte-d'Or (21)",
            "Fédération de la Nièvre (58)",
        ],
        "acepp_federations": [],
    },
    {
        "region": "Centre-Val de Loire",
        "code": "24",
        "type": "metropole",
        "elisfa_referent": "Siège ELISFA",
        "elisfa_email": "contact@elisfa.fr",
        "region_label": "Région Centre-Val de Loire",
        "region_url": "https://www.centre-valdeloire.fr",
        "prefecture_url": "https://www.prefectures-regions.gouv.fr/centre-val-de-loire",
        "fcsf_federations": ["Fédération régionale Centre-Val de Loire"],
        "acepp_federations": [
            "ACHIL-ACEPP — Indre-et-Loire (37)",
            "ARPPE en Berry ACEPP 18 — Cher",
        ],
    },

    # ═══════════ DROM (Départements et Régions d'Outre-Mer) ═══════════
    {
        "region": "Guadeloupe",
        "code": "01",
        "type": "drom",
        "elisfa_referent": "Fabien Laquitaine",
        "elisfa_email": "fabien.laquitaine@elisfa.fr",
        "region_label": "Région Guadeloupe (971)",
        "region_url": "https://www.regionguadeloupe.fr",
        "prefecture_url": "https://www.guadeloupe.gouv.fr",
        "fcsf_federations": [],
        "acepp_federations": [],
    },
    {
        "region": "Martinique",
        "code": "02",
        "type": "drom",
        "elisfa_referent": "Fabien Laquitaine",
        "elisfa_email": "fabien.laquitaine@elisfa.fr",
        "region_label": "Collectivité Territoriale de Martinique (972)",
        "region_url": "https://www.collectivitedemartinique.mq",
        "prefecture_url": "https://www.martinique.gouv.fr",
        "fcsf_federations": [],
        "acepp_federations": [],
    },
    {
        "region": "Guyane",
        "code": "03",
        "type": "drom",
        "elisfa_referent": "Fabien Laquitaine",
        "elisfa_email": "fabien.laquitaine@elisfa.fr",
        "region_label": "Collectivité Territoriale de Guyane (973)",
        "region_url": "https://www.ctguyane.fr",
        "prefecture_url": "https://www.guyane.gouv.fr",
        "fcsf_federations": [],
        "acepp_federations": [],
    },
    {
        "region": "La Réunion",
        "code": "04",
        "type": "drom",
        "elisfa_referent": "Sabine Hamot",
        "elisfa_email": "sabine.hamot@elisfa.fr",
        "region_label": "Région Réunion (974)",
        "region_url": "https://www.regionreunion.com",
        "prefecture_url": "https://www.reunion.gouv.fr",
        "fcsf_federations": [],
        "acepp_federations": [],
    },
    {
        "region": "Mayotte",
        "code": "06",
        "type": "drom",
        "elisfa_referent": "Sabine Hamot",
        "elisfa_email": "sabine.hamot@elisfa.fr",
        "region_label": "Département de Mayotte (976)",
        "region_url": "https://www.cg976.fr",
        "prefecture_url": "https://www.mayotte.gouv.fr",
        "fcsf_federations": [],
        "acepp_federations": [],
    },

    # ═══════════ COM (Collectivités d'Outre-Mer) ═══════════
    {
        "region": "Saint-Pierre-et-Miquelon",
        "code": "975",
        "type": "com",
        "elisfa_referent": "Siège ELISFA",
        "elisfa_email": "contact@elisfa.fr",
        "region_label": "Collectivité de Saint-Pierre-et-Miquelon",
        "region_url": "https://www.collectivitespm.fr",
        "prefecture_url": "https://www.saint-pierre-et-miquelon.gouv.fr",
        "fcsf_federations": [],
        "acepp_federations": [],
    },
    {
        "region": "Saint-Barthélemy",
        "code": "977",
        "type": "com",
        "elisfa_referent": "Fabien Laquitaine",
        "elisfa_email": "fabien.laquitaine@elisfa.fr",
        "region_label": "Collectivité de Saint-Barthélemy",
        "region_url": "https://www.comstbarth.fr",
        "prefecture_url": "https://www.guadeloupe.gouv.fr",
        "fcsf_federations": [],
        "acepp_federations": [],
    },
    {
        "region": "Saint-Martin",
        "code": "978",
        "type": "com",
        "elisfa_referent": "Fabien Laquitaine",
        "elisfa_email": "fabien.laquitaine@elisfa.fr",
        "region_label": "Collectivité de Saint-Martin",
        "region_url": "https://www.com-saint-martin.fr",
        "prefecture_url": "https://www.guadeloupe.gouv.fr",
        "fcsf_federations": [],
        "acepp_federations": [],
    },
    {
        "region": "Polynésie française",
        "code": "987",
        "type": "com",
        "elisfa_referent": "Siège ELISFA",
        "elisfa_email": "contact@elisfa.fr",
        "region_label": "Polynésie française",
        "region_url": "https://www.presidence.pf",
        "prefecture_url": "https://www.polynesie-francaise.pref.gouv.fr",
        "fcsf_federations": [],
        "acepp_federations": [],
    },
    {
        "region": "Nouvelle-Calédonie",
        "code": "988",
        "type": "com",
        "elisfa_referent": "Siège ELISFA",
        "elisfa_email": "contact@elisfa.fr",
        "region_label": "Gouvernement Nouvelle-Calédonie",
        "region_url": "https://gouv.nc",
        "prefecture_url": "https://www.haut-commissariat.gouv.nc",
        "fcsf_federations": [],
        "acepp_federations": [],
    },
    {
        "region": "Wallis-et-Futuna",
        "code": "986",
        "type": "com",
        "elisfa_referent": "Siège ELISFA",
        "elisfa_email": "contact@elisfa.fr",
        "region_label": "Wallis-et-Futuna",
        "region_url": "https://www.wallis-et-futuna.gouv.fr",
        "prefecture_url": "https://www.wallis-et-futuna.gouv.fr",
        "fcsf_federations": [],
        "acepp_federations": [],
    },
]


# ────────────────────────── API helpers ──────────────────────────

def get_acteur(acteur_id: str) -> Acteur | None:
    return ACTEURS.get(acteur_id)


def get_orientation(orientation_id: str) -> Orientation | None:
    for o in ORIENTATIONS:
        if o["id"] == orientation_id:
            return o
    return None


def list_orientations() -> list[Orientation]:
    return ORIENTATIONS


def expand_orientation(orientation_id: str) -> dict | None:
    """Retourne l'orientation enrichie avec les acteurs résolus."""
    o = get_orientation(orientation_id)
    if o is None:
        return None
    return {
        "id": o["id"],
        "label": o["label"],
        "icon": o["icon"],
        "description": o["description"],
        "acteurs": [a for aid in o["acteurs"] if (a := get_acteur(aid)) is not None],
    }


def list_acteurs() -> list[Acteur]:
    return list(ACTEURS.values())


def list_regions() -> list[RegionInfo]:
    return FEDERATIONS_BY_REGION
