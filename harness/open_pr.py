"""Open one evidence PR on the FORK (WhitehatD/n8n), never on n8n-io/n8n.

Creates two branches on the fork: bench/base-<pr> at the parent of the merged fix, and
bench/<pr>-<arm> = base + the agent's diff. The PR goes base <- agent inside the fork, with the
evidence block as its body. Usage: python harness/open_pr.py <run.json>
"""
import json, os, subprocess, sys, tempfile

from common import load_task

FORK = "WhitehatD/n8n"
run_path = sys.argv[1]
run = json.load(open(run_path, encoding="utf-8"))
task = load_task(run["task"])
base_branch = f"bench/base-{task['pr']}"
head_branch = f"bench/{task['pr']}-amd-{run['agents_md']}"
body = subprocess.check_output([sys.executable, "harness/evidence.py", run_path], encoding="utf-8")


def git(*a, cwd=None, inp=None):
    return subprocess.run(["git", *a], cwd=cwd, input=inp, check=True, capture_output=True, text=True).stdout


wt = tempfile.mkdtemp(prefix="pr-")
git("-C", "cache/n8n.git", "worktree", "add", "--detach", wt, task["base_sha"])
try:
    if run["diff"].strip():
        git("-c", "core.autocrlf=false", "apply", "--whitespace=nowarn", "-", cwd=wt, inp=run["diff"])
    git("add", "-A", cwd=wt)
    msg = f"fix: agent run for #{task['issue']} ({run['model']}, AGENTS.md {run['agents_md']})\n\nReplayed by n8n-agent-bench."
    git("-c", "user.name=n8n-agent-bench", "-c", "user.email=bench@ciocandco.com", "commit", "--allow-empty", "-qm", msg, cwd=wt)
    url = f"https://github.com/{FORK}.git"
    git("push", "-f", url, f"{task['base_sha']}:refs/heads/{base_branch}", cwd=wt)
    git("push", "-f", url, f"HEAD:refs/heads/{head_branch}", cwd=wt)
finally:
    git("-C", "cache/n8n.git", "worktree", "remove", "--force", wt)

verdict = "pass" if json.load(open(run_path.replace(".json", ".score.json"), encoding="utf-8"))["held_out_tests_pass"] else "fail"
title = f"[bench {verdict}, AGENTS.md {run['agents_md']}] #{task['issue']}: {task['issue_title'][:60]}"
existing = subprocess.run(["gh", "pr", "list", "-R", FORK, "--head", head_branch, "--json", "url", "-q", ".[0].url"],
                          capture_output=True, text=True).stdout.strip()
if existing:
    subprocess.run(["gh", "pr", "edit", existing, "-R", FORK, "--title", title, "--body", body], check=True, capture_output=True)
    url = existing
else:
    url = subprocess.check_output(["gh", "pr", "create", "-R", FORK, "--base", base_branch, "--head", head_branch,
                                   "--title", title, "--body", body], encoding="utf-8").strip()
index = json.load(open("results/prs.json", encoding="utf-8")) if os.path.exists("results/prs.json") else {}
index[f"{task['id']}/{run['agents_md']}"] = url
json.dump(index, open("results/prs.json", "w", encoding="utf-8"), indent=1, sort_keys=True)
print(url)
