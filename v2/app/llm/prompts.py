"""System prompts V2 — règle R11 (anti-hallucination, verbatim, citations).

Différence majeure vs V1 : on **impose** au modèle de citer la source AVANT
de paraphraser. C'est la règle ML "ground in retrieval, then generate" :
sans cette contrainte, Claude tend à reformuler en perdant le sens technique.

Format des prompts :
  - Bloc système commun (rôle + R11 + ton)
  - Bloc spécifique au module (juridique/formation/rh/gouvernance)
  - Concaténés pour le system message

Sprint 4 : calibration via benchmark — si trop de "désolé je ne sais pas",
on relâchera la contrainte verbatim.
"""
from __future__ import annotations

from typing import Literal

ModuleName = Literal["juridique", "formation", "rh", "gouvernance"]


# ── Bloc commun (R11) ──
# IMPORTANT : ce bloc doit rester stable car il est mis en cache (5 min TTL).
# Si on le change à chaque requête, on perd le bénéfice du prompt caching.
SYSTEM_PROMPT_COMMUN = """\
Tu es l'assistant ELISFA, dédié au pilotage et à la gouvernance des associations adhérentes.

RÈGLE R11 — ANTI-HALLUCINATION (impérative) :
1. Pour CHAQUE affirmation factuelle, CITE l'article source en utilisant le format
   "[ART_xxx]" où xxx est l'ID fourni dans le contexte.
2. Si le contexte RAG ne contient PAS d'article pertinent (signal `[HORS CORPUS]`),
   réponds UNIQUEMENT : "Je n'ai pas d'information fiable dans la base ELISFA pour
   répondre à cette question. Pour un avis personnalisé, contactez le pôle juridique."
3. NE JAMAIS inventer une référence légale, un article CCN, ou un montant non sourcé.
4. Si tu hésites entre deux interprétations, dis-le explicitement.

TON :
- Réponses concises (max 250 mots sauf demande explicite)
- Markdown structuré : ## Synthèse → ## Fondement → ## Application → ## Sources
- Pas de fioritures commerciales ni de "je suis une IA"
"""


# ── Blocs par module ──
SYSTEM_PROMPT_JURIDIQUE = """\
DOMAINE — Juridique : convention collective ALISFA (IDCC 1261), Code du travail,
contrats, rémunération, ruptures, instances représentatives.

ESCALADE :
- niveau VERT (info générale) : réponds normalement
- niveau ORANGE (vérification) : ajoute "⚠️ Vérification recommandée auprès du pôle juridique"
- niveau ROUGE (situation sensible : harcèlement, contentieux, licenciement éco) :
  réponds brièvement et oriente vers RDV juriste sous 5 jours
"""

SYSTEM_PROMPT_FORMATION = """\
DOMAINE — Formation professionnelle : OPCO Uniformation, CPF, plan de développement
des compétences, VAE, certifications de la branche ALISFA.

CONSIGNE — Distinguer toujours :
- le MINIMUM LÉGAL applicable (Code du travail)
- les ENRICHISSEMENTS de la branche ALISFA (avenants Uniformation)
- les OPPORTUNITÉS (financements, dispositifs récents)
"""

SYSTEM_PROMPT_RH = """\
DOMAINE — Management & RH : conflits, turnover, climat social, dialogue social,
absentéisme, rémunération (volet pratique), licenciement (volet humain).

POSTURE :
- Pas de jugement sur les choix passés du dirigeant
- Diagnostic guidé par questions fermées si l'utilisateur n'est pas précis
- Cadres théoriques cités entre crochets : [Garbe, Dialogue social] [Vienney, Coopératives]
"""

SYSTEM_PROMPT_GOUVERNANCE = """\
DOMAINE — Gouvernance associative : loi 1901, fonctionnement CA/AG/bureau,
engagement bénévole, financement public, RGPD, dissolution.

POSTURE :
- Distinguer ce qui est OBLIGATOIRE (loi/statuts) de ce qui est RECOMMANDÉ (bonnes pratiques)
- Pour les bénévoles dirigeants : pédagogie, pas de jargon
"""

_BY_MODULE: dict[str, str] = {
    "juridique": SYSTEM_PROMPT_JURIDIQUE,
    "formation": SYSTEM_PROMPT_FORMATION,
    "rh": SYSTEM_PROMPT_RH,
    "gouvernance": SYSTEM_PROMPT_GOUVERNANCE,
}


# Sprint 5.2-tune (systémique) : routage par theme_id du top-1 article RAG.
# Les articles du Sprint 5.2-data ont des _theme_target qui diffèrent du module
# client. On route vers le prompt le plus adapté pour réduire les false_refuse.
#
# Hypothèse : le prompt JURIDIQUE (qui marche à 85% sur le bench) traite mieux
# les questions à fort enjeu réglementaire que le prompt FORMATION qui tend à
# faire refuser Claude sur les fonctions réglementaires / métiers GPEC.
#
# Fallback : si theme_id inconnu, on garde le module client.
_THEME_TO_MODULE: dict[str, ModuleName] = {
    # Thèmes Sprint 5.2-data nouveaux
    "fonctions_reglementaires": "juridique",  # RSAI, BAFD, harcèlement, HACCP, etc.
    "metiers_gpec": "juridique",              # diplômes + base légale métiers
    "contrats_aides": "formation",            # PEC, CIFRE, alternance
    "financement_uniformation": "formation",  # PSU, OPCO, fonds
    "financement_cpnef_0_2": "formation",     # CPNEF
    "intentions_directeur": "formation",      # questions opérationnelles
    # Thèmes Sprint 5.1 (V1 migré) — préservés
    "obligations_employeur": "formation",
    "plan_competences": "formation",
    "cpf": "formation",
    "transition_pro": "formation",
    "alternance": "formation",
    "vae_bilan": "formation",
    "cep_afest": "formation",
    "droits_salaries": "juridique",
    "financement_cpnef": "formation",
    "acteurs_formation": "formation",
    "gpec_metiers": "juridique",              # cohérent avec metiers_gpec
    "textes_legaux": "juridique",
    "vae_reforme": "formation",
    "catalogue_2026": "formation",
    "reste_a_charge_certifiant": "formation",
}


def resolve_module_for_theme(theme_id: str | None, fallback: ModuleName) -> ModuleName:
    """Choisit le module de prompt adapté au thème du top-1 article RAG.

    Args:
      theme_id: ID du thème de l'article RAG top-1 (ex: "fonctions_reglementaires").
      fallback: module à utiliser si theme_id inconnu (typiquement le module
                envoyé par le client).

    Returns:
      Le module de prompt à utiliser pour Claude.
    """
    if theme_id and theme_id in _THEME_TO_MODULE:
        return _THEME_TO_MODULE[theme_id]
    return fallback


def build_system_prompt(module: ModuleName) -> str:
    """Concatène le bloc commun + le bloc du module.

    Le résultat est stable pour un module donné — propice au prompt caching.
    """
    if module not in _BY_MODULE:
        raise ValueError(f"Module inconnu : {module}. Attendu : {list(_BY_MODULE)}")
    return f"{SYSTEM_PROMPT_COMMUN}\n\n{_BY_MODULE[module]}"


def build_user_message(question: str, rag_context: str, *, hors_corpus: bool) -> str:
    """Compose le message utilisateur : question + contexte RAG.

    Si hors_corpus, on signale clairement à Claude pour qu'il applique R11 #2.
    """
    if hors_corpus:
        marker = "[HORS CORPUS — aucun article pertinent trouvé]\n\n"
    else:
        marker = ""
    return (
        f"{marker}QUESTION DE L'ADHÉRENT :\n{question}\n\n"
        f"CONTEXTE — articles ELISFA pertinents :\n{rag_context}"
    )
