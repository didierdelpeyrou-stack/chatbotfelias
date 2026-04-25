"""Migration KB V1 → V2 — enrichissement structurel (Sprint 5.1).

Ajoute aux articles V1 les 3 champs requis par le schéma V2 strict (audit
2026-04-21) sans toucher au contenu existant :

  1. ``niveau`` ∈ {vert, orange, rouge} — hérite de ``theme.niveau`` si présent
     (juridique : 21/21 thèmes ont déjà un niveau), sinon défaut ``vert``.
  2. ``escalade`` — préserve la valeur V1 (bool ou string) si présente, sinon
     ``false`` par défaut. Pas de conversion vers une struct enrichie tant que
     V2 ne le requiert pas formellement.
  3. ``revision`` — ajoute ``{derniere_verification, verifie_par}`` avec la
     date du jour et un marqueur de migration. Sera repushé manuellement par
     les juristes ELISFA après revue (Sprint 6.x).

Idempotent : un article qui a déjà les 3 champs n'est pas re-modifié (le
rapport indique 0 enrichissement). Permet de rerun safely.

Usage::

    cd v2/
    python scripts/migrate_kb_v1_v2.py
    # ou avec un dossier custom :
    python scripts/migrate_kb_v1_v2.py --source ../data --target ../data/v2

Concept inline — Schema migration as code :
    Le schéma Pydantic V2 (v2/app/kb/schema.py) est le contrat. Ce script
    le fait respecter par construction. Aucune dérive possible : si la
    KB V1 ne valide pas après enrichissement, le script raise et n'écrit
    rien. Anti-pattern évité : "schéma documenté sur Confluence" qui drift
    inévitablement avec le code.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections import Counter
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

# On importe le schéma V2 depuis le repo (PYTHONPATH géré par l'utilisateur)
try:
    from app.kb.schema import KnowledgeBase
except ImportError as exc:
    print(f"❌ Impossible d'importer app.kb.schema : {exc}", file=sys.stderr)
    print("   Lance avec : PYTHONPATH=. ../.venv/bin/python scripts/migrate_kb_v1_v2.py")
    sys.exit(2)


MIGRATION_AUTHOR = "ELISFA Migration V1→V2"

# Modules attendus — l'ordre détermine celui du rapport
KB_FILES = [
    "base_juridique.json",
    "base_formation.json",
    "base_rh.json",
    "base_gouvernance.json",
]


# ─────────────────────────── Enrichissement article ───────────────────────────

def enrich_article(
    article: dict[str, Any],
    theme_niveau: str | None,
    today: date,
) -> dict[str, str]:
    """Ajoute les champs V2 manquants à un article V1 (in-place).

    Retourne un dict des champs effectivement ajoutés (utile pour le rapport).
    Idempotent : si tous les champs sont déjà présents, retourne {}.
    """
    added: dict[str, str] = {}

    # 1. niveau — hérite du thème si l'article ne l'a pas
    if not article.get("niveau"):
        article["niveau"] = theme_niveau or "vert"
        added["niveau"] = article["niveau"]

    # 2. escalade — défaut False si absent (None ou key missing)
    if "escalade" not in article or article.get("escalade") is None:
        article["escalade"] = False
        added["escalade"] = "false"

    # 3. revision — défaut migration metadata
    if not isinstance(article.get("revision"), dict):
        article["revision"] = {
            "derniere_verification": today.isoformat(),
            "verifie_par": MIGRATION_AUTHOR,
        }
        added["revision"] = "migration_default"

    return added


# ─────────────────────────── Migration KB complète ───────────────────────────

def migrate_kb(kb_dict: dict[str, Any], today: date) -> tuple[dict[str, Any], dict[str, Any]]:
    """Enrichit une KB V1 → V2. Retourne (kb_v2, stats_dict).

    Modifie ``kb_dict`` in-place (caller copie avant si besoin).
    """
    n_articles = 0
    enrichments: Counter[str] = Counter()
    niveaux_distribution: Counter[str] = Counter()

    for theme in kb_dict.get("themes", []):
        theme_niveau = theme.get("niveau")
        for article in theme.get("articles", []):
            n_articles += 1
            added = enrich_article(article, theme_niveau, today)
            for field in added:
                enrichments[field] += 1
            niveaux_distribution[article["niveau"]] += 1

    return kb_dict, {
        "articles_total": n_articles,
        "enrichments_added": dict(enrichments),
        "niveaux_distribution": dict(niveaux_distribution),
    }


# ─────────────────────────── Validation post-migration ───────────────────────────

def validate_v2(kb_dict: dict[str, Any], file_label: str) -> None:
    """Lance le schéma Pydantic V2 strict. Raise si invalide."""
    try:
        kb = KnowledgeBase.model_validate(kb_dict)
    except Exception as exc:
        raise SystemExit(
            f"❌ {file_label} ne valide pas le schéma V2 après migration :\n  {exc}"
        ) from exc
    # Sanity check : les compteurs doivent être cohérents
    expected_arts = sum(len(t.get("articles", [])) for t in kb_dict.get("themes", []))
    if kb.n_articles != expected_arts:
        raise SystemExit(
            f"❌ {file_label} : KB.n_articles={kb.n_articles} ≠ {expected_arts} (themes×articles)"
        )


# ─────────────────────────── CLI ───────────────────────────

def _backup_originals(source: Path, backup_dir: Path) -> Path:
    """Copie les KB V1 originales dans `backup_dir/<timestamp>/`."""
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    target = backup_dir / stamp
    target.mkdir(parents=True, exist_ok=True)
    for fname in KB_FILES:
        src = source / fname
        if src.exists():
            shutil.copy2(src, target / fname)
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="Migration KB V1 → V2 (Sprint 5.1)")
    parser.add_argument("--source", type=Path, default=Path("../data"),
                        help="Dossier source des KB V1 (défaut : ../data)")
    parser.add_argument("--target", type=Path, default=Path("../data/v2"),
                        help="Dossier cible pour les KB V2 enrichies (défaut : ../data/v2)")
    parser.add_argument("--backup-dir", type=Path, default=Path("../data/v1_backup"),
                        help="Dossier où sauvegarder les originaux V1")
    parser.add_argument("--dry-run", action="store_true",
                        help="N'écrit rien, affiche juste ce qui serait fait")
    args = parser.parse_args()

    source: Path = args.source.resolve()
    target: Path = args.target.resolve()
    backup_dir: Path = args.backup_dir.resolve()

    if not source.is_dir():
        print(f"❌ Source non trouvée : {source}", file=sys.stderr)
        return 2

    today = date.today()
    print(f"🚀 Migration KB V1 → V2  ({today.isoformat()})")
    print(f"   Source : {source}")
    print(f"   Cible  : {target}{' (dry-run)' if args.dry_run else ''}")

    if not args.dry_run:
        backup_path = _backup_originals(source, backup_dir)
        print(f"📦 Backup originaux : {backup_path}")
        target.mkdir(parents=True, exist_ok=True)

    report = {
        "migrated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "author": MIGRATION_AUTHOR,
        "source": str(source),
        "target": str(target),
        "files": {},
        "totals": {"articles": 0, "themes": 0},
    }

    for fname in KB_FILES:
        src_path = source / fname
        if not src_path.exists():
            print(f"⏭  {fname} : absent, skip")
            continue
        with src_path.open(encoding="utf-8") as fp:
            kb_dict = json.load(fp)

        # Migration in-memory
        migrated, stats = migrate_kb(kb_dict, today)

        # Validation V2 stricte — raise si KO
        validate_v2(migrated, fname)

        report["files"][fname] = stats
        report["totals"]["articles"] += stats["articles_total"]
        report["totals"]["themes"] += len(migrated.get("themes", []))

        if not args.dry_run:
            out_path = target / fname
            with out_path.open("w", encoding="utf-8") as fp:
                json.dump(migrated, fp, ensure_ascii=False, indent=2)
            print(
                f"✅ {fname}: {stats['articles_total']} articles, "
                f"+niveau×{stats['enrichments_added'].get('niveau', 0)} "
                f"+escalade×{stats['enrichments_added'].get('escalade', 0)} "
                f"+revision×{stats['enrichments_added'].get('revision', 0)}"
            )
        else:
            print(f"   {fname}: {stats}")

    if not args.dry_run:
        report_path = target / "migration_report.json"
        with report_path.open("w", encoding="utf-8") as fp:
            json.dump(report, fp, ensure_ascii=False, indent=2)
        print(f"\n📄 Rapport : {report_path}")
        print(f"   Total : {report['totals']['articles']} articles, "
              f"{report['totals']['themes']} thèmes")

    return 0


if __name__ == "__main__":
    sys.exit(main())
