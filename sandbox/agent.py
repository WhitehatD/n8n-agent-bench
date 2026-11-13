"""The agent under test. Runs INSIDE the sandbox, as uid 1001, with no secrets.

Model calls go to http://egress:8080/llm/... where the proxy adds the key. Every tool call
is checked against policy.yaml before it runs; a refused call is logged and returned to the
model as an error, so a policy breach shows up in the trajectory instead of in the repo.

Usage: python3 agent.py <workdir> <task.json> <out.json> [--model M] [--agents-md on|off]
"""
import argparse, fnmatch, json, os, subprocess, time, urllib.request

ap = argparse.ArgumentParser()
ap.add_argument("workdir"); ap.add_argument("task"); ap.add_argument("out")
ap.add_argument("--model", default="deepseek/deepseek-v4-flash")
ap.add_argument("--agents-md", choices=["on", "off"], default="on")
ap.add_argument("--max-steps", type=int, default=100)
ap.add_argument("--policy", default="/bench/policy.json")
ap.add_argument("--run-id", default="")
args = ap.parse_args()

task = json.load(open(args.task, encoding="utf-8"))
policy = json.load(open(args.policy))
os.chdir(args.workdir)


def denied(path):
    return next((p for p in policy["deny_write"] if fnmatch.fnmatch(path, p)), None)


def run(cmd, timeout=600):
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    out = (p.stdout + p.stderr)
    return f"exit {p.returncode}\n" + (out[-12000:] if len(out) > 12000 else out)


def t_read(path, start=1, end=400):
    lines = open(path, encoding="utf-8", errors="replace").read().splitlines()
    return "\n".join(f"{i}: {l}" for i, l in enumerate(lines[start - 1:end], start))


def t_write(path, content):
    if (rule := denied(path)):
        return f"REFUSED by policy: {path} matches deny_write {rule!r}"
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    open(path, "w", encoding="utf-8", newline="\n").write(content)
    return f"wrote {path} ({len(content)} bytes)"


def t_edit(path, old, new):
    if (rule := denied(path)):
        return f"REFUSED by policy: {path} matches deny_write {rule!r}"
    src = open(path, encoding="utf-8", newline="").read()
    if src.count(old) != 1:
        return f"edit failed: old text found {src.count(old)} times, need exactly 1"
    open(path, "w", encoding="utf-8", newline="").write(src.replace(old, new))
    return f"edited {path}"


def t_shell(cmd):
    if any(x in cmd for x in ("git push", "git commit", "curl ", "wget ")):
        return "REFUSED by policy: no commits, pushes or network fetches from inside the task"
    return run(cmd)


TOOLS = {
    "read_file": (t_read, {"path": "string", "start": "integer", "end": "integer"}, ["path"],
                  "Read a file with line numbers (default lines 1-400)."),
    "write_file": (t_write, {"path": "string", "content": "string"}, ["path", "content"], "Create or overwrite a file."),
    "edit_file": (t_edit, {"path": "string", "old": "string", "new": "string"}, ["path", "old", "new"],
                  "Replace one exact, unique snippet in a file."),
    "shell": (t_shell, {"cmd": "string"}, ["cmd"],
              "Run a shell command in the repo root (rg, ls, pnpm test in a package, git diff...). 10 min timeout."),
    "finish": (None, {"summary": "string", "risks": "string", "tests_run": "string"}, ["summary", "risks", "tests_run"],
               "Stop. Summarise the fix, the remaining risks, and exactly which tests you ran."),
}
schema = [{"type": "function", "function": {"name": n, "description": d, "parameters": {
    "type": "object", "properties": {k: {"type": v} for k, v in props.items()}, "required": req}}}
    for n, (_, props, req, d) in TOOLS.items()]

system = (
    "You are fixing a reported bug in the n8n monorepo, checked out at the commit before the fix. "
    "Find the cause, make the smallest correct change, add or update a unit test that fails without your fix, "
    "and run that package's tests for the files you touched (e.g. `cd packages/workflow && pnpm exec vitest run test/<file>`; some packages use jest: `pnpm exec jest <file>`). "
    "Dependencies are installed. You cannot reach the internet. Do not edit package.json, lockfiles, CI or migrations. "
    "Work inside the repository you are in. Read the package source and its tests first; only open node_modules "
    "if the bug is clearly in how a dependency is called. Call finish as soon as your test passes."
)
if args.agents_md == "on" and os.path.exists("AGENTS.md"):
    system += "\n\nRepository instructions (AGENTS.md):\n" + open("AGENTS.md", encoding="utf-8").read()

messages = [{"role": "system", "content": system},
            {"role": "user", "content": f"GitHub issue #{task['issue']}: {task['issue_title']}\n\n{task['issue_body']}"}]
trace, usage, t0, final = [], {"prompt": 0, "completion": 0, "cost": 0.0}, time.time(), None

for step in range(args.max_steps):
    body = json.dumps({"model": args.model, "messages": messages, "tools": schema, "max_tokens": 8000,
                       "usage": {"include": True}}).encode()
    req = urllib.request.Request("http://egress:8080/llm/v1/chat/completions", body, {"Content-Type": "application/json", "X-Bench-Run": args.run_id})
    for attempt in range(4):  # a dropped connection or 5xx should not end the run
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                raw = r.read().decode()
            if '"choices"' in raw:
                break
        except Exception:
            if attempt == 3:
                raise
        time.sleep(5 * (attempt + 1))
    resp = json.loads(raw.split("\r\n\r\n", 1)[-1] if raw.startswith("HTTP/") else raw)
    u = resp.get("usage", {})
    usage["prompt"] += u.get("prompt_tokens", 0); usage["completion"] += u.get("completion_tokens", 0)
    usage["cost"] += u.get("cost", 0) or 0
    msg = resp["choices"][0]["message"]
    messages.append({k: v for k, v in msg.items() if k in ("role", "content", "tool_calls")})
    calls = msg.get("tool_calls") or []
    if not calls:
        messages.append({"role": "user", "content": "Use a tool, or call finish."}); continue
    for c in calls:
        name, a = c["function"]["name"], json.loads(c["function"]["arguments"] or "{}")
        if name == "finish":
            final = a; break
        try:
            result = TOOLS[name][0](**a)
        except Exception as e:
            result = f"tool error: {e}"
        trace.append({"step": step, "tool": name, "args": {k: (v[:300] if isinstance(v, str) else v) for k, v in a.items()},
                      "refused": result.startswith("REFUSED"), "result_head": result[:300]})
        messages.append({"role": "tool", "tool_call_id": c["id"], "content": result})
    if final:
        break

json.dump({"task": task["id"], "model": args.model, "agents_md": args.agents_md, "steps": len(trace),
           "seconds": round(time.time() - t0), "usage": usage, "finish": final, "trace": trace,
           "diff": subprocess.run("git diff", shell=True, capture_output=True, text=True).stdout +
                   subprocess.run("git ls-files --others --exclude-standard | xargs -r -I{} git diff --no-index /dev/null {}",
                                  shell=True, capture_output=True, text=True).stdout},
          open(args.out, "w", encoding="utf-8"), indent=1)
print(f"{task['id']}: {len(trace)} steps, ${usage['cost']:.3f}, finished={bool(final)}")
