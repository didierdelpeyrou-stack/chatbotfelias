"""
Sprint 5.3 — fusion R-Vague1 + G-Vague1 dans base_rh.json + base_gouvernance.json

Lit tous les drafts sprint53_*.json dans v2/scripts/kb_drafts/, les fusionne
dans data/v2/base_rh.json et data/v2/base_gouvernance.json en respectant le
champ `_theme_target` de chaque article (champ retiré avant écriture).

Crée les thèmes manquants avec un label par défaut. Met à jour
metadata.enrichissements avec une entrée Sprint 5.3.

Backup avant écriture dans data/v2_backup/sprint53_premerge_<ts>/.
"""
from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "v2"
DRAFTS_DIR = ROOT / "v2" / "scripts" / "kb_drafts"
BACKUP_DIR = ROOT / "data" / "v2_backup" / f"sprint53_premerge_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

# Labels pour thèmes éventuellement manquants
THEME_LABELS = {
    # RH existants
    "recrutement_integration": "Recrutement et intégration",
    "entretiens_evaluation": "Entretiens et évaluation",
    "gpec_mobilite": "GPEC, classification et mobilité",
    "qvct_sante_travail": "QVCT et santé au travail",
    "dialogue_social_local": "Dialogue social local",
    # RH nouveaux (Sprint 5.3)
    "discipline_sanctions": "Discipline et sanctions",
    "absences_rupture": "Absences, préavis et rupture",
    "contrats_specifiques": "Contrats spécifiques (CDD, intérim)",
    "temps_de_travail": "Durée et organisation du temps de travail",
    "remuneration": "Rémunération, primes et frais professionnels",
    "conges": "Congés payés, jours fériés et exceptionnels",
    # Gouvernance existants
    "cadre_legal": "Cadre légal de l'association employeuse",
    "instances": "Instances et gouvernance",
    "benevolat": "Bénévolat et droits des bénévoles",
    "patronat_associatif": "Patronat associatif",
    "doctrine_recherche": "Doctrine et recherche en ESS",
}


def load(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save(path: Path, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def merge_module(base_path: Path, drafts: list[Path], module_label: str) -> dict:
    """Fusionne les drafts dans la base existante, par _theme_target."""
    base = load(base_path)
    existing_themes = {t["id"]: t for t in base["themes"]}
    existing_ids = {a["id"] for t in base["themes"] for a in t["articles"]}

    by_target: dict[str, list[dict]] = {}
    for draft_path in drafts:
        draft = load(draft_path)
        for art in draft["articles"]:
            tgt = art.pop("_theme_target", None)
            if not tgt:
                raise SystemExit(f"  ERREUR : pas de _theme_target sur {art.get('id')}")
            if art["id"] in existing_ids:
                raise SystemExit(f"  ERREUR : id {art['id']} déjà présent dans la base")
            by_target.setdefault(tgt, []).append(art)

    added_total = 0
    for theme_id, arts in by_target.items():
        if theme_id not in existing_themes:
            label = THEME_LABELS.get(theme_id, theme_id.replace("_", " ").capitalize())
            new_theme = {"id": theme_id, "label": label, "articles": []}
            base["themes"].append(new_theme)
            existing_themes[theme_id] = new_theme
            print(f"    + nouveau thème '{theme_id}' créé ({label})")
        existing_themes[theme_id]["articles"].extend(arts)
        added_total += len(arts)
        print(f"    + {len(arts)} articles → '{theme_id}' [{', '.join(a['id'] for a in arts)}]")

    # Met à jour metadata.enrichissements
    new_ids = sorted({a["id"] for arts in by_target.values() for a in arts})
    enrich_entry = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "source": "Sprint 5.3 R-Vague1 + G-Vague1 — CCN ELISFA mars 2026 + Avenant 10-22 + Cours UE1 SOCIO ECO ASSO + Loi Hamon 2014",
        "ajouts": new_ids,
        "note": f"Sprint 5.3 enrichissement {module_label} : {len(new_ids)} articles ajoutés.",
    }
    base["metadata"].setdefault("enrichissements", []).append(enrich_entry)
    base["metadata"]["date_consolidation"] = datetime.now().strftime("%Y-%m-%d")

    print(f"  → total articles fusionnés : {added_total}")
    print(f"  → total {module_label} après fusion : {sum(len(t['articles']) for t in base['themes'])}")
    return base


def main():
    if not DATA_DIR.exists():
        sys.exit(f"DATA_DIR introuvable : {DATA_DIR}")

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    for p in (DATA_DIR / "base_rh.json", DATA_DIR / "base_gouvernance.json"):
        shutil.copy2(p, BACKUP_DIR / p.name)
    print(f"Backup → {BACKUP_DIR}")

    rh_drafts = sorted(DRAFTS_DIR.glob("sprint53_lot*_rh_*.json"))
    gv_drafts = sorted(DRAFTS_DIR.glob("sprint53_gv*_gouvernance_*.json"))
    print(f"\nRH drafts : {[p.name for p in rh_drafts]}")
    print(f"GV drafts : {[p.name for p in gv_drafts]}")

    print("\n=== Fusion RH ===")
    rh_merged = merge_module(DATA_DIR / "base_rh.json", rh_drafts, "RH")
    save(DATA_DIR / "base_rh.json", rh_merged)

    print("\n=== Fusion Gouvernance ===")
    gv_merged = merge_module(DATA_DIR / "base_gouvernance.json", gv_drafts, "Gouvernance")
    save(DATA_DIR / "base_gouvernance.json", gv_merged)

    print("\n✅ Fusion terminée. Lancer la validation Pydantic puis regenérer embeddings.")


if __name__ == "__main__":
    main()
