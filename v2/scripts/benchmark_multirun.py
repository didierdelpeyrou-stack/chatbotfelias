"""Multi-run wrapper pour benchmark.py — évaluation statistique.

Sprint 5.2-tune (systémique) : la variance LLM ±5pts entre runs rend
inutilisables les décisions sur un seul run. Ce script lance N runs et
calcule moyenne / médiane / écart-type / IC95 sur le success_rate global
et par module pour V1 et V2.

Usage :
  cd v2/
  PYTHONPATH=. ../.venv/bin/python scripts/benchmark_multirun.py --runs 3
  PYTHONPATH=. ../.venv/bin/python scripts/benchmark_multirun.py --runs 5 --limit 20

Pré-requis : V1 (port 8080) et V2 (port 8000) lancés + ANTHROPIC_API_KEY.

Sorties :
  - benchmark_results/multirun_<timestamp>.json
  - benchmark_results/multirun_<timestamp>.md
"""
from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import time
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent  # v2/
RESULTS_DIR = ROOT / "benchmark_results"


def run_one(run_idx: int, total_runs: int, limit: int | None) -> dict[str, Any]:
    """Lance un run de benchmark.py et retourne le résumé V1+V2.

    Re-utilise le runner existant (pas de duplication) ; capture le JSON
    de sortie via le timestamp du fichier.
    """
    print(f"\n=== Run {run_idx + 1}/{total_runs} ===")

    cmd = [sys.executable, str(ROOT / "scripts" / "benchmark.py")]
    if limit is not None:
        cmd += ["--limit", str(limit)]

    t0 = time.time()
    proc = subprocess.run(
        cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=600,
    )
    duration = time.time() - t0

    if proc.returncode != 0:
        print(f"  ❌ Run {run_idx + 1} échoué : code {proc.returncode}")
        print(proc.stderr[:500])
        return {"error": proc.stderr, "duration": duration}

    # Récupère le dernier fichier JSON généré par ce run
    jsons = sorted(RESULTS_DIR.glob("run_*.json"), key=lambda p: p.stat().st_mtime)
    if not jsons:
        return {"error": "Aucun fichier JSON généré", "duration": duration}

    latest_json = jsons[-1]
    with open(latest_json) as f:
        data = json.load(f)

    # Calcule summary V1 et V2 depuis rows
    v1_results = [r["v1"]["eval"] for r in data["rows"] if "eval" in r["v1"]]
    v2_results = [r["v2"]["eval"] for r in data["rows"] if "eval" in r["v2"]]

    def summarize(results: list[dict]) -> dict:
        n = len(results)
        if n == 0:
            return {"total": 0, "success_rate": 0.0, "by_module": {}}
        cats = [r["category"] for r in results]
        success = sum(1 for c in cats if c in ("correct", "hors_corpus_ok"))
        rate = round(success / n * 100, 1)
        by_module: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "success": 0})
        for r in results:
            by_module[r["module"]]["total"] += 1
            if r["category"] in ("correct", "hors_corpus_ok"):
                by_module[r["module"]]["success"] += 1
        rates_by_module = {
            m: round(d["success"] / d["total"] * 100, 1) if d["total"] else 0.0
            for m, d in by_module.items()
        }
        return {
            "total": n,
            "success_rate": rate,
            "rates_by_module": rates_by_module,
        }

    v1_summary = summarize(v1_results)
    v2_summary = summarize(v2_results)
    print(f"  ✅ Terminé en {duration:.0f}s — V1={v1_summary['success_rate']}% V2={v2_summary['success_rate']}%")

    return {
        "run_idx": run_idx,
        "duration": duration,
        "json_file": str(latest_json),
        "v1": v1_summary,
        "v2": v2_summary,
    }


def stats(values: list[float]) -> dict[str, float]:
    """Stats robustes : moyenne, médiane, écart-type, min, max, IC95 si N≥3."""
    n = len(values)
    if n == 0:
        return {}
    out = {
        "n": n,
        "mean": round(statistics.mean(values), 2),
        "median": round(statistics.median(values), 2),
        "min": round(min(values), 2),
        "max": round(max(values), 2),
    }
    if n >= 2:
        out["stdev"] = round(statistics.stdev(values), 2)
    if n >= 3:
        # IC 95 % approximatif : ±2σ (pour petit échantillon)
        out["ic95_low"] = round(out["mean"] - 2 * out["stdev"], 2)
        out["ic95_high"] = round(out["mean"] + 2 * out["stdev"], 2)
    return out


def aggregate(runs: list[dict]) -> dict:
    """Agrège N runs en stats globales V1 vs V2."""
    valid = [r for r in runs if "error" not in r]
    if not valid:
        return {"error": "Aucun run valide"}

    v1_rates = [r["v1"]["success_rate"] for r in valid]
    v2_rates = [r["v2"]["success_rate"] for r in valid]

    # Stats par module
    modules = set()
    for r in valid:
        modules.update(r["v1"].get("rates_by_module", {}).keys())
        modules.update(r["v2"].get("rates_by_module", {}).keys())

    by_module = {}
    for m in sorted(modules):
        v1_m = [r["v1"]["rates_by_module"].get(m, 0.0) for r in valid]
        v2_m = [r["v2"]["rates_by_module"].get(m, 0.0) for r in valid]
        by_module[m] = {"v1": stats(v1_m), "v2": stats(v2_m)}

    return {
        "n_runs": len(valid),
        "n_failed": len(runs) - len(valid),
        "global": {"v1": stats(v1_rates), "v2": stats(v2_rates)},
        "by_module": by_module,
    }


def render_markdown(agg: dict, runs: list[dict], cmd_args: argparse.Namespace) -> str:
    """Rapport Markdown statistique."""
    lines = []
    ts = datetime.now(UTC).isoformat(timespec="seconds")
    total_dur = sum(r.get("duration", 0) for r in runs)

    lines.append(f"# Multi-run benchmark — {ts}")
    lines.append("")
    lines.append(f"- **Runs** : {agg.get('n_runs', 0)} valides ({agg.get('n_failed', 0)} échoués)")
    lines.append(f"- **Limit** : {cmd_args.limit if cmd_args.limit else 'aucune (full corpus)'}")
    lines.append(f"- **Durée totale** : {total_dur:.0f}s")
    lines.append("")

    if "error" in agg:
        lines.append(f"⚠️ **Erreur** : {agg['error']}")
        return "\n".join(lines)

    g = agg["global"]
    lines.append("## Synthèse globale (success_rate %)")
    lines.append("")
    lines.append("| | V1 | V2 |")
    lines.append("|---|---:|---:|")
    for k in ("n", "mean", "median", "stdev", "min", "max", "ic95_low", "ic95_high"):
        if k in g["v1"] or k in g["v2"]:
            lines.append(f"| **{k}** | {g['v1'].get(k, '-')} | {g['v2'].get(k, '-')} |")
    lines.append("")

    if "stdev" in g["v2"]:
        delta_mean = g["v2"]["mean"] - g["v1"]["mean"]
        lines.append(f"**Δ moyenne V2 - V1** : {delta_mean:+.2f} pts")
        if "ic95_low" in g["v2"]:
            lines.append(f"**IC 95 % V2** : [{g['v2']['ic95_low']}, {g['v2']['ic95_high']}]")
        lines.append("")

    lines.append("## Par module")
    lines.append("")
    lines.append("| Module | V1 mean | V1 stdev | V2 mean | V2 stdev | V2 ic95 |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for m, d in agg["by_module"].items():
        v1 = d["v1"]
        v2 = d["v2"]
        ic95 = f"[{v2.get('ic95_low', '-')}, {v2.get('ic95_high', '-')}]" if "ic95_low" in v2 else "-"
        lines.append(
            f"| {m} | {v1.get('mean', '-')} | {v1.get('stdev', '-')} | "
            f"{v2.get('mean', '-')} | {v2.get('stdev', '-')} | {ic95} |"
        )

    lines.append("")
    lines.append("## Détail par run")
    lines.append("")
    lines.append("| Run | V1 % | V2 % | Durée |")
    lines.append("|---:|---:|---:|---:|")
    for r in runs:
        if "error" in r:
            lines.append(f"| {r['run_idx'] + 1} | ❌ | ❌ | {r.get('duration', 0):.0f}s |")
        else:
            lines.append(
                f"| {r['run_idx'] + 1} | {r['v1']['success_rate']} | "
                f"{r['v2']['success_rate']} | {r['duration']:.0f}s |"
            )
    lines.append("")
    lines.append("## Lecture")
    lines.append("")
    lines.append("- **stdev** : variabilité entre runs sur la même configuration. Une stdev > 5 pts indique du bruit LLM significatif.")
    lines.append("- **IC 95 %** : intervalle de confiance approximatif (mean ± 2σ). Une amélioration < 2σ n'est pas statistiquement significative.")
    lines.append("- **Décision tuning** : pour valider une modification de prompt/RAG, lancer multi-run AVANT et APRÈS, comparer les IC95.")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=3, help="Nombre de runs (défaut 3)")
    parser.add_argument("--limit", type=int, default=None, help="Limit questions par run")
    args = parser.parse_args()

    print(f"Multi-run : {args.runs} runs, limit={args.limit or 'full'}")
    RESULTS_DIR.mkdir(exist_ok=True)

    runs = []
    for i in range(args.runs):
        try:
            runs.append(run_one(i, args.runs, args.limit))
        except subprocess.TimeoutExpired:
            print(f"  ⏰ Run {i + 1} timeout (10 min)")
            runs.append({"run_idx": i, "error": "timeout", "duration": 600})

    agg = aggregate(runs)

    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    json_path = RESULTS_DIR / f"multirun_{ts}.json"
    md_path = RESULTS_DIR / f"multirun_{ts}.md"

    payload = {
        "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
        "args": {"runs": args.runs, "limit": args.limit},
        "runs": runs,
        "aggregate": agg,
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    md_path.write_text(render_markdown(agg, runs, args))

    print()
    print(f"✅ JSON : {json_path}")
    print(f"✅ MD   : {md_path}")
    print()

    if "global" in agg and "stdev" in agg["global"].get("v2", {}):
        v2g = agg["global"]["v2"]
        print(f"V2 : {v2g['mean']}% ± {v2g['stdev']} (n={v2g['n']})")
        if "ic95_low" in v2g:
            print(f"     IC 95% : [{v2g['ic95_low']}, {v2g['ic95_high']}]")

    return 0


if __name__ == "__main__":
    sys.exit(main())
