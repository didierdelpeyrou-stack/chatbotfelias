"""Annuaire d'orientation — Sprint 4.6 F6.

Cœur de l'outil ELISFA : l'utilisateur arrive avec une SITUATION/PROBLÈME et
veut savoir QUI CONTACTER. On structure :

  1. ACTEURS — fiches contacts typées (nom, rôle, email, téléphone, URL)
  2. ORIENTATIONS — natures de problème → liste d'acteurs prioritaires
     dans l'ordre où les contacter
  3. FEDERATIONS_BY_REGION — référents ELISFA + fédérations FCSF/ACEPP
     par région (porté de V1 templates/index.html FEDERATIONS_DATA)

Vue principale Phase 1 : "Mon problème" (par ORIENTATIONS).
Vue secondaire : "Ma région" (par FEDERATIONS_BY_REGION).
"""
from __future__ import annotations

from typing import Literal, TypedDict

# ────────────────────────── Types ──────────────────────────

ActeurType = Literal[
    "elisfa", "federation", "syndicat", "opco",
    "institutionnel", "operateur", "partenaire", "ressource",
]


class Acteur(TypedDict, total=False):
    id: str
    nom: str
    type: ActeurType
    role: str           # "Pôle juridique ELISFA"
    description: str    # 1 phrase
    email: str
    phone: str
    url: str


class Orientation(TypedDict):
    id: str
    label: str
    icon: str
    description: str
    acteurs: list[str]  # liste d'IDs acteurs (ordre = priorité)


class RegionInfo(TypedDict):
    region: str
    elisfa_referent: str
    fcsf_federations: list[str]
    acepp_federations: list[str]


# ────────────────────────── Acteurs ──────────────────────────

ACTEURS: dict[str, Acteur] = {
    # ── ELISFA (syndicat employeur ALISFA) ──
    "elisfa_siege": {
        "id": "elisfa_siege",
        "nom": "ELISFA — Siège national",
        "type": "elisfa",
        "role": "Syndicat employeur de la branche ALISFA (IDCC 1261)",
        "description": (
            "Représentation et défense des employeurs du lien social et familial. "
            "Pilote la CCN ALISFA, l'avenant 10-2022 (classification + rémunération). "
            "ELISFA est un syndicat employeur — PAS une fédération."
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
        "description": (
            "Sanction, rupture, contentieux, application CCN ALISFA, jurisprudence. "
            "Permanence téléphonique + emails + RDV juriste."
        ),
        "email": "rdv-juriste@elisfa.fr",
        "url": "https://www.elisfa.fr",
    },
    "elisfa_social": {
        "id": "elisfa_social",
        "nom": "Pôle social / RH ELISFA",
        "type": "elisfa",
        "role": "Conseil RH, RPS, harcèlement, dialogue social",
        "description": (
            "Accompagnement des situations RH sensibles : RPS, harcèlement, climat social, "
            "dialogue avec les IRP, GEPP. Permanences téléphoniques."
        ),
        "email": "contact@elisfa.fr",
        "url": "https://www.elisfa.fr",
    },

    # ── Fédérations partenaires ──
    "fcsf": {
        "id": "fcsf",
        "nom": "FCSF — Fédération des Centres Sociaux et Socio-culturels de France",
        "type": "federation",
        "role": "Fédération nationale des centres sociaux",
        "description": (
            "Réseau national + 22 unions/fédérations régionales et départementales. "
            "Charte fédérale, Pacte de Coopération CNAF/FCSF mai 2024, accompagnement projet social."
        ),
        "url": "https://www.centres-sociaux.fr",
    },
    "acepp": {
        "id": "acepp",
        "nom": "ACEPP — Association des Collectifs Enfants Parents Professionnels",
        "type": "federation",
        "role": "Fédération nationale petite enfance associative et parentale",
        "description": (
            "Réseau national des EAJE associatifs et participatifs. "
            "Accompagnement pédagogique + politique petite enfance + plaidoyer."
        ),
        "url": "https://acepp.asso.fr",
    },
    "ffec": {
        "id": "ffec",
        "nom": "FFEC — Fédération Française des Entreprises de Crèches",
        "type": "federation",
        "role": "Fédération employeurs crèches (multi-statuts)",
        "description": "Représentation des structures d'accueil petite enfance, dont associatives.",
        "url": "https://www.ff-entreprises-creches.fr",
    },

    # ── OPCO et formation ──
    "uniformation": {
        "id": "uniformation",
        "nom": "Uniformation — OPCO Cohésion sociale",
        "type": "opco",
        "role": "OPCO de la branche ALISFA (formation pro)",
        "description": (
            "Financements formation : Plan de Développement des Compétences, CPF de transition, "
            "Pro-A, alternance, AFEST. Conseillers formation par région."
        ),
        "phone": "01 53 02 13 13",
        "url": "https://www.uniformation.fr",
    },
    "cpnef_alisfa": {
        "id": "cpnef_alisfa",
        "nom": "CPNEF Branche ALISFA",
        "type": "institutionnel",
        "role": "Commission Paritaire Nationale Emploi Formation",
        "description": (
            "Politique formation de branche : certifications, fiches métiers (25 fiches CPNEF), "
            "observatoire emploi-formation."
        ),
        "url": "https://www.cpnef-branche-alisfa.fr",
    },
    "centre_inffo": {
        "id": "centre_inffo",
        "nom": "Centre Inffo",
        "type": "ressource",
        "role": "Information formation professionnelle",
        "description": "Décryptage juridique formation pro + actualités secteur.",
        "url": "https://www.centre-inffo.fr",
    },

    # ── Acteurs vie associative ──
    "guid_asso": {
        "id": "guid_asso",
        "nom": "Guid'Asso",
        "type": "operateur",
        "role": "Réseau public d'accompagnement de la vie associative",
        "description": (
            "Premier accueil, orientation, conseil 1er niveau pour les associations. "
            "Présent dans tous les départements via Maisons des Associations / PAVA."
        ),
        "url": "https://www.associations.gouv.fr/guid-asso.html",
    },
    "dla": {
        "id": "dla",
        "nom": "DLA — Dispositif Local d'Accompagnement",
        "type": "operateur",
        "role": "Accompagnement gratuit des structures d'utilité sociale",
        "description": (
            "Diagnostic + 2 à 5 jours de conseil expert (modèle économique, RH, gouvernance, "
            "stratégie). Gratuit pour les associations employeuses. Réseau Avise."
        ),
        "url": "https://www.avise.org/dla",
    },
    "hcva": {
        "id": "hcva",
        "nom": "HCVA — Haut Conseil à la Vie Associative",
        "type": "institutionnel",
        "role": "Instance consultative auprès du Premier ministre",
        "description": "Avis et études sur le cadre juridique et fiscal de la vie associative.",
        "url": "https://www.associations.gouv.fr/le-haut-conseil-a-la-vie-associative.html",
    },
    "associations_gouv": {
        "id": "associations_gouv",
        "nom": "Associations.gouv.fr",
        "type": "ressource",
        "role": "Portail officiel de la vie associative",
        "description": (
            "Démarches en ligne (Compte Asso, déclarations préfecture, agréments JEP/FDVA), "
            "fiches juridiques, modèles de statuts."
        ),
        "url": "https://www.associations.gouv.fr",
    },
    "france_benevolat": {
        "id": "france_benevolat",
        "nom": "France Bénévolat",
        "type": "operateur",
        "role": "Promotion et reconnaissance du bénévolat",
        "description": (
            "Passeport Bénévole®, Compte d'Engagement Citoyen, recrutement bénévoles "
            "via plateforme nationale."
        ),
        "url": "https://www.francebenevolat.org",
    },
    "le_mouvement_associatif": {
        "id": "le_mouvement_associatif",
        "nom": "Le Mouvement Associatif",
        "type": "ressource",
        "role": "Coordination des associations en France",
        "description": "Plaidoyer, études, ressources sur la vie associative.",
        "url": "https://lemouvementassociatif.org",
    },

    # ── Acteurs sociaux et travail ──
    "medecine_travail": {
        "id": "medecine_travail",
        "nom": "Médecine du travail (SPST)",
        "type": "institutionnel",
        "role": "Service de prévention et santé au travail",
        "description": (
            "Visite d'embauche, suivi salariés à risque, alerte RPS, inaptitude. "
            "Saisine sans délai en cas de danger grave et imminent."
        ),
    },
    "dreets": {
        "id": "dreets",
        "nom": "DREETS — Direction régionale Économie, Emploi, Travail et Solidarités",
        "type": "institutionnel",
        "role": "Inspection du travail + politiques emploi/social",
        "description": (
            "Contrôle application droit du travail, signalements harcèlement, "
            "validation PSE, agréments JEP, accord d'entreprise."
        ),
        "url": "https://travail-emploi.gouv.fr/le-ministere-en-action/regions",
    },
    "drajes": {
        "id": "drajes",
        "nom": "DRAJES — Délégations régionales Académiques Jeunesse Engagement Sport",
        "type": "institutionnel",
        "role": "Politique jeunesse, sport, vie associative régionale",
        "description": "Agréments JEP, FONJEP, FDVA, soutien aux projets jeunesse.",
    },
    "agefiph": {
        "id": "agefiph",
        "nom": "AGEFIPH",
        "type": "operateur",
        "role": "Insertion professionnelle des personnes handicapées",
        "description": (
            "OETH 6%, aides à l'embauche, aménagements de poste, financement adaptations. "
            "Réseau Cap emploi départemental."
        ),
        "url": "https://www.agefiph.fr",
    },

    # ── Financement ──
    "caf": {
        "id": "caf",
        "nom": "CAF — Caisse d'Allocations Familiales",
        "type": "institutionnel",
        "role": "Financement structures petite enfance / parentalité / vie sociale",
        "description": (
            "PSU pour EAJE, agrément Centre Social, EVS, CTG, CLAS, REAAP. "
            "Compte partenaire MyCAF."
        ),
        "url": "https://www.caf.fr/partenaires",
    },
    "france_active": {
        "id": "france_active",
        "nom": "France Active",
        "type": "operateur",
        "role": "Financement solidaire des entreprises de l'ESS",
        "description": (
            "Prêts à taux zéro, garanties bancaires, France Active Transition Écologique. "
            "44 implantations territoriales."
        ),
        "url": "https://www.franceactive.org",
    },
    "fonjep": {
        "id": "fonjep",
        "nom": "FONJEP",
        "type": "operateur",
        "role": "Cofinancement de postes JEP en associations",
        "description": (
            "~7 000 €/an/poste, durée 3 ans renouvelable. 1 500 postes en France. "
            "Réservé aux associations agréées JEP."
        ),
        "url": "https://www.fonjep.org",
    },
    "fdva": {
        "id": "fdva",
        "nom": "FDVA — Fonds pour le Développement de la Vie Associative",
        "type": "institutionnel",
        "role": "Soutien financier aux associations",
        "description": (
            "Volet 1 (formation bénévoles, jusqu'à 3 000 €), volet 2 (fonctionnement et "
            "innovation, jusqu'à 15 000 €). Dépôt préfecture."
        ),
        "url": "https://www.associations.gouv.fr/le-fdva.html",
    },

    # ── RGPD et numérique ──
    "cnil": {
        "id": "cnil",
        "nom": "CNIL — Commission Nationale Informatique et Libertés",
        "type": "institutionnel",
        "role": "Protection des données personnelles",
        "description": (
            "Guides RGPD pour associations, modèles registre des traitements, "
            "désignation DPO, notification fuite 72h."
        ),
        "url": "https://www.cnil.fr",
    },
    "anssi": {
        "id": "anssi",
        "nom": "ANSSI / Cybermalveillance.gouv.fr",
        "type": "institutionnel",
        "role": "Cybersécurité",
        "description": (
            "Guide cybersécurité TPE/PME/associations, assistance en cas d'attaque, "
            "ransomware, phishing."
        ),
        "url": "https://www.cybermalveillance.gouv.fr",
    },

    # ── Tribunal et urgence ──
    "tribunal_judiciaire": {
        "id": "tribunal_judiciaire",
        "nom": "Tribunal judiciaire",
        "type": "institutionnel",
        "role": "Procédures collectives + contentieux",
        "description": (
            "Déclaration cessation des paiements (45 j max), sauvegarde, redressement, "
            "liquidation judiciaire. Litiges associatifs (statuts, élections)."
        ),
    },
    "avocat_droit_social": {
        "id": "avocat_droit_social",
        "nom": "Avocat droit social / droit des associations",
        "type": "partenaire",
        "role": "Conseil et défense contentieux",
        "description": (
            "Pour Prud'hommes, contentieux pénal, défense association mise en cause. "
            "Demander à votre fédération une recommandation."
        ),
    },
    "samu": {
        "id": "samu",
        "nom": "Numéros d'urgence",
        "type": "institutionnel",
        "role": "Danger vital",
        "description": (
            "15 SAMU · 17 Police · 18 Pompiers · 112 urgence européenne · "
            "3114 prévention suicide · 3919 violences femmes · 119 enfance en danger"
        ),
        "phone": "112",
    },

    # ── Transition écologique ──
    "ademe": {
        "id": "ademe",
        "nom": "ADEME — Agence de la transition écologique",
        "type": "institutionnel",
        "role": "Transition énergétique et environnementale",
        "description": (
            "Audits énergétiques, aides rénovation thermique, conseils EGalim "
            "(restauration collective), bilan carbone."
        ),
        "url": "https://www.ademe.fr",
    },
}


# ────────────────────────── Orientations par nature de problème ──────────────────────────
# Ordre : la plus fréquente / urgente en premier
ORIENTATIONS: list[Orientation] = [
    {
        "id": "conflit_rps",
        "label": "Conflit, harcèlement, RPS, mal-être au travail",
        "icon": "🚨",
        "description": (
            "Tension dans l'équipe, signalement de harcèlement, alerte RPS, burn-out, "
            "absences répétées, démissions en série."
        ),
        "acteurs": ["elisfa_social", "medecine_travail", "dreets", "samu", "avocat_droit_social"],
    },
    {
        "id": "discipline_rupture",
        "label": "Sanction, licenciement, fin de contrat",
        "icon": "⚖️",
        "description": (
            "Procédure disciplinaire à engager, faute grave, licenciement éco, rupture "
            "conventionnelle, rédaction lettre, contestation Prud'hommes."
        ),
        "acteurs": ["elisfa_juridique", "avocat_droit_social", "dreets", "tribunal_judiciaire"],
    },
    {
        "id": "formation_dispositifs",
        "label": "Formation : CPF, plan, alternance, financement",
        "icon": "🎓",
        "description": (
            "Choisir un dispositif (CPF/Pro-A/PTP/AFEST), entretien pro, plan de "
            "développement des compétences, certifications branche."
        ),
        "acteurs": ["uniformation", "cpnef_alisfa", "centre_inffo", "elisfa_juridique"],
    },
    {
        "id": "financement_subvention",
        "label": "Financer un projet, subvention, CPO",
        "icon": "💰",
        "description": (
            "Convention pluriannuelle CAF/Mairie, FONJEP, FDVA, FSE+, mécénat, "
            "trésorerie et investissement solidaire."
        ),
        "acteurs": ["caf", "fonjep", "fdva", "france_active", "dla"],
    },
    {
        "id": "gouvernance_statuts",
        "label": "Statuts, AG, CA, modifs préfecture",
        "icon": "🏛",
        "description": (
            "Mise à jour statuts, déclaration en préfecture, organisation AG, "
            "responsabilité dirigeants bénévoles, agrément JEP/RIG/RUP."
        ),
        "acteurs": ["associations_gouv", "guid_asso", "dla", "hcva", "le_mouvement_associatif"],
    },
    {
        "id": "petite_enfance",
        "label": "EAJE, crèche, accueil petite enfance",
        "icon": "🍼",
        "description": (
            "Création/gestion EAJE, agrément PMI, PSU CAF, application CCN aux EJE/RPE, "
            "spécificités petite enfance associative."
        ),
        "acteurs": ["acepp", "caf", "elisfa_juridique", "ffec"],
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
        "acteurs": ["france_benevolat", "fdva", "fcsf", "acepp", "dla"],
    },
    {
        "id": "handicap_oeth",
        "label": "Inclusion handicap, OETH 6%",
        "icon": "♿",
        "description": (
            "Recruter une personne handicapée, OETH, aménagement de poste, "
            "accueillir un enfant porteur de handicap en EAJE/ALSH."
        ),
        "acteurs": ["agefiph", "medecine_travail", "elisfa_juridique"],
    },
    {
        "id": "transition_ecologique",
        "label": "Transition écologique, sobriété, EGalim",
        "icon": "🌱",
        "description": (
            "Restauration collective EGalim, rénovation thermique, mobilité durable, "
            "bilan carbone, financement transition."
        ),
        "acteurs": ["ademe", "france_active", "dla"],
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
            "fcsf", "acepp", "dla",
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
            "guid_asso", "associations_gouv", "dla",
            "fcsf", "acepp", "le_mouvement_associatif",
        ],
    },
]


# ────────────────────────── Fédérations par région (porté V1) ──────────────────────────

FEDERATIONS_BY_REGION: list[RegionInfo] = [
    {
        "region": "Île-de-France",
        "elisfa_referent": "Sabine Hamot — sabine.hamot@elisfa.fr",
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
        "elisfa_referent": "Agnès Stemler — agnes.stemler@elisfa.fr",
        "fcsf_federations": [
            "Fédération Nord Pas-de-Calais",
            "Fédération des Pays Picards",
            "Union des centres sociaux des Hauts-de-France",
        ],
        "acepp_federations": ["COLLINE ACEPP — Hauts-de-France"],
    },
    {
        "region": "Grand Est",
        "elisfa_referent": "Agnès Stemler — agnes.stemler@elisfa.fr",
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
        "elisfa_referent": "Valentin Chaix — valentin.chaix@elisfa.fr",
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
        "region": "PACA / Corse",
        "elisfa_referent": "Isabelle Pudepiece — isabelle.pudepiece@elisfa.fr",
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
        "region": "Occitanie",
        "elisfa_referent": "Isabelle Pudepiece — isabelle.pudepiece@elisfa.fr",
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
        "elisfa_referent": "Siège ELISFA — contact@elisfa.fr",
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
        "elisfa_referent": "Sandra Floch — sandra.floch@elisfa.fr",
        "fcsf_federations": ["Fédération des centres sociaux de Bretagne"],
        "acepp_federations": ["ACEPP 29 — Finistère"],
    },
    {
        "region": "Pays de la Loire",
        "elisfa_referent": "Sandra Floch — sandra.floch@elisfa.fr",
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
        "elisfa_referent": "Sandra Floch — sandra.floch@elisfa.fr",
        "fcsf_federations": ["Fédération de Seine-Maritime (76)"],
        "acepp_federations": ["ACEPP Basse-Normandie (14, 50, 61)"],
    },
    {
        "region": "Bourgogne-Franche-Comté",
        "elisfa_referent": "Siège ELISFA — contact@elisfa.fr",
        "fcsf_federations": [
            "Union régionale de Bourgogne",
            "Fédération de Côte-d'Or (21)",
            "Fédération de la Nièvre (58)",
        ],
        "acepp_federations": [],
    },
    {
        "region": "Centre-Val de Loire",
        "elisfa_referent": "Siège ELISFA — contact@elisfa.fr",
        "fcsf_federations": ["Fédération régionale Centre-Val de Loire"],
        "acepp_federations": [
            "ACHIL-ACEPP — Indre-et-Loire (37)",
            "ARPPE en Berry ACEPP 18 — Cher",
        ],
    },
    {
        "region": "Antilles / Guyane",
        "elisfa_referent": "Fabien Laquitaine — fabien.laquitaine@elisfa.fr",
        "fcsf_federations": [],
        "acepp_federations": [],
    },
    {
        "region": "Mayotte / Réunion",
        "elisfa_referent": "Sabine Hamot — sabine.hamot@elisfa.fr",
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
    """Retourne l'orientation enrichie avec les acteurs résolus (full data)."""
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
