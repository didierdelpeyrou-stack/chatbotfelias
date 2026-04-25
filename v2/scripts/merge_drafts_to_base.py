"""Sprint 5.2-merge — Fusion des 95 KB drafts vers data/v2/base_formation.json.

Lit tous les fichiers `v2/scripts/kb_drafts/sprint52_*.json`, regroupe les
articles par leur champ `_theme_target`, ajoute les 6 nouveaux thèmes
(ou agrandit ceux existants), met à jour la métadata, et écrit le
nouveau `base_formation.json`.

Mode dry-run par défaut : ne touche au fichier que si --write est passé.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DRAFTS_DIR = ROOT / "v2" / "scripts" / "kb_drafts"
BASE_FORMATION = ROOT / "data" / "v2" / "base_formation.json"

# Mapping _theme_target draft -> theme cible dans base_formation.json
# Si le thème existe déjà, on agrandit ; sinon on en crée un nouveau.
THEME_MAPPING = {
    "financement_uniformation": {
        "id": "financement_uniformation",
        "label": "Financement Uniformation (fonds légaux + conventionnels ALISFA)",
        "chapitre": "Financements",
    },
    "financement_cpnef_0_2": {
        "id": "financement_cpnef_0_2",
        "label": "Financement CPNEF 0,2% (gestion directe branche ALISFA)",
        "chapitre": "Financements",
    },
    "metiers_gpec": {
        "id": "metiers_gpec",
        "label": "Métiers GPEC ALISFA — répertoire des fiches",
        "chapitre": "Métiers et compétences",
    },
    "fonctions_reglementaires": {
        "id": "fonctions_reglementaires",
        "label": "Fonctions réglementaires (RSAI, direction ACM, référents CAF, métiers sociaux, santé/sécurité)",
        "chapitre": "Cadre réglementaire",
    },
    "contrats_aides": {
        "id": "contrats_aides",
        "label": "Contrats aidés (apprentissage, professionnalisation, PEC, CIFRE)",
        "chapitre": "Contrats en alternance",
    },
    "intentions_directeur": {
        "id": "intentions_directeur",
        "label": "Questions opérationnelles directeur·trice (budget, recrutement, situations RH)",
        "chapitre": "Pilotage et gestion",
    },
}


def load_drafts() -> dict[str, list[dict]]:
    """Lit tous les drafts, retourne {theme_target: [articles]}."""
    by_theme: dict[str, list[dict]] = defaultdict(list)
    for path in sorted(DRAFTS_DIR.glob("sprint52_*.json")):
        data = json.loads(path.read_text())
        articles = data.get("articles") or data.get("demo_articles") or []
        for art in articles:
            theme = art.get("_theme_target")
            if not theme:
                print(f"  ⚠️  {path.name} :: {art.get('id')} sans _theme_target", file=sys.stderr)
                continue
            by_theme[theme].append(art)
    return by_theme


def merge(by_theme: dict[str, list[dict]], base: dict) -> tuple[dict, dict[str, int]]:
    """Fusionne les drafts dans la base. Retourne (base modifiée, stats)."""
    existing_ids = set()
    existing_themes_by_id = {t["id"]: t for t in base["themes"]}
    for theme in base["themes"]:
        for art in theme.get("articles", []):
            existing_ids.add(art["id"])

    stats: dict[str, int] = {}
    for theme_target, articles in by_theme.items():
        if theme_target not in THEME_MAPPING:
            print(f"  ⚠️  thème inconnu : {theme_target}", file=sys.stderr)
            continue

        theme_meta = THEME_MAPPING[theme_target]
        target_id = theme_meta["id"]

        # Filtrer collisions
        new_articles = []
        for art in articles:
            if art["id"] in existing_ids:
                print(f"  ⚠️  collision id={art['id']} déjà dans la base — skip", file=sys.stderr)
                continue
            new_articles.append(art)
            existing_ids.add(art["id"])

        if target_id in existing_themes_by_id:
            target_theme = existing_themes_by_id[target_id]
            target_theme.setdefault("articles", []).extend(new_articles)
            stats[target_id] = stats.get(target_id, 0) + len(new_articles)
        else:
            new_theme = {
                "id": theme_meta["id"],
                "label": theme_meta["label"],
                "chapitre": theme_meta["chapitre"],
                "articles": new_articles,
            }
            base["themes"].append(new_theme)
            existing_themes_by_id[target_id] = new_theme
            stats[target_id] = len(new_articles)

    return base, stats


def update_metadata(base: dict, stats: dict[str, int]) -> None:
    today = date.today().isoformat()
    md = base.setdefault("metadata", {})
    md["date_consolidation"] = today
    enrichissements = md.setdefault("enrichissements", [])
    enrichissements.append({
        "date": today,
        "source": (
            "Tableau ALISFA financement formation au 13 mars 2026 + "
            "Référentiel GPEC ALISFA 2025-07-07 + Code travail + Code action sociale + "
            "Légifrance + CAF + ANCT + France Compétences"
        ),
        "sprint": "5.2-data",
        "articles_added": sum(stats.values()),
        "themes_touched": list(stats.keys()),
    })


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="écrit le fichier (sinon dry-run)")
    parser.add_argument("--out", type=Path, default=BASE_FORMATION)
    args = parser.parse_args()

    by_theme = load_drafts()
    print(f"Drafts chargés : {sum(len(a) for a in by_theme.values())} articles dans {len(by_theme)} thèmes")
    for t, arts in sorted(by_theme.items()):
        print(f"  {t:30s} : {len(arts):3} articles")

    base = json.loads(BASE_FORMATION.read_text())
    n_before = sum(len(t.get("articles", [])) for t in base["themes"])
    n_themes_before = len(base["themes"])

    merged, stats = merge(by_theme, base)
    update_metadata(merged, stats)

    n_after = sum(len(t.get("articles", [])) for t in merged["themes"])
    n_themes_after = len(merged["themes"])

    print()
    print(f"Articles : {n_before} → {n_after} (+{n_after - n_before})")
    print(f"Thèmes   : {n_themes_before} → {n_themes_after} (+{n_themes_after - n_themes_before})")
    print("Stats par thème touché :")
    for t, n in sorted(stats.items()):
        print(f"  {t:30s} : +{n} articles")

    if args.write:
        args.out.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n")
        print(f"\n✅ Écrit : {args.out}")
    else:
        print("\n(dry-run — pas d'écriture, passer --write pour appliquer)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
