"""Fiches métiers CPNEF ALISFA — Sprint 4.6 F5.

25 fiches métiers officielles publiées par la CPNEF ALISFA, organisées en 5
familles selon la cartographie GPEC de la branche (alisfa.fr/emploi-et-formation/gpec/).

Sources :
  - API JobMap Cognito (https://jobmap.cognito.fr/clients/alisfa)
  - PDF officiels publiés sur alisfa.fr/wp-content/uploads/2026/02/

Les URL des PDF sont absolues et stables (pattern cpnef-fiche-metier-*-bd.pdf).
Pas de proxy : on renvoie l'utilisateur directement sur alisfa.fr.
"""
from __future__ import annotations

from typing import TypedDict

PDF_BASE = "https://www.alisfa.fr/wp-content/uploads/2026/02"


class FicheMetier(TypedDict):
    id: str
    nom: str
    famille_id: str
    pdf_url: str
    description: str


class FamilleMetier(TypedDict):
    id: str
    label: str
    icon: str
    description: str
    fiches: list[FicheMetier]


# 5 familles de la cartographie GPEC ALISFA (avenant 10-22)
_FAMILLES: dict[str, dict] = {
    "animation_intervention": {
        "label": "Animation et intervention sociale",
        "icon": "🎯",
        "description": (
            "Animation socio-éducative, intervention sociale, projets "
            "territoriaux, accompagnement des publics."
        ),
    },
    "petite_enfance": {
        "label": "Petite enfance",
        "icon": "🍼",
        "description": (
            "Accueil et accompagnement des enfants de 0 à 6 ans : "
            "EAJE, RPE, LAEP, crèches familiales."
        ),
    },
    "encadrement_direction": {
        "label": "Encadrement et direction",
        "icon": "🏛",
        "description": (
            "Pilotage de structure, coordination d'équipe, "
            "direction administrative et financière."
        ),
    },
    "administratif_communication": {
        "label": "Administratif, financier, communication",
        "icon": "📊",
        "description": (
            "Fonctions support : accueil, secrétariat, comptabilité, "
            "communication, gestion administrative."
        ),
    },
    "services_technique": {
        "label": "Services et technique",
        "icon": "🔧",
        "description": (
            "Maintenance, entretien, restauration, intervention "
            "médicale ou paramédicale."
        ),
    },
}


# Les 25 fiches métiers — identifiants stables, URLs vérifiées
# (slugs alignés sur les noms de fichiers PDF officiels)
_FICHES: list[FicheMetier] = [
    # --- Animation et intervention sociale (6) ---
    {
        "id": "animateur_activites",
        "nom": "Animateur·trice d'activités",
        "famille_id": "animation_intervention",
        "pdf_url": f"{PDF_BASE}/cpnef-fiche-metier-animateur-trice-dactivites-bd.pdf",
        "description": (
            "Conduit des activités d'animation auprès d'un public défini "
            "(enfants, jeunes, adultes, familles)."
        ),
    },
    {
        "id": "animateur",
        "nom": "Animateur·trice",
        "famille_id": "animation_intervention",
        "pdf_url": f"{PDF_BASE}/cpnef-fiche-metier-animateur-trice-bd.pdf",
        "description": (
            "Anime et accompagne un secteur d'activités, met en œuvre "
            "des projets socio-éducatifs ou socioculturels."
        ),
    },
    {
        "id": "intervenant_specialise",
        "nom": "Intervenant·e spécialisé·e",
        "famille_id": "animation_intervention",
        "pdf_url": f"{PDF_BASE}/cpnef-fiche-metier-intervenant-e-specialise-e-bd.pdf",
        "description": (
            "Intervient dans son domaine d'expertise (musique, théâtre, "
            "sport, langue, etc.) auprès des publics."
        ),
    },
    {
        "id": "intervenant_social",
        "nom": "Intervenant·e social·e",
        "famille_id": "animation_intervention",
        "pdf_url": f"{PDF_BASE}/cpnef-fiche-metier-intervenant-e-social-e-bd.pdf",
        "description": (
            "Accompagne individuellement ou collectivement les personnes "
            "dans leurs démarches sociales et éducatives."
        ),
    },
    {
        "id": "charge_projet",
        "nom": "Chargé·e de projet, mission, développement",
        "famille_id": "animation_intervention",
        "pdf_url": f"{PDF_BASE}/cpnef-fiche-metier-charge-e-de-projet-bd.pdf",
        "description": (
            "Pilote un projet ou une mission spécifique : conception, "
            "mise en œuvre, partenariats, évaluation."
        ),
    },
    {
        "id": "referent_secteur",
        "nom": "Référent·e secteur",
        "famille_id": "animation_intervention",
        "pdf_url": f"{PDF_BASE}/cpnef-fiche-metier-referent-e-secteur-bd.pdf",
        "description": (
            "Coordonne un secteur d'activités (enfance, jeunesse, "
            "adultes, familles) et encadre une équipe d'animation."
        ),
    },
    # --- Petite enfance (6) ---
    {
        "id": "animateur_petite_enfance",
        "nom": "Animateur·trice petite enfance",
        "famille_id": "petite_enfance",
        "pdf_url": f"{PDF_BASE}/cpnef-fiche-metier-animateur-trice-petite-enfance-bd.pdf",
        "description": (
            "Accueille et accompagne les enfants de 0 à 6 ans dans un "
            "EAJE (crèche, halte-garderie, multi-accueil)."
        ),
    },
    {
        "id": "auxiliaire_puericulture",
        "nom": "Auxiliaire de puériculture",
        "famille_id": "petite_enfance",
        "pdf_url": f"{PDF_BASE}/cpnef-fiche-metier-auxiliaire-de-puericulture-bd.pdf",
        "description": (
            "Diplômé·e d'État, accompagne les enfants de moins de 3 ans "
            "et soutient les parents au quotidien."
        ),
    },
    {
        "id": "assistant_maternel",
        "nom": "Assistant·e maternel·le en crèche familiale",
        "famille_id": "petite_enfance",
        "pdf_url": f"{PDF_BASE}/cpnef-fiche-metier-assistant-e-maternel-le-en-creche-familiale-bd.pdf",
        "description": (
            "Accueille à son domicile les enfants de la crèche familiale, "
            "agréé·e par les services de PMI."
        ),
    },
    {
        "id": "accueillant_laep",
        "nom": "Accueillant·e LAEP (Lieux d'Accueil Enfants-Parents)",
        "famille_id": "petite_enfance",
        "pdf_url": f"{PDF_BASE}/cpnef-fiche-metier-accueillant-e-laep-lieux-daccueil-enfants-parents-bd.pdf",
        "description": (
            "Accueille parents et jeunes enfants dans un LAEP, soutient "
            "le lien parent-enfant et la fonction parentale."
        ),
    },
    {
        "id": "animateur_rpe",
        "nom": "Animateur·trice RPE (Relais Petite Enfance)",
        "famille_id": "petite_enfance",
        "pdf_url": f"{PDF_BASE}/cpnef-fiche-metier-animateur-trice-relais-bd.pdf",
        "description": (
            "Anime un Relais Petite Enfance : information des parents, "
            "professionnalisation des assistants maternels."
        ),
    },
    {
        "id": "educateur_jeunes_enfants",
        "nom": "Éducateur·trice de jeunes enfants (EJE)",
        "famille_id": "petite_enfance",
        "pdf_url": f"{PDF_BASE}/cpnef-fiche-metier-educateur-trice-de-jeunes-enfants-bd.pdf",
        "description": (
            "Diplômé·e d'État, élabore et met en œuvre le projet éducatif "
            "auprès des enfants de 0 à 7 ans."
        ),
    },
    # --- Encadrement et direction (4) ---
    {
        "id": "responsable_coordinateur",
        "nom": "Responsable, Coordinateur·trice",
        "famille_id": "encadrement_direction",
        "pdf_url": f"{PDF_BASE}/cpnef-fiche-metier-responsable-coordinateur-trice-bd.pdf",
        "description": (
            "Coordonne une équipe ou un secteur d'activités, met en œuvre "
            "le projet de la structure."
        ),
    },
    {
        "id": "rh_administratif_financier",
        "nom": "Directeur·trice RH, administratif et financier",
        "famille_id": "encadrement_direction",
        "pdf_url": f"{PDF_BASE}/cpnef-fiche-metier-rh-administratif-et-financier-bd.pdf",
        "description": (
            "Pilote les fonctions RH, administratives et financières "
            "d'une structure ou d'un réseau."
        ),
    },
    {
        "id": "directeur",
        "nom": "Directeur·rice",
        "famille_id": "encadrement_direction",
        "pdf_url": f"{PDF_BASE}/cpnef-fiche-metier-directeur-bd.pdf",
        "description": (
            "Dirige la structure : projet associatif, gestion, équipe, "
            "partenariats, représentation institutionnelle."
        ),
    },
    {
        "id": "delegue_federal",
        "nom": "Délégué·e fédéral·e",
        "famille_id": "encadrement_direction",
        "pdf_url": f"{PDF_BASE}/cpnef-fiche-metier-delegue-federal-bd.pdf",
        "description": (
            "Anime une fédération territoriale : accompagnement des "
            "structures adhérentes, représentation, développement."
        ),
    },
    # --- Administratif, financier, communication (5) ---
    {
        "id": "charge_accueil",
        "nom": "Chargé·e d'accueil",
        "famille_id": "administratif_communication",
        "pdf_url": f"{PDF_BASE}/cpnef-fiche-metier-charge-e-daccueil-bd.pdf",
        "description": (
            "Accueille, informe et oriente les publics de la structure, "
            "physiquement et par téléphone."
        ),
    },
    {
        "id": "secretaire",
        "nom": "Secrétaire",
        "famille_id": "administratif_communication",
        "pdf_url": f"{PDF_BASE}/cpnef-fiche-metier-secretaire-bd.pdf",
        "description": (
            "Assure le secrétariat courant, la gestion administrative "
            "et le soutien aux équipes."
        ),
    },
    {
        "id": "assistant_direction",
        "nom": "Assistant·e de direction",
        "famille_id": "administratif_communication",
        "pdf_url": f"{PDF_BASE}/cpnef-fiche-metier-assistant-e-de-direction-bd.pdf",
        "description": (
            "Assiste la direction dans la gestion administrative, "
            "le suivi des dossiers et les relations partenariales."
        ),
    },
    {
        "id": "charge_communication",
        "nom": "Chargé·e de communication",
        "famille_id": "administratif_communication",
        "pdf_url": f"{PDF_BASE}/cpnef-fiche-metier-charge-e-de-communication-bd.pdf",
        "description": (
            "Conçoit et met en œuvre la stratégie de communication "
            "interne et externe de la structure."
        ),
    },
    {
        "id": "personnel_admin_financier",
        "nom": "Personnel administratif ou financier",
        "famille_id": "administratif_communication",
        "pdf_url": f"{PDF_BASE}/cpnef-fiche-metier-personnel-administratif-ou-financier-bd.pdf",
        "description": (
            "Assure les fonctions de gestion administrative, comptable, "
            "paie ou financière au sein de la structure."
        ),
    },
    # --- Services et technique (4) ---
    {
        "id": "agent_entretien_service",
        "nom": "Agent·e d'entretien et de service",
        "famille_id": "services_technique",
        "pdf_url": f"{PDF_BASE}/cpnef-fiche-metier-agent-e-dentretien-et-de-service-bd.pdf",
        "description": (
            "Assure l'entretien des locaux, la propreté et le service "
            "(restauration, lingerie selon les structures)."
        ),
    },
    {
        "id": "agent_maintenance",
        "nom": "Agent·e de maintenance",
        "famille_id": "services_technique",
        "pdf_url": f"{PDF_BASE}/cpnef-fiche-metier-agent-e-de-maintenance-bd.pdf",
        "description": (
            "Effectue la maintenance technique des bâtiments, "
            "équipements et matériels de la structure."
        ),
    },
    {
        "id": "cuisinier",
        "nom": "Cuisinier·ère",
        "famille_id": "services_technique",
        "pdf_url": f"{PDF_BASE}/cpnef-fiche-metier-cuisinier-ere-bd.pdf",
        "description": (
            "Prépare les repas dans le respect des règles d'hygiène "
            "et des besoins nutritionnels des publics accueillis."
        ),
    },
    {
        "id": "intervenant_medical",
        "nom": "Intervenant·e médical·e ou paramédical·e",
        "famille_id": "services_technique",
        "pdf_url": f"{PDF_BASE}/cpnef-fiche-metier-intervenant-e-medical-e-ou-paramedical-e-bd.pdf",
        "description": (
            "Médecin, infirmier·ère, psychologue, psychomotricien·ne… "
            "intervient ponctuellement ou régulièrement."
        ),
    },
]


# Documents transverses associés (panorama, brochures, classification)
class DocAnnexe(TypedDict):
    id: str
    label: str
    url: str
    description: str


_DOCS_ANNEXES: list[DocAnnexe] = [
    {
        "id": "panorama_2023",
        "label": "Panorama de la branche ALISFA 2023",
        "url": f"{PDF_BASE}/panorama-2023-version-mise-en-ligne.pdf",
        "description": (
            "Données sociodémographiques, emploi, formation : "
            "photographie complète de la branche."
        ),
    },
    {
        "id": "brochure_cadres",
        "label": "Brochure « Le travail des cadres »",
        "url": f"{PDF_BASE}/cpnef-brochure-travail-des-cadres.pdf",
        "description": (
            "Repères CPNEF sur l'organisation du travail et les "
            "responsabilités des fonctions d'encadrement."
        ),
    },
    {
        "id": "depliant_mixite",
        "label": "Dépliant Mixité et égalité",
        "url": f"{PDF_BASE}/cpnef-depliant-mixite-et-egalite-version-finale.pdf",
        "description": (
            "Outils de la branche pour l'égalité professionnelle "
            "femmes-hommes et la mixité des métiers."
        ),
    },
    {
        "id": "depliant_observatoire",
        "label": "Dépliant Observatoire / Entretien professionnel",
        "url": f"{PDF_BASE}/cpnef-depliant-observatoire-etude-entretien-pro.pdf",
        "description": (
            "Méthode et outils pour l'entretien professionnel "
            "obligatoire tous les 2 ans."
        ),
    },
    {
        "id": "guide_entretien_pro",
        "label": "Guide de l'entretien professionnel",
        "url": f"{PDF_BASE}/guide-de-lentretien-professionnel.pdf",
        "description": (
            "Guide complet pour conduire les entretiens professionnels "
            "et bilans 6 ans (modèles inclus)."
        ),
    },
    {
        "id": "notice_gpec",
        "label": "Notice cartographie GPEC ALISFA",
        "url": f"{PDF_BASE}/notice-cartographie-gpec-alisfa.pdf",
        "description": (
            "Présentation de la cartographie des métiers et des "
            "passerelles de mobilité dans la branche."
        ),
    },
    {
        "id": "flyer_classification",
        "label": "Flyer « Impact classification — synthèse »",
        "url": f"{PDF_BASE}/flyer-cpnef-impact-classification-synthese.pdf",
        "description": (
            "Synthèse pédagogique de la nouvelle classification issue "
            "de l'avenant 10-22."
        ),
    },
]


def list_familles() -> list[FamilleMetier]:
    """Retourne les 5 familles avec leurs fiches métiers."""
    by_famille: dict[str, list[FicheMetier]] = {fid: [] for fid in _FAMILLES}
    for f in _FICHES:
        by_famille[f["famille_id"]].append(f)

    return [
        {
            "id": fid,
            "label": meta["label"],
            "icon": meta["icon"],
            "description": meta["description"],
            "fiches": by_famille[fid],
        }
        for fid, meta in _FAMILLES.items()
    ]


def list_fiches() -> list[FicheMetier]:
    """Retourne les 25 fiches à plat."""
    return list(_FICHES)


def list_docs_annexes() -> list[DocAnnexe]:
    """Retourne les documents transverses (panorama, brochures…)."""
    return list(_DOCS_ANNEXES)
