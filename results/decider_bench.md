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
