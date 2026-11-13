"""Run the whole benchmark in parallel.

Per task: prepare the base (installer container), control (base must fail the held-out tests),
then one agent run per (model, AGENTS.md) arm, all arms of a task at once.
Already-scored runs are skipped, so this can be re-run after a crash.

Usage: python harness/run_all.py --models deepseek/deepseek-v4-flash --arms on off -j 4
"""
import argparse, json, os, shutil, subprocess, sys
import threading
from concurrent.futures import ThreadPoolExecutor

from common import sx

# Git Bash, not WSL bash (the WSL one in System32 has no python on PATH).
BASH = "C:/Program Files/Git/bin/bash.exe" if os.name == "nt" else shutil.which("bash")

ap = argparse.ArgumentParser()
ap.add_argument("--models", nargs="+", default=["deepseek/deepseek-v4-flash"])
ap.add_argument("--arms", nargs="+", default=["on", "off"])
ap.add_argument("-j", type=int, default=3)
ap.add_argument("--only", nargs="*")
args = ap.parse_args()
tasks = [t["id"] for t in json.load(open("tasks/tasks.json", encoding="utf-8"))]
if args.only:
    tasks = [t for t in tasks if t in args.only]


def tag(model, arm):
    return f"{model.replace('/', '_').replace(':', '_')}-amd-{arm}"


def log(msg):
    print(msg, flush=True)


AGENT_SLOTS = threading.Semaphore(4)  # agent containers idle at <100 MB while waiting on the model
PREPARE_LOCK = threading.Semaphore(2)  # two installs/builds at a time: builds are the RAM hog, agents are not


def one_task(tid):
    d = f"results/runs/{tid}"
    os.makedirs(d, exist_ok=True)
    todo = [(m, a) for m in args.models for a in args.arms if not os.path.exists(f"{d}/{tag(m, a)}.score.json")]
    if not todo:
        return log(f"{tid}: all arms already scored")
    if sx(f"test -f /work/base/{tid}/.prepared")[0] != 0:
      with PREPARE_LOCK:
        with open(f"{d}/prepare.log", "w") as f:
            if subprocess.run([BASH, "harness/prepare.sh", tid], stdout=f, stderr=subprocess.STDOUT).returncode:
                return log(f"{tid}: PREPARE FAILED (see {d}/prepare.log)")
    if not os.path.exists(f"{d}/control.json"):
        r = subprocess.run([sys.executable, "harness/control.py", tid], capture_output=True, text=True)
        log(r.stdout.strip() or r.stderr[-500:])
    if not json.load(open(f"{d}/control.json", encoding="utf-8"))["base_fails"]:
        return log(f"{tid}: control did not fail on base, task excluded")

    def arm(ma):
      with AGENT_SLOTS:
        with open(f"{d}/{tag(*ma)}.log", "w", encoding="utf-8") as f:
            r = subprocess.run([sys.executable, "harness/run_one.py", tid, *ma], stdout=f, stderr=subprocess.STDOUT)
        s = f"{d}/{tag(*ma)}.score.json"
        if r.returncode or not os.path.exists(s):
            return log(f"{tid} {tag(*ma)}: FAILED (see log)")
        sc = json.load(open(s, encoding="utf-8"))
        log(f"{tid} {tag(*ma)}: tests {'PASS' if sc['held_out_tests_pass'] else 'fail'}  "
            f"${sc['cost_usd']}  {sc['steps']} steps  {sc['seconds']}s  needs_human={sc['policy']['needs_human']}")

    with ThreadPoolExecutor(len(todo)) as ex:
        list(ex.map(arm, todo))


with ThreadPoolExecutor(args.j) as ex:
    list(ex.map(one_task, tasks))
log("ALL DONE")
