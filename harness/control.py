"""Control: the merged PR's tests must FAIL on the untouched base, or the task proves nothing.

Runs on a throwaway copy of the base tree, inside the sandbox (no network).
Usage: python harness/control.py <task-id>   (writes results/runs/<id>/control.json)
"""
import json, os, re, sys

from common import clone, load_task, run_held_out, sx

task = load_task(sys.argv[1])
work = f"/work/runs/{task['id']}/control"
sx(clone(f"/work/base/{task['id']}", work))
code, out = run_held_out(task, work)
sx(f"rm -rf {work}")
failing = re.findall(r"^\s*[×✕]\s+(.+?)(?:\s+\d+m?s)?$", out, re.M)[:10]
# A run that errors before any test executes (no test files, config crash) is not a valid control.
res = {"task": task["id"], "base_fails": code != 0 and bool(failing), "failing": failing, "tail": out[-1500:]}
os.makedirs(f"results/runs/{task['id']}", exist_ok=True)
json.dump(res, open(f"results/runs/{task['id']}/control.json", "w", encoding="utf-8"), indent=1)
print(f"control {task['id']}: base_fails={res['base_fails']} {res['failing'][:2]}")
