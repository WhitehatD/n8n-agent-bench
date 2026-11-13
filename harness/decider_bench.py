"""Benchmark decision models on labels the agent benchmark produced.

Every scored agent run has a ground truth: did n8n's held-out maintainer tests pass?
That gives two decisions worth automating, asked of every decision model:

  verifier  state = issue + the agent's diff + the tests it says it ran.
            "Will the maintainer tests pass?"  -> reject bad agent PRs before a human reads them.
  triage    state = issue only (one per task; label = any arm passed).
            "Will a cheap agent fix this?"     -> skip runs that will fail, before spending on them.

Metrics per model: accuracy, Brier score (calibration), and for the verifier the operational
numbers: share of failing PRs it would reject, and share of passing PRs it would wrongly reject.

Usage: python harness/decider_bench.py [-j 6]   -> results/decider_bench.json + .md
"""
import argparse, glob, json, os, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

from common import load_task

ap = argparse.ArgumentParser()
ap.add_argument("-j", type=int, default=6)
args = ap.parse_args()
KEY = os.environ.get("OPENROUTER_API_KEY") or next(
    l.split("=", 1)[1].strip() for l in open(os.path.expanduser("~/.config/openrouter/.env")) if l.startswith("OPENROUTER_API_KEY="))
MODELS = [
    "morph/reflex", "typesafe/jev-1.14", "google/gemini-decision-1", "openai/gpt-6-luna-decisions",
    "perplexity/pplx-decider-v1.2", "perplexity/pplx-decider-flash-v1.2", "perplexity/pplx-decider-v1.3:free",
    "cloudflare/clef", "cloudflare/clef-flash", "liquid/d1.1", "liquid/d1-ultra", "microsoft/microsoft-decision-1",
    "nace-ai/drex-max", "upstage/solar-decide", "baseten/mammoth-1", "baseten/joey-1", "scaledown/classify-1",
]
Q = {
    "verifier": {"type": "noul",
        "instructions": "An automated coding agent tried to fix the GitHub issue below. Will the maintainers' own unit tests for this fix pass on the agent's change?",
        "criteria": {"true": "The diff addresses the root cause described in the issue, in the right file, with the behaviour the issue asks for.",
                     "false": "The diff is empty, misses the root cause, patches a symptom, changes the wrong place, or only adds tests."}},
    "triage": {"type": "noul",
        "instructions": "Will a cheap autonomous coding agent, working alone in a sandbox, produce a fix for this n8n issue that passes the maintainers' tests?",
        "criteria": {"true": "A small, local, well-specified bug: one function or node, clear expected behaviour, easy to reproduce in a unit test.",
                     "false": "A subtle bug in runtime internals, concurrency, streaming, token counting or cross-package behaviour, or an underspecified report."}},
}

runs = []
for f in sorted(glob.glob("results/runs/*/*.score.json")):
    s = json.load(open(f, encoding="utf-8"))
    if s["task"] == "n8n-43353":
        continue  # excluded: held-out test needs a database
    if s.get("timed_out"):
        continue  # no diff to judge
    r = json.load(open(f.replace(".score.json", ".json"), encoding="utf-8"))
    runs.append((s, r))
tasks = {}
for s, _ in runs:
    tasks[s["task"]] = tasks.get(s["task"], False) or s["held_out_tests_pass"]


def issue_text(t, n=4000):
    return f"Issue #{t['issue']}: {t['issue_title']}\n\n{t['issue_body'][:n]}"


items = []
for s, r in runs:
    t = load_task(s["task"])
    state = (issue_text(t, 3000) + "\n\n--- agent diff ---\n" + (r["diff"][:8000] or "(empty)") +
             "\n\n--- tests the agent says it ran ---\n" + str((r.get("finish") or {}).get("tests_run", "none"))[:800])
    items.append({"q": "verifier", "id": f"{s['task']}/{s['agents_md']}", "state": state, "label": s["held_out_tests_pass"]})
for tid, solved in tasks.items():
    t = load_task(tid)
    items.append({"q": "triage", "id": tid, "state": f"Package: {t['package']}\n\n" + issue_text(t), "label": solved})


def ask(model, it):
    body = json.dumps({"model": model, "state": it["state"], "questions": {"a": Q[it["q"]]}}).encode()
    for attempt in range(3):
        try:
            t0 = time.time()
            req = urllib.request.Request("https://openrouter.ai/api/alpha/decisions", body,
                                         {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json", "X-Title": "n8n-agent-bench"})
            out = json.load(urllib.request.urlopen(req, timeout=90))
            a = out["answers"]["a"]
            return {"p": a.get("noul", a.get("probability")), "cost": out.get("usage", {}).get("cost", 0) or 0,
                    "s": time.time() - t0}
        except Exception as e:
            err = str(e)[:120]
            time.sleep(2 * (attempt + 1))
    return {"error": err}


jobs = [(m, it) for m in MODELS for it in items]
with ThreadPoolExecutor(args.j) as ex:
    answers = list(ex.map(lambda mi: ask(*mi), jobs))

res = {}
for (m, it), a in zip(jobs, answers):
    res.setdefault(m, {}).setdefault(it["q"], []).append({**a, "label": it["label"], "id": it["id"]})


def summarise(xs):
    ok = [x for x in xs if "p" in x and x["p"] is not None]
    if not ok:
        return {"n": 0, "error": next((x.get("error") for x in xs if "error" in x), "no answers")}
    acc = sum((x["p"] >= 0.5) == x["label"] for x in ok) / len(ok)
    brier = sum((x["p"] - x["label"]) ** 2 for x in ok) / len(ok)
    fails = [x for x in ok if not x["label"]]; passes = [x for x in ok if x["label"]]
    return {"n": len(ok), "acc": round(acc, 3), "brier": round(brier, 3),
            "rejects_failing": round(sum(x["p"] < 0.5 for x in fails) / max(len(fails), 1), 3),
            "rejects_passing": round(sum(x["p"] < 0.5 for x in passes) / max(len(passes), 1), 3),
            "cost_usd": round(sum(x["cost"] for x in ok), 5), "p50_s": round(sorted(x["s"] for x in ok)[len(ok) // 2], 2)}


table = {m: {q: summarise(v) for q, v in qs.items()} for m, qs in res.items()}
base = {q: round(max(sum(i["label"] for i in items if i["q"] == q), sum(not i["label"] for i in items if i["q"] == q)) /
                 max(sum(i["q"] == q for i in items), 1), 3) for q in Q}
json.dump({"n_runs": len(runs), "n_tasks": len(tasks), "majority_baseline": base, "table": table, "raw": res},
          open("results/decider_bench.json", "w", encoding="utf-8"), indent=1)

lines = [f"Decision models on {len(runs)} agent runs / {len(tasks)} tasks. Majority-class baseline: "
         f"verifier {base['verifier']}, triage {base['triage']}.", "",
         "| Model | Verifier acc | Brier | rejects failing PRs | wrongly rejects passing | Triage acc | Brier | cost | p50 |",
         "|---|---|---|---|---|---|---|---|---|"]
for m, qs in sorted(table.items(), key=lambda kv: -(kv[1].get("verifier", {}).get("acc") or 0)):
    v, t = qs.get("verifier", {}), qs.get("triage", {})
    if not v.get("n"):
        lines.append(f"| {m} | error: {v.get('error', '')[:40]} |||||||| ")
        continue
    lines.append(f"| {m} | {v['acc']} | {v['brier']} | {v['rejects_failing']} | {v['rejects_passing']} | "
                 f"{t.get('acc', '-')} | {t.get('brier', '-')} | ${v['cost_usd'] + t.get('cost_usd', 0):.4f} | {v['p50_s']}s |")
open("results/decider_bench.md", "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("\n".join(lines))
