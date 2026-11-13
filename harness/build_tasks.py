"""Build tasks/tasks.json from merged n8n PRs that close a public GitHub issue.

Each task is replayed from the parent of the squash-merge commit. The agent gets the
issue text only. The PR's test changes are held out and used to score the run.
"""
import json, re, subprocess, sys

REPO = "n8n-io/n8n"
# PR -> the public issue it closes (picked 2026-11-12, see README "Task selection")
PAIRS = {
    42569: 42554, 43306: 43289, 42436: 42394, 43517: 43576, 41116: 36470,
    43252: 43173, 43518: 43577, 41021: 40984, 43142: 43136, 43353: 36386,
    42081: 42077, 41570: 36174, 41838: 35309, 41064: 36363, 43033: 43017,
    42473: 35547, 42475: 35545, 41061: 41029, 43061: 43059, 43286: 43283,
}
TEST_RE = re.compile(r"(\.test\.|\.spec\.|__tests__/)")


def gh(*args):
    return json.loads(subprocess.check_output(["gh", *args], encoding="utf-8"))


def package_of(path):
    parts = path.split("/")
    return "/".join(parts[:3]) if parts[1].startswith("@") or parts[1] == "frontend" else "/".join(parts[:2])


tasks = []
for pr, issue in PAIRS.items():
    p = gh("pr", "view", str(pr), "-R", REPO, "--json", "number,title,mergedAt,mergeCommit,files,url")
    i = gh("issue", "view", str(issue), "-R", REPO, "--json", "number,title,body,author,url")
    merge = p["mergeCommit"]["oid"]
    commit = gh("api", f"repos/{REPO}/commits/{merge}")
    files = [f["path"] for f in p["files"]]
    tests = [f for f in files if TEST_RE.search(f)]
    tasks.append({
        "id": f"n8n-{pr}",
        "pr": pr, "pr_url": p["url"], "pr_title": p["title"], "merged_at": p["mergedAt"],
        "merge_sha": merge, "base_sha": commit["parents"][0]["sha"],
        "issue": issue, "issue_url": i["url"], "issue_author": i["author"]["login"],
        "issue_title": i["title"], "issue_body": i["body"],
        "package": package_of(files[0]),
        "gold_src_files": [f for f in files if f not in tests],
        "test_files": tests,
        "gold_additions": sum(f["additions"] for f in p["files"]),
        "gold_deletions": sum(f["deletions"] for f in p["files"]),
    })
    print(pr, tasks[-1]["package"], tasks[-1]["base_sha"][:9], file=sys.stderr)

tasks.sort(key=lambda t: t["merged_at"])
json.dump(tasks, open("tasks/tasks.json", "w", encoding="utf-8", newline="\n"), indent=2, ensure_ascii=False)
print(len(tasks), "tasks", file=sys.stderr)
