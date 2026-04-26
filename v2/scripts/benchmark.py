"""Runner benchmark V1 vs V2 — Sprint 4.2.

Lance les 50 questions du corpus (Sprint 4.1) sur V1 (port 8080) et
V2 (port 8000) en parallèle async, évalue chaque réponse, produit un
rapport markdown comparatif.

Pré-requis avant d'exécuter ce script :
  1. V1 lance : cd .. && .venv/bin/python app.py        (port 8080)
  2. V2 lance : cd v2 && PYTHONPATH=. KB_DATA_DIR=../data \\
                ../.venv/bin/python -m uvicorn app.main:app --port 8000
  3. ANTHROPIC_API_KEY exporté dans l'env

Usage :
  cd v2/
  PYTHONPATH=. ../.venv/bin/python scripts/benchmark.py
  # Optionnel : --limit N pour tester sur N questions seulement
  PYTHONPATH=. ../.venv/bin/python scripts/benchmark.py --limit 5

Sorties :
  - benchmark_results/run_<timestamp>.json   (résultats bruts)
  - benchmark_results/run_<timestamp>.md     (rapport lisible)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import httpx

from app.benchmark.evaluate import evaluate_answer, load_corpus, summarize
from app.benchmark.schema import BenchmarkQuestion, EvalResult

V1_URL = "http://localhost:8080/api/ask"
V2_URL = "http://localhost:8000/api/ask"

DEFAULT_TIMEOUT = 60.0


# ────────────────────────── Calls async ──────────────────────────

async def query_endpoint(
    client: httpx.AsyncClient, url: str, question: str, module: str
) -> tuple[str, str]:
    """Renvoie (answer, status). Status ∈ {ok, error_HTTP_xxx, error_exc, timeout}."""
    try:
        r = await client.post(url, json={"question": question, "module": module}, timeout=DEFAULT_TIMEOUT)
        if r.status_code != 200:
            return f"[ERROR HTTP {r.status_code}]", f"error_HTTP_{r.status_code}"
        body = r.json()
        # V1 et V2 ont la même clé "answer"
        return body.get("answer", ""), "ok"
    except httpx.TimeoutException:
        return "[TIMEOUT]", "timeout"
    except httpx.ConnectError as exc:
        return f"[CONNECT_ERROR: {exc}]", "error_connect"
    except Exception as exc:  # noqa: BLE001
        return f"[ERROR {type(exc).__name__}: {exc}]", "error_exc"


async def benchmark_question(
    client: httpx.AsyncClient, q: BenchmarkQuestion
) -> dict:
    """Lance V1 + V2 en parallèle pour une question, évalue, retourne un dict de comparaison."""
    t0 = time.perf_counter()
    v1_task = query_endpoint(client, V1_URL, q.question, q.module)
    v2_task = query_endpoint(client, V2_URL, q.question, q.module)
    (v1_ans, v1_status), (v2_ans, v2_status) = await asyncio.gather(v1_task, v2_task)
    elapsed = time.perf_counter() - t0

    return {
        "question_id": q.id,
        "module": q.module,
        "expected_type": q.expected_type,
        "question": q.question,
        "v1": {
            "answer": v1_ans,
            "status": v1_status,
            "eval": evaluate_answer(q, v1_ans).model_dump(),
        },
        "v2": {
            "answer": v2_ans,
            "status": v2_status,
            "eval": evaluate_answer(q, v2_ans).model_dump(),
        },
        "elapsed_seconds": round(elapsed, 2),
    }


async def run_benchmark(questions: list[BenchmarkQuestion]) -> list[dict]:
    """Lance le benchmark sur la liste de questions, en respectant un parallélisme raisonnable.

    On limite à 5 requêtes simultanées (semaphore) pour ne pas saturer Claude
    (rate limit Anthropic). Sur 50 Q, ~5 batches × ~10s/batch = ~50s.
    """
    sem = asyncio.Semaphore(5)

    async def _wrapped(q: BenchmarkQuestion):
        async with sem:
            return await benchmark_question(client, q)

    timeout = httpx.Timeout(DEFAULT_TIMEOUT, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        tasks = [_wrapped(q) for q in questions]
        return await asyncio.gather(*tasks)


# ────────────────────────── Rapport markdown ──────────────────────────

def _category_table(results: list[EvalResult]) -> dict[str, int]:
    return dict(Counter(r.category for r in results))


def _success_rate(by_cat: dict[str, int], total: int) -> float:
    if not total:
        return 0.0
    success = by_cat.get("correct", 0) + by_cat.get("hors_corpus_ok", 0)
    return round(success / total * 100, 1)


def render_report(rows: list[dict], started_at: str, duration: float) -> str:
    """Construit un rapport markdown comparatif lisible."""
    n = len(rows)
    v1_evals = [EvalResult.model_validate(r["v1"]["eval"]) for r in rows]
    v2_evals = [EvalResult.model_validate(r["v2"]["eval"]) for r in rows]
    v1_cats = _category_table(v1_evals)
    v2_cats = _category_table(v2_evals)

    out = []
    out.append(f"# Benchmark V1 ↔ V2 — {started_at}\n")
    out.append(f"- **Questions** : {n}")
    out.append(f"- **Durée totale** : {duration:.1f}s")
    out.append("- **V1** : Flask `http://localhost:8080/api/ask`")
    out.append("- **V2** : FastAPI `http://localhost:8000/api/ask`")
    out.append("")

    out.append("## 1. Synthèse globale\n")
    out.append("| Catégorie | V1 | V2 | Δ |")
    out.append("|---|---:|---:|---:|")
    all_cats = sorted(set(v1_cats) | set(v2_cats))
    for cat in all_cats:
        v1c = v1_cats.get(cat, 0)
        v2c = v2_cats.get(cat, 0)
        delta = v2c - v1c
        delta_str = f"{'+' if delta > 0 else ''}{delta}"
        out.append(f"| {cat} | {v1c} | {v2c} | {delta_str} |")
    out.append(f"| **TOTAL** | **{n}** | **{n}** | — |")
    out.append("")

    v1_success = _success_rate(v1_cats, n)
    v2_success = _success_rate(v2_cats, n)
    out.append("**Taux de succès** (correct + hors_corpus_ok) :")
    out.append(f"- V1 : {v1_success}%")
    out.append(f"- V2 : {v2_success}%")
    out.append(f"- Δ : {'+' if v2_success >= v1_success else ''}{v2_success - v1_success:.1f} pts")
    out.append("")

    # Par module
    out.append("## 2. Détail par module\n")
    by_module: dict[str, dict] = {}
    for r in rows:
        m = r["module"]
        by_module.setdefault(m, {"v1": [], "v2": []})
        by_module[m]["v1"].append(EvalResult.model_validate(r["v1"]["eval"]))
        by_module[m]["v2"].append(EvalResult.model_validate(r["v2"]["eval"]))

    out.append("| Module | N | V1 succès | V2 succès | Δ |")
    out.append("|---|---:|---:|---:|---:|")
    for module, evals in sorted(by_module.items()):
        n_m = len(evals["v1"])
        v1_s = _success_rate(_category_table(evals["v1"]), n_m)
        v2_s = _success_rate(_category_table(evals["v2"]), n_m)
        delta = round(v2_s - v1_s, 1)
        out.append(f"| {module} | {n_m} | {v1_s}% | {v2_s}% | {'+' if delta >= 0 else ''}{delta} pts |")
    out.append("")

    # Différences notables
    out.append("## 3. Différences saillantes\n")
    v1_better = [r for r in rows if _better(r["v1"]["eval"], r["v2"]["eval"])]
    v2_better = [r for r in rows if _better(r["v2"]["eval"], r["v1"]["eval"])]
    out.append(f"- **V2 > V1** sur {len(v2_better)} question(s)")
    out.append(f"- **V1 > V2** sur {len(v1_better)} question(s)")
    out.append("")

    if v2_better:
        out.append("### Questions où V2 fait mieux que V1")
        out.append("")
        for r in v2_better[:10]:
            out.append(
                f"- **{r['question_id']}** ({r['module']}/{r['expected_type']}) — "
                f"V1={r['v1']['eval']['category']} → V2={r['v2']['eval']['category']}"
            )
            out.append(f"  > _{r['question'][:120]}_")
        out.append("")

    if v1_better:
        out.append("### Questions où V1 fait mieux que V2 (régressions à investiguer)")
        out.append("")
        for r in v1_better[:10]:
            out.append(
                f"- **{r['question_id']}** ({r['module']}/{r['expected_type']}) — "
                f"V1={r['v1']['eval']['category']} → V2={r['v2']['eval']['category']}"
            )
            out.append(f"  > _{r['question'][:120]}_")
        out.append("")

    out.append("## 4. Erreurs / timeouts\n")
    err_v1 = [r for r in rows if r["v1"]["status"] != "ok"]
    err_v2 = [r for r in rows if r["v2"]["status"] != "ok"]
    out.append(f"- V1 : {len(err_v1)} erreur(s) — {Counter(r['v1']['status'] for r in err_v1)}")
    out.append(f"- V2 : {len(err_v2)} erreur(s) — {Counter(r['v2']['status'] for r in err_v2)}")
    out.append("")

    return "\n".join(out)


# Ordre relatif des catégories pour décider "lequel est meilleur" :
# du meilleur (0) au pire (5).
_CAT_ORDER = {
    "correct": 0,
    "hors_corpus_ok": 0,        # un refus juste vaut une bonne réponse
    "partial": 1,
    "false_refuse": 2,           # devrait répondre mais refuse → moyennement grave
    "incorrect": 3,
    "false_response": 4,         # devrait refuser mais répond → grave
    "hallucinated": 5,           # le pire : invente
}


def _better(a_eval: dict, b_eval: dict) -> bool:
    """True si a est strictement meilleur que b."""
    return _CAT_ORDER.get(a_eval["category"], 99) < _CAT_ORDER.get(b_eval["category"], 99)


# ────────────────────────── CLI ──────────────────────────

async def main():
    parser = argparse.ArgumentParser(description="Benchmark V1↔V2 sur le corpus Sprint 4.1")
    parser.add_argument("--limit", type=int, default=None, help="Limiter à N questions (pour test rapide)")
    parser.add_argument("--out-dir", type=Path, default=Path("benchmark_results"))
    parser.add_argument("--module", choices=["juridique", "formation", "rh", "gouvernance"], help="Limiter à un module")
    parser.add_argument("--llm-judge", action="store_true",
                        help="Évalue V2 avec Claude Haiku 4.5 au lieu du rule-based")
    args = parser.parse_args()

    corpus = load_corpus()
    questions = corpus.questions
    if args.module:
        questions = [q for q in questions if q.module == args.module]
    if args.limit:
        questions = questions[:args.limit]

    print(f"📊 Benchmark : {len(questions)} questions sur V1 ({V1_URL}) ↔ V2 ({V2_URL})")
    if args.llm_judge:
        print("🧑‍⚖️  LLM-judge actif : Claude Haiku 4.5 évaluera chaque réponse V2")
    started = datetime.now(UTC).isoformat(timespec="seconds")
    t0 = time.perf_counter()
    rows = await run_benchmark(questions)
    duration = time.perf_counter() - t0
    print(f"✅ Bench terminé en {duration:.1f}s")

    # Sprint 5.2-stack Phase A2 : LLM-judge évaluation
    if args.llm_judge:
        from app.benchmark.llm_judge import judge_answer
        from app.llm.claude import ClaudeClient
        from app.settings import get_settings

        settings = get_settings()
        if not settings.anthropic_api_key:
            print("⚠️ ANTHROPIC_API_KEY manquante : LLM-judge désactivé")
        else:
            judge_client = ClaudeClient(
                api_key=settings.anthropic_api_key,
                model=settings.claude_model,
                max_tokens=300,  # JSON court suffit
                timeout=30.0,
            )
            t_judge = time.perf_counter()
            sem = asyncio.Semaphore(5)

            async def _judge(row, version="v2"):
                q = next((q for q in questions if q.id == row["question_id"]), None)
                if q is None:
                    return row
                async with sem:
                    new_eval = await judge_answer(judge_client, q, row[version]["answer"])
                row[version]["eval_rule"] = row[version]["eval"]
                row[version]["eval"] = new_eval.model_dump()
                return row

            print(f"🧑‍⚖️  Jugement de {len(rows)} réponses V2 par LLM-judge...")
            await asyncio.gather(*[_judge(r) for r in rows])
            print(f"✅ LLM-judge terminé en {time.perf_counter() - t_judge:.1f}s")

    # Synthèse à l'écran
    v1_evals = [EvalResult.model_validate(r["v1"]["eval"]) for r in rows]
    v2_evals = [EvalResult.model_validate(r["v2"]["eval"]) for r in rows]
    print(f"\nV1 : {summarize(v1_evals)}")
    print(f"V2 : {summarize(v2_evals)}")

    # Sauvegarde JSON + rapport markdown
    args.out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = args.out_dir / f"run_{stamp}.json"
    md_path = args.out_dir / f"run_{stamp}.md"

    with json_path.open("w", encoding="utf-8") as f:
        json.dump({"started_at": started, "duration": duration, "rows": rows}, f, ensure_ascii=False, indent=2)

    md_path.write_text(render_report(rows, started, duration), encoding="utf-8")
    print(f"\n📄 Rapport : {md_path}")
    print(f"📦 Données : {json_path}")


if __name__ == "__main__":
    asyncio.run(main())
