#!/usr/bin/env python3
"""
Extraction de texte des 189 PDFs scrapés + déduplication croisée avec
l'ancien corpus (alisfa_docs/, fiches_pratiques/).

Produit :
  data/alisfa_public/pdf_index.jsonl    — 1 ligne par PDF (path, hash, size, pages, text, category)
  data/alisfa_public/dedup_report.json  — comparaison avec l'existant
"""
from __future__ import annotations

import hashlib
import json
import re
import signal
import sys
import time
from pathlib import Path

import pdfplumber


class _Timeout(Exception):
    pass


def _raise_timeout(signum, frame):
    raise _Timeout()


signal.signal(signal.SIGALRM, _raise_timeout)

# PDFs trop gros / print-ready qu'on indexe sans extraire le texte
MAX_BYTES_FOR_EXTRACT = 8 * 1024 * 1024  # 8 MB
PER_PDF_TIMEOUT_S = 45

ROOT = Path(__file__).resolve().parent.parent
PDF_DIR = ROOT / "data" / "alisfa_public" / "pdfs"
INDEX = ROOT / "data" / "alisfa_public" / "pdf_index.jsonl"
DEDUP_REPORT = ROOT / "data" / "alisfa_public" / "dedup_report.json"

OLD_DIRS = [
    ROOT / "data" / ".trash_20260414_223533" / "alisfa_docs",
    ROOT / "fiches_pratiques",
]


# Catégorisation basée sur le nom du fichier
def categorize(name: str) -> str:
    n = name.lower()
    if n.startswith("avenant-") or "avenant-" in n:
        return "avenant"
    if n.startswith("accord-") or "/accord-" in n or "accord_" in n:
        return "accord"
    if "guide-paritaire" in n:
        return "guide_paritaire"
    if "guide" in n:
        return "guide"
    if "brochure" in n:
        return "brochure"
    if "affiche" in n or "flyer" in n or "depliant" in n:
        return "affiche_flyer"
    if "lettre-dinfo" in n or "lettre-n-" in n or "lettre-info" in n:
        return "lettre_info"
    if "fiche-metier" in n or "fiches-metiers" in n:
        return "fiche_metier"
    if "garanties" in n or "grille-optique" in n:
        return "prevoyance_sante"
    if "rps" in n or "harce" in n or "prevention" in n:
        return "sante_securite"
    if "gpec" in n:
        return "gpec"
    if "rapport" in n or "panorama" in n or "etude" in n:
        return "rapport_etude"
    if re.match(r"\d{4}-\d{2}-\d{2}", n):
        return "communique_presse"
    return "autre"


def sha1(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_text(path: Path, max_chars: int = 60_000) -> tuple[str, int]:
    """Return (text, n_pages). Best-effort, never crash, global timeout."""
    size = path.stat().st_size
    if size > MAX_BYTES_FOR_EXTRACT:
        return f"[SKIP extraction: fichier {size // 1024 // 1024} MB > seuil]", 0
    signal.alarm(PER_PDF_TIMEOUT_S)
    try:
        with pdfplumber.open(path) as pdf:
            pages = pdf.pages
            parts = []
            total = 0
            for p in pages:
                try:
                    t = p.extract_text() or ""
                except Exception:
                    t = ""
                if t:
                    parts.append(t)
                    total += len(t)
                    if total > max_chars:
                        break
            text = "\n".join(parts)
            text = re.sub(r"[ \t]+\n", "\n", text)
            text = re.sub(r"\n{3,}", "\n\n", text).strip()
            return text[:max_chars], len(pages)
    except _Timeout:
        return f"[TIMEOUT extraction > {PER_PDF_TIMEOUT_S}s]", 0
    except Exception as e:
        return f"[ERREUR extraction: {e}]", 0
    finally:
        signal.alarm(0)


def main() -> int:
    t0 = time.time()
    pdfs = sorted(PDF_DIR.glob("*.pdf"))
    print(f"[index] {len(pdfs)} PDFs à traiter")
    # Pré-hashing de l'ancien corpus pour dedup
    old_hashes: dict[str, str] = {}
    old_names: set[str] = set()
    for d in OLD_DIRS:
        if not d.exists():
            continue
        for p in d.rglob("*.pdf"):
            try:
                old_hashes[sha1(p)] = str(p.relative_to(ROOT))
            except Exception:
                pass
            old_names.add(p.name.lower())
    print(f"[index] ancien corpus : {len(old_hashes)} PDFs, {len(old_names)} noms uniques")

    dup_hash = 0
    dup_name = 0
    new_pdfs = []
    with INDEX.open("w", encoding="utf-8") as out:
        for i, pdf in enumerate(pdfs, 1):
            if i % 20 == 0:
                print(f"  … {i}/{len(pdfs)}")
            size = pdf.stat().st_size
            h = sha1(pdf)
            is_dup_hash = h in old_hashes
            is_dup_name = pdf.name.lower() in old_names and not is_dup_hash
            text, n_pages = extract_text(pdf)
            entry = {
                "file": pdf.name,
                "path": str(pdf.relative_to(ROOT)),
                "sha1": h,
                "size": size,
                "pages": n_pages,
                "category": categorize(pdf.name),
                "text_len": len(text),
                "text": text,
                "dup_of_existing_hash": old_hashes.get(h),
                "dup_by_name_only": is_dup_name,
            }
            out.write(json.dumps(entry, ensure_ascii=False) + "\n")
            if is_dup_hash:
                dup_hash += 1
            elif is_dup_name:
                dup_name += 1
            else:
                new_pdfs.append(pdf.name)

    report = {
        "total_pdfs": len(pdfs),
        "duplicates_by_hash": dup_hash,
        "duplicates_by_name_only": dup_name,
        "genuinely_new": len(new_pdfs),
        "new_files_sample": new_pdfs[:50],
        "categories": {},
        "duration_s": round(time.time() - t0, 1),
    }
    # Compter catégories
    for line in INDEX.open(encoding="utf-8"):
        try:
            e = json.loads(line)
            c = e.get("category", "autre")
            report["categories"][c] = report["categories"].get(c, 0) + 1
        except Exception:
            pass
    DEDUP_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n" + "=" * 60)
    print(f"Index: {INDEX}")
    print(f"Rapport: {DEDUP_REPORT}")
    print(f"  total           : {report['total_pdfs']}")
    print(f"  dup par hash    : {report['duplicates_by_hash']}")
    print(f"  dup par nom     : {report['duplicates_by_name_only']}")
    print(f"  NOUVEAUX        : {report['genuinely_new']}")
    print(f"  catégories      : {report['categories']}")
    print(f"  durée           : {report['duration_s']}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
