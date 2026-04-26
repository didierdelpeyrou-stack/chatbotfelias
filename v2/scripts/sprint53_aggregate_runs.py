"""Agrège les N derniers run_*.json en stats V2 (V1 ignoré, --skip-v1).

Usage :
  cd v2/
  ../.venv/bin/python scripts/sprint53_aggregate_runs.py 3
"""
from __future__ import annotations

import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "benchmark_results"


def stats(values: list[float]) -> dict:
    n = len(values)
    if n == 0:
        return {}
    out = {"n": n, "mean": round(statistics.mean(values), 2)}
    if n >= 2:
        out["stdev"] = round(statistics.stdev(values), 2)
    if n >= 3:
        out["ic95_low"] = round(out["mean"] - 2 * out["stdev"], 2)
        out["ic95_high"] = round(out["mean"] + 2 * out["stdev"], 2)
    return out


def summarize(rows: list[dict], side: str) -> dict:
    """Calcule success_rate global + par module pour V1 ou V2."""
    evals = [r[side]["eval"] for r in rows if "eval" in r[side]]
    n = len(evals)
    if n == 0:
        return {"total": 0, "success_rate": 0.0, "by_module": {}}
    success = sum(1 for e in evals if e["category"] in ("correct", "hors_corpus_ok"))
    rate = round(success / n * 100, 1)
    by_module: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "success": 0})
    for r, e in zip(rows, evals, strict=False):
        m = r["module"]
        by_module[m]["total"] += 1
        if e["category"] in ("correct", "hors_corpus_ok"):
            by_module[m]["success"] += 1
    return {
        "total": n,
        "success_rate": rate,
        "by_module": {
            m: round(d["success"] / d["total"] * 100, 1) if d["total"] else 0.0
            for m, d in by_module.items()
        },
    }


def main():
    n_runs = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    runs = sorted(RESULTS_DIR.glob("run_*.json"), key=lambda p: p.stat().st_mtime)[-n_runs:]
    if len(runs) < n_runs:
        print(f"⚠️  Seulement {len(runs)} runs trouvés (demandé: {n_runs})")
    print(f"Agrégation de {len(runs)} runs :")
    for r in runs:
        print(f"  - {r.name}")
    print()

    summaries = []
    for path in runs:
        with open(path) as f:
            data = json.load(f)
        s = summarize(data["rows"], "v2")
        summaries.append(s)

    if not summaries:
        sys.exit("Aucun run trouvé")

    # Global
    rates = [s["success_rate"] for s in summaries]
    print("=" * 60)
    print(f"V2 success_rate (global, {len(rates)} runs)")
    print(f"  par run     : {rates}")
    g = stats(rates)
    print(f"  mean        : {g['mean']}%")
    if "stdev" in g:
        print(f"  stdev       : ±{g['stdev']} pts")
    if "ic95_low" in g:
        print(f"  IC95        : [{g['ic95_low']}, {g['ic95_high']}]")
    print()

    # Par module
    print("V2 par module")
    modules = sorted(set(m for s in summaries for m in s["by_module"]))
    print(f"  {'module':14s} {'mean':>6s} {'stdev':>7s} {'min':>5s} {'max':>5s}")
    for m in modules:
        vals = [s["by_module"].get(m, 0.0) for s in summaries]
        ms = stats(vals)
        print(f"  {m:14s} {ms['mean']:>5}% {('±' + str(ms.get('stdev', 0))):>7s} {min(vals):>4}% {max(vals):>4}%")
    print()

    # Comparaison baseline
    BASELINE = 75.2
    BASELINE_IC = 2.1
    print("=" * 60)
    print(f"Baseline V2 pré-Sprint 5.3 (LLM-judge) : {BASELINE}% ± {BASELINE_IC}")
    print(f"V2 post-Sprint 5.3 (heuristic)         : {g['mean']}%")
    delta = g["mean"] - BASELINE
    sign = "+" if delta >= 0 else ""
    print(f"Δ                                       : {sign}{delta:.1f} pts")
    print("⚠️  baseline = LLM-judge ; mesure actuelle = heuristic — comparaison indicative seulement")


if __name__ == "__main__":
    main()
