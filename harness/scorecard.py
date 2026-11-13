"""Build results/scorecard.md from every scored run (and the decision-model bench if present).
Usage: python harness/scorecard.py
"""
import glob, json, os

from common import load_task

EXCLUDED = {"n8n-43353": "held-out test is a cli integration test that needs a database"}
rows, arms = {}, {"on": [], "off": []}
for f in sorted(glob.glob("results/runs/*/*.score.json")):
    s = json.load(open(f, encoding="utf-8"))
    if s["task"] in EXCLUDED:
        continue
    rows.setdefault(s["task"], {})[s["agents_md"]] = s
    arms[s["agents_md"]].append(s)


def cell(s):
    if not s:
        return "–"
    mark = "✅" if s["held_out_tests_pass"] else "❌"
    return f"{mark} ${s['cost_usd']:.3f}"


all_runs = arms["on"] + arms["off"]
passed = [s for s in all_runs if s["held_out_tests_pass"]]
solved = [t for t, r in rows.items() if any(s["held_out_tests_pass"] for s in r.values())]
lines = [
    f"**{len(passed)}/{len(all_runs)} runs pass n8n's own maintainer tests** "
    f"({len(solved)}/{len(rows)} tasks solved at least once). Model: `deepseek/deepseek-v4-flash`. "
    f"Total spend ${sum(s['cost_usd'] for s in all_runs):.2f}; "
    f"${sum(s['cost_usd'] for s in passed) / max(len(passed), 1):.3f} per passing fix.",
    "",
    f"- AGENTS.md **on**: {sum(s['held_out_tests_pass'] for s in arms['on'])}/{len(arms['on'])} pass",
    f"- AGENTS.md **off**: {sum(s['held_out_tests_pass'] for s in arms['off'])}/{len(arms['off'])} pass",
    f"- Policy: {sum(len(s['policy']['deny_write_hits']) for s in all_runs)} deny-list writes, "
    f"{sum(s['policy']['refused_tool_calls'] for s in all_runs)} refused tool calls, "
    f"{sum(s['policy']['needs_human'] for s in all_runs)} runs flagged for human review",
    "",
    "| Task | Issue | Package | AGENTS.md on | AGENTS.md off | Needs human |",
    "|---|---|---|---|---|---|",
]
for tid in sorted(rows):
    t, r = load_task(tid), rows[tid]
    human = any(s["policy"]["needs_human"] for s in r.values())
    lines.append(f"| [{tid}]({t['pr_url']}) | [#{t['issue']}]({t['issue_url']}) {t['issue_title'][:60]} | "
                 f"`{t['package'].replace('packages/', '')}` | {cell(r.get('on'))} | {cell(r.get('off'))} | {'⚠️' if human else ''} |")
for tid, why in EXCLUDED.items():
    lines.append(f"\nExcluded: {tid}, {why}.")

if os.path.exists("results/decider_bench.md"):
    lines += ["", "### Decision models on the same runs", "", open("results/decider_bench.md", encoding="utf-8").read()]
open("results/scorecard.md", "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("\n".join(lines[:8]))

# Per-run egress summary (counts only, no payloads), so the published evidence is checkable.
summary = {}
for l in open("results/logs/egress.jsonl", encoding="utf-8"):
    e = json.loads(l)
    key = e.get("run") or f"<{e.get('client')}>"
    s = summary.setdefault(key, {"llm_calls": 0, "allowed_connects": {}, "denied": {}})
    if e.get("kind") == "llm":
        s["llm_calls"] += 1
    elif e.get("allowed"):
        s["allowed_connects"][e.get("host")] = s["allowed_connects"].get(e.get("host"), 0) + 1
    else:
        h = e.get("host") or e.get("target")
        s["denied"][h] = s["denied"].get(h, 0) + 1
json.dump(summary, open("results/egress-summary.json", "w", encoding="utf-8"), indent=1, sort_keys=True)
