"""Live probe: which decision model best answers the policy gate on real n8n diffs.

Labels are hand-set from reading each merged diff (2026-11-12). Gate question: does the
change touch authentication, credentials, secrets or their redaction, so a human must review?
"""
import json, os, subprocess, sys, time, urllib.request

KEY = os.environ["OPENROUTER_API_KEY"]
MIRROR = "cache/n8n.git"
MODELS = sys.argv[1:] or [
    "typesafe/jev-1.14", "google/gemini-decision-1", "openai/gpt-6-luna-decisions",
    "perplexity/pplx-decider-v1.3:free", "perplexity/pplx-decider-flash-v1.3:free",
    "cloudflare/clef-flash", "morph/reflex", "liquid/d1.1", "microsoft/microsoft-decision-1",
]
# PR -> needs human review under the policy (True = auth/credentials/secrets)
LABELS = {42475: True, 43061: True, 42473: True, 41249: True, 40779: True, 43319: True,
          43252: False, 43517: False, 43518: False, 41570: False, 43286: False, 42081: False}
tasks = {t["pr"]: t for t in json.load(open("tasks/tasks.json", encoding="utf-8"))}


def diff_for(pr):
    if pr in tasks:
        t = tasks[pr]; a, b = t["base_sha"], t["merge_sha"]
    else:
        sha = json.loads(subprocess.check_output(["gh", "pr", "view", str(pr), "-R", "n8n-io/n8n", "--json", "mergeCommit"]))["mergeCommit"]["oid"]
        a, b = sha + "^", sha
    d = subprocess.check_output(["git", "-C", MIRROR, "diff", a, b, "--", ".", ":(exclude)*.test.*", ":(exclude)*.spec.*"], encoding="utf-8", errors="replace")
    return d[:12000]


QUESTIONS = {
    "needs_human": {"type": "noul",
        "instructions": "Does this code change touch authentication, credentials, OAuth scopes or tokens, secrets, encryption keys, or the redaction of sensitive headers, so that under the repository policy a human must review it before merge?",
        "criteria": {"true": "The diff changes how credentials, tokens, auth headers, scopes, secrets or keys are read, sent, stored, validated or redacted.",
                     "false": "The diff changes only other behaviour, such as formatting, search filters, data handling or error messages, with no auth or secret handling."}},
    "area": {"type": "choice", "instructions": "Which policy area does this change belong to?",
        "criteria": {"auth_credentials": "Authentication, credentials, tokens, scopes, secrets, redaction.",
                     "data_migrations": "Database schema or data migrations.",
                     "ci_build": "CI, build or release tooling.",
                     "ordinary": "Ordinary product code with none of the above."}},
}


def ask(model, state):
    body = json.dumps({"model": model, "state": state, "questions": QUESTIONS}).encode()
    req = urllib.request.Request("https://openrouter.ai/api/alpha/decisions", body,
        {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json", "X-Title": "n8n-agent-bench"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=60) as r:
        out = json.load(r)
    return out, time.time() - t0


diffs = {pr: diff_for(pr) for pr in LABELS}
rows = []
for m in MODELS:
    ok = brier = cost = 0.0; lat = []; err = None
    for pr, label in LABELS.items():
        try:
            out, dt = ask(m, diffs[pr])
            a = out["answers"]["needs_human"]; p = a.get("noul", a.get("probability"))
            ok += (p >= 0.5) == label; brier += (p - label) ** 2
            cost += out.get("usage", {}).get("cost", 0) or 0; lat.append(dt)
        except Exception as e:
            err = str(e)[:80]; break
    n = len(lat)
    rows.append((m, ok, n, brier / max(n, 1), cost, sorted(lat)[n // 2] if n else 0, err))
    print(f"{m:<42} acc {int(ok)}/{n}  brier {brier/max(n,1):.3f}  cost ${cost:.5f}  p50 {rows[-1][5]:.2f}s  {err or ''}", flush=True)

json.dump([dict(zip(["model", "correct", "n", "brier", "cost_usd", "p50_s", "error"], r)) for r in rows],
          open("results/probe_deciders.json", "w"), indent=2)
