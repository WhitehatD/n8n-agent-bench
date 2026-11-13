"""Shared helpers for the harness (runs on the host, drives the containers)."""
import json, os, re, subprocess

os.environ["MSYS_NO_PATHCONV"] = "1"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def load_task(task_id):
    return next(t for t in json.load(open("tasks/tasks.json", encoding="utf-8")) if t["id"] == task_id)


def sx(cmd, inp=None, timeout=1800, service="sandbox"):
    p = subprocess.run(["docker", "compose", "exec", "-T", service, "sh", "-c", cmd], input=inp,
                       capture_output=True, timeout=timeout)
    return p.returncode, ANSI.sub("", (p.stdout + p.stderr).decode("utf-8", "replace"))


def run_held_out(task, work):
    """Write the merged PR's test files into `work` and run them. Returns (exit code, output)."""
    for f in task["test_files"]:
        blob = subprocess.check_output(["git", "-C", "cache/n8n.git", "show", f"{task['merge_sha']}:{f}"])
        sx(f"mkdir -p $(dirname {work}/{f}) && cat > {work}/{f}", inp=blob)
    pkg = task["package"]
    rel = " ".join(os.path.relpath(f, pkg).replace("\\", "/") for f in task["test_files"])
    runner = "vitest run" if sx(f"test -e {work}/{pkg}/node_modules/.bin/vitest")[0] == 0 else "jest"
    return sx(f"cd {work}/{pkg} && timeout 900 pnpm exec {runner} {rel} 2>&1")


def clone(src, dst):
    """Shell snippet: copy a prepared tree fast. Sources are copied for real; node_modules are
    hardlinked (shared, so the policy forbids writing under node_modules)."""
    return (f"rm -rf {dst} && mkdir -p {dst} && (cd {src} && tar -c --exclude=node_modules .) | tar -x -C {dst} && "
            f"(cd {src} && find . -name node_modules -type d -prune) | while read d; do "
            f"mkdir -p \"{dst}/$(dirname $d)\"; cp -al \"{src}/$d\" \"{dst}/$d\"; done && rm -f {dst}/.prepared")
