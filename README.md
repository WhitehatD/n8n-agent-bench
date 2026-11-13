# n8n-agent-bench

A benchmark of coding agents on **n8n's own merged bug fixes**, run in a sandbox with an explicit
safety model, scored with **n8n's own maintainer tests**, and producing a PR evidence block per run.

## How a task works

1. **Pick a real fix.** 20 PRs merged into `n8n-io/n8n` between 2026-10-12 and 2026-11-12, each
   closing a public GitHub issue, touching one package, with unit tests
   ([`tasks/tasks.json`](tasks/tasks.json), built by [`harness/build_tasks.py`](harness/build_tasks.py)).
2. **Rewind.** Check out the parent of the merge commit. Install and build that package's
   workspace dependencies.
3. **Control.** Copy the merged PR's test files in and run them on the untouched code. They must
   fail, or the task proves nothing. One task (43353) was excluded here: its test needs a database.
4. **Run the agent.** The agent sees only the issue text. It does not see the fix or the tests.
5. **Score.** Copy the merged PR's tests over the agent's change and run them. Pass means the
   agent's fix satisfies the same checks n8n's maintainers wrote.
6. **Evidence.** Render a PR body ([`harness/evidence.py`](harness/evidence.py)): diff, the tests
   the agent ran, the held-out result, the egress log for that run, policy hits, and where a
   reviewer should look.

## Sandbox and safety model

| Layer | What it enforces |
|---|---|
| **One container per agent run** | Mounts only its own copy of the repo (a volume subpath). It cannot see other tasks, the base trees or the harness. uid 1001, all capabilities dropped, `no-new-privileges`, 2 GB memory and 1024-pid caps. |
| **No route to the internet** | The run sits on an `internal` Docker network. The only reachable host is the egress proxy. |
| **Egress proxy** ([`egress/proxy.py`](egress/proxy.py)) | Agent containers may make **no** outbound connections. Their only call is `POST /llm`, which the proxy forwards to the model API **adding the API key itself**: the agent never holds a secret. A separate installer container may reach the npm registry and nothing else. Every decision, allowed or refused, is logged to `egress.jsonl` with the run id. |
| **Write policy** ([`policy/policy.yaml`](policy/policy.yaml)) | Writes to CI, lockfiles, `package.json`, migrations, `.env` and `node_modules` are refused at the tool layer and logged. No commits, pushes or network fetches from inside a task. |
| **Human-review gate** | Paths (auth, SSO, licence, credentials, DB) plus a **decision model** asked of every diff: "does this touch authentication, credentials, tokens, secrets or redaction?" p ≥ 0.5 marks the PR needs-human. |

Prompting is not part of the safety model. Everything above is enforced by the harness, the
container runtime or the proxy, so a prompt-injected issue cannot talk its way past it.

## Results

See [`results/scorecard.md`](results/scorecard.md) for the full table. Summary:

| | |
|---|---|
| Tasks | 19 (one excluded at control) × 2 arms = 38 runs |
| Agent | `deepseek/deepseek-v4-flash`, one attempt per run, max 100 tool calls |
| **Runs passing n8n's maintainer tests** | **16 / 38 (42%)** |
| Tasks solved at least once | 10 / 19 |
| AGENTS.md on / off | 7 / 19 vs 9 / 19 |
| Spend | $3.31 for all 38 runs, **$0.061 per passing fix** |
| Policy | 0 deny-list writes, 0 refused tool calls, 0 outbound connections from any agent container |
| Flagged needs-human | 7 runs, all in auth or credential-header code |

Pass rate by package:

| Package | Pass |
|---|---|
| `workflow` | 3 / 4 |
| `cli` | 3 / 4 |
| `core` | 1 / 2 |
| `nodes-base` | 6 / 12 |
| `@n8n/nodes-langchain` | 3 / 10 |
| `@n8n/agents` | **0 / 6** |

### What the results say

- **Where a cheap agent is already useful, and where it is not.** Fixes local to one node or
  utility (header casing, queue bindings, webhook static data, tool-name truncation, bot-detection
  messages) pass. Agent-runtime internals (token counting, offloaded tool results, streamed tool
  calls) failed every time.
- **AGENTS.md did not help this agent.** With n8n's 24 KB root `AGENTS.md` in context the agent
  passed 7 of 19; without it, 9 of 19. One run per arm, so this is within noise, but there is no
  sign of a benefit for a small model, and a plausible cost: the instructions are written for
  frontier agents and take a large share of a small model's attention. Worth measuring with the
  models n8n actually runs, and with the package-level AGENTS.md files instead of the root one.
- **Decision models can take work off reviewers.** Every run has a ground truth, so the same data
  scores three bounded decisions. [`harness/decider_bench.py`](harness/decider_bench.py) asks 17
  decision models on OpenRouter (full table in the scorecard). As a **verifier** ("will the
  maintainer tests pass on this diff?", majority baseline 57%):

  | Model | Accuracy | Failing PRs rejected | Passing PRs wrongly rejected |
  |---|---|---|---|
  | `openai/gpt-6-luna-decisions` | 72% | 50% | 0% |
  | `upstage/solar-decide` | 70% | 48% | 0% |
  | `google/gemini-decision-1` (released 2026-11-11) | 59% | 29% | 0% |
  | `morph/reflex` | 59% | 29% | 0% |
  | `typesafe/jev-1.14` | 54% | 19% | 0% |

  One call costing a fraction of a cent would have sent half of the failing agent PRs back before
  a human opened them, without blocking any passing one. The ranking changes per decision: Reflex
  was the best **gate** (12/12 on auth-or-not, Brier 0.002) and one of the weakest verifiers. The
  model has to be chosen per decision, on your own runs.

## Evidence PRs

Every run is a PR on the fork [WhitehatD/n8n](https://github.com/WhitehatD/n8n/pulls) (base =
the parent of the merged fix, head = the agent's change), with the evidence block as its
description. Index: [`results/prs.json`](results/prs.json). Good ones to start with:

- [n8n-43061, AGENTS.md on](https://github.com/WhitehatD/n8n/pull/1): auth header casing, pass, flagged for human review
- [n8n-43033, AGENTS.md on](https://github.com/WhitehatD/n8n/pull/24): RabbitMQ queue bindings, pass
- [n8n-43142, AGENTS.md off](https://github.com/WhitehatD/n8n/pull/26): child job waits on workers, pass, 188-line fix
- [n8n-41570, AGENTS.md on](https://github.com/WhitehatD/n8n/pull/11): Code node console output, fail, with the same bug passing in the AGENTS.md-off run
- [n8n-42436, AGENTS.md on](https://github.com/WhitehatD/n8n/pull/17): agent token counting, fail

## Limits

- One cheap model (`deepseek/deepseek-v4-flash`), one run per arm: the numbers are a measurement
  of this setup, not a ranking of models. Run-to-run variance is not measured yet.
- Held-out tests are unit tests only. CI, lint and type checks are not run, so "pass" is necessary
  but not sufficient for merge.
- Reviewer acceptance and rework rate need real reviewers; they are not measured here.

## Run it

```bash
docker compose up -d --build          # OPENROUTER_ENV=path/to/.env with OPENROUTER_API_KEY
python harness/run_all.py --models deepseek/deepseek-v4-flash --arms on off -j 4
python harness/decider_bench.py
python harness/scorecard.py
python harness/status.py              # live progress
```

Built by [Alexandru Cioc](https://ciocandco.com) in November 2026.
