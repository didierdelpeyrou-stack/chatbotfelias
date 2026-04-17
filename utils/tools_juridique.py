"""
Schémas d'outils (tool_use) Anthropic pour les calculs juridiques déterministes.

Ce module expose :
  - TOOLS_CALCUL : la liste des schémas JSON à passer au paramètre `tools=` de
    client.messages.create(...) quand la fonction juridique_calcul est activée.
  - execute_tool_call(name, tool_input) : le pont vers les calculateurs Python
    purs du module utils.calculs_juridiques.

Le flot côté app.py :
  1. L'utilisateur pose une question impliquant un calcul.
  2. Claude Haiku reçoit le prompt juridique_calcul + la liste TOOLS_CALCUL.
  3. Claude décide d'appeler un ou plusieurs outils → stop_reason == "tool_use".
  4. app.py lit chaque bloc tool_use, appelle execute_tool_call(), et renvoie
     un bloc tool_result à Claude.
  5. Claude reçoit les résultats numériques fiables, les met en forme, rend la
     réponse finale.
"""

import json
from typing import Any

from utils.calculs_juridiques import dispatch_calcul


# ══════════════════════════════════════════════════════════════════════
#  SCHÉMAS TOOL_USE
#  Format Anthropic : https://docs.anthropic.com/en/docs/build-with-claude/tool-use
# ══════════════════════════════════════════════════════════════════════

TOOLS_CALCUL = [
    {
        "name": "calcul_anciennete",
        "description": (
            "Calcule l'ancienneté d'un salarié entre une date d'entrée et une date de "
            "référence (par défaut aujourd'hui). Retourne années, mois, jours et totaux. "
            "À utiliser pour toute question de durée d'engagement, de seuil d'ancienneté, "
            "ou de préalable à un calcul d'indemnité."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "date_debut": {
                    "type": "string",
                    "description": (
                        "Date d'entrée dans l'entreprise, au format ISO (YYYY-MM-DD) ou "
                        "français (DD/MM/YYYY). Exemple : '2018-06-15' ou '15/06/2018'."
                    ),
                },
                "date_fin": {
                    "type": "string",
                    "description": (
                        "Date de référence (optionnel ; défaut = aujourd'hui). "
                        "Mêmes formats acceptés."
                    ),
                },
            },
            "required": ["date_debut"],
        },
    },
    {
        "name": "preavis_licenciement",
        "description": (
            "Calcule la durée du préavis de licenciement applicable, en comparant le "
            "Code du travail (art. L1234-1) et la CCN ALISFA (art. 2.6) et en "
            "retenant la disposition la plus favorable au salarié (principe de faveur L2251-1)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "anciennete_mois": {
                    "type": "integer",
                    "description": (
                        "Ancienneté du salarié en mois. Si tu n'as que l'ancienneté en "
                        "années, convertis-la (années × 12)."
                    ),
                },
                "statut": {
                    "type": "string",
                    "enum": ["employe", "cadre"],
                    "description": (
                        "Statut du salarié : 'employe' (non-cadre) ou 'cadre'. "
                        "Par défaut : 'employe'."
                    ),
                },
            },
            "required": ["anciennete_mois"],
        },
    },
    {
        "name": "indemnite_licenciement",
        "description": (
            "Calcule l'indemnité légale de licenciement selon le barème Code du travail "
            "(art. L1234-9 + R1234-2) : 1/4 de mois par année pour les 10 premières "
            "années, puis 1/3 au-delà. Retourne 0 si ancienneté < 8 mois."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "salaire_mensuel_brut": {
                    "type": "number",
                    "description": (
                        "Salaire mensuel brut de référence en euros. Si le salaire varie, "
                        "retenir soit le 1/12 des 12 derniers mois, soit le 1/3 des 3 "
                        "derniers mois si plus favorable (R1234-4)."
                    ),
                },
                "anciennete_annees": {
                    "type": "number",
                    "description": (
                        "Ancienneté en années (peut être fractionnaire, ex: 7.5 pour "
                        "7 ans et 6 mois)."
                    ),
                },
            },
            "required": ["salaire_mensuel_brut", "anciennete_annees"],
        },
    },
    {
        "name": "salaire_minimum_alisfa",
        "description": (
            "Calcule la rémunération annuelle minimale CCN ALISFA selon l'avenant "
            "n° 10-2022 (applicable au 1er janvier 2024). Formule officielle pour un "
            "temps plein : Rémunération annuelle = SSC + (points pesée × valeur du "
            "point) + (points ancienneté × valeur du point) + (points expérience × "
            "valeur du point). SSC 2024 = 22 100 €/an, valeur du point 2024 = 55 €/an. "
            "Pour un temps partiel, appliquer un prorata via l'ETP. Important : la "
            "CCN ALISFA n'a PAS de prime d'ancienneté distincte — les points "
            "d'ancienneté sont intégrés au salaire minimum hiérarchique."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "points_pesee": {
                    "type": "number",
                    "description": (
                        "Points de pesée du poste selon la grille de classification "
                        "CCN ALISFA (Chapitre XII — Classification, avenant 10-2022)."
                    ),
                },
                "points_anciennete": {
                    "type": "number",
                    "description": (
                        "Points d'ancienneté acquis (optionnel, défaut 0). Barème "
                        "plein temps : 1 point par an la 1ère année, puis selon les "
                        "paliers définis au Chapitre V. Prorata ETP : 1 pt si ETP ≥ "
                        "0,50 ; 0,5 pt si 0,23 ≤ ETP < 0,50 ; 0,25 pt si ETP < 0,23."
                    ),
                },
                "points_experience": {
                    "type": "number",
                    "description": (
                        "Points d'expérience professionnelle (optionnel, défaut 0). "
                        "Valorisation des expériences antérieures pertinentes pour "
                        "le poste occupé."
                    ),
                },
                "ssc_annuel": {
                    "type": "number",
                    "description": (
                        "Salaire de Socle Commun annuel en euros (optionnel ; "
                        "défaut 22 100 € correspondant à la valeur 2024)."
                    ),
                },
                "valeur_point_annuel": {
                    "type": "number",
                    "description": (
                        "Valeur annuelle du point en euros (optionnel ; défaut 55 € "
                        "correspondant à la valeur 2024)."
                    ),
                },
                "etp": {
                    "type": "number",
                    "description": (
                        "Équivalent Temps Plein (défaut 1.0 = temps plein). Pour un "
                        "temps partiel, renseigner la quotité (ex: 0.8 pour 80 %). "
                        "Le prorata est appliqué sur la rémunération annuelle "
                        "temps plein."
                    ),
                },
            },
            "required": ["points_pesee"],
        },
    },
]


# ══════════════════════════════════════════════════════════════════════
#  DISPATCHER TOOL_USE
# ══════════════════════════════════════════════════════════════════════

def execute_tool_call(name: str, tool_input: dict) -> str:
    """Exécute un appel tool_use et renvoie la réponse sérialisée en JSON.

    Args:
        name       : nom du calculateur (doit être dans CALCULATEURS)
        tool_input : kwargs extraits par Claude depuis la question

    Returns:
        JSON string à injecter dans un bloc tool_result.
    """
    result: dict[str, Any] = dispatch_calcul(name, **(tool_input or {}))
    # Sérialisation sans accents perdus, ensure_ascii=False pour lisibilité
    return json.dumps(result, ensure_ascii=False, default=str)
