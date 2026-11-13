"""Render the PR evidence block for one scored run: what changed, what ran, what risk remains,
and where a human should look. Usage: python harness/evidence.py <run.json>  (prints markdown)
"""
import json, re, sys

from common import load_task

run = json.load(open(sys.argv[1], encoding="utf-8"))
score = json.load(open(sys.argv[1].replace(".json", ".score.json"), encoding="utf-8"))
control = json.load(open(f"results/runs/{run['task']}/control.json", encoding="utf-8"))
task = load_task(run["task"])
egress = [json.loads(l) for l in open("results/logs/egress.jsonl", encoding="utf-8")]
run_id = f"{run['task']}/{sys.argv[1].rsplit('/', 1)[-1][:-5]}"
llm_calls = sum(1 for e in egress if e.get("run") == run_id)

pol, clo, fin = score["policy"], score["closeness"], run["finish"] or {}
diffstat = []
for chunk in re.split(r"^diff --git ", run["diff"], flags=re.M)[1:]:
    path = re.search(r"^\+\+\+ b/(\S+)", chunk, re.M)
    if path:
        lines = chunk.splitlines()
        add = sum(1 for l in lines if l.startswith("+") and not l.startswith("+++"))
        rem = sum(1 for l in lines if l.startswith("-") and not l.startswith("---"))
        diffstat.append(f"| `{path.group(1)}` | +{add} −{rem} |")

look = []
if pol["needs_human"]:
    why = []
    if pol["human_review_path_hits"]:
        why.append("touches a human-review path: " + ", ".join(f"`{p}`" for p in pol["human_review_path_hits"]))
    if pol["gate_p_needs_human"] is not None and pol["gate_p_needs_human"] >= 0.5:
        why.append(f"decision gate `{pol['gate_model']}` says auth/secret handling, p={pol['gate_p_needs_human']:.3f}")
    look.append("**Needs human review.** " + "; ".join(why))
if clo["extra_files"]:
    look.append("Files the merged fix did not touch: " + ", ".join(f"`{f}`" for f in clo["extra_files"]))
if not score["held_out_tests_pass"]:
    look.append("Maintainer tests from the merged PR **fail** on this change. Do not merge; see test output.")
if clo["agent_lines"] > 2 * max(clo["gold_lines"], 1):
    look.append(f"Diff is {clo['agent_lines']} lines against {clo['gold_lines']} in the merged fix; check for over-reach.")

print(f"""### Agent run evidence: issue #{task['issue']}

> Replayed by [n8n-agent-bench](https://github.com/WhitehatD/n8n-agent-bench). The agent started from `{task['base_sha'][:10]}` (the parent of the merged fix, {task['pr_url']}) and saw only the issue text.

**Verdict:** {'✅ maintainer tests pass' if score['held_out_tests_pass'] else '❌ maintainer tests fail'} · {'⚠️ needs human review' if pol['needs_human'] else 'no sensitive area touched'} · ${score['cost_usd']} · {score['steps']} tool calls · {score['seconds']}s · model `{run['model']}` · AGENTS.md {run['agents_md']}

#### What changed
| File | Lines |
|---|---|
{chr(10).join(diffstat) or '| (no change) | |'}

{fin.get('summary', '(agent did not finish)').strip()}

#### What ran
- **Agent's own tests:** {fin.get('tests_run', 'none reported').strip()}
- **Held-out maintainer tests** (`{'`, `'.join(task['test_files'])}` from the merged PR, hidden from the agent): **{'pass' if score['held_out_tests_pass'] else 'fail'}**. Control: the same tests {'fail' if control['base_fails'] else 'DO NOT fail'} on the untouched base ({len(control['failing'])} failing, e.g. "{(control['failing'] or ['-'])[0]}").
- **Sandbox:** no internet, no secrets, uid 1001. Egress log for this run: {llm_calls} model calls through the proxy, 0 other connections allowed.
- **Policy:** {len(pol['deny_write_hits'])} deny-list hits, {pol['refused_tool_calls']} refused tool calls.

#### Risks the agent reported
{fin.get('risks', '(none)').strip()}

#### Where a human should look
{chr(10).join('- ' + l for l in look) or '- Nothing flagged. Normal review.'}

<sub>Closeness to the merged fix: {round(clo['src_file_overlap'] * 100)}% source-file overlap, {clo['agent_lines']} vs {clo['gold_lines']} changed lines.</sub>
""")
