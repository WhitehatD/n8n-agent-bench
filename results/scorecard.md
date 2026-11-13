**16/38 runs pass n8n's own maintainer tests** (10/19 tasks solved at least once). Model: `deepseek/deepseek-v4-flash`. Total spend $3.31; $0.061 per passing fix.

- AGENTS.md **on**: 7/19 pass
- AGENTS.md **off**: 9/19 pass
- Policy: 0 deny-list writes, 0 refused tool calls, 7 runs flagged for human review

| Task | Issue | Package | AGENTS.md on | AGENTS.md off | Needs human |
|---|---|---|---|---|---|
| [n8n-41021](https://github.com/n8n-io/n8n/pull/41021) | [#40984](https://github.com/n8n-io/n8n/issues/40984) Gemini Node error with tool calls | `@n8n/nodes-langchain` | ✅ $0.026 | ❌ $0.009 |  |
| [n8n-41061](https://github.com/n8n-io/n8n/pull/41061) | [#41029](https://github.com/n8n-io/n8n/issues/41029) Corrupted decrypted content in asymmetric mode from the cryp | `nodes-base` | ❌ $0.051 | ❌ $0.073 |  |
| [n8n-41064](https://github.com/n8n-io/n8n/pull/41064) | [#36363](https://github.com/n8n-io/n8n/issues/36363) Webhook "Ignore Bots" rejection returns misleading "Authoriz | `nodes-base` | ✅ $0.216 | ✅ $0.046 |  |
| [n8n-41116](https://github.com/n8n-io/n8n/pull/41116) | [#36470](https://github.com/n8n-io/n8n/issues/36470) [Bug]: Google Gemini node silently routes Gemma models (e.g. | `@n8n/nodes-langchain` | ❌ $0.554 | ❌ $0.069 |  |
| [n8n-41570](https://github.com/n8n-io/n8n/pull/41570) | [#36174](https://github.com/n8n-io/n8n/issues/36174) Code node console.log(null) floods 'Cannot read properties o | `core` | ❌ $0.031 | ✅ $0.008 |  |
| [n8n-41838](https://github.com/n8n-io/n8n/pull/41838) | [#35309](https://github.com/n8n-io/n8n/issues/35309) n8n node GET A WORKFLOW on localhost install FAILS when curl | `nodes-base` | ❌ $0.121 | ❌ $0.146 | ⚠️ |
| [n8n-42081](https://github.com/n8n-io/n8n/pull/42081) | [#42077](https://github.com/n8n-io/n8n/issues/42077) Static data written in a webhook trigger's webhook() is not  | `cli` | ✅ $0.137 | ✅ $0.128 |  |
| [n8n-42436](https://github.com/n8n-io/n8n/pull/42436) | [#42394](https://github.com/n8n-io/n8n/issues/42394) Native Agent token counting blocks the main process during m | `@n8n/agents` | ❌ $0.078 | ❌ $0.136 |  |
| [n8n-42473](https://github.com/n8n-io/n8n/pull/42473) | [#35547](https://github.com/n8n-io/n8n/issues/35547) Notion predefined credentials override `Notion-Version` and  | `nodes-base` | ✅ $0.104 | ✅ $0.054 | ⚠️ |
| [n8n-42475](https://github.com/n8n-io/n8n/pull/42475) | [#35545](https://github.com/n8n-io/n8n/issues/35545) **Google Service Account with Domain-Wide Delegation fails w | `nodes-base` | ❌ $0.080 | ❌ $0.035 | ⚠️ |
| [n8n-42569](https://github.com/n8n-io/n8n/pull/42569) | [#42554](https://github.com/n8n-io/n8n/issues/42554) Agents: mixed-whitespace tool errors still block token count | `@n8n/agents` | ❌ $0.050 | ❌ $0.000 |  |
| [n8n-43033](https://github.com/n8n-io/n8n/pull/43033) | [#43017](https://github.com/n8n-io/n8n/issues/43017) RabbitMQ node: queue bindings aren't awaited before the chan | `nodes-base` | ✅ $0.006 | ✅ $0.003 |  |
| [n8n-43061](https://github.com/n8n-io/n8n/pull/43061) | [#43059](https://github.com/n8n-io/n8n/issues/43059) redactedHeaders() misses consumed auth headers when the name | `workflow` | ✅ $0.004 | ✅ $0.019 | ⚠️ |
| [n8n-43142](https://github.com/n8n-io/n8n/pull/43142) | [#43136](https://github.com/n8n-io/n8n/issues/43136) Native Agent workflow tools wait ~60s on workers: missing ch | `cli` | ❌ $0.170 | ✅ $0.021 |  |
| [n8n-43252](https://github.com/n8n-io/n8n/pull/43252) | [#43173](https://github.com/n8n-io/n8n/issues/43173) AI Agent output adding \n newline characters when using Mist | `@n8n/nodes-langchain` | ❌ $0.203 | ❌ $0.186 |  |
| [n8n-43286](https://github.com/n8n-io/n8n/pull/43286) | [#43283](https://github.com/n8n-io/n8n/issues/43283) nodeNameToToolName returns an empty tool name after truncati | `workflow` | ❌ $0.007 | ✅ $0.007 |  |
| [n8n-43306](https://github.com/n8n-io/n8n/pull/43306) | [#43289](https://github.com/n8n-io/n8n/issues/43289) Native Agent mid-run observer sees live offloaded tool resul | `@n8n/agents` | ❌ $0.058 | ❌ $0.179 |  |
| [n8n-43517](https://github.com/n8n-io/n8n/pull/43517) | [#43576](https://github.com/n8n-io/n8n/issues/43576) Weaviate Vector Store: hybrid search ignores the search filt | `@n8n/nodes-langchain` | ✅ $0.187 | ✅ $0.012 |  |
| [n8n-43518](https://github.com/n8n-io/n8n/pull/43518) | [#43577](https://github.com/n8n-io/n8n/issues/43577) Weaviate Vector Store: Clear Data keeps only the last insert | `@n8n/nodes-langchain` | ❌ $0.043 | ❌ $0.046 |  |

Excluded: n8n-43353, held-out test is a cli integration test that needs a database.

### Decision models on the same runs

Decision models on 37 agent runs / 19 tasks. Majority-class baseline: verifier 0.568, triage 0.526.

| Model | Verifier acc | Brier | rejects failing PRs | wrongly rejects passing | Triage acc | Brier | cost | p50 |
|---|---|---|---|---|---|---|---|---|
| openai/gpt-6-luna-decisions | 0.722 | 0.225 | 0.5 | 0.0 | 0.737 | 0.166 | $0.0091 | 0.27s |
| upstage/solar-decide | 0.703 | 0.283 | 0.476 | 0.0 | 0.684 | 0.221 | $0.0062 | 0.86s |
| baseten/mammoth-1 | 0.649 | 0.234 | 0.381 | 0.0 | 0.789 | 0.146 | $0.0097 | 0.38s |
| perplexity/pplx-decider-v1.2 | 0.622 | 0.264 | 0.333 | 0.0 | 0.737 | 0.163 | $0.0019 | 0.42s |
| perplexity/pplx-decider-flash-v1.2 | 0.622 | 0.292 | 0.333 | 0.0 | 0.526 | 0.233 | $0.0010 | 0.28s |
| perplexity/pplx-decider-v1.3:free | 0.622 | 0.298 | 0.333 | 0.0 | 0.789 | 0.164 | $0.0000 | 0.51s |
| cloudflare/clef | 0.622 | 0.247 | 0.333 | 0.0 | 0.684 | 0.171 | $0.0213 | 0.64s |
| liquid/d1-ultra | 0.622 | 0.204 | 0.333 | 0.0 | 0.684 | 0.168 | $0.0039 | 0.39s |
| microsoft/microsoft-decision-1 | 0.622 | 0.231 | 0.429 | 0.125 | 0.737 | 0.154 | $0.0044 | 0.43s |
| nace-ai/drex-max | 0.622 | 0.273 | 0.333 | 0.0 | 0.737 | 0.179 | $0.0058 | 0.42s |
| morph/reflex | 0.595 | 0.354 | 0.286 | 0.0 | 0.842 | 0.14 | $0.0012 | 0.45s |
| google/gemini-decision-1 | 0.595 | 0.305 | 0.286 | 0.0 | 0.684 | 0.174 | $0.0104 | 0.37s |
| liquid/d1.1 | 0.568 | 0.28 | 0.238 | 0.0 | 0.737 | 0.165 | $0.0019 | 0.43s |
| typesafe/jev-1.14 | 0.541 | 0.31 | 0.19 | 0.0 | 0.789 | 0.167 | $0.0047 | 0.3s |
| baseten/joey-1 | 0.541 | 0.264 | 0.19 | 0.0 | 0.579 | 0.218 | $0.0010 | 0.33s |
| cloudflare/clef-flash | 0.514 | 0.292 | 0.143 | 0.0 | 0.737 | 0.198 | $0.0024 | 0.42s |
| scaledown/classify-1 | 0.486 | 0.286 | 0.143 | 0.062 | 0.579 | 0.252 | $0.0040 | 0.45s |

