"""Live status of the benchmark run: what each task is doing right now, and the score so far.
Usage: python harness/status.py
"""
import glob, json, os, subprocess

from common import ROOT  # noqa: F401  (chdir to the repo)

tasks = [t["id"] for t in json.load(open("tasks/tasks.json", encoding="utf-8"))]
running = subprocess.run(["docker", "ps", "--format", "{{.Names}}"], capture_output=True, text=True).stdout.split()
agents = {n for n in running if n.startswith("agent-")}

done = passed = 0
cost = 0.0
for t in tasks:
    d = f"results/runs/{t}"
    cells = []
    for arm in ("on", "off"):
        s = f"{d}/deepseek_deepseek-v4-flash-amd-{arm}.score.json"
        if os.path.exists(s):
            sc = json.load(open(s, encoding="utf-8"))
            done += 1; passed += sc["held_out_tests_pass"]; cost += sc["cost_usd"]
            cells.append(f"{arm}:{'PASS' if sc['held_out_tests_pass'] else 'fail'}")
        elif any(a.startswith(f"agent-{t}") and a.endswith(f"amd-{arm}") for a in agents):
            cells.append(f"{arm}:agent running")
        else:
            cells.append(f"{arm}:-")
    stage = ("waiting" if not os.path.isdir(d) else
             "setup failed" if os.path.exists(f"{d}/prepare.log") and "ERR" in open(f"{d}/prepare.log", errors="replace").read() else
             "setup" if not os.path.exists(f"{d}/control.json") else "ready")
    print(f"{t:<10} {stage:<13} {'  '.join(cells)}")
print(f"\n{done}/40 runs scored, {passed} pass, ${cost:.2f} spent, {len(agents)} agent containers running now")
