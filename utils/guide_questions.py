"""
Banque de questions-pistes (hints) pour le wizard juridique guidé.

⚠️  Distinction importante :
  - `GUIDE_QUESTIONS` dans app.py est un FORMULAIRE STRUCTURÉ (champs typés
    avec options, placeholders, input) utilisé par le formulaire email-juriste.
  - `WIZARD_HINTS_JURIDIQUE` ci-dessous est une BANQUE DE RELANCES
    méthodologiques (listes de strings cliquables) utilisée par l'étape
    « Les faits » du wizard juridique pour aider l'utilisateur à cadrer
    la rédaction de son cas.

Les deux sont complémentaires :
  - Formulaire → saisie structurée orientée production d'un email au juriste.
  - Hints → relances ouvertes orientées rédaction libre du cas dans le wizard.

Les clés du dict DOIVENT correspondre exactement aux `options` de l'étape
`theme` du wizard juridique (templates/index.html, WIZARDS.juridique.steps).
"""

from typing import Dict, List


WIZARD_HINTS_JURIDIQUE: Dict[str, List[str]] = {
    "Discipline / sanction": [
        "Quels faits précis, datés et circonstanciés reprochez-vous au salarié ?",
        "Quand en avez-vous eu connaissance (point de départ du délai de 2 mois, art. L1332-4) ?",
        "Avez-vous des écrits probants (mails, CR, témoignages nominatifs) ?",
        "Y a-t-il des antécédents disciplinaires dans le dossier du salarié ?",
        "Le salarié bénéficie-t-il d'un statut protégé (RP, maternité, AT-MP) ?",
        "Quelle sanction envisagez-vous et pourquoi celle-ci et pas une autre ?",
    ],
    "Rupture du contrat": [
        "Quel motif de rupture invoquez-vous (personnel, économique, RC individuelle) ?",
        "Quelle est l'ancienneté et le statut (cadre / non-cadre) du salarié ?",
        "La procédure préalable a-t-elle été respectée (convocation, délai, entretien) ?",
        "Quels documents de fin de contrat devez-vous remettre (STC, certificat, attestation France Travail) ?",
        "Le salarié est-il en arrêt, en congés, protégé (RP, maternité, AT-MP) ?",
        "Quel préavis et quelle indemnité de licenciement avez-vous calculés ?",
    ],
    "Inaptitude / santé au travail": [
        "L'avis d'inaptitude est-il définitif, et mentionne-t-il une dispense de reclassement ?",
        "L'inaptitude est-elle d'origine professionnelle (AT-MP) ou non professionnelle ?",
        "Quelles recherches de reclassement avez-vous effectuées (écrits, propositions, refus) ?",
        "Le CSE a-t-il été consulté sur les propositions de reclassement (art. L1226-10) ?",
        "Dans quel délai d'un mois après avis se situe-t-on (reprise de salaire : L1226-4) ?",
        "Le médecin du travail a-t-il été associé à la recherche de postes compatibles ?",
    ],
    "Temps de travail / congés": [
        "Quelle est la durée contractuelle de travail (temps plein, partiel, forfait jours) ?",
        "Sur quel accord d'entreprise ou CCN ALISFA vous appuyez-vous (chap. II) ?",
        "Quel est le compteur d'heures supplémentaires / complémentaires à ce jour ?",
        "Les salariés ont-ils des badgeages, feuilles de temps, ordres de mission ?",
        "Qui décide de la pose des congés : employeur, salarié, accord ?",
        "Un décompte annuel / pluriannuel est-il en place (annualisation, modulation) ?",
    ],
    "Rémunération / classification": [
        "Quel est le coefficient CCN ALISFA actuellement appliqué au salarié ?",
        "Quelle est la valeur du point en vigueur dans votre structure (dernière MAJ) ?",
        "Le salaire actuel est-il au minimum conventionnel (coeff × valeur point) ?",
        "Quelles primes et sujétions s'appliquent (encadrement, dimanche, nuit) ?",
        "Les bulletins de paie mentionnent-ils clairement la CCN 1261 et le coefficient ?",
        "Un changement de classification est-il envisagé (promotion, nouveau poste) ?",
    ],
    "CSE / représentants": [
        "Quel est votre effectif ETP sur les 12 derniers mois (seuil des 11) ?",
        "Les élections CSE ont-elles été organisées dans les délais légaux ?",
        "Quels sujets relèvent d'une information, d'une consultation, d'une négociation ?",
        "Des heures de délégation sont-elles prises et comptabilisées correctement ?",
        "Des réunions périodiques du CSE ont-elles lieu (ordre du jour, PV) ?",
        "Un représentant est-il protégé et de quel type de protection relève-t-il ?",
    ],
    "Modification du contrat": [
        "S'agit-il d'une modification du contrat (avenant requis) ou des conditions de travail (pouvoir de direction) ?",
        "Quel élément change : rémunération, durée, lieu, fonctions, horaires ?",
        "Le contrat contient-il une clause de mobilité / de variabilité d'horaires valide ?",
        "Quel délai de réflexion donnez-vous au salarié pour se prononcer ?",
        "Quelles conséquences en cas de refus du salarié (maintien / rupture) ?",
        "La modification est-elle motivée par un motif économique (procédure L1222-6) ?",
    ],
    "Contentieux Prud\u2019hommes": [
        "Quelle est la date précise de saisine du Conseil de prud'hommes ?",
        "Sur quels griefs le salarié fonde-t-il sa demande (licenciement, rappels, dommages) ?",
        "Quel est le montant total des demandes chiffrées ?",
        "Disposez-vous déjà d'un conseil (avocat, défenseur syndical employeur) ?",
        "Une tentative de conciliation a-t-elle échoué et à quelle date ?",
        "Quelles pièces adverses avez-vous reçues, et lesquelles vous manquent pour défendre ?",
    ],
    "Autre": [
        "Pouvez-vous qualifier plus précisément la catégorie juridique en jeu ?",
        "À quel article du Code du travail ou de la CCN ALISFA pensez-vous spontanément ?",
        "Quelle est l'échéance ou le délai qui motive votre question ?",
        "Qui sont les personnes concernées (salariés, représentants, tiers) ?",
        "Quelles pièces écrites sont déjà constituées dans le dossier ?",
        "Quelle issue recherchez-vous : conseil, décision, rédaction, action ?",
    ],
}


def get_wizard_hints(theme: str) -> List[str]:
    """Retourne la liste de questions-pistes pour un thème donné.

    Args:
        theme : libellé exact tel qu'utilisé par le wizard juridique.

    Returns:
        Liste de questions (strings). Liste vide si thème inconnu.
    """
    return WIZARD_HINTS_JURIDIQUE.get(theme, [])


def list_themes() -> List[str]:
    """Retourne la liste des thèmes disponibles."""
    return list(WIZARD_HINTS_JURIDIQUE.keys())
