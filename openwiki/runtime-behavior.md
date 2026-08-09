---
type: runtime
title: Runtime Behavior — LangSmith Evidence for This Repository
description: "Consolidated production telemetry from the LangSmith connector pull: one error trace from the OpenWiki CLI agent (model-name typo 400), middleware timing, sample-bias caveats, and what it means for agents working here."
tags: [runtime, telemetry, langsmith, findings]
---

# Runtime Behavior — LangSmith Evidence

> Scope of this page: the runtime complement to the static code docs — what actually runs and what it costs, as observed in the LangSmith sample. This is a **runtime snapshot for working in this repo**, not a performance report, and it recurs as an offline loop over a fresh sample each run. Read the registers below accordingly; never treat the sample as fleet statistics.

## Sample provenance and bias

- Connector config: `/openwiki/.langsmith.json` → workspace key env `OPENWIKI_LANGSMITH_API_KEY`, project **`openwiki`**. Raw dump: `2026-08-09T11-34-52-951Z/langsmith-results.json` (fetched `2026-08-09T11:34:56.585Z`).
- Project `openwiki` is the **OpenWiki CLI's own agent** (the tool that generates this wiki), not the Index RAG backend agent. The error stack frames point into the globally installed npm package (`.../npm/node_modules/openwiki/node_modules/langchain/...`).
- Sample: **1 trace**, buckets `error: 1, baseline: 0, outlier: 0`; `baselineMedianLatencyMs: null`, `baselineMedianTokens: null`. Bucket counts are the composition of a deliberately anomaly-weighted sample — **not** fleet error/latency rates. With no baseline traces, no "normal operation" median exists for this pull.
<!-- openwiki: broken internal link [config.md] file "config.md" does not exist. Fix the href or restore the target, then delete this comment. -->
- Nothing in this sample originates from Index RAG's own runtime (its observability is Langfuse — see [backend config](config.md)); the LangSmith project traces the OpenWiki tool itself, which operates on this repository.

## The one trace — error bucket

**Trace `019fe473-6da8-75da-ac64-dc4cfa59e5b6`** (root run `LangGraph`, `status: error`, `2026-08-09T02:56:37.800Z → 02:56:38.058Z`, latency 258 ms, 0 tokens).

Run shape (observed, all under the root):

| Run | Latency | Status |
|---|---|---|
| `__start__` | 2 ms | success |
| `SkillsMiddleware.before_agent` | 43 ms | success |
| `FilesystemMiddleware.before_agent` | 1 ms | success |
| `patchToolCallsMiddleware.before_agent` | 1 ms | success |
| `OpenWikiIndexMiddleware.before_agent` | 3 ms | success |
| `model_request` | 174 ms | **error** |
| `ChatOpenAI` | 163 ms | **error** |

**Error signature (Observed):** the DeepSeek-compatible API rejected the request before any token was generated:

```
400 The supported API model names are deepseek-v4-pro or deepseek-v4-flash, but you passed deepseek-v4-flas.
```

The failed model name is `deepseek-v4-flas` — a truncated typo of `deepseek-v4-flash`.

**Correlated (code in this repo):** the scheduled workflow `.github/workflows/openwiki-update.yml` pins `OPENWIKI_MODEL_ID: z-ai/glm-5.2` via `OPENWIKI_PROVIDER: openrouter` and itself traces to LangSmith under `LANGCHAIN_PROJECT: openwiki`. The failing model name therefore comes from a **local OpenWiki CLI configuration outside this repository** (a DeepSeek-compatible endpoint), not from the repo's workflow. No file in this repo contains `deepseek-v4-flas`; the repo's own model config uses `deepseek-v4-flash` (`model_config.yaml`).

## Runtime findings and opportunities (ranked)

1. **Model-id typos fail fast and silently cost nothing but produce a hard 400 (error bucket).**
   Evidence: the sole trace died in 258 ms at the first model call with a 400 naming error; 0 tokens billed.
   Code that produces this class of behavior: the OpenWiki CLI's model resolution (npm package, outside this repo); for the repo's own runtime, the analogous surface is `backend/core/models/llm_settings.py` + `model_config.yaml` (`deepseek.model`) and `model_factory.get_active_llm()`.
   *So what for an agent:* when an OpenWiki run fails immediately with `400 ... but you passed <model>`, check the local CLI model config for a typo before touching repo code. When the repo's own chat returns a 400 from the provider, the first place to look is `model_config.yaml` (or the `model` tab in settings), which is hot-reloaded per graph build.

2. **Pre-model middleware cost is dominated by one middleware (run-shape quantification).**
   Evidence: of the 48 ms spent in the four `before_agent` middlewares, `SkillsMiddleware.before_agent` consumed 43 ms (≈ 89%); the three others took 1–3 ms total. This is the OpenWiki CLI's chain (its source is not in this repo), so nothing here is actionable in Index RAG code — but it quantifies that the wiki tool has a small fixed pre-model overhead per run.
   *So what for an agent:* do not treat the ~50 ms pre-model overhead as a bug in this repo; if the scheduled wiki refresh ever shows runaway run time, the skill-loading step is the first place to look on the CLI side.

3. **No baseline or outlier data this pull — latency and token envelopes are unknown.**
   Evidence: `baseline: 0`, `outlier: 0`, no baseline medians; the error trace consumed 0 tokens and made no tool calls (the model call failed before tool selection, so the run contains no `tool` runs at all).
   *So what for an agent:* per-tool runtime usage, retry/fallback frequency, and turn counts for the Index RAG agent cannot be derived from this sample. The repo's own agents are traced to Langfuse, not LangSmith — inspect Langfuse for that runtime data. Do not infer tool-choice guidance from this dump.

4. **No evidence of the repo's retry/fallback paths firing (or not firing).**
   Evidence: the sample contains a single `ChatOpenAI` run; the LangChain `pRetry` frame appears in the error stack but the dump records no repeated runs. The Index RAG agent's own retry/fallback machinery (`dynamic_model_switcher` in `backend/core/custom_middleware/model_switcher.py`: `MAX_RETRIES_PER_MODEL = 2`, `FALLBACK_CHAIN = [deepseek, ali, ollama]`) is not observable in this sample.
   *So what for an agent:* keep code-reading as the source of truth for fallback semantics; there is no production data yet to say how often fallback triggers.

## Cost / latency note (this pull's numbers — volatile, refresh each pull)

- Total trace latency: **258 ms**; model call: **163 ms** (of which the request was rejected); all pre-model middleware: **~48 ms**.
- Tokens: **0** (request rejected before generation).
- These are single-trace numbers from a deliberately biased sample; do not compare across pulls as if they were medians.

## Registers

- **Observed** — everything in the trace table, the 400 error text, run latencies, token counts, bucket counts.
- **Correlated** — the workflow's `OPENWIKI_MODEL_ID`/`OPENWIKI_PROVIDER`/`LANGCHAIN_PROJECT` settings; the repo's own `deepseek-v4-flash` model name; the statement that no repo file contains the typo'd string.
- **Hypothesis** — none this pull: the sample is too small to propose a code change. A future hypothesis to test when baselines appear: whether the repo's `dynamic_model_switcher` fallback chain ever triggers in production (its FALLBACK_CHAIN ordering deepseek → ali → ollama has never been observed firing).

## Weaving into the rest of the wiki

<!-- openwiki: broken internal link [tools.md] file "tools.md" does not exist. Fix the href or restore the target, then delete this comment. -->
- [Tools](tools.md) — no tool invocation observed in the current sample (see the "runtime usage" note there).
<!-- openwiki: broken internal link [agent-core.md] file "agent-core.md" does not exist. Fix the href or restore the target, then delete this comment. -->
- [Agent core](agent-core.md) — no completed agent turns in the current sample; turn count/latency claims stay code-derived until baselines arrive.

## Related pages

- [Operations](operations.md) — where telemetry is configured and read
<!-- openwiki: broken internal link [config.md] file "config.md" does not exist. Fix the href or restore the target, then delete this comment. -->
- [Backend config](config.md) — Langfuse vs LangSmith split
<!-- openwiki: broken internal link [overview.md] file "overview.md" does not exist. Fix the href or restore the target, then delete this comment. -->
- [Backend overview](overview.md) — the repo runtime that Langfuse traces
