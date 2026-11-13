"""One agent run in its own throwaway container, on a private copy of a prepared base tree, then scoring.

The agent container mounts ONLY its own copy (a volume subpath), so it cannot see the other
tasks' trees, the base trees, or the harness. It sits on the jail network (no route out except
the egress proxy), runs as uid 1001 with no capabilities, and has its own memory and pid caps.

Usage: python harness/run_one.py <task-id> <model> <on|off>
Writes results/runs/<id>/<tag>.json (trajectory + diff) and <tag>.score.json.
"""
import json, os, subprocess, sys, time

from common import clone, load_task, sx

task_id, model, amd = sys.argv[1], sys.argv[2], sys.argv[3]
task = load_task(task_id)
tag = f"{model.replace('/', '_').replace(':', '_')}-amd-{amd}"
rel, work = f"runs/{task_id}/{tag}", f"/work/runs/{task_id}/{tag}"
os.makedirs(f"results/runs/{task_id}", exist_ok=True)
out = f"results/runs/{task_id}/{tag}.json"

sx(clone(f"/work/base/{task_id}", work))
sx(f"rm -rf {work}.bench && mkdir -p {work}.bench")
for src, dst in (("sandbox/agent.py", "agent.py"), ("policy/policy.json", "policy.json")):
    sx(f"cat > {work}.bench/{dst}", inp=open(src, "rb").read())
sx(f"cat > {work}.bench/task.json", inp=json.dumps(task).encode())

name = f"agent-{task_id}-{tag}".replace(".", "-")[:60]
subprocess.run(["docker", "rm", "-f", name], capture_output=True)
t0 = time.time()
p = subprocess.run([
    "docker", "run", "--rm", "--name", name, "--network", "n8n-agent-bench_jail",
    "--user", "1001", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
    "--memory", "2g", "--memory-swap", "2g", "--cpus", "4", "--pids-limit", "1024",
    "--mount", f"type=volume,src=n8n-agent-bench_work,dst={work},volume-subpath={rel}",
    "--mount", f"type=volume,src=n8n-agent-bench_work,dst=/bench,volume-subpath={rel}.bench",
    "-w", work, "n8n-agent-bench-sandbox",
    "python3", "/bench/agent.py", work, "/bench/task.json", "/bench/run.json", "--model", model,
    "--agents-md", amd, "--policy", "/bench/policy.json", "--run-id", f"{task_id}/{tag}",
], capture_output=True, timeout=3000)
if p.returncode != 0:
    print(f"{task_id} {tag}: agent crashed\n{(p.stdout + p.stderr).decode('utf-8', 'replace')[-1500:]}")
    sys.exit(1)
run = json.loads(sx(f"cat {work}.bench/run.json")[1])
run["isolation"] = {"container": "per-run", "mounts": [rel], "network": "jail (egress /llm only)",
                    "user": "1001", "caps": "none", "memory": "2g"}
json.dump(run, open(out, "w", encoding="utf-8"), indent=1)

subprocess.run([sys.executable, "harness/score.py", out, work], check=True)
sx(f"rm -rf {work} {work}.bench")
print(f"{task_id} {tag}: done in {round(time.time() - t0)}s")
