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

# ══════════════════════════════════════════════════════════════════════
#  CCN ALISFA — AVENANT 10-2022 (applicable depuis le 1er janvier 2024)
# ══════════════════════════════════════════════════════════════════════
# La CCN ALISFA NE FONCTIONNE PLUS en coefficient × valeur du point.
# Depuis l'avenant 10-2022, le salaire minimum se compose ANNUELLEMENT de :
#
#   Rémunération annuelle brute =
#       SSC                                        (salaire socle conventionnel)
#     + points_pesée       × valeur_point         (classification de l'emploi)
#     + points_ancienneté  × valeur_point         (ancienneté dans la branche)
#     + points_expérience  × valeur_point         (expérience professionnelle)
#
# Puis : salaire mensuel = rémunération annuelle / 12
# Puis : prorata temps partiel = salaire × (heures contractuelles × 12 / 1820)
#
# Source : Avenant n° 10-2022 du 6 décembre 2022 à la CCN ALISFA (IDCC 1261),
#          Chapitre V (rémunération) + Annexes 3, 4, 5 (pesée des emplois).
#
# Les valeurs ci-dessous sont celles de 2024 (SSC + valeur du point). Les
# projections 2025-2027 évoquées dans la base de connaissances ne sont pas
# répliquées ici tant qu'elles n'ont pas été validées par le pôle juridique
# ELISFA sur la base d'un avenant salarial daté.

# Valeur annuelle du point CCN ALISFA au 1er janvier 2024 (avenant 10-2022).
# Une valeur du point CCN ALISFA est une valeur ANNUELLE (pas mensuelle).
CCN_VALEUR_POINT_ANNUEL_EUROS = 55.0  # ⚠️ À actualiser à chaque avenant salarial

# Salaire Socle Conventionnel annuel brut au 1er janvier 2024 (avenant 10-2022).
# Correspond au positionnement au niveau 1 de tous les critères classants.
CCN_SSC_ANNUEL_EUROS_2024 = 22_100.0  # ⚠️ À actualiser à chaque avenant salarial

# Heures annuelles CCN ALISFA (base temps plein). Utilisé pour le prorata
# temps partiel : (heures_contractuelles_mois × 12) / 1820.
CCN_HEURES_ANNUELLES_TEMPS_PLEIN = 1820

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
#  CALCUL 4 — SALAIRE MINIMUM HIÉRARCHIQUE ALISFA (AVENANT 10-2022)
# ══════════════════════════════════════════════════════════════════════

def salaire_minimum_alisfa(
    points_pesee: float,
    points_anciennete: float = 0,
    points_experience: float = 0,
    ssc_annuel: Optional[float] = None,
    valeur_point_annuel: Optional[float] = None,
    etp: float = 1.0,
) -> dict:
    """Salaire minimum hiérarchique CCN ALISFA (avenant 10-2022, applicable 2024).

    Formule officielle :
        Rémunération annuelle brute =
            SSC
          + points_pesée       × valeur_point
          + points_ancienneté  × valeur_point
          + points_expérience  × valeur_point

    Puis salaire mensuel = (rémunération annuelle × ETP) / 12.

    Args:
        points_pesee        : points issus de la pesée de l'emploi sur les
                              8 critères classants (hors SSC). Ex : 150.
        points_anciennete   : points d'ancienneté de branche (1 pt/an pour
                              ≥ 0,50 ETP ; 0,5 pt/an pour 0,23–0,50 ETP ;
                              0,25 pt/an pour < 0,23 ETP). Défaut : 0.
        points_experience   : points d'expérience professionnelle (cycle
                              d'évaluation de 24 mois). Défaut : 0.
        ssc_annuel          : Salaire Socle Conventionnel annuel en euros.
                              Défaut : CCN_SSC_ANNUEL_EUROS_2024 (22 100 €).
        valeur_point_annuel : valeur annuelle du point en euros.
                              Défaut : CCN_VALEUR_POINT_ANNUEL_EUROS (55 €).
        etp                 : équivalent temps plein (0 < ETP ≤ 1.0) pour
                              proratiser un temps partiel. Défaut : 1.0.

    Returns:
        dict avec la rémunération annuelle et mensuelle brutes.

    Raises:
        ValueError : paramètre hors bornes (négatif, ETP hors ]0, 1]).
    """
    # Validations
    for nom, val in (
        ("points_pesee", points_pesee),
        ("points_anciennete", points_anciennete),
        ("points_experience", points_experience),
    ):
        if val < 0:
            raise ValueError(f"{nom} ne peut pas être négatif (reçu : {val}).")
    if not (0 < etp <= 1.0):
        raise ValueError(f"L'ETP doit être dans ]0, 1] (reçu : {etp}).")

    ssc = ssc_annuel if ssc_annuel is not None else CCN_SSC_ANNUEL_EUROS_2024
    vp = valeur_point_annuel if valeur_point_annuel is not None else CCN_VALEUR_POINT_ANNUEL_EUROS

    if ssc < 0:
        raise ValueError(f"Le SSC ne peut pas être négatif (reçu : {ssc}).")
    if vp < 0:
        raise ValueError(f"La valeur du point ne peut pas être négative (reçu : {vp}).")

    # Calcul
    remuneration_pesee = points_pesee * vp
    remuneration_anciennete = points_anciennete * vp
    remuneration_experience = points_experience * vp
    remuneration_annuelle_tp = ssc + remuneration_pesee + remuneration_anciennete + remuneration_experience
    remuneration_annuelle = remuneration_annuelle_tp * etp
    remuneration_mensuelle = remuneration_annuelle / 12

    detail_lines = [
        f"SSC : {ssc:.2f} €",
        f"+ Pesée : {points_pesee:g} pts × {vp:.2f} € = {remuneration_pesee:.2f} €",
    ]
    if points_anciennete:
        detail_lines.append(
            f"+ Ancienneté : {points_anciennete:g} pts × {vp:.2f} € = {remuneration_anciennete:.2f} €"
        )
    if points_experience:
        detail_lines.append(
            f"+ Expérience : {points_experience:g} pts × {vp:.2f} € = {remuneration_experience:.2f} €"
        )
    detail_lines.append(
        f"= Rémunération annuelle temps plein : {remuneration_annuelle_tp:.2f} €"
    )
    if etp < 1.0:
        detail_lines.append(
            f"× ETP {etp:g} = Rémunération annuelle : {remuneration_annuelle:.2f} €"
        )
    detail_lines.append(
        f"/ 12 = Rémunération mensuelle : {remuneration_mensuelle:.2f} €"
    )

    return {
        "resultat": round(remuneration_mensuelle, 2),
        "unite": "euros/mois",
        "salaire_mensuel_brut": round(remuneration_mensuelle, 2),
        "salaire_annuel_brut": round(remuneration_annuelle, 2),
        "remuneration_annuelle_temps_plein": round(remuneration_annuelle_tp, 2),
        "points_pesee": points_pesee,
        "points_anciennete": points_anciennete,
        "points_experience": points_experience,
        "ssc_annuel": ssc,
        "valeur_point_annuel": vp,
        "etp": etp,
        "detail_calcul": "\n".join(detail_lines),
        "base_ccn": [
            "Avenant n° 10-2022 du 6 décembre 2022 — Chapitre V (rémunération)",
            "CCN ALISFA IDCC 1261 — grille des salaires en vigueur",
        ],
        "avertissement": (
            f"Valeurs utilisées : SSC {ssc:.2f} €/an, valeur du point {vp:.2f} €/an. "
            "⚠️ VÉRIFIER qu'elles correspondent à l'avenant salarial en vigueur à la "
            "date du calcul (à actualiser dans CCN_SSC_ANNUEL_EUROS_2024 et "
            "CCN_VALEUR_POINT_ANNUEL_EUROS de utils/calculs_juridiques.py à chaque "
            "nouvel avenant). La CCN ALISFA ne prévoit pas de « prime d'ancienneté » "
            "distincte — l'ancienneté est valorisée par des points intégrés au salaire "
            "minimum hiérarchique. Le salaire réel peut être supérieur via heures supp "
            "ou compléments conventionnels locaux."
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
