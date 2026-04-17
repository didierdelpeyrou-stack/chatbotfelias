"""
Calculs juridiques déterministes — Chatbot ELISFA
==================================================

Ce module regroupe les fonctions de calcul juridique *pures* (pas de LLM,
pas d'I/O réseau). L'objectif : retirer le calcul arithmétique du prompt
pour éviter les erreurs de l'IA.

Architecture :
  LLM → extrait les paramètres de la question → appelle ces fonctions
       ← reformule le résultat humainement ←

Tous les calculs reposent sur :
  - Code du travail (articles L. et R. cités dans chaque docstring)
  - CCN ALISFA IDCC 1261 (les valeurs spécifiques à la branche sont
    concentrées dans la constante CCN_ALISFA pour audit facile)

⚠️ AVERTISSEMENT :
Les coefficients CCN ALISFA ci-dessous sont des VALEURS DE TRAVAIL qui
DOIVENT être validées par le pôle juridique ELISFA avant usage en
production. Ce module fournit la MÉCANIQUE de calcul, pas la donnée de
référence qui doit rester sous la gouvernance du service juridique.

Chaque fonction renvoie un dict structuré :
  {
    "resultat": <valeur principale, ex: 3 pour 3 mois de préavis>,
    "unite": "mois" | "jours" | "euros" | etc.,
    "detail_calcul": "explication pas à pas",
    "base_legale": ["L1234-1", ...],
    "base_ccn": ["art. 2.6 CCN ALISFA", ...],  # optionnel
    "avertissement": "..." ou None,
  }
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Optional


# ══════════════════════════════════════════════════════════════════════
#  CONSTANTES CCN ALISFA IDCC 1261
#  ⚠️ À valider par le pôle juridique ELISFA
# ══════════════════════════════════════════════════════════════════════

# Préavis de licenciement CCN ALISFA (chapitre II, article 2.6 — à confirmer)
# Valeurs plus favorables que le Code du travail (L1234-1).
CCN_PREAVIS_LICENCIEMENT_MOIS = {
    # (anciennete_min_mois, anciennete_max_mois_exclu) : duree_mois
    # Code du travail : <6 mois = usages locaux, 6-24 mois = 1 mois, >=24 mois = 2 mois
    # CCN ALISFA : 2 mois dès 2 ans pour tous (plus favorable = appliqué)
    # TODO VALIDATION : confirmer les seuils < 2 ans
    "employe_avant_2_ans": 1,
    "employe_apres_2_ans": 2,
    "cadre_avant_2_ans": 2,
    "cadre_apres_2_ans": 3,
}

# Valeur du point CCN ALISFA — à mettre à jour à chaque accord de branche.
# Placeholder : valeur indicative, à remplacer par la valeur conventionnelle
# en vigueur à la date du calcul.
CCN_VALEUR_POINT_EUROS = 6.77  # ⚠️ TODO VALIDATION date de l'accord

# Coefficient plancher pour le calcul de l'indemnité de licenciement légale
# (Code du travail L1234-9 + R1234-2)
INDEMNITE_LICENCIEMENT_TAUX_10_PREMIERES_ANNEES = 0.25  # 1/4 de mois par année
INDEMNITE_LICENCIEMENT_TAUX_APRES_10_ANS = 1.0 / 3.0   # 1/3 de mois par année


# ══════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════

def _parse_date(d: Any) -> date:
    """Accepte date, datetime, ou str ISO (YYYY-MM-DD ou DD/MM/YYYY)."""
    if isinstance(d, date) and not isinstance(d, datetime):
        return d
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, str):
        s = d.strip()
        # Formats français courants
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                continue
        raise ValueError(f"Format de date non reconnu : {d!r} (attendu : YYYY-MM-DD ou DD/MM/YYYY)")
    raise TypeError(f"Type de date non supporté : {type(d).__name__}")


@dataclass
class AncienneteResult:
    annees: int
    mois: int
    jours: int
    total_mois: int
    total_jours: int
    date_debut: date
    date_fin: date


# ══════════════════════════════════════════════════════════════════════
#  CALCUL 1 — ANCIENNETÉ
# ══════════════════════════════════════════════════════════════════════

def calcul_anciennete(date_debut: Any, date_fin: Any = None) -> dict:
    """Calcul de l'ancienneté entre deux dates.

    Base légale : Code du travail, L1234-11 (ancienneté des services continus).
    L'ancienneté CCN ALISFA suit la règle commune (continuité des services
    dans la branche, article 2.5 CCN — à confirmer).

    Args:
        date_debut : date d'entrée dans l'entreprise (str ISO ou DD/MM/YYYY,
                     ou objet date/datetime)
        date_fin   : date de référence (défaut : aujourd'hui)

    Returns:
        dict avec résultat structuré.

    Raises:
        ValueError : si date_fin < date_debut ou format invalide.
    """
    debut = _parse_date(date_debut)
    fin = _parse_date(date_fin) if date_fin else date.today()

    if fin < debut:
        raise ValueError(
            f"La date de fin ({fin}) est antérieure à la date de début ({debut}). "
            "Vérifiez l'ordre des dates."
        )

    # Calcul année / mois / jours
    annees = fin.year - debut.year
    mois = fin.month - debut.month
    jours = fin.day - debut.day

    if jours < 0:
        mois -= 1
        # Nombre de jours du mois précédent la date de fin
        if fin.month == 1:
            prev_month_last_day = 31
        else:
            import calendar
            prev_month_last_day = calendar.monthrange(fin.year, fin.month - 1)[1]
        jours += prev_month_last_day

    if mois < 0:
        annees -= 1
        mois += 12

    total_jours = (fin - debut).days
    total_mois = annees * 12 + mois

    return {
        "resultat": annees,
        "unite": "ans",
        "annees": annees,
        "mois": mois,
        "jours": jours,
        "total_mois": total_mois,
        "total_jours": total_jours,
        "date_debut": debut.isoformat(),
        "date_fin": fin.isoformat(),
        "detail_calcul": (
            f"Du {debut.strftime('%d/%m/%Y')} au {fin.strftime('%d/%m/%Y')} : "
            f"{annees} an{'s' if annees > 1 else ''} {mois} mois {jours} jours "
            f"(soit {total_jours} jours au total)."
        ),
        "base_legale": ["Code du travail, art. L1234-11 (ancienneté des services continus)"],
        "base_ccn": ["CCN ALISFA IDCC 1261, art. 2.5 (à valider — continuité des services dans la branche)"],
        "avertissement": (
            "Ne tient pas compte des suspensions du contrat (congé parental > 1 an, "
            "congé sabbatique, arrêt maladie > 30j pour certains calculs). "
            "Pour un calcul d'ancienneté ouvrant droit à indemnité, vérifier au cas par cas."
        ),
    }


# ══════════════════════════════════════════════════════════════════════
#  CALCUL 2 — PRÉAVIS DE LICENCIEMENT
# ══════════════════════════════════════════════════════════════════════

def preavis_licenciement(
    anciennete_mois: int,
    statut: str = "employe",
) -> dict:
    """Durée du préavis de licenciement.

    Base légale :
      - Code du travail art. L1234-1 : < 6 mois = usage local, 6 à 24 mois = 1 mois,
        >= 24 mois = 2 mois
      - CCN ALISFA IDCC 1261 (art. 2.6 — à confirmer) : disposition plus favorable
        applicable en vertu du principe de faveur (L2251-1)

    Args:
        anciennete_mois : ancienneté en mois (entier)
        statut          : "employe" (non-cadre) ou "cadre"

    Returns:
        dict avec la durée retenue + les deux bases (loi + CCN) + le principe de faveur.
    """
    if anciennete_mois < 0:
        raise ValueError("L'ancienneté ne peut pas être négative.")

    statut = statut.lower().strip()
    if statut not in ("employe", "employé", "non-cadre", "cadre"):
        raise ValueError(
            f"Statut inconnu : {statut!r}. Attendu : 'employe' (non-cadre) ou 'cadre'."
        )
    is_cadre = statut == "cadre"

    # Code du travail
    if anciennete_mois < 6:
        preavis_legal = None  # usage local
        legal_note = "Moins de 6 mois d'ancienneté : durée selon usages locaux ou CCN."
    elif anciennete_mois < 24:
        preavis_legal = 1
        legal_note = "6 à 24 mois : 1 mois (art. L1234-1)."
    else:
        preavis_legal = 2
        legal_note = "24 mois et plus : 2 mois (art. L1234-1)."

    # CCN ALISFA
    if is_cadre:
        if anciennete_mois < 24:
            preavis_ccn = CCN_PREAVIS_LICENCIEMENT_MOIS["cadre_avant_2_ans"]
        else:
            preavis_ccn = CCN_PREAVIS_LICENCIEMENT_MOIS["cadre_apres_2_ans"]
    else:
        if anciennete_mois < 24:
            preavis_ccn = CCN_PREAVIS_LICENCIEMENT_MOIS["employe_avant_2_ans"]
        else:
            preavis_ccn = CCN_PREAVIS_LICENCIEMENT_MOIS["employe_apres_2_ans"]

    # Principe de faveur : on retient la disposition la plus favorable au salarié
    # (= la plus longue durée, protégeant le temps de recherche d'emploi)
    if preavis_legal is None:
        preavis_retenu = preavis_ccn
        fondement = "CCN ALISFA (disposition conventionnelle seule applicable)"
    else:
        preavis_retenu = max(preavis_legal, preavis_ccn)
        if preavis_ccn > preavis_legal:
            fondement = "CCN ALISFA (plus favorable au salarié, principe de faveur L2251-1)"
        elif preavis_legal > preavis_ccn:
            fondement = "Code du travail (plus favorable au salarié, principe de faveur L2251-1)"
        else:
            fondement = "Code du travail = CCN ALISFA (durées identiques)"

    return {
        "resultat": preavis_retenu,
        "unite": "mois",
        "preavis_legal_mois": preavis_legal,
        "preavis_ccn_mois": preavis_ccn,
        "statut": "cadre" if is_cadre else "employé / non-cadre",
        "anciennete_mois": anciennete_mois,
        "fondement_retenu": fondement,
        "detail_calcul": (
            f"Ancienneté : {anciennete_mois} mois, statut : {'cadre' if is_cadre else 'non-cadre'}.\n"
            f"• Code du travail : {legal_note}\n"
            f"• CCN ALISFA : {preavis_ccn} mois.\n"
            f"• Retenu : {preavis_retenu} mois ({fondement})."
        ),
        "base_legale": ["Code du travail, art. L1234-1", "L2251-1 (principe de faveur)"],
        "base_ccn": ["CCN ALISFA IDCC 1261, art. 2.6 (à valider)"],
        "avertissement": (
            "Les valeurs CCN ALISFA sont issues de la constante CCN_PREAVIS_LICENCIEMENT_MOIS "
            "du module utils/calculs_juridiques.py. À VALIDER par le pôle juridique avant usage. "
            "En cas de licenciement pour faute grave ou lourde, pas de préavis (L1234-1)."
        ),
    }


# ══════════════════════════════════════════════════════════════════════
#  CALCUL 3 — INDEMNITÉ LÉGALE DE LICENCIEMENT
# ══════════════════════════════════════════════════════════════════════

def indemnite_licenciement(
    salaire_mensuel_brut: float,
    anciennete_annees: float,
) -> dict:
    """Indemnité légale de licenciement (barème minimum).

    Base légale :
      - Code du travail, art. L1234-9 (droit à l'indemnité à partir de 8 mois d'ancienneté ininterrompue)
      - Code du travail, art. R1234-2 (barème : 1/4 de mois par année pour les 10 premières,
        1/3 de mois par année au-delà)

    Args:
        salaire_mensuel_brut : salaire mensuel brut de référence (€)
        anciennete_annees    : ancienneté en années (peut être fractionnaire, ex: 7.5)

    Returns:
        dict avec le montant détaillé.

    Note :
        La CCN ALISFA peut prévoir un barème plus favorable — dans ce cas retenir
        le plus élevé des deux. Cette fonction calcule uniquement le MINIMUM LÉGAL.
    """
    if salaire_mensuel_brut < 0:
        raise ValueError("Le salaire ne peut pas être négatif.")
    if anciennete_annees < 0:
        raise ValueError("L'ancienneté ne peut pas être négative.")

    # Seuil d'éligibilité : 8 mois (L1234-9)
    if anciennete_annees < (8 / 12):
        return {
            "resultat": 0.0,
            "unite": "euros",
            "montant": 0.0,
            "eligible": False,
            "anciennete_annees": anciennete_annees,
            "salaire_mensuel_brut": salaire_mensuel_brut,
            "detail_calcul": (
                f"Ancienneté : {anciennete_annees:.2f} ans (< 8 mois). "
                "Non éligible à l'indemnité légale de licenciement (art. L1234-9)."
            ),
            "base_legale": ["Code du travail, art. L1234-9 (seuil de 8 mois d'ancienneté ininterrompue)"],
            "avertissement": (
                "La CCN ALISFA peut prévoir des règles différentes. "
                "Le licenciement pour faute grave ou lourde ne donne pas droit à cette indemnité."
            ),
        }

    # Calcul : 1/4 de mois pour les 10 premières années, 1/3 au-delà
    if anciennete_annees <= 10:
        montant = salaire_mensuel_brut * INDEMNITE_LICENCIEMENT_TAUX_10_PREMIERES_ANNEES * anciennete_annees
        detail = (
            f"{anciennete_annees:.2f} an(s) × {salaire_mensuel_brut:.2f} € × 1/4 "
            f"= {montant:.2f} €"
        )
    else:
        part_1 = salaire_mensuel_brut * INDEMNITE_LICENCIEMENT_TAUX_10_PREMIERES_ANNEES * 10
        part_2 = salaire_mensuel_brut * INDEMNITE_LICENCIEMENT_TAUX_APRES_10_ANS * (anciennete_annees - 10)
        montant = part_1 + part_2
        detail = (
            f"10 premières années : 10 × {salaire_mensuel_brut:.2f} € × 1/4 = {part_1:.2f} €\n"
            f"Au-delà ({anciennete_annees - 10:.2f} an(s)) : "
            f"{anciennete_annees - 10:.2f} × {salaire_mensuel_brut:.2f} € × 1/3 = {part_2:.2f} €\n"
            f"Total : {montant:.2f} €"
        )

    return {
        "resultat": round(montant, 2),
        "unite": "euros",
        "montant": round(montant, 2),
        "eligible": True,
        "anciennete_annees": anciennete_annees,
        "salaire_mensuel_brut": salaire_mensuel_brut,
        "detail_calcul": detail,
        "base_legale": [
            "Code du travail, art. L1234-9 (droit à indemnité)",
            "Code du travail, art. R1234-2 (barème : 1/4 puis 1/3 de mois par année)",
        ],
        "base_ccn": ["CCN ALISFA IDCC 1261, art. 2.7 (à vérifier si barème plus favorable)"],
        "avertissement": (
            "Ce montant est le MINIMUM LÉGAL. Vérifier si la CCN ALISFA prévoit un barème plus "
            "favorable (dans ce cas, retenir le plus élevé). "
            "Le salaire de référence peut être soit le 1/12 des 12 derniers mois, soit le 1/3 "
            "des 3 derniers mois si plus favorable (R1234-4). "
            "Pas d'indemnité en cas de faute grave ou lourde."
        ),
    }


# ══════════════════════════════════════════════════════════════════════
#  CALCUL 4 — SALAIRE MINIMAL ALISFA (COEFFICIENT × VALEUR DU POINT)
# ══════════════════════════════════════════════════════════════════════

def salaire_minimum_alisfa(
    coefficient: int,
    valeur_point: Optional[float] = None,
) -> dict:
    """Salaire minimum conventionnel ALISFA = coefficient × valeur du point.

    Args:
        coefficient  : coefficient du poste (selon grille CCN ALISFA)
        valeur_point : valeur du point en euros. Si None, utilise la constante
                       CCN_VALEUR_POINT_EUROS du module (à maintenir à jour).

    Returns:
        dict avec le salaire mensuel brut de base.
    """
    if coefficient < 0:
        raise ValueError("Le coefficient ne peut pas être négatif.")

    vp = valeur_point if valeur_point is not None else CCN_VALEUR_POINT_EUROS
    salaire = coefficient * vp

    return {
        "resultat": round(salaire, 2),
        "unite": "euros/mois",
        "salaire_mensuel_brut": round(salaire, 2),
        "coefficient": coefficient,
        "valeur_point": vp,
        "detail_calcul": f"{coefficient} × {vp:.2f} € = {salaire:.2f} € brut/mois",
        "base_ccn": ["CCN ALISFA IDCC 1261, grille des salaires (accord de branche en vigueur)"],
        "avertissement": (
            f"Valeur du point utilisée : {vp:.2f} €. "
            "⚠️ VÉRIFIER qu'elle correspond à l'accord de branche en vigueur à la date du calcul "
            "(les revalorisations annuelles doivent être reportées dans la constante "
            "CCN_VALEUR_POINT_EUROS du module utils/calculs_juridiques.py). "
            "Le salaire réel peut être supérieur via prime d'ancienneté, heures supp, "
            "compléments conventionnels."
        ),
    }


# ══════════════════════════════════════════════════════════════════════
#  DISPATCHER — pour appel depuis tool_use Anthropic
# ══════════════════════════════════════════════════════════════════════

CALCULATEURS = {
    "calcul_anciennete": calcul_anciennete,
    "preavis_licenciement": preavis_licenciement,
    "indemnite_licenciement": indemnite_licenciement,
    "salaire_minimum_alisfa": salaire_minimum_alisfa,
}


def dispatch_calcul(nom: str, **kwargs) -> dict:
    """Appelle le calculateur `nom` avec les kwargs fournis.

    Utilisé par la couche tool_use Anthropic (app.py) pour router
    les appels Claude vers le bon calculateur Python.
    """
    if nom not in CALCULATEURS:
        return {
            "erreur": f"Calculateur inconnu : {nom!r}",
            "disponibles": list(CALCULATEURS.keys()),
        }
    try:
        return CALCULATEURS[nom](**kwargs)
    except (ValueError, TypeError) as e:
        return {
            "erreur": f"{type(e).__name__}: {e}",
            "calculateur": nom,
            "parametres_recus": kwargs,
        }
