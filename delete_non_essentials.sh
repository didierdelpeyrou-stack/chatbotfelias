#!/usr/bin/env bash
# Suppression des documents non indispensables de la base de connaissance ELISFA
# Usage :
#   DRY_RUN=1 ./delete_non_essentials.sh    # aperçu sans suppression (défaut)
#   DRY_RUN=0 ./delete_non_essentials.sh    # suppression réelle (vers corbeille locale)
set -euo pipefail

DATA_DIR="$(cd "$(dirname "$0")" && pwd)/data"
ALISFA="$DATA_DIR/alisfa_docs"
CPNEF="$DATA_DIR/cpnef_docs"
DRY_RUN="${DRY_RUN:-1}"
TRASH="$DATA_DIR/.trash_$(date +%Y%m%d_%H%M%S)"

if [ ! -d "$ALISFA" ] || [ ! -d "$CPNEF" ]; then
  echo "❌ Dossiers data introuvables : $ALISFA / $CPNEF" >&2
  exit 1
fi

echo "📁 DATA_DIR = $DATA_DIR"
echo "🧪 DRY_RUN  = $DRY_RUN"
echo

TO_DELETE=()

# WHITELIST (fichiers à NE JAMAIS supprimer, même si un pattern les attrape)
# On matche par nom de fichier (basename), insensible à la casse.
WHITELIST_REGEX='(fiches-metiers|fiche-metier|cpnef-fiche|cpnef-fiches|brochure-dispositifs|brochure-travail|cpnef-brochure|depliant-mixite|rapport-dactivite-cpnef-2025|rapport-dactivite-cpnef\.docx|accord-01-26|guide-pratique-aides|guide-achats-foad|charte-des-formations-multimodales|tableau-des-financements-alisfa-2025|tableau-des-regles-de-financements-alisfa-2025|modalites-et-criteres-de-prise-en-charge|panorama|fiche-metiers-animation|fiche-metiers-petite-enfance|fiches-metiers-encadrement|fiches-metiers-administratif|fiches-metiers-services|fiches-metiers-animation|liste-diplomes-npec|deliberation-determination-des-niveaux|cpnef-flyer-rr|flyer-rr)'

is_whitelisted() {
  local base
  base=$(basename "$1")
  [[ "$base" =~ $WHITELIST_REGEX ]]
}

add_pattern() {
  local dir="$1"; shift
  local label="$1"; shift
  local found=()
  while IFS= read -r -d '' f; do
    if ! is_whitelisted "$f"; then
      found+=("$f")
    fi
  done < <(find "$dir" -maxdepth 1 -type f \( "$@" \) -print0 2>/dev/null)
  echo "  • $label : ${#found[@]} fichiers"
  if [ ${#found[@]} -gt 0 ]; then
    TO_DELETE+=("${found[@]}")
  fi
}

add_exact() {
  local f="$1"
  if [ -f "$f" ] && ! is_whitelisted "$f"; then
    TO_DELETE+=("$f")
  fi
}

echo "=== cpnef_docs/ ==="

echo "[1] Convocations"
add_pattern "$CPNEF" "convocation-*" -iname 'convocation-*'
add_pattern "$CPNEF" "*_convocation*" -iname '*_convocation*'

echo "[2] Ordres du jour (odj)"
add_pattern "$CPNEF" "*ordre-du-jour*" -iname '*ordre-du-jour*'
add_pattern "$CPNEF" "*-odj*" -iname '*-odj*'
add_pattern "$CPNEF" "*_odj*" -iname '*_odj*'
add_pattern "$CPNEF" "*-odj-*" -iname '*-odj-*'

echo "[3] Comptes rendus (CR abrégés et complets)"
add_pattern "$CPNEF" "*compte-rendu*" -iname '*compte-rendu*'
add_pattern "$CPNEF" "cr-*" -iname 'cr-*'
add_pattern "$CPNEF" "*-cr-*" -iname '*-cr-*'
add_pattern "$CPNEF" "*cr-copil*" -iname '*cr-copil*'
add_pattern "$CPNEF" "*cr-gpc*" -iname '*cr-gpc*'
add_pattern "$CPNEF" "*cr-cppni*" -iname '*cr-cppni*'
add_pattern "$CPNEF" "*cr-reunion*" -iname '*cr-reunion*'
add_pattern "$CPNEF" "*projet-cr-*" -iname '*projet-cr-*'
add_pattern "$CPNEF" "*projet-rd-*" -iname '*projet-rd-*'

echo "[4] Doublons (1) (2) (3)"
add_pattern "$CPNEF" "* (1).*" -iname '* (1).*'
add_pattern "$CPNEF" "* (2).*" -iname '* (2).*'
add_pattern "$CPNEF" "* (3).*" -iname '* (3).*'

echo "[5] Mails"
add_pattern "$CPNEF" "*mail*" -iname '*mail*'

echo "[6] Devis / propositions commerciales"
add_pattern "$CPNEF" "*devis*" -iname '*devis*'
add_pattern "$CPNEF" "*proposition-accompagnement*" -iname '*proposition-accompagnement*'

echo "[7] Notes de travail"
add_pattern "$CPNEF" "*note-*" -iname '*note-*'
add_pattern "$CPNEF" "*-note*" -iname '*-note*'

echo "[8] Tableaux suivi / dates d'instances (hors financements)"
add_pattern "$CPNEF" "*tableau-dates*" -iname '*tableau-dates*'
add_pattern "$CPNEF" "*suivi-des-actions*" -iname '*suivi-des-actions*'
add_pattern "$CPNEF" "*suivi-des-orientations*" -iname '*suivi-des-orientations*'
add_pattern "$CPNEF" "*tableau-suivi*" -iname '*tableau-suivi*'
add_pattern "$CPNEF" "*suivi-des-engagements*" -iname '*suivi-des-engagements*'

echo "[9] Supports de réunion / présentations"
add_pattern "$CPNEF" "*support-present*" -iname '*support-present*'
add_pattern "$CPNEF" "*support-presentation*" -iname '*support-presentation*'
add_pattern "$CPNEF" "*-support-*" -iname '*-support-*'
add_pattern "$CPNEF" "support-*" -iname 'support-*'
add_pattern "$CPNEF" "*-presentation-*" -iname '*-presentation-*'
add_pattern "$CPNEF" "presentation-*" -iname 'presentation-*'

echo "[10] Courriers / lettres"
add_pattern "$CPNEF" "courrier-*" -iname 'courrier-*'
add_pattern "$CPNEF" "*-courrier-*" -iname '*-courrier-*'
add_pattern "$CPNEF" "lettre-*" -iname 'lettre-*'
add_pattern "$CPNEF" "*-lettre-*" -iname '*-lettre-*'

echo "[11] Convocations annulées"
add_pattern "$CPNEF" "*annulee*" -iname '*annulee*'

echo "[12] Budget interne"
add_pattern "$CPNEF" "*budget*" -iname '*budget*'

echo "[13] Événementiel WorldSkills / stands / logistique salon"
add_pattern "$CPNEF" "*worldskills*" -iname '*worldskills*'
add_pattern "$CPNEF" "*-stand*" -iname '*-stand*'
add_pattern "$CPNEF" "*stand-*" -iname '*stand-*'
add_pattern "$CPNEF" "*maison-geante*" -iname '*maison-geante*'
add_pattern "$CPNEF" "*palais-des-evenements*" -iname '*palais-des-evenements*'
add_pattern "$CPNEF" "*parc-chanot*" -iname '*parc-chanot*'
add_pattern "$CPNEF" "*bon-de-reservation*" -iname '*bon-de-reservation*'
add_pattern "$CPNEF" "*tarif*" -iname '*tarif*'
add_pattern "$CPNEF" "*guide-de-lexposant*" -iname '*guide-de-lexposant*'
add_pattern "$CPNEF" "*ambassadeurs-metier*" -iname '*ambassadeurs-metier*'
add_pattern "$CPNEF" "*ambassadeurs-metiers*" -iname '*ambassadeurs-metiers*'

echo "[14] Bilans opérationnels / rapports internes (hors rapport d'activité CPNEF)"
add_pattern "$CPNEF" "*-bilan-*" -iname '*-bilan-*'
add_pattern "$CPNEF" "bilan-*" -iname 'bilan-*'
add_pattern "$CPNEF" "*-rapport-*" -iname '*-rapport-*'

echo "[15] Questionnaires, enquêtes, études internes"
add_pattern "$CPNEF" "*questionnaire*" -iname '*questionnaire*'
add_pattern "$CPNEF" "*enquete*" -iname '*enquete*'
add_pattern "$CPNEF" "*quizz*" -iname '*quizz*'
add_pattern "$CPNEF" "*quiz-*" -iname '*quiz-*'

echo "[16] Affiches, visuels, habillage, planches"
add_pattern "$CPNEF" "*affiche*" -iname '*affiche*'
add_pattern "$CPNEF" "*visuel*" -iname '*visuel*'
add_pattern "$CPNEF" "*habillage*" -iname '*habillage*'
add_pattern "$CPNEF" "*planches-video*" -iname '*planches-video*'
add_pattern "$CPNEF" "*plan-2d*" -iname '*plan-2d*'
add_pattern "$CPNEF" "*plan-stand*" -iname '*plan-stand*'

echo "[17] Invitations / convocations externes"
add_pattern "$CPNEF" "invitation-*" -iname 'invitation-*'
add_pattern "$CPNEF" "*-invitation*" -iname '*-invitation*'

echo "[18] Newsletters, trames, recaps"
add_pattern "$CPNEF" "*newsletter*" -iname '*newsletter*'
add_pattern "$CPNEF" "*trame-*" -iname '*trame-*'
add_pattern "$CPNEF" "*-trame-*" -iname '*-trame-*'
add_pattern "$CPNEF" "*recap-*" -iname '*recap-*'
add_pattern "$CPNEF" "*-recap*" -iname '*-recap*'

echo "[19] Fiches de mandat internes"
add_pattern "$CPNEF" "*fiche-mandat*" -iname '*fiche-mandat*'

echo "[20] Documents régionaux / COS / CRF"
add_pattern "$CPNEF" "*cos-pays-*" -iname '*cos-pays-*'
add_pattern "$CPNEF" "*cos-pdl*" -iname '*cos-pdl*'
add_pattern "$CPNEF" "*-crf-*" -iname '*-crf-*'
add_pattern "$CPNEF" "*copil-crf*" -iname '*copil-crf*'
add_pattern "$CPNEF" "*copil-marseille*" -iname '*copil-marseille*'
add_pattern "$CPNEF" "*regional*" -iname '*regional*'
add_pattern "$CPNEF" "*languedoc-roussillon*" -iname '*languedoc-roussillon*'
add_pattern "$CPNEF" "*avenant-paca*" -iname '*avenant-paca*'
add_pattern "$CPNEF" "*avenant-pays-de-la-loire*" -iname '*avenant-pays-de-la-loire*'
add_pattern "$CPNEF" "*avenant-normandie*" -iname '*avenant-normandie*'
add_pattern "$CPNEF" "*gpec-pdc*" -iname '*gpec-pdc*'
add_pattern "$CPNEF" "*nouvelle-aquitaine*" -iname '*nouvelle-aquitaine*'

echo "[21] Plannings, calendriers opérationnels"
add_pattern "$CPNEF" "*planning*" -iname '*planning*'
add_pattern "$CPNEF" "*calendrier-previsionnel*" -iname '*calendrier-previsionnel*'
add_pattern "$CPNEF" "*calendrier-travail*" -iname '*calendrier-travail*'

echo "[22] Benchmark, méthodologies, documents de travail"
add_pattern "$CPNEF" "*benchmark*" -iname '*benchmark*'
add_pattern "$CPNEF" "*methodologie*" -iname '*methodologie*'
add_pattern "$CPNEF" "*doc-de-travail*" -iname '*doc-de-travail*'
add_pattern "$CPNEF" "*reunion-de-cadrage*" -iname '*reunion-de-cadrage*'
add_pattern "$CPNEF" "*cahier-des-charges*" -iname '*cahier-des-charges*'

echo "[23] Plans de communication internes"
add_pattern "$CPNEF" "*plan-de-communication*" -iname '*plan-de-communication*'
add_pattern "$CPNEF" "*plan_de_communication*" -iname '*plan_de_communication*'

echo "[24] Programmes JRR / journées RR"
add_pattern "$CPNEF" "*programme-jrr*" -iname '*programme-jrr*'
add_pattern "$CPNEF" "*programme-des-jrr*" -iname '*programme-des-jrr*'

echo "[25] Cartographies / synthèses / comparatifs internes"
add_pattern "$CPNEF" "*cartographie*" -iname '*cartographie*'
add_pattern "$CPNEF" "*-synthese*" -iname '*-synthese*'
add_pattern "$CPNEF" "synthese-*" -iname 'synthese-*'
add_pattern "$CPNEF" "*comparatif*" -iname '*comparatif*'
add_pattern "$CPNEF" "*consultations-sectorielles*" -iname '*consultations-sectorielles*'

echo "[26] Communiqués presse / motion design"
add_pattern "$CPNEF" "*communique*" -iname '*communique*'
add_pattern "$CPNEF" "*motion-design*" -iname '*motion-design*'

echo "[27] Documents 'etat-de-consommation' (récurrent, ~9 exemplaires)"
add_pattern "$CPNEF" "*etat-de-consommation*" -iname '*etat-de-consommation*'

echo "[28] Documents intermédiaires mentionnés"
add_exact "$CPNEF/doc-11-4-convention-cnam-cpnef-alisfa.docx"
add_exact "$CPNEF/doc-12-4-2025-04-22-cpnef-urnacs-protocole-transactionnel.pdf"
add_exact "$CPNEF/doc-13-2-avenant-cpnef-normandie-2025-2026.doc"
add_exact "$CPNEF/doc-13-2-cpnef-depliant-observatoire-entretien-professionnel.pdf"
add_exact "$CPNEF/doc-7-5-reponses-faq-cpnef.docx"
add_exact "$CPNEF/doc-14-2-liste-questions-faq-cpnef.docx"
add_exact "$CPNEF/doc-5-annexe-actions-orientations-strategiques-2025-2027-valide-en-cpnef.docx"
add_exact "$CPNEF/doc-9-proposition-calendrier-dates-cpnef-2026.pdf"
add_exact "$CPNEF/doc-5-orientations-strategiques-2025-2027-validees-lors-de-la-cppni-du-07-11-2024.docx"
add_exact "$CPNEF/doc-4-suivi-des-orientations-strategiques-doc-au-11-decembre-2025.docx"
add_exact "$CPNEF/doc-5-suivi-des-orientations-strategiques-doc-au-9-octobre-2025.docx"

echo
echo "=== alisfa_docs/ ==="
echo "[A] Formulaire administratif & webinaires ponctuels"
add_exact "$ALISFA/cpnef-alisfa-_formulaire-soutien-colloque-conference-seminaire-2026.docx"
add_exact "$ALISFA/webinaire-cpnef-alisfa-drom-22-janvier-2026.pdf"
add_exact "$ALISFA/webinaire-cpnef-alisfa-employeurs-19-janvier-2026.pdf"
add_exact "$ALISFA/webinaire-cpnef-salaries-20-janvier-2026.pdf"

# Déduplication
UNIQ=$(printf '%s\n' "${TO_DELETE[@]}" | awk 'NF' | sort -u)
TOTAL=$(printf '%s\n' "$UNIQ" | awk 'NF' | wc -l | tr -d ' ')

echo
echo "────────────────────────────────────────"
echo "📊 TOTAL (unique) : $TOTAL fichiers ciblés"
echo "────────────────────────────────────────"

if [ "$DRY_RUN" = "1" ]; then
  echo
  echo "🧪 DRY RUN — aucun fichier supprimé."
  echo "$UNIQ" > /tmp/elisfa_to_delete.txt
  echo "Liste complète écrite dans /tmp/elisfa_to_delete.txt"
  echo "Pour supprimer : DRY_RUN=0 $0"
  exit 0
fi

echo
echo "🗑️  Déplacement vers corbeille : $TRASH"
mkdir -p "$TRASH/alisfa_docs" "$TRASH/cpnef_docs"
COUNT=0
while IFS= read -r f; do
  [ -z "$f" ] && continue
  base=$(basename "$f")
  if [[ "$f" == *"/alisfa_docs/"* ]]; then
    mv -f "$f" "$TRASH/alisfa_docs/$base"
  else
    mv -f "$f" "$TRASH/cpnef_docs/$base"
  fi
  COUNT=$((COUNT+1))
done <<< "$UNIQ"

echo "✅ $COUNT fichiers déplacés vers $TRASH"
echo "   (rien n'est détruit — vérifie puis 'rm -rf' manuellement)"
