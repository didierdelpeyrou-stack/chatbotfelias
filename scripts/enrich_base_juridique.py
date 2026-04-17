#!/usr/bin/env python3
"""
Enrichit base_juridique.json avec les avenants 2024-2025 officiels
récupérés lors du scraping public d'alisfa.fr.

Ajouts :
  - av-07 : Avenant 05-24 « Emploi des personnes en situation de handicap »
            + Avenant n° 01 à l'avenant 05-24 (12 février 2025) — champ d'application.
  - av-08 : Avenants 2025 — 01-25 complémentaire santé, 02-25 prévoyance.

Met également à jour av-05 pour référencer les nouveaux avenants santé/prévoyance 2025.

Sauvegarde base_juridique.json.bak avant modif.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "base_juridique.json"
BAK = ROOT / "data" / "base_juridique.json.bak"

LEGIFRANCE_CCN = "https://www.legifrance.gouv.fr/conv_coll/id/KALICONT000005635384"
ALISFA_AVENANTS = "https://www.alisfa.fr/comprendre-la-ccn/"


NEW_ARTICLES = [
    {
        "id": "av-07",
        "question_type": "Qu'est-ce que l'avenant 05-24 et son avenant 01 de 2025 sur l'emploi des personnes en situation de handicap ?",
        "mots_cles": [
            "avenant 05-24",
            "avenant 01-25 handicap",
            "handicap",
            "travailleur handicapé",
            "RQTH",
            "maintien dans l'emploi",
            "AGEFIPH",
            "OETH",
            "obligation emploi",
            "accessibilité",
            "insertion",
            "situation de handicap",
            "chapitre handicap",
        ],
        "reponse": {
            "synthese": "L'avenant 05-24 crée un dispositif conventionnel dédié à l'emploi et au maintien dans l'emploi des personnes en situation de handicap dans la branche ALISFA. Il est complété par l'avenant n° 01 à l'avenant 05-24, signé le 12 février 2025, qui ajoute un article « Champ d'application » précisant que le dispositif s'applique à toutes les entreprises de la branche, quel que soit leur effectif (pas de disposition dérogatoire pour les entreprises de moins de 50 salariés).",
            "fondement_legal": "Loi n° 87-517 du 10 juillet 1987 (obligation d'emploi de 6 % de travailleurs handicapés — OETH). Articles L5212-1 à L5212-17 du Code du travail. Loi n° 2005-102 du 11 février 2005 pour l'égalité des droits et des chances. Loi « Avenir professionnel » du 5 septembre 2018 (réforme OETH). Article L2261-23-1 C. trav. (dispositions spécifiques entreprises < 50 salariés).",
            "fondement_ccn": "Avenant 05-24 à la CCN ALISFA (IDCC 1261) — Emploi des personnes en situation de handicap. Avenant n° 01 à l'avenant 05-24 du 12 février 2025 — ajout d'un article 10 « Champ d'application » motivé par le fait que la branche est majoritairement composée d'entreprises de moins de 50 salariés et que le thème du handicap ne peut donner lieu à des stipulations différenciées selon l'effectif.",
            "application": "Toute structure de la branche ALISFA doit appliquer les dispositions de l'avenant 05-24 indépendamment de son effectif. Les employeurs doivent : (1) recenser les bénéficiaires de l'obligation d'emploi (BOETH), (2) déclarer annuellement (DOETH) via la DSN, (3) aménager les postes et les conditions de travail pour les salariés RQTH, (4) mobiliser les aides AGEFIPH/Cap Emploi pour l'insertion et le maintien dans l'emploi.",
            "vigilance": "L'avenant 01 de 2025 est conclu pour une durée déterminée de 3 ans. Il entre en vigueur au 1er jour du mois suivant la publication de son arrêté d'extension au Journal officiel — vérifier la date d'extension effective avant application. Le non-respect de l'OETH expose à une contribution AGEFIPH majorée.",
            "sources": [
                "Avenant 05-24 à la CCN ALISFA (IDCC 1261)",
                "Avenant n° 01 à l'avenant 05-24 du 12 février 2025",
                "Art. L5212-1 à L5212-17 C. trav.",
                "Loi n° 2005-102 du 11 février 2005",
            ],
            "liens": [
                {"titre": "CCN ALISFA (IDCC 1261) — Legifrance", "url": LEGIFRANCE_CCN},
                {"titre": "AGEFIPH — accompagnement OETH", "url": "https://www.agefiph.fr/"},
                {"titre": "Comprendre la CCN — ALISFA", "url": ALISFA_AVENANTS},
            ],
        },
        "fiches_pratiques": [],
    },
    {
        "id": "av-08",
        "question_type": "Quels sont les avenants 2025 sur la complémentaire santé et la prévoyance ALISFA ?",
        "mots_cles": [
            "avenant 01-25",
            "avenant 02-25",
            "complémentaire santé 2025",
            "prévoyance 2025",
            "frais santé",
            "mutuelle",
            "cotisation mutuelle",
            "garanties",
            "100% santé",
            "invalidité",
            "décès",
            "incapacité",
            "maintien de salaire",
            "avenant santé",
        ],
        "reponse": {
            "synthese": "La branche ALISFA a signé en 2025 deux nouveaux avenants sur la protection sociale : l'avenant n° 01-25 relatif à la complémentaire santé (frais de santé) et l'avenant n° 02-25 relatif au régime de prévoyance (incapacité, invalidité, décès). Ces avenants actualisent le régime mutualisé de branche en tenant compte de l'évolution du 100 % santé, des équilibres techniques des organismes assureurs et de la sinistralité observée.",
            "fondement_legal": "Article L911-1 du Code de la sécurité sociale (garanties collectives). ANI du 11 janvier 2013 et loi du 14 juin 2013 (généralisation de la complémentaire santé). Articles L2261-15 et L2261-24 C. trav. (procédure d'extension). Réforme 100 % santé — décret n° 2019-21 du 11 janvier 2019.",
            "fondement_ccn": "Avenant n° 01-25 du 2025 (complémentaire santé) et avenant n° 02-25 du 2025 (prévoyance) à la CCN ALISFA (IDCC 1261). S'inscrivent dans la continuité des avenants 02-15, 03-17, 06-18, 04-19, 06-20 et 07-22. Signés entre ELISFA et les organisations syndicales représentatives de la branche.",
            "application": "Les nouveaux avenants s'imposent à toutes les entreprises de la branche dès leur extension par arrêté ministériel (application obligatoire). Les employeurs doivent : (1) informer les salariés et les représentants du personnel, (2) actualiser la DUE ou l'accord d'entreprise si nécessaire, (3) mettre à jour les bulletins de paie (nouvelles cotisations), (4) respecter la part patronale minimale de 50 % de la cotisation isolée santé.",
            "vigilance": "Les textes intégraux des avenants 01-25 et 02-25 doivent être consultés directement sur le site ALISFA ou Legifrance après publication de l'arrêté d'extension. Vérifier les dates d'entrée en vigueur, l'évolution des cotisations et les nouveaux plafonds de garantie. Le non-respect de l'obligation d'affiliation expose à un redressement URSSAF.",
            "sources": [
                "Avenant n° 01-25 à la CCN ALISFA — complémentaire santé",
                "Avenant n° 02-25 à la CCN ALISFA — prévoyance",
                "Art. L911-1 CSS",
                "CCN ALISFA (IDCC 1261)",
            ],
            "liens": [
                {"titre": "CCN ALISFA (IDCC 1261) — Legifrance", "url": LEGIFRANCE_CCN},
                {"titre": "Comprendre la CCN — ALISFA", "url": ALISFA_AVENANTS},
                {"titre": "Code de la Sécurité sociale", "url": "https://www.legifrance.gouv.fr/codes/id/LEGITEXT000006073189/"},
            ],
        },
        "fiches_pratiques": [],
    },
]


def main() -> int:
    data = json.loads(SRC.read_text(encoding="utf-8"))
    shutil.copy(SRC, BAK)

    themes = data["themes"]
    avenants_theme = next(t for t in themes if t["id"] == "avenants")
    existing_ids = {a["id"] for a in avenants_theme["articles"]}

    added = 0
    for art in NEW_ARTICLES:
        if art["id"] in existing_ids:
            print(f"  ⏭  déjà présent : {art['id']}")
            continue
        avenants_theme["articles"].append(art)
        added += 1
        print(f"  ✅ ajouté : {art['id']} — {art['question_type'][:70]}")

    # Update av-05 sources to mention 2025 avenants
    av05 = next((a for a in avenants_theme["articles"] if a["id"] == "av-05"), None)
    if av05:
        for ref in ("Avenant 01-25 (complémentaire santé)", "Avenant 02-25 (prévoyance)"):
            if ref not in av05["reponse"]["sources"]:
                av05["reponse"]["sources"].append(ref)
        for kw in ("01-25", "02-25", "2025"):
            if kw not in av05["mots_cles"]:
                av05["mots_cles"].append(kw)

    # Update metadata
    data["metadata"]["date_consolidation"] = "2026-04-14"
    data["metadata"].setdefault("enrichissements", []).append(
        {
            "date": "2026-04-14",
            "source": "Scraping public alisfa.fr (189 PDFs, sitemap Yoast)",
            "ajouts": [a["id"] for a in NEW_ARTICLES],
            "note": "Avenants 2024-2025 : 05-24 handicap + son avenant 01, 01-25 santé, 02-25 prévoyance.",
        }
    )

    SRC.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{added} article(s) ajouté(s). Sauvegarde : {BAK}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
