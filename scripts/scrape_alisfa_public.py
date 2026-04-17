#!/usr/bin/env python3
"""
Scraping public du site https://www.alisfa.fr (sans identifiants).

Ce que fait ce script :
  1. Lit les sitemaps Yoast (pages + articles) pour obtenir la liste complète
     des URLs publiques — pas de crawl aveugle.
  2. Récupère chaque page via Scrapling (Fetcher HTTP, pas de navigateur).
  3. S'arrête dès qu'une page renvoie 401/403 ou contient un formulaire de login.
  4. Télécharge tous les PDFs référencés dans ces pages (brochures, guides, fiches).
  5. Sauvegarde les pages « Comprendre la CCN » (et apparentées) en JSONL
     avec titre + contenu texte propre.
  6. Journalise l'ensemble dans un rapport final.

Destination : chatbot_elisfa/data/alisfa_public/
"""
from __future__ import annotations

import json
import re
import time
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote
import xml.etree.ElementTree as ET

from scrapling.fetchers import Fetcher

BASE = "https://www.alisfa.fr"
SITEMAP_INDEX = f"{BASE}/sitemap_index.xml"
OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "alisfa_public"
PDF_DIR = OUT_DIR / "pdfs"
PAGES_JSONL = OUT_DIR / "pages.jsonl"
CCN_JSONL = OUT_DIR / "comprendre_ccn.jsonl"
REPORT = OUT_DIR / "scrape_report.json"

POLITE_DELAY_S = 0.6  # délai entre requêtes
TIMEOUT = 25

# URL prefixes qui identifient des zones réservées (pages "login requis")
RESTRICTED_PATH_PREFIXES = (
    "/espace-negociateur",
    "/espace-adherent",
    "/espace-adherents",
    "/wp-login",
    "/wp-admin",
    "/my-account",
    "/mon-compte",
)
# Marqueurs dans le contenu principal (pas dans tout le HTML — trop large)
LOGIN_CONTENT_MARKERS = (
    'type="password"',
    "veuillez vous connecter",
    "vous devez être connecté",
    "accès réservé",
    "contenu réservé",
)

# Catégories / slugs considérés comme "Comprendre la CCN"
CCN_PATTERNS = [
    r"/comprendre",
    r"/ccn",
    r"/convention-collective",
    r"/avenant",
    r"/classification",
    r"/remuneration",
    r"/annexe",
    r"/accord-",
    r"/formation-professionnelle",
    r"/sante-securite",
    r"/prevoyance",
    r"/egalite",
    r"/contrat-de-travail",
    r"/temps-de-travail",
    r"/conges",
    r"/rupture",
    r"/licenciement",
    r"/inaptitude",
    r"/fiche-",
    r"/guide-",
    r"/dossier-",
]

OUT_DIR.mkdir(parents=True, exist_ok=True)
PDF_DIR.mkdir(parents=True, exist_ok=True)


def log(msg: str) -> None:
    print(f"[alisfa-scraper] {msg}", flush=True)


def fetch(url: str):
    """Scrapling fetch with polite delay."""
    time.sleep(POLITE_DELAY_S)
    try:
        r = Fetcher.get(url, timeout=TIMEOUT, stealthy_headers=True)
        return r
    except Exception as e:
        log(f"ERREUR fetch {url} → {e}")
        return None


def parse_sitemap_xml(xml_bytes: bytes) -> list[str]:
    """Extract <loc> URLs from a sitemap XML."""
    ns = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        log(f"XML invalide : {e}")
        return []
    return [el.text.strip() for el in root.iter(f"{ns}loc") if el.text]


def collect_sitemap_urls() -> list[str]:
    """Return all page URLs from every sub-sitemap of the index."""
    log("Lecture du sitemap index…")
    r = fetch(SITEMAP_INDEX)
    if not r or r.status != 200:
        log("Échec lecture sitemap_index.xml — fallback /sitemap.xml")
        r = fetch(f"{BASE}/sitemap.xml")
        if not r or r.status != 200:
            return []
    sub_sitemaps = parse_sitemap_xml(r.body)
    log(f"  → {len(sub_sitemaps)} sous-sitemaps détectés")
    all_urls: list[str] = []
    for sm in sub_sitemaps:
        # On ignore le sitemap "questionnaire" qui n'est pas de la doctrine
        if "questionnaire" in sm:
            log(f"  ⏭  ignoré : {sm}")
            continue
        sr = fetch(sm)
        if not sr or sr.status != 200:
            continue
        urls = parse_sitemap_xml(sr.body)
        log(f"  + {len(urls):4d} URLs dans {sm.rsplit('/',1)[-1]}")
        all_urls.extend(urls)
    # Déduplication + garde uniquement même domaine
    seen = set()
    uniq = []
    for u in all_urls:
        if urlparse(u).netloc.endswith("alisfa.fr") and u not in seen:
            seen.add(u)
            uniq.append(u)
    log(f"Total URLs publiques collectées : {len(uniq)}")
    return uniq


def is_restricted_url(url: str) -> bool:
    path = urlparse(url).path.lower()
    return any(path.startswith(p) for p in RESTRICTED_PATH_PREFIXES)


def looks_like_login_content(main_text: str) -> bool:
    if not main_text:
        return False
    low = main_text.lower()
    return any(m in low for m in LOGIN_CONTENT_MARKERS)


def extract_text(adaptor) -> str:
    """Extraction du contenu textuel principal (main/article) via Scrapling."""
    for sel in ("main article", "main", "article", ".entry-content", "#content", "body"):
        try:
            node = adaptor.find(sel)
        except Exception:
            node = None
        if node:
            try:
                txt = node.get_all_text(separator="\n", strip=True)
            except Exception:
                txt = node.text if hasattr(node, "text") else ""
            if txt and len(txt) > 80:
                return re.sub(r"\n{3,}", "\n\n", txt).strip()
    return ""


def extract_title(adaptor) -> str:
    for sel in ("h1", "title"):
        try:
            n = adaptor.find(sel)
        except Exception:
            n = None
        if n:
            t = getattr(n, "text", "") or ""
            t = t.strip()
            if t:
                return t
    return ""


def extract_pdf_links(adaptor, page_url: str) -> list[str]:
    pdfs = set()
    try:
        anchors = adaptor.find_all("a")
    except Exception:
        anchors = []
    for a in anchors or []:
        href = None
        try:
            href = a.attrib.get("href")
        except Exception:
            href = None
        if not href:
            continue
        absu = urljoin(page_url, href)
        low = absu.lower().split("?")[0]
        if low.endswith(".pdf") and urlparse(absu).netloc.endswith("alisfa.fr"):
            pdfs.add(absu)
    return sorted(pdfs)


def is_ccn_page(url: str) -> bool:
    path = urlparse(url).path.lower()
    return any(re.search(p, path) for p in CCN_PATTERNS)


def safe_filename(url: str) -> str:
    name = unquote(urlparse(url).path.rsplit("/", 1)[-1]) or "index.pdf"
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    if not name.lower().endswith(".pdf"):
        name += ".pdf"
    return name[:180]


def download_pdf(url: str, dest: Path) -> bool:
    if dest.exists() and dest.stat().st_size > 1024:
        return True
    r = fetch(url)
    if not r or r.status != 200:
        return False
    try:
        dest.write_bytes(r.body)
        return dest.stat().st_size > 512
    except Exception as e:
        log(f"ERREUR écriture {dest.name} → {e}")
        return False


def main() -> int:
    t0 = time.time()
    urls = collect_sitemap_urls()
    if not urls:
        log("Aucune URL collectée — arrêt.")
        return 1

    pages_f = PAGES_JSONL.open("w", encoding="utf-8")
    ccn_f = CCN_JSONL.open("w", encoding="utf-8")

    stats = {
        "urls_total": len(urls),
        "pages_ok": 0,
        "pages_skip_login": 0,
        "pages_error": 0,
        "pdfs_found": 0,
        "pdfs_downloaded": 0,
        "ccn_pages": 0,
    }
    seen_pdfs: set[str] = set()

    for i, url in enumerate(urls, 1):
        if i % 20 == 0:
            log(f"  … {i}/{len(urls)}  (ok={stats['pages_ok']} skip={stats['pages_skip_login']} pdfs={stats['pdfs_downloaded']})")

        if is_restricted_url(url):
            stats["pages_skip_login"] += 1
            continue

        r = fetch(url)
        if not r:
            stats["pages_error"] += 1
            continue
        if r.status in (401, 403):
            log(f"  🚫 accès restreint ({r.status}) : {url}")
            stats["pages_skip_login"] += 1
            continue
        if r.status != 200:
            stats["pages_error"] += 1
            continue

        title = extract_title(r)
        text = extract_text(r)
        pdfs = extract_pdf_links(r, url)

        if looks_like_login_content(text):
            log(f"  🔒 contenu réservé : {url}")
            stats["pages_skip_login"] += 1
            continue

        entry = {
            "url": url,
            "title": title,
            "text": text,
            "pdfs": pdfs,
        }
        pages_f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        stats["pages_ok"] += 1

        if is_ccn_page(url) and text:
            ccn_f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            stats["ccn_pages"] += 1

        for p in pdfs:
            if p in seen_pdfs:
                continue
            seen_pdfs.add(p)
            stats["pdfs_found"] += 1
            dest = PDF_DIR / safe_filename(p)
            if download_pdf(p, dest):
                stats["pdfs_downloaded"] += 1
                log(f"  📄 {dest.name}")

    pages_f.close()
    ccn_f.close()

    stats["duration_s"] = round(time.time() - t0, 1)
    REPORT.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")

    log("")
    log("=" * 60)
    log("RAPPORT")
    log("=" * 60)
    for k, v in stats.items():
        log(f"  {k:20} : {v}")
    log(f"  PDFs dans        : {PDF_DIR}")
    log(f"  Pages JSONL      : {PAGES_JSONL}")
    log(f"  CCN JSONL        : {CCN_JSONL}")
    log(f"  Rapport          : {REPORT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
