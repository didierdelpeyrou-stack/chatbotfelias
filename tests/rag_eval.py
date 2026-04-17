"""
RAG Evaluation Harness — Chatbot ELISFA

Exécute le jeu de questions de référence (tests/rag_reference.json) contre l'API
en production et mesure :
  - précision top-1 (la source principale attendue est-elle dans la réponse ?)
  - rappel top-5 (au moins 1 source attendue est-elle dans les résultats ?)
  - keyword coverage (les mots-clés obligatoires sont-ils dans la réponse ?)
  - forbidden detection (la réponse contient-elle des phrases interdites ?)
  - escalade correctness (le niveau renvoyé correspond-il à l'attendu ?)
  - latence bout-en-bout

Usage :
    python tests/rag_eval.py --url https://felias-reseau-eli2026.duckdns.org
    python tests/rag_eval.py --url http://localhost:5000 --subset juridique
    python tests/rag_eval.py --report report.json

Sortie :
    tests/rag_eval_report_YYYYMMDD_HHMMSS.json
    + résumé console (précision, rappel, erreurs, latences)
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib import request, error

ROOT = Path(__file__).parent
REFERENCE_FILE = ROOT / "rag_reference.json"
DEFAULT_URL = "https://felias-reseau-eli2026.duckdns.org"
TIMEOUT = 45  # secondes par question (Haiku est rapide, mais sécurité)


def _post_json(url: str, payload: dict, timeout: int = TIMEOUT) -> tuple[int, dict]:
    """POST JSON — renvoie (status_code, body_dict ou {})."""
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            try:
                return resp.status, json.loads(body)
            except json.JSONDecodeError:
                return resp.status, {"_raw": body[:500]}
    except error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return e.code, {"_error": body[:500]}
    except Exception as e:  # noqa: BLE001 — test harness
        return 0, {"_error": f"{type(e).__name__}: {e}"}


def load_reference() -> dict:
    with REFERENCE_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def evaluate_answer(answer_text: str, test_case: dict) -> dict:
    """Mesure une réponse contre les attentes du test."""
    answer_lower = (answer_text or "").lower()

    # Rappel des sources attendues (au moins 1 match)
    sources_expected = [s.lower() for s in test_case.get("expected_sources_any", [])]
    sources_found = [s for s in sources_expected if s in answer_lower]
    recall_sources = (
        len(sources_found) / len(sources_expected) if sources_expected else None
    )

    # Keywords obligatoires (tous doivent être présents)
    keywords_required = [k.lower() for k in test_case.get("expected_keywords_all", [])]
    keywords_missing = [k for k in keywords_required if k not in answer_lower]
    keywords_ok = len(keywords_missing) == 0

    # Phrases interdites (aucune ne doit apparaître)
    forbidden = [p.lower() for p in test_case.get("forbidden_phrases", [])]
    forbidden_hits = [p for p in forbidden if p in answer_lower]
    forbidden_ok = len(forbidden_hits) == 0

    return {
        "recall_sources": recall_sources,
        "sources_found": sources_found,
        "keywords_ok": keywords_ok,
        "keywords_missing": keywords_missing,
        "forbidden_ok": forbidden_ok,
        "forbidden_hits": forbidden_hits,
    }


def run_one(base_url: str, test_case: dict) -> dict:
    """Exécute un test et retourne le résultat."""
    endpoint = f"{base_url.rstrip('/')}/api/ask"
    payload = {
        "module": test_case["module"],
        "question": test_case["question"],
    }
    t0 = time.time()
    status, body = _post_json(endpoint, payload)
    latency_ms = int((time.time() - t0) * 1000)

    answer = body.get("answer") or body.get("reply") or ""
    niveau = body.get("niveau")

    eval_result = evaluate_answer(answer, test_case)

    niveau_ok = None
    if test_case.get("expected_niveau") is not None:
        niveau_ok = niveau == test_case["expected_niveau"]

    passed = (
        status == 200
        and eval_result["keywords_ok"]
        and eval_result["forbidden_ok"]
        and (niveau_ok is None or niveau_ok)
        and (eval_result["recall_sources"] is None or eval_result["recall_sources"] > 0)
    )

    return {
        "id": test_case["id"],
        "module": test_case["module"],
        "question": test_case["question"],
        "http_status": status,
        "latency_ms": latency_ms,
        "niveau_received": niveau,
        "niveau_expected": test_case.get("expected_niveau"),
        "niveau_ok": niveau_ok,
        "answer_len": len(answer),
        "answer_preview": answer[:200],
        "eval": eval_result,
        "passed": passed,
        "error": body.get("_error") if status != 200 else None,
    }


def summarize(results: list[dict]) -> dict:
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    http_ok = sum(1 for r in results if r["http_status"] == 200)
    latencies = [r["latency_ms"] for r in results if r["http_status"] == 200]
    latencies.sort()

    def p(pct: int) -> int:
        if not latencies:
            return 0
        return latencies[max(0, min(len(latencies) - 1, int(len(latencies) * pct / 100)))]

    by_module: dict[str, dict] = {}
    for r in results:
        m = r["module"]
        by_module.setdefault(m, {"total": 0, "passed": 0})
        by_module[m]["total"] += 1
        if r["passed"]:
            by_module[m]["passed"] += 1

    return {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round(passed / total, 3) if total else 0,
        "http_ok": http_ok,
        "latency_p50_ms": p(50),
        "latency_p95_ms": p(95),
        "latency_max_ms": max(latencies) if latencies else 0,
        "by_module": by_module,
    }


def print_report(summary: dict, results: list[dict], verbose: bool = False) -> None:
    print("\n" + "=" * 70)
    print(f"  RAG EVAL — {summary['total']} tests, {summary['passed']} OK, "
          f"{summary['failed']} KO ({summary['pass_rate']*100:.1f}%)")
    print("=" * 70)
    print(f"  HTTP 200        : {summary['http_ok']}/{summary['total']}")
    print(f"  Latence P50     : {summary['latency_p50_ms']} ms")
    print(f"  Latence P95     : {summary['latency_p95_ms']} ms")
    print(f"  Latence max     : {summary['latency_max_ms']} ms")
    print()
    for module, stats in summary["by_module"].items():
        rate = stats["passed"] / stats["total"] * 100 if stats["total"] else 0
        print(f"  {module:<13}: {stats['passed']}/{stats['total']} ({rate:.0f}%)")
    print()

    failed = [r for r in results if not r["passed"]]
    if failed:
        print("  ─── Tests en échec ───")
        for r in failed:
            print(f"  ✗ {r['id']} [{r['module']}] {r['question'][:60]}…")
            if r["error"]:
                print(f"      error  : {r['error'][:80]}")
            if not r["eval"]["keywords_ok"]:
                print(f"      kw manquants : {r['eval']['keywords_missing']}")
            if not r["eval"]["forbidden_ok"]:
                print(f"      forbidden    : {r['eval']['forbidden_hits']}")
            if r["niveau_ok"] is False:
                print(f"      niveau : attendu={r['niveau_expected']} "
                      f"reçu={r['niveau_received']}")
            if verbose:
                print(f"      preview: {r['answer_preview'][:140]}")
        print()


def main():
    ap = argparse.ArgumentParser(description="RAG evaluation harness ELISFA")
    ap.add_argument("--url", default=DEFAULT_URL, help="URL de base du serveur")
    ap.add_argument("--subset", help="Limiter à un module (juridique|rh|formation|gouvernance)")
    ap.add_argument("--report", help="Chemin du JSON de rapport (par défaut: auto)")
    ap.add_argument("--verbose", action="store_true", help="Affiche les previews")
    ap.add_argument("--fail-under", type=float, default=0.80,
                    help="Taux de passage min (exit 1 sinon)")
    args = ap.parse_args()

    ref = load_reference()
    tests = ref["tests"]
    if args.subset:
        tests = [t for t in tests if t["module"] == args.subset]
        if not tests:
            print(f"Aucun test pour le module '{args.subset}'")
            sys.exit(2)

    print(f"▶ Exécution de {len(tests)} tests contre {args.url}")
    results = []
    for i, t in enumerate(tests, 1):
        print(f"  [{i}/{len(tests)}] {t['id']} {t['module']:<11} "
              f"{t['question'][:50]}…", end=" ", flush=True)
        r = run_one(args.url, t)
        results.append(r)
        status = "✓" if r["passed"] else "✗"
        print(f"{status} {r['latency_ms']}ms")

    summary = summarize(results)
    print_report(summary, results, verbose=args.verbose)

    # Export JSON
    report_path = args.report or (
        ROOT / f"rag_eval_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "results": results,
                   "meta": {"url": args.url, "timestamp": datetime.now().isoformat()}},
                  f, ensure_ascii=False, indent=2)
    print(f"  Rapport : {report_path}")

    if summary["pass_rate"] < args.fail_under:
        print(f"\n✗ FAIL : taux de passage {summary['pass_rate']:.1%} "
              f"< seuil {args.fail_under:.0%}")
        sys.exit(1)

    print(f"\n✓ PASS : taux de passage {summary['pass_rate']:.1%}")


if __name__ == "__main__":
    main()
