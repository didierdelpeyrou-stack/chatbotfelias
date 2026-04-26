"""Profils utilisateur — Sprint 4.6 F1.5 (porté de V1 USER_PROFILES).

Chaque profil :
  - filtre les modules accessibles (gouvernance pas pour les RH/paie pros, etc.)
  - injecte un CONTEXTE dans le system prompt pour adapter le niveau de la
    réponse (vulgarisation pour bénévoles, technique pour pros).

Différence vs MODES (modes.py) :
  - MODE = intention pour UNE question (urgence, analyse, rédaction…)
  - PROFIL = qui est l'utilisateur (président bénévole / directeur pro / RH…)

Les deux sont cumulatifs : un président bénévole en mode urgence reçoit une
réponse vulgarisée + ultra-opérationnelle.
"""
from __future__ import annotations

from typing import Literal, TypedDict

ProfileType = Literal["benevole", "professionnel"]


class ProfileMeta(TypedDict):
    id: str
    icon: str
    name: str
    type: ProfileType
    modules: list[str]
    context: str


PROFILES: dict[str, ProfileMeta] = {
    "benevole_president": {
        "id": "benevole_president",
        "icon": "🏡",
        "name": "Président·e bénévole",
        "type": "benevole",
        "modules": ["juridique", "rh", "gouvernance", "formation"],
        "context": (
            "L'utilisateur est président·e bénévole du conseil d'administration d'une "
            "association ALISFA (centre social, crèche, EVS). Responsable employeur "
            "non professionnel, il/elle a besoin d'explications ACCESSIBLES sur ses "
            "obligations, les risques juridiques, la gestion RH et la gouvernance "
            "associative. Évite le jargon technique pur, donne des exemples concrets, "
            "souligne explicitement les responsabilités personnelles du dirigeant "
            "bénévole et oriente vers les ressources d'accompagnement (DLA, Guid'Asso, "
            "fédération employeur FCSF/ACEPP/FFEC, syndicat ELISFA)."
        ),
    },
    "benevole_bureau": {
        "id": "benevole_bureau",
        "icon": "📋",
        "name": "Membre du bureau / Trésorier·ère",
        "type": "benevole",
        "modules": ["juridique", "gouvernance", "rh"],
        "context": (
            "L'utilisateur est membre bénévole du bureau ou trésorier·ère d'une "
            "association ALISFA. Impliqué·e dans les décisions RH et financières. "
            "Insister sur les IMPACTS BUDGÉTAIRES des décisions sociales, les "
            "obligations légales liées à la fonction employeur et la CCN ALISFA. "
            "Donner des chiffres et ratios quand c'est pertinent."
        ),
    },
    "pro_directeur": {
        "id": "pro_directeur",
        "icon": "💻",
        "name": "Directeur·rice de structure",
        "type": "professionnel",
        "modules": ["juridique", "formation", "rh", "gouvernance"],
        "context": (
            "L'utilisateur est directeur·rice professionnel·le d'une structure ALISFA. "
            "Gère l'équipe, le budget, les relations partenariales. Maîtrise les bases "
            "du droit du travail et de la CCN. A besoin de PRÉCISIONS TECHNIQUES, "
            "de jurisprudence récente et d'aide à la décision sur des cas complexes. "
            "Niveau de détail élevé attendu, citations d'articles précises."
        ),
    },
    "pro_rh": {
        "id": "pro_rh",
        "icon": "👥",
        "name": "Responsable RH / Paie",
        "type": "professionnel",
        "modules": ["juridique", "formation", "rh"],
        "context": (
            "L'utilisateur est responsable RH ou chargé·e de paie d'une structure "
            "ALISFA. Gère contrats, paie, congés, formation, classification, "
            "application quotidienne de la CCN. Réponses TECHNIQUES PRÉCISES "
            "attendues : références aux articles, calculs de salaire détaillés "
            "(SMHB, ancienneté, primes), procédures RH étape par étape. "
            "Cite systématiquement les articles L./R. + article CCN concerné."
        ),
    },
    "pro_admin": {
        "id": "pro_admin",
        "icon": "📈",
        "name": "Responsable admin. & financier",
        "type": "professionnel",
        "modules": ["juridique", "formation", "rh"],
        "context": (
            "L'utilisateur est responsable administratif·ve et financier·ère d'une "
            "structure ALISFA. Supervise gestion financière, budgets, conformité "
            "administrative et obligations sociales. INTÉRESSÉ·E PAR LES COÛTS, "
            "charges, simulations budgétaires liées aux salaires et obligations "
            "employeur. Donner les ordres de grandeur chiffrés (cotisations sociales, "
            "indemnités, plafonds) et l'impact comptable."
        ),
    },
}


def get_profile(profile_id: str | None) -> ProfileMeta | None:
    """Retourne un profil par son id (None si absent ou id invalide)."""
    if not profile_id:
        return None
    return PROFILES.get(profile_id)


def list_profiles() -> list[ProfileMeta]:
    """Retourne la liste des profils disponibles."""
    return list(PROFILES.values())
